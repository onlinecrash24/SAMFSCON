"""Shares, over srvsvc.

The same interface the Windows "Shared Folders" console uses, and the same one
``net rpc share`` speaks. A share created here is one ``net conf list`` shows on
the server and one Explorer can open — which is the only definition of "it
worked" this module accepts.

A share has two halves and they live in different places:

* **srvsvc** carries the name, the path, the comment and the counters. It is
  authoritative for *which shares exist*, including the ones defined in the text
  smb.conf that no registry key describes.
* **the registry** carries everything else (:mod:`samfscon.srv.shareconf`).

Reading merges them. Writing splits them again — and the split is not
cosmetic: a share defined in the text smb.conf can be *read* here and cannot be
changed, because changing it would mean writing a file this console has no
access to. That state is reported rather than papered over. A console that
silently created a registry key shadowing a text-file share would produce a
server whose configuration says two different things.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any

from samfscon.core.errors import Conflict, InvalidRequest, NotFound, translate
from samfscon.srv import registry, shareconf
from samfscon.srv.connection import ServerConnection

logger = logging.getLogger(__name__)

# Share types (MS-SRVS 2.2.2.4). The high bits are flags on the low value.
STYPE_DISKTREE = 0x00000000
STYPE_PRINTQ = 0x00000001
STYPE_DEVICE = 0x00000002
STYPE_IPC = 0x00000003
STYPE_MASK = 0x0000000F
STYPE_TEMPORARY = 0x40000000
STYPE_SPECIAL = 0x80000000

TYPE_NAMES = {
    STYPE_DISKTREE: "disk",
    STYPE_PRINTQ: "printer",
    STYPE_DEVICE: "device",
    STYPE_IPC: "ipc",
}

# Shares the server owns. Listed, never offered for editing: a console that
# lets someone redefine IPC$ is a console that can lock its user out of the
# server it is managing.
ADMINISTRATIVE = frozenset({"ipc$", "admin$", "print$"})


@dataclass
class Share:
    """One share, as SAMFSCON presents it."""

    name: str
    type: str
    path: str | None
    comment: str | None
    special: bool
    current_users: int | None = None
    max_users: int | None = None
    # False for a share that exists only in the server's text smb.conf. It can
    # be read and not changed, and the interface says which.
    editable: bool = True
    options: shareconf.ShareOptions = field(default_factory=shareconf.ShareOptions)
    vfs: list[str] = field(default_factory=list)

    @property
    def administrative(self) -> bool:
        return self.name.lower() in ADMINISTRATIVE or self.special

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "path": self.path,
            "comment": self.comment,
            "special": self.special,
            "administrative": self.administrative,
            "current_users": self.current_users,
            "max_users": self.max_users,
            "editable": self.editable,
            "options": self.options.describe(),
            "vfs": list(self.vfs),
        }


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def list_shares(conn: ServerConnection, *, include_administrative: bool = False) -> list[Share]:
    """Every share the server publishes.

    Level 2 rather than 1, because the path is the field an administrator looks
    at first and a second round trip per share to fetch it would make the list
    unusable on a server with fifty of them.

    Whether each share is editable comes from one registry enumeration, not one
    per share: the question is only "does this name have a key", and asking it
    fifty times over RPC is fifty round trips for a boolean.
    """
    raw = _enumerate(conn)
    editable = _registry_sections(conn)

    shares: list[Share] = []
    for entry in raw:
        share = _from_srvsvc(entry)
        if share.administrative and not include_administrative:
            continue
        # None means the registry could not be read at all — every share then
        # reports as not editable, which is the truth for this session.
        share.editable = share.name.lower() in editable if editable is not None else False
        shares.append(share)

    shares.sort(key=lambda item: item.name.lower())
    return shares


def get_share(conn: ServerConnection, name: str) -> Share:
    """One share, with its stored options."""
    _reject_administrative(name)

    try:
        raw = conn.srvsvc.NetShareGetInfo(None, name, 2)
    except Exception as exc:
        error = translate(exc)
        if _missing(error):
            raise NotFound(
                "The share does not exist on this server.",
                code="share_not_found",
                context={"share": name},
            ) from exc
        raise error from exc

    share = _from_srvsvc(raw)
    if not share.name:
        share.name = name

    stored = registry.read_options(conn, share.name)
    share.options = shareconf.split(stored)
    share.vfs = shareconf.vfs_modules(stored)
    # A share with no registry key of its own comes from the text smb.conf.
    share.editable = bool(stored)
    return share


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def create_share(
    conn: ServerConnection,
    *,
    name: str,
    path: str,
    comment: str | None = None,
    options: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """Create a share by writing it into the registry configuration.

    Not through ``NetShareAdd``, and that is the whole point. Samba's
    implementation of that call requires an ``add share command`` in smb.conf —
    unconditionally, with no exemption for registry shares — and refuses with
    WERR_ACCESS_DENIED when there is none. It exists to run a script that edits
    the text smb.conf, which is a thing this console has no business asking a
    server to do.

    The registry needs none of it. A share *is* a key under
    ``HKLM\\Software\\Samba\\smbconf`` with a ``path`` value, which is exactly
    what ``net rpc conf addshare`` writes and exactly what this connection's
    winreg pipe is already open for. Samba loads registry shares on demand, so
    the share exists as soon as the key does.

    Everything is written in one go: a key with a path but no options would be a
    share that exists for a moment with none of the access restrictions it was
    created with — open to whoever looks in that moment.
    """
    _reject_administrative(name)
    checked = shareconf.validate(options or {})

    if _exists(conn, name):
        raise Conflict(
            "A share with this name already exists.",
            code="share_exists",
            context={"share": name},
        )

    values: dict[str, str | None] = {"path": path}
    if comment:
        values["comment"] = comment
    values.update(checked)

    try:
        applied = registry.write_options(conn, name, values)
    except Exception as exc:
        error = translate(exc)
        logger.warning("creating the share %s failed: %s", name, error.message)
        # A key that got half-written is a share Samba may already be serving.
        # Take it back rather than leave one behind that nobody meant to make.
        with contextlib.suppress(Exception):
            registry.delete_section(conn, name)
        raise error from exc

    # Written. Whether the server is serving it yet is a separate question, and
    # not one that makes this a failure: smbd re-reads the registry on its own
    # schedule, so a share that is correct and complete can be invisible for a
    # moment.
    #
    # The first version of this raised an error saying `registry shares = yes`
    # was missing. It was not — the line was already there, and one
    # `smbcontrol all reload-config` was the whole fix. Reporting a correct
    # creation as a configuration fault sent somebody to change a setting that
    # was right.
    served = _exists(conn, name)
    if not served:
        logger.info(
            "the registry key for %s is written; the server is not serving it yet", name
        )

    logger.info("share created: %s -> %s", name, path)
    return {
        "name": name,
        "path": path,
        "comment": comment,
        "options": applied,
        # Which of the two happened, so the interface can say so rather than
        # reporting a success that looks like nothing happened.
        "served": served,
    }


def update_share(
    conn: ServerConnection,
    name: str,
    *,
    path: str | None = None,
    comment: str | None = None,
    options: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """Change a share. Only what was sent is changed.

    The path and the comment are registry values like everything else — they
    have their own fields in the interface because every console puts them on
    the first tab, not because the protocol treats them differently.

    Returns the applied changes with their previous values, for the audit log.
    """
    _reject_administrative(name)
    checked = shareconf.validate(options or {})

    current = get_share(conn, name)
    if not current.editable:
        raise InvalidRequest(
            "This share is defined in the server's smb.conf and cannot be changed here.",
            code="share_not_editable",
            hint=(
                "SAMFSCON edits the registry configuration, which is what can be "
                "reached over the network. A share written into smb.conf has to be "
                "changed there — or moved into the registry with "
                "'net conf import'."
            ),
            context={"share": name},
        )

    values: dict[str, str | None] = dict(checked)
    if path is not None and path != current.path:
        values["path"] = path
    if comment is not None and comment != (current.comment or ""):
        values["comment"] = comment

    if not values:
        return {}
    return registry.write_options(conn, name, values)


def delete_share(conn: ServerConnection, name: str) -> None:
    """Remove a share by removing its registry key.

    The counterpart of the creation, and for the same reason: ``NetShareDel``
    wants a ``delete share command`` on the server. Deleting the key removes the
    share and its configuration together, which is what leaving one behind used
    to risk — the next share created under the same name inheriting the old
    one's access restrictions.

    The directory on the server is left alone. Deleting a share is a
    configuration change; deleting the data behind it is not something a console
    should do as a side effect of one.
    """
    _reject_administrative(name)

    if not _exists(conn, name):
        raise NotFound(
            "The share does not exist on this server.",
            code="share_not_found",
            context={"share": name},
        )

    registry.delete_section(conn, name)
    logger.info("share deleted: %s", name)


# ---------------------------------------------------------------------------
# The srvsvc calls, isolated because their shapes drift between releases
# ---------------------------------------------------------------------------


def _enumerate(conn: ServerConnection) -> list[Any]:
    """NetShareEnumAll at level 2, paged until the server stops.

    The resume handle is what makes this a loop rather than one call: a server
    with more shares than fit in the buffer returns the first batch and expects
    to be asked again. Ignoring it works right up to the server where it does
    not, and then a share is simply missing from the list with no error at all.
    """
    from samba.dcerpc import srvsvc

    pipe = conn.srvsvc
    found: list[Any] = []
    resume = 0

    while True:
        info = srvsvc.NetShareInfoCtr()
        info.level = 2
        info.ctr = srvsvc.NetShareCtr2()

        try:
            result = _attempt(
                lambda c=info, r=resume: pipe.NetShareEnumAll(None, c, 0xFFFFFFFF, r),
                lambda c=info, r=resume: pipe.NetShareEnumAll(None, c, -1, r),
            )
        except Exception as exc:
            raise translate(exc) from exc

        ctr, total, resume_out = _unpack_enum(result)
        batch = list(getattr(ctr, "array", None) or [])
        found.extend(batch)

        # Stop on any of the three ways a server says "that was all": no
        # progress, the total reached, or no resume handle handed back.
        if not batch or resume_out in (None, 0, resume) or len(found) >= (total or 0):
            break
        resume = resume_out

    return found


def _unpack_enum(result: Any) -> tuple[Any, int | None, int | None]:
    """Pull (ctr, total, resume) out of whatever the binding returned."""
    if not isinstance(result, tuple):
        return getattr(result, "ctr", result), None, None

    ctr = None
    numbers: list[int] = []
    for item in result:
        if hasattr(item, "ctr"):
            ctr = item.ctr
        elif hasattr(item, "array"):
            ctr = item
        elif isinstance(item, int):
            numbers.append(item)

    total = numbers[0] if numbers else None
    resume = numbers[1] if len(numbers) > 1 else None
    return ctr, total, resume


def _from_srvsvc(entry: Any) -> Share:
    from samfscon.srv.discovery import _text

    raw_type = int(getattr(entry, "type", 0) or 0)
    return Share(
        name=_text(getattr(entry, "name", None)) or "",
        type=TYPE_NAMES.get(raw_type & STYPE_MASK, "unknown"),
        path=_normalise_path(_text(getattr(entry, "path", None))),
        comment=_text(getattr(entry, "comment", None)),
        special=bool(raw_type & STYPE_SPECIAL),
        current_users=_number(getattr(entry, "current_users", None)),
        max_users=_max_users(getattr(entry, "max_users", None)),
    )


def _normalise_path(path: str | None) -> str | None:
    """srvsvc reports Unix paths with backslashes; smb.conf uses slashes.

    Shown the way the administrator wrote it in smb.conf, not the way the wire
    carries it — a path that reads ``\\srv\\shares\\projects`` on a Linux server
    is a path nobody recognises as their own.
    """
    if not path:
        return None
    return path.replace("\\", "/")


def _number(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _max_users(value: Any) -> int | None:
    """0xFFFFFFFF is srvsvc's way of saying "no limit"; report it as none."""
    number = _number(value)
    if number is None or number in (0xFFFFFFFF, -1):
        return None
    return number


