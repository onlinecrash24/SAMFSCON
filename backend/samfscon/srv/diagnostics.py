"""What this account may do on this server, and what the server is set up for.

Two questions turn "access denied" from a dead end into something actionable,
and neither is answerable from the status code alone:

1. **Is the server set up for remote share management at all?** Samba stores
   shares created over the network in its registry configuration, and only
   serves them when ``include = registry`` and ``registry shares = yes`` are in
   smb.conf. Without that, a share creation is refused — or worse, accepted
   into a registry nothing reads.
2. **Does this account hold SeDiskOperatorPrivilege?** That is the right the
   srvsvc share calls check, and it is granted separately from any group
   membership that looks like it should imply it.

Both are read here, once, and reported wherever a refusal needs explaining.
Guessing between them is the failure this module exists to prevent: they are
the same WERR_ACCESS_DENIED, and the advice for one sends the reader entirely
the wrong way for the other.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from samfscon.core.errors import SamfsconError, translate
from samfscon.srv.connection import ServerConnection

logger = logging.getLogger(__name__)

# The right srvsvc checks before it will add, change or delete a share.
DISK_OPERATOR_RIGHT = "SeDiskOperatorPrivilege"

# Where Samba keeps the configuration that can be edited over the network.
SMBCONF_KEY = "SOFTWARE\\Samba\\smbconf"

# winreg access masks (MS-RRP 2.2.2). Read and write are asked for separately:
# an account that may look at the configuration but not change it should see
# the shares and be refused only on the save.
KEY_READ = 0x00020019
KEY_WRITE = 0x00020006


@dataclass
class Note:
    """One reason a capability could not be established, as a code.

    A code rather than a sentence, because the interface is bilingual and the
    server writes English. The first version of this carried prose, and a
    German banner ended with "the signed-in account's SID is unknown" tacked on
    the end of it — half a sentence in the wrong language, which is exactly the
    half that explains what to do.
    """

    code: str
    params: dict[str, Any] = field(default_factory=dict)

    def describe(self) -> dict[str, Any]:
        return {"code": self.code, "params": dict(self.params)}


@dataclass
class Capabilities:
    """What this session can actually do, as opposed to what it may attempt."""

    # None where it could not be determined — which is different from False and
    # must stay different, or the interface starts telling people their
    # permissions are missing when it simply could not look.
    registry_config: bool | None = None
    registry_writable: bool | None = None
    has_disk_operator: bool | None = None
    disk_operators: list[str] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)

    @property
    def can_manage_shares(self) -> bool | None:
        if self.registry_config is False or self.has_disk_operator is False:
            return False
        if self.registry_config and self.has_disk_operator:
            return True
        return None

    def describe(self) -> dict[str, Any]:
        return {
            "registry_config": self.registry_config,
            "registry_writable": self.registry_writable,
            "has_disk_operator": self.has_disk_operator,
            "disk_operators": list(self.disk_operators),
            "can_manage_shares": self.can_manage_shares,
            "notes": [note.describe() for note in self.notes],
        }


def whoami(conn: ServerConnection) -> dict[str, Any]:
    """The signed-in account as the server resolved it, plus its capabilities."""
    from samfscon.srv import identity

    account: dict[str, Any] = {"name": None, "sid": None, "groups": []}
    try:
        account = identity.current_account(conn)
    except SamfsconError as exc:
        logger.info("could not resolve the signed-in account: %s", exc.message)

    caps = capabilities(conn, sid=account.get("sid"))
    return {
        "account": account,
        "server": conn.info.describe(),
        "connection": conn.transport.describe(),
        "capabilities": caps.describe(),
    }


def capabilities(conn: ServerConnection, *, sid: str | None = None) -> Capabilities:
    """Read both preconditions for managing shares.

    Neither check changes anything, and neither is allowed to fail the caller:
    an administrator whose account cannot read the privilege list should still
    get a console, with the parts that need it explained rather than broken.

    ``sid`` is optional and is looked up when it is not given. It used not to
    be — every caller but one passed nothing, and the privilege check then
    reported the signed-in account's SID as unknown. Which was true, and
    thoroughly misleading: nobody had asked. The banner said so for four rounds
    of testing while the lookup that would have answered it sat on a path only
    `samfsconctl check` ever took.
    """
    caps = Capabilities()
    _check_registry(conn, caps)
    _check_privilege(conn, caps, sid if sid is not None else _own_sid(conn))
    return caps


def _own_sid(conn: ServerConnection) -> str | None:
    """The signed-in account's SID, resolved once per connection.

    Cached because it cannot change while the session lasts: it is the identity
    the connection was opened with. The privilege check runs on every share
    write as well as on every listing, and three LSA round trips per click is a
    cost with nothing to show for it.
    """
    cached = getattr(conn, "_own_sid", "unset")
    if cached != "unset":
        return cached

    from samfscon.srv import identity

    try:
        sid = identity.current_account(conn).get("sid")
    except Exception:  # a probe must not break the console
        logger.debug("the signed-in account could not be resolved", exc_info=True)
        sid = None

    conn._own_sid = sid  # the cache belongs to the connection
    return sid


def _check_registry(conn: ServerConnection, caps: Capabilities) -> None:
    """Whether Samba's registry configuration is reachable, and writable."""
    from samfscon.srv import registry

    try:
        with registry.open_smbconf(conn, write=False):
            caps.registry_config = True
    except SamfsconError as exc:
        if exc.status_code in (403, 401):
            # The store exists — we were refused, not told it is absent. Saying
            # "not configured" here would send an administrator to edit an
            # smb.conf that is already right.
            caps.registry_config = True
            caps.registry_writable = False
            caps.notes.append(Note("registry_unreadable"))
            return
        caps.registry_config = False
        caps.notes.append(Note("registry_missing"))
        return
    except Exception as exc:  # a probe must not break the console
        logger.debug("registry probe failed", exc_info=True)
        caps.notes.append(Note("registry_probe_failed", {"detail": str(exc)}))
        return

    try:
        with registry.open_smbconf(conn, write=True):
            caps.registry_writable = True
    except SamfsconError:
        caps.registry_writable = False
        caps.notes.append(Note("registry_read_only"))
    except Exception:
        logger.debug("registry write probe failed", exc_info=True)


