"""Names, SIDs and privileges, over lsarpc.

A security descriptor is a list of SIDs. An administrator thinks in names. This
module is the translation between the two, and it is the backend of the object
picker in the permission editor.

It runs against the **file server**, not against a domain controller, and that
is the point: a member server resolves both its own local accounts and the
domain's through the same interface, in the same call, with the same answer the
server itself would use when deciding access. Asking a DC instead would give a
different answer for exactly the cases that matter — a local group, a
well-known SID, an account from a trusted domain the server cannot see.

Names are accepted the way people write them: ``alice``, ``EXAMPLE\\alice``,
``alice@example.lan``. LSA takes all three.
"""

from __future__ import annotations

import logging
from typing import Any

from samfscon.core.errors import InvalidRequest, NotFound, SamfsconError, translate
from samfscon.srv.connection import ServerConnection

logger = logging.getLogger(__name__)

# LSA policy access rights (MS-LSAD 2.2.1.1), the two this module needs.
LSA_POLICY_VIEW_LOCAL_INFORMATION = 0x00000001
LSA_POLICY_LOOKUP_NAMES = 0x00000800

# SID types (MS-LSAT 2.2.13), named because the numbers appear in the answers
# and an interface that shows "type 1" helps nobody.
SID_TYPE_NAMES = {
    1: "user",
    2: "group",
    3: "domain",
    4: "alias",
    5: "well_known_group",
    6: "deleted",
    7: "invalid",
    8: "unknown",
    9: "computer",
}

# What a permission editor offers before anyone types anything. These exist on
# every SMB server, need no lookup, and are the trustees most ACEs actually
# name — which is why they are listed rather than left to be discovered.
WELL_KNOWN = (
    ("S-1-1-0", "Everyone", "well_known_group"),
    ("S-1-5-11", "Authenticated Users", "well_known_group"),
    ("S-1-3-0", "Creator Owner", "well_known_group"),
    ("S-1-3-1", "Creator Group", "well_known_group"),
    ("S-1-5-32-544", "Administrators", "alias"),
    ("S-1-5-32-545", "Users", "alias"),
    ("S-1-5-32-546", "Guests", "alias"),
    ("S-1-5-18", "SYSTEM", "well_known_group"),
)


def current_account(conn: ServerConnection) -> dict[str, Any]:
    """Who the server thinks is signed in.

    ``GetUserName`` answers from the session's own token, so it reports the
    account as the *server* resolved it — which is not always what was typed. A
    Kerberos principal maps to a domain account, a standalone login to a local
    one, and a name the server canonicalised differently is worth seeing.

    Group membership is reported for **local** groups only, and the field says
    so. A member server's domain groups come from the ticket and are not
    enumerable over lsarpc without asking the domain, which is SAMADCON's job
    and not this one. The local aliases are what decides the privileges this
    console cares about, so they are the ones worth having.
    """
    pipe = conn.lsa
    account: dict[str, Any] = {
        "name": None,
        "authority": None,
        "sid": None,
        "type": None,
        "groups": [],
        "groups_are_local_only": True,
    }

    try:
        result = _attempt(
            lambda: pipe.GetUserName(None, None, None),
            lambda: pipe.GetUserName(None, None),
        )
    except SamfsconError:
        logger.info("the server would not report the session's account name")
        return account

    name, authority = _unpack_user_name(result)

    if not name:
        # The server would not say. We know anyway: this connection was opened
        # by somebody, and the account domain came from the probe. Falling back
        # to that is the difference between a capability report that explains
        # itself and one that says "could not be determined".
        name = getattr(conn, "principal", None)
        authority = conn.target.netbios_name or conn.target.workgroup
        if name:
            account["from_session"] = True

    account["name"] = name
    account["authority"] = authority

    if not name:
        return account

    qualified = f"{authority}\\{name}" if authority else name
    try:
        resolved = lookup_names(conn, [qualified])
    except SamfsconError:
        return account

    if resolved:
        account["sid"] = resolved[0].get("sid")
        account["type"] = resolved[0].get("type")

    if account["sid"]:
        account["groups"] = _local_groups(conn, account["sid"])
    return account