# What NetShareGetInfo answers for a share that is not there.
#
# `WERR_INVALID_NAME` is in this list and it looks wrong. It is not: Samba's
# _srvsvc_NetShareGetInfo returns it when find_service() comes up empty, so a
# name that is perfectly valid and simply unused produces "invalid name". Every
# attempt to create a share died on that — the existence check treated it as a
# refusal and raised, and NetShareAdd was never reached. The message then
# complained about a name the person had just typed correctly.
_SHARE_MISSING = frozenset({"share_not_found", "not_found", "invalid_name"})


def _missing(error: Any) -> bool:
    return error.status_code == 404 or error.code in _SHARE_MISSING


def _exists(conn: ServerConnection, name: str) -> bool:
    try:
        conn.srvsvc.NetShareGetInfo(None, name, 1)
    except Exception as exc:  # anything but success means "not there"
        error = translate(exc)
        if _missing(error):
            return False
        # A refusal is not an absence. Reporting it as one would let a create
        # proceed and fail again, less clearly, one call later.
        raise error from exc
    return True


def _registry_sections(conn: ServerConnection) -> set[str] | None:
    """Which shares have registry configuration, lower-cased.

    ``None`` when the registry could not be read at all — deliberately not an
    empty set, which would claim every share is uneditable as a fact rather
    than as a consequence of not having looked.
    """
    try:
        return {name.lower() for name in registry.read_sections(conn)}
    except Exception:  # a server without registry config is normal
        logger.debug("the registry configuration could not be enumerated", exc_info=True)
        return None


