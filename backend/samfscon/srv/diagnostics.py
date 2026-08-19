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
    """
    caps = Capabilities()
    _check_registry(conn, caps)
    _check_privilege(conn, caps, sid)
    return caps


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

    # Not held directly. Group membership decides, and that is what the account
    # lookup already resolved.
    try:
        groups = identity.current_account(conn).get("groups", [])
    except Exception:  # noqa: BLE001
        groups = []

    if any(group.get("sid") in holder_sids for group in groups):
        caps.has_disk_operator = True
        return

    caps.has_disk_operator = False
    if caps.disk_operators:
        caps.notes.append(
            Note("disk_operators_are", {"names": ", ".join(caps.disk_operators)})
        )
    else:
        caps.notes.append(Note("no_disk_operators"))


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
    if caps.has_disk_operator is False:
        raise PermissionDenied(
            "Your account may not manage this server's shares.",
            code="missing_disk_operator",
            hint=(
                "The server checks SeDiskOperatorPrivilege for this. Grant it "
                "with: net rpc rights grant '<group>' SeDiskOperatorPrivilege "
                "-U <admin>"
            ),
            context={"holders": caps.disk_operators},
        )


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