def lookup_names(conn: ServerConnection, names: list[str]) -> list[dict[str, Any]]:
    """Resolve names to SIDs.

    Every input gets an entry in the answer, in order, including the ones that
    did not resolve — a picker that silently drops what it could not find sends
    the user looking for a typo in the wrong field.
    """
    wanted = [name.strip() for name in names if name and name.strip()]
    if not wanted:
        return []

    from samba.dcerpc import lsa

    pipe = conn.lsa
    handle = _policy_handle(conn, LSA_POLICY_LOOKUP_NAMES | LSA_POLICY_VIEW_LOCAL_INFORMATION)

    lsa_names = []
    for name in wanted:
        entry = lsa.String()
        entry.string = name
        lsa_names.append(entry)

    sids = lsa.TransSidArray2()
    domains = None
    count = 0

    try:
        result = _attempt(
            lambda: pipe.LookupNames3(handle, lsa_names, domains, sids, 1, count, 0, 0),
            lambda: pipe.LookupNames2(handle, 0, lsa_names, domains, sids, 1, count, 0, 0),
            lambda: pipe.LookupNames(handle, lsa_names, domains, sids, 1, count),
        )
    except SamfsconError as exc:
        # NT_STATUS_NONE_MAPPED means nothing resolved, which is an answer
        # rather than a failure: the picker shows every name as unresolved.
        if exc.code == "sid_not_resolved":
            return [_unresolved(name) for name in wanted]
        raise

    return _merge_lookup(wanted, result)


def lookup_sids(conn: ServerConnection, sids: list[str]) -> list[dict[str, Any]]:
    """Resolve SIDs to names, for rendering an ACL.

    A SID that resolves to nothing keeps its string form and is marked
    unresolved. That is not an error either — an ACE naming an account that has
    since been deleted is exactly what an administrator opened the editor to
    find.
    """
    wanted = [sid.strip() for sid in sids if sid and sid.strip()]
    if not wanted:
        return []

    from samba.dcerpc import lsa, security

    pipe = conn.lsa
    handle = _policy_handle(conn, LSA_POLICY_LOOKUP_NAMES | LSA_POLICY_VIEW_LOCAL_INFORMATION)

    array = lsa.SidArray()
    entries = []
    for text in wanted:
        try:
            item = lsa.SidPtr()
            item.sid = security.dom_sid(text)
            entries.append(item)
        except Exception as exc:  # a malformed SID is the caller's
            raise InvalidRequest(
                "This is not a valid security identifier.",
                code="invalid_sid",
                context={"sid": text},
            ) from exc
    array.sids = entries
    array.num_sids = len(entries)

    names = lsa.TransNameArray2()
    domains = None
    count = 0

    try:
        result = _attempt(
            lambda: pipe.LookupSids3(handle, array, domains, names, 1, count, 0, 0),
            lambda: pipe.LookupSids2(handle, array, domains, names, 1, count, 0, 0),
            lambda: pipe.LookupSids(handle, array, domains, names, 1, count),
        )
    except SamfsconError as exc:
        if exc.code == "sid_not_resolved":
            return [_unresolved_sid(sid) for sid in wanted]
        raise

    return _merge_sid_lookup(wanted, result)


def accounts_with_right(conn: ServerConnection, right: str) -> list[dict[str, Any]]:
    """Who holds a privilege on this server.

    Used for SeDiskOperatorPrivilege, which is what srvsvc checks before it will
    touch a share. Reported as names rather than SIDs because the point is to
    tell an administrator which group to join.
    """
    from samba.dcerpc import lsa

    pipe = conn.lsa
    handle = _policy_handle(conn, LSA_POLICY_VIEW_LOCAL_INFORMATION | LSA_POLICY_LOOKUP_NAMES)

    name = lsa.String()
    name.string = right

    try:
        result = _attempt(lambda: pipe.EnumAccountsWithUserRight(handle, name))
    except SamfsconError as exc:
        # An empty right is reported as "no such object" rather than as an empty
        # list, which is a distinction without a difference to the caller.
        if isinstance(exc, NotFound) or exc.code in ("not_found", "sid_not_resolved"):
            return []
        raise

    sids = _sid_strings(result)
    if not sids:
        return []

    try:
        return lookup_sids(conn, sids)
    except SamfsconError:
        # The privilege list is worth having even when the names are not.
        return [_unresolved_sid(sid) for sid in sids]