def registry_shares_served(conn: ServerConnection) -> bool | None:
    """Whether this server actually serves what is in its registry.

    Not answerable by asking: `registry shares` lives in the text smb.conf,
    which is exactly the file this console cannot read. But it is observable —
    if the registry holds share sections and none of them appears in the live
    share list, the server is ignoring them.

    ``None`` when there is nothing to compare: a registry with no sections
    proves nothing either way, and neither does one whose sections are all also
    defined in smb.conf.
    """
    sections = _registry_sections(conn)
    if not sections:
        return None

    try:
        live = {share.name.lower() for share in _enumerate_names(conn)}
    except Exception:  # a probe must not break the console
        logger.debug("the share list could not be read for the registry check", exc_info=True)
        return None

    return bool(sections & live)


def _enumerate_names(conn: ServerConnection) -> list[Share]:
    """The live share list, without the registry lookup list_shares does.

    Called *from* that lookup's neighbour, so it must not call back into it.
    """
    return [_from_srvsvc(entry) for entry in _enumerate(conn)]


def _reject_administrative(name: str) -> None:
    if name.lower() in ADMINISTRATIVE:
        raise InvalidRequest(
            "This share belongs to the server itself and is not editable.",
            code="administrative_share",
            hint="IPC$, ADMIN$ and print$ are managed by Samba, not by a console.",
            context={"share": name},
        )