def _check_privilege(conn: ServerConnection, caps: Capabilities, sid: str | None) -> None:
    """Who holds SeDiskOperatorPrivilege on this server.

    The list matters as much as the yes/no. The right is usually granted to a
    group rather than to a person, so an account that does not hold it directly
    may still be a member of one that does — and naming the holders is what
    lets an administrator see which group to join instead of guessing.
    """
    from samfscon.srv import identity

    try:
        holders = identity.accounts_with_right(conn, DISK_OPERATOR_RIGHT)
    except SamfsconError as exc:
        caps.notes.append(Note("privilege_list_unreadable", {"reason": exc.message}))
        return
    except Exception as exc:
        logger.debug("privilege probe failed", exc_info=True)
        caps.notes.append(Note("privilege_list_unreadable", {"reason": str(exc)}))
        return

    caps.disk_operators = [entry["name"] for entry in holders if entry.get("name")]

    if sid is None:
        caps.notes.append(Note("sid_unknown"))
        return

    holder_sids = {entry.get("sid") for entry in holders}
    if sid in holder_sids:
        caps.has_disk_operator = True
        return

    # Nobody holds it. That absence *is* establishable — an empty list is an
    # answer — and it is the one case where refusing up front is right.
    if not holders:
        caps.has_disk_operator = False
        caps.notes.append(Note("no_disk_operators", {"command": _grant_command(conn)}))
        return

    # Held by somebody. Whether that somebody includes us is the part this
    # cannot settle.
    try:
        groups = identity.current_account(conn).get("groups", [])
    except Exception:  # noqa: BLE001 — a probe must not break the console
        groups = []

    if any(group.get("sid") in holder_sids for group in groups):
        caps.has_disk_operator = True
        return

    # And here is the honest end of it. GetAliasMembership returns the groups
    # that contain this SID *directly*. A domain administrator is in
    # BUILTIN\Administrators through Domain Admins, and no amount of asking this
    # way will show that — so "not found" is not "not a member", and saying
    # otherwise disabled the one button the person came to press.
    #
    # The server evaluates the whole token when it is asked to do something.
    # That is the only complete answer, and it costs nothing to let it give one.
    caps.has_disk_operator = None
    caps.notes.append(
        Note(
            "privilege_unconfirmed",
            {
                "holders": ", ".join(caps.disk_operators) or "—",
                "command": _grant_command(conn),
            },
        )
    )