def well_known(conn: ServerConnection) -> list[dict[str, Any]]:
    """The trustees the permission editor offers before anyone searches.

    Resolved against the server where possible so the names come back in the
    server's own language, and falling back to the English ones where the
    lookup is refused — a picker with no entries at all would be worse.
    """
    sids = [sid for sid, _, _ in WELL_KNOWN]
    try:
        resolved = {entry["sid"]: entry for entry in lookup_sids(conn, sids)}
    except SamfsconError:
        resolved = {}

    result = []
    for sid, fallback, kind in WELL_KNOWN:
        entry = resolved.get(sid)
        if entry and entry.get("name"):
            result.append(entry)
        else:
            result.append({"sid": sid, "name": fallback, "domain": None, "type": kind})
    return result


# ---------------------------------------------------------------------------
# Binding details, isolated
# ---------------------------------------------------------------------------


def _policy_handle(conn: ServerConnection, access: int) -> Any:
    """Open an LSA policy handle for this connection.

    Cached on the connection: opening one is a round trip, and the permission
    editor resolves names on nearly every keystroke.
    """
    cached = getattr(conn, "_lsa_policy", None)
    if cached is not None:
        return cached

    from samba.dcerpc import lsa

    pipe = conn.lsa
    attr = lsa.ObjectAttribute()
    attr.sec_qos = lsa.QosInfo()

    handle = _attempt(
        lambda: pipe.OpenPolicy2(None, attr, access),
        lambda: pipe.OpenPolicy(None, attr, access),
    )
    conn._lsa_policy = handle  # the cache belongs to the connection
    return handle


def _local_groups(conn: ServerConnection, sid: str) -> list[dict[str, Any]]:
    """The server's local aliases this SID belongs to.

    ``GetAliasMembership`` against the builtin domain is the call, and a server
    that refuses it is not a problem worth surfacing: the caller treats an
    empty list as "could not tell", which is what the notes on the capability
    report already say.
    """
    from samba.dcerpc import lsa, security

    try:
        pipe = conn.samr
        server = _attempt(lambda: pipe.Connect2(None, security.SEC_FLAG_MAXIMUM_ALLOWED))
        builtin = security.dom_sid("S-1-5-32")
        domain = _attempt(
            lambda: pipe.OpenDomain(server, security.SEC_FLAG_MAXIMUM_ALLOWED, builtin)
        )

        array = lsa.SidArray()
        item = lsa.SidPtr()
        item.sid = security.dom_sid(sid)
        array.sids = [item]
        array.num_sids = 1

        rids = _attempt(lambda: pipe.GetAliasMembership(domain, array))
    except Exception:  # a refused enumeration is not a failure here
        logger.debug("local group membership could not be read", exc_info=True)
        return []

    values = getattr(rids, "ids", None) or []
    if not values:
        return []

    try:
        return lookup_sids(conn, [f"S-1-5-32-{rid}" for rid in values])
    except SamfsconError:
        return [{"sid": f"S-1-5-32-{rid}", "name": None, "type": "alias"} for rid in values]


def _attempt(*attempts: Any) -> Any:
    """Run the first call shape this binding accepts.

    A ``TypeError`` means the signature was wrong and the next shape is worth
    trying. Anything else came from the server and is translated.
    """
    errors: list[str] = []
    for attempt in attempts:
        try:
            return attempt()
        except TypeError as exc:
            errors.append(str(exc))
            continue
        except Exception as exc:
            raise translate(exc) from exc

    raise SamfsconError(
        "This Samba build's LSA bindings have an unexpected signature.",
        code="lsa_unsupported",
        detail="; ".join(errors),
    )


def _unpack_user_name(result: Any) -> tuple[str | None, str | None]:
    """GetUserName returns (account, authority) in one shape or another."""
    from samfscon.srv.discovery import _text

    if not isinstance(result, tuple):
        return _text(getattr(result, "string", result)), None

    parts = [_text(getattr(item, "string", item)) for item in result if item is not None]
    name = parts[0] if parts else None
    authority = parts[1] if len(parts) > 1 else None
    return name, authority