def share_info(level: int, value: Any) -> Any:
    """Wrap a NetShareInfo<level> in the union the call actually takes.

    ``NetShareAdd`` and ``NetShareSetInfo`` declare
    ``[switch_is(level)] srvsvc_NetShareInfo *info`` — a union, whose arm is
    chosen by the level beside it. Handing them the bare NetShareInfo2 does not
    fail on the client: it marshals *something*, the server reads a different
    arm, and `share_name` arrives empty. Samba then answers WERR_INVALID_NAME,
    which is how creating a share called "test" reported that "test" is not a
    valid name.

    The member is set by name, falling back to assigning the union whole, the
    same way the enumeration containers are filled — this is the fourth union
    in this codebase to need it.
    """
    from samba.dcerpc import srvsvc

    try:
        union = srvsvc.NetShareInfo()
    except (AttributeError, TypeError):  # pragma: no cover - a build without it
        return value

    try:
        setattr(union, f"info{level}", value)
        return union
    except (AttributeError, TypeError):
        pass

    try:
        union.info = value
        return union
    except (AttributeError, TypeError):
        # A build whose bindings take the struct directly. Passing the union
        # object would be the wrong shape there, so the bare value goes back.
        return value


def _attempt(*attempts: Any) -> Any:
    """Run the first call shape this binding accepts.

    A ``TypeError`` means the signature was wrong and the next shape is worth
    trying. Anything else came from the server and is raised as it is — trying
    another argument order against a server that already said "access denied"
    would only ask it twice.
    """
    errors: list[str] = []
    for attempt in attempts:
        try:
            return attempt()
        except (TypeError, AttributeError) as exc:
            # A wrong signature, or a type this Samba build does not have.
            # Both mean "not this shape"; neither came from the server.
            errors.append(f"{type(exc).__name__}: {exc}")
            continue
    raise TypeError("; ".join(errors))