def _grant_command(conn: ServerConnection) -> str:
    """A command that can be pasted, not a template to be filled in.

    The placeholders were the complaint: `<group>` and `<admin>` are two more
    things to work out at the moment somebody wants an answer. Everything
    needed is already known — the domain from the realm, the account from the
    session — so it is written out.
    """
    domain = (
        conn.target.workgroup
        or (conn.target.realm.split(".")[0] if conn.target.realm else None)
        or conn.info.name
    )
    admin = getattr(conn, "principal", None) or "Administrator"
    group = f"{domain}\\Domain Admins" if conn.target.uses_kerberos else "Administrators"
    return f"net rpc rights grant '{group}' {DISK_OPERATOR_RIGHT} -U {admin}"


def require_share_management(caps: Capabilities) -> None:
    """Refuse a share write before it reaches the server, where it can be said why.

    Called on the write paths. The server's own refusal is a bare
    WERR_ACCESS_DENIED, which names neither cause; this raises the one that
    actually applies, with the command that fixes it.
    """
    from samfscon.core.errors import NotConfigured, PermissionDenied

    if caps.registry_config is False:
        raise NotConfigured(
            "This server is not set up for managing shares over the network.",
            code="registry_config_missing",
            hint=(
                "Add 'include = registry' and 'registry shares = yes' to the "
                "[global] section of the server's smb.conf and reload Samba. "
                "Reading works without it; only changes need it."
            ),
        )
    # Only a confirmed absence. `None` means this check could not resolve the
    # nested group membership that decides it — and the server evaluates the
    # whole token anyway, so the attempt goes through and its answer stands.
    # Refusing here on an unconfirmed guess is how a domain administrator was
    # told they could not do something they can.
    if caps.has_disk_operator is False:
        raise PermissionDenied(
            "Nobody on this server may manage its shares.",
            code="missing_disk_operator",
            hint=(
                "The server checks SeDiskOperatorPrivilege for this, and no "
                "account or group holds it. Grant it on the server with: "
                + _grant_command_from(caps)
            ),
            context={"holders": caps.disk_operators},
        )


def _grant_command_from(caps: Capabilities) -> str:
    """The command out of whichever note carries it."""
    for note in caps.notes:
        command = note.params.get("command")
        if command:
            return str(command)
    return f"net rpc rights grant '<group>' {DISK_OPERATOR_RIGHT} -U <admin>"


def server_facts(conn: ServerConnection) -> dict[str, Any]:
    """Everything the diagnostics view shows about the server itself."""
    try:
        raw = conn.srvsvc.NetSrvGetInfo(None, 102)
    except Exception as exc:  # level 102 needs more rights than 101
        logger.debug("NetSrvGetInfo(102) refused", exc_info=True)
        raise translate(exc) from exc

    from samfscon.srv.discovery import _text

    return {
        "name": _text(getattr(raw, "server_name", None)),
        "comment": _text(getattr(raw, "comment", None)),
        "platform_id": getattr(raw, "platform_id", None),
        "version": f"{getattr(raw, 'version_major', '?')}.{getattr(raw, 'version_minor', '?')}",
        "users": getattr(raw, "users", None),
        "hidden": bool(getattr(raw, "hidden", False)),
    }
