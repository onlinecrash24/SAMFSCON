"""Permissions, at both levels.

Three endpoints and one editor behind them, because a share permission and a
file permission are the same structure. What differs is where the descriptor
comes from — srvsvc level 502 for the share, SMB for a path inside it — and
that is the only thing this module has to keep straight.

The fourth endpoint is the one that earns the module: :func:`effective_access`
intersects the two. SMB checks the share permission once when the share is
opened and the file permission on every operation afterwards, so the answer to
"may Alice write this" is neither number alone. A console that showed only one
of them is a console people end up arguing with, holding a screenshot that says
Full Control next to a client that says access denied.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from samfscon.api.common import Audit, PathQuery, ShareQuery
from samfscon.auth.deps import CurrentSession, VerifiedSession, VerifiedWorker, Worker
from samfscon.schemas.requests import SecurityDescriptorRequest
from samfscon.srv import acl, files, identity, shareacl
from samfscon.srv.access import srv_read, srv_write
from samfscon.srv.connection import ServerConnection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("/share")
async def get_share_permissions(
    share: ShareQuery, session: CurrentSession, worker: Worker
) -> dict[str, Any]:
    """The share-level descriptor.

    Checked once, when a client connects to the share, and it bounds
    everything that follows. Granting Everyone full control here is the usual
    Samba arrangement — the file permissions then do the real work — and the
    answer says so rather than leaving it to be inferred.
    """

    def _read(conn: ServerConnection) -> dict[str, Any]:
        descriptor = shareacl.read(conn, share)
        return {
            "share": share,
            "level": "share",
            **descriptor.describe(),
            "trustees": _resolve_trustees(conn, descriptor),
        }

    return await srv_read(worker, session, _read, label="permissions.share")


@router.put("/share")
async def set_share_permissions(
    share: ShareQuery,
    payload: SecurityDescriptorRequest,
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
) -> dict[str, Any]:
    """Replace the share-level descriptor."""

    def _write(conn: ServerConnection) -> dict[str, Any]:
        before = shareacl.read(conn, share)
        shareacl.write(conn, share, payload.sddl)
        return {"old": before.sddl, "new": payload.sddl}

    with audit.operation("permissions.share", target=share) as record:
        change = await srv_write(worker, session, _write, label="permissions.shareWrite")
        record["sddl"] = change

    return {"share": share, "status": "saved"}


@router.get("/path")
async def get_path_permissions(
    share: ShareQuery, session: CurrentSession, worker: Worker, path: PathQuery = ""
) -> dict[str, Any]:
    """The descriptor of one path inside a share.

    An empty path is the share's root directory, and it is the one this view
    opens on: a share's file permissions are the root's, and everything below
    inherits from there unless somebody broke the chain.
    """

    def _read(conn: ServerConnection) -> dict[str, Any]:
        relative = files.normalise(path)
        sddl = acl.read_path_sddl(conn, share, relative)
        descriptor = acl.parse(sddl)
        return {
            "share": share,
            "path": relative,
            "level": "file",
            **descriptor.describe(),
            "trustees": _resolve_trustees(conn, descriptor),
        }

    return await srv_read(worker, session, _read, label="permissions.path")


@router.put("/path")
async def set_path_permissions(
    share: ShareQuery,
    payload: SecurityDescriptorRequest,
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
    path: PathQuery = "",
) -> dict[str, Any]:
    """Replace the descriptor of one path.

    ``apply_to_children`` is not a loop over the tree, and the difference
    matters. Setting the DACL as *protected* stops the parent's entries flowing
    in; letting the inheritance flags do their work is what propagates a change
    downwards, and the server does that itself. A console that walked the tree
    rewriting every file would take hours on a real share and would flatten
    every deliberate exception it passed.
    """

    def _write(conn: ServerConnection) -> dict[str, Any]:
        relative = files.normalise(path)
        before = acl.read_path_sddl(conn, share, relative)
        acl.write_path_sddl(
            conn, share, relative, payload.sddl, protected=payload.apply_to_children or None
        )
        return {"old": before, "new": payload.sddl}

    with audit.operation("permissions.path", target=f"{share}\\{path}") as record:
        change = await srv_write(worker, session, _write, label="permissions.pathWrite")
        record["sddl"] = change

    return {"share": share, "path": path, "status": "saved"}


@router.get("/effective")
async def effective(
    share: ShareQuery,
    sid: str,
    session: CurrentSession,
    worker: Worker,
    path: PathQuery = "",
) -> dict[str, Any]:
    """What one account may actually do, given both descriptors.

    The intersection of the share permission and the file permission, which is
    how SMB decides and what neither descriptor answers on its own.

    Deliberately naive about groups: it computes what the entries naming this
    SID grant, not what the account's group memberships add. Doing the full
    token evaluation would mean resolving every group the account is in, on a
    server that may not be able to tell us — and a number that is *sometimes*
    the whole answer is worse than one that is honestly partial. The response
    says which it is.
    """

    def _read(conn: ServerConnection) -> dict[str, Any]:
        relative = files.normalise(path)
        share_descriptor = shareacl.read(conn, share)
        file_descriptor = acl.parse(acl.read_path_sddl(conn, share, relative))

        result = acl.effective_access(
            _mask_for(share_descriptor, sid), _mask_for(file_descriptor, sid)
        )
        result.update(
            {
                "share": share,
                "path": relative,
                "sid": sid,
                # Said out loud: this is what the ACEs naming this SID grant,
                # not the full token evaluation.
                "direct_entries_only": True,
            }
        )
        return result

    return await srv_read(worker, session, _read, label="permissions.effective")


def _resolve_trustees(
    conn: ServerConnection, descriptor: acl.SecurityDescriptor
) -> dict[str, Any]:
    """Names for every trustee in the descriptor, keyed by what the ACE said.

    Resolved here rather than in the editor: one call for the whole descriptor
    instead of one per row, against the LSA pipe this connection already holds.
    A descriptor of nine entries was making nine round trips' worth of work look
    reasonable right up until somebody opened one with ninety.

    Three sources, and the order matters. An SDDL alias is expanded first,
    because ``WD`` is a spelling of a SID rather than a name to look up. A Unix
    mapping is named locally, because no lookup will ever resolve one. Whatever
    is left is a real SID and goes to the server.

    Never raises. A descriptor whose names could not be fetched is still a
    descriptor worth showing — with the SIDs it had, which is what it showed
    before this function existed.
    """
    from samfscon.core.errors import SamfsconError

    trustees: dict[str, Any] = {}
    to_look_up: dict[str, str] = {}  # sid -> the trustee string that produced it

    for entry in descriptor.aces:
        if entry.trustee in trustees or entry.trustee in to_look_up.values():
            continue

        sid = acl.canonical_sid(entry.trustee)
        if sid is None:
            # An alias that only means something relative to a domain. The
            # server knows which domain that is; we do not.
            trustees[entry.trustee] = {"sid": None, "name": None, "alias": entry.trustee}
            continue

        to_look_up[sid] = entry.trustee

    if to_look_up:
        try:
            for found in identity.lookup_sids(conn, list(to_look_up)):
                sid = found.get("sid")
                if sid in to_look_up:
                    trustees[to_look_up[sid]] = found
        except SamfsconError as exc:
            # The names are decoration on a descriptor that is already correct,
            # so this must not fail the request — but a silent fallback is how
            # a column of derived names looked like a working lookup for a
            # whole round of testing. The reason belongs in `docker logs`.
            logger.warning(
                "resolving %d trustee(s) failed (%s); falling back to what the SIDs "
                "themselves say: %s",
                len(to_look_up),
                exc.code,
                exc.detail or exc.message,
            )

    for sid, trustee in to_look_up.items():
        # Only now. `smbcacls` renders S-1-22-2-0 as "Unix Group\\root", which
        # means the server resolves Samba's Unix mappings perfectly well through
        # winbind — so asking it first and naming them ourselves second gets the
        # server's own name where there is one, and a usable one where there is
        # not. The other way round, this console would have insisted on "Unix
        # group 0" for something the server calls root.
        # Whatever the server would not name, in descending order of how much
        # is actually known about it: a SID the specification names, Samba's
        # Unix mapping, and finally the SID itself.
        derived = identity.well_known_name(sid)
        if derived is not None:
            trustees.setdefault(trustee, derived)
            continue

        unix = acl.unix_identity(sid)
        if unix is not None:
            trustees.setdefault(trustee, {"sid": sid, "name": None, "unix": unix})
        else:
            trustees.setdefault(trustee, {"sid": sid, "name": None, "resolved": False})

    return trustees


def _mask_for(descriptor: acl.SecurityDescriptor, sid: str) -> int:
    """What the entries naming *sid* add up to.

    Deny wins over allow, as it does on the wire: the denied bits are removed
    from the allowed ones rather than merged with them. Getting this backwards
    would report an account as permitted to do precisely what it is forbidden.
    """
    allowed = 0
    denied = 0
    for entry in descriptor.aces:
        if entry.trustee != sid:
            continue
        if entry.kind == "deny":
            denied |= acl.expand_generic(entry.mask)
        else:
            allowed |= acl.expand_generic(entry.mask)
    return allowed & ~denied