def _merge_lookup(wanted: list[str], result: Any) -> list[dict[str, Any]]:
    """Line the LSA answer up with what was asked, in order."""
    domains, sids = _split_lookup(result)
    entries = getattr(sids, "sids", None) or []

    merged: list[dict[str, Any]] = []
    for index, name in enumerate(wanted):
        if index >= len(entries):
            merged.append(_unresolved(name))
            continue
        entry = entries[index]
        sid = _sid_text(entry, domains)
        if sid is None:
            merged.append(_unresolved(name))
            continue
        merged.append(
            {
                "name": name,
                "sid": sid,
                "domain": _domain_name(domains, getattr(entry, "sid_index", None)),
                "type": SID_TYPE_NAMES.get(int(getattr(entry, "sid_type", 8) or 8), "unknown"),
                "resolved": True,
            }
        )
    return merged


def _merge_sid_lookup(wanted: list[str], result: Any) -> list[dict[str, Any]]:
    domains, names = _split_lookup(result)
    entries = getattr(names, "names", None) or []

    from samfscon.srv.discovery import _text

    merged: list[dict[str, Any]] = []
    for index, sid in enumerate(wanted):
        if index >= len(entries):
            merged.append(_unresolved_sid(sid))
            continue
        entry = entries[index]
        name = _text(getattr(getattr(entry, "name", None), "string", None))
        if not name:
            merged.append(_unresolved_sid(sid))
            continue
        merged.append(
            {
                "name": name,
                "sid": sid,
                "domain": _domain_name(domains, getattr(entry, "sid_index", None)),
                "type": SID_TYPE_NAMES.get(int(getattr(entry, "sid_type", 8) or 8), "unknown"),
                "resolved": True,
            }
        )
    return merged


def _split_lookup(result: Any) -> tuple[Any, Any]:
    """The lookup calls return (domains, translated, count) in some order."""
    if not isinstance(result, tuple):
        return None, result
    domains = result[0] if len(result) > 0 else None
    translated = result[1] if len(result) > 1 else None
    return domains, translated


def _domain_name(domains: Any, index: Any) -> str | None:
    from samfscon.srv.discovery import _text

    if domains is None or index is None:
        return None
    entries = getattr(domains, "domains", None) or []
    try:
        entry = entries[int(index)]
    except (IndexError, TypeError, ValueError):
        return None
    return _text(getattr(getattr(entry, "name", None), "string", None))


def _sid_text(entry: Any, domains: Any) -> str | None:
    """A translated SID, whether the answer carried it whole or as a RID.

    ``LookupNames3`` returns the full SID. The older calls return a domain
    index and a RID, and the SID has to be assembled — the same value, two wire
    formats, and a caller that handled only one would work against one Samba
    version and not the next.
    """
    sid = getattr(entry, "sid", None)
    if sid is not None:
        return str(sid)

    rid = getattr(entry, "rid", None)
    if rid is None:
        return None

    index = getattr(entry, "sid_index", None)
    if domains is None or index is None:
        return None
    entries = getattr(domains, "domains", None) or []
    try:
        domain_sid = getattr(entries[int(index)], "sid", None)
    except (IndexError, TypeError, ValueError):
        return None
    if domain_sid is None:
        return None
    return f"{domain_sid}-{rid}"


def _sid_strings(result: Any) -> list[str]:
    entries = getattr(result, "sids", None)
    if entries is None and isinstance(result, tuple) and result:
        entries = getattr(result[0], "sids", None)
    if not entries:
        return []
    out = []
    for entry in entries:
        sid = getattr(entry, "sid", entry)
        if sid is not None:
            out.append(str(sid))
    return out


def _unresolved(name: str) -> dict[str, Any]:
    return {"name": name, "sid": None, "domain": None, "type": "unknown", "resolved": False}


def _unresolved_sid(sid: str) -> dict[str, Any]:
    return {"name": None, "sid": sid, "domain": None, "type": "unknown", "resolved": False}
