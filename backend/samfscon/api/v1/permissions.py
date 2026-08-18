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

from typing import Any

from fastapi import APIRouter

from samfscon.api.common import Audit, PathQuery, ShareQuery
from samfscon.auth.deps import CurrentSession, VerifiedSession, VerifiedWorker, Worker
from samfscon.schemas.requests import SecurityDescriptorRequest
from samfscon.srv import acl, files, shareacl
from samfscon.srv.access import srv_read, srv_write
from samfscon.srv.connection import ServerConnection

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
        return {"share": share, "level": "share", **descriptor.describe()}

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
        return {"share": share, "path": relative, "level": "file", **descriptor.describe()}

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
