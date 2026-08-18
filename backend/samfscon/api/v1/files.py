"""Browsing a share's contents.

Read-only, plus one creation. SAMFSCON is a permissions console rather than a
file manager: what it needs from a share's contents is a tree to point the
permission editor at, and offering upload, download and delete on top of that
would be a second product with a second set of ways to lose data.

``mkdir`` is the exception, and it earns its place: creating a subfolder is what
one does *while* setting permissions on a new project directory, and it is the
one write to a server's file system these protocols can perform — precisely
because it happens inside a share that already exists.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from samfscon.api.common import Audit, PathQuery, ShareQuery
from samfscon.auth.deps import CurrentSession, VerifiedSession, VerifiedWorker, Worker
from samfscon.srv import files
from samfscon.srv.access import srv_read, srv_write
from samfscon.srv.connection import ServerConnection

router = APIRouter(prefix="/files", tags=["files"])


@router.get("")
async def list_directory(
    share: ShareQuery, session: CurrentSession, worker: Worker, path: PathQuery = ""
) -> dict[str, Any]:
    """What is directly below *path* inside *share*.

    Listed as the signed-in administrator, so a directory they may not read is
    one this call cannot list either. That is the correct behaviour: a console
    that could see more than the account it runs as would be a console that
    lies about what the account can do.
    """

    def _read(conn: ServerConnection) -> dict[str, Any]:
        return files.listdir(conn, share, path)

    return await srv_read(worker, session, _read, label="files.list")


@router.post("/directory")
async def create_directory(
    share: ShareQuery,
    path: PathQuery,
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
) -> dict[str, Any]:
    """Create one directory inside a share.

    It inherits the parent's permissions, as any directory created over SMB
    does. Setting different ones is the permissions tab's job, on the directory
    that now exists.
    """

    def _write(conn: ServerConnection) -> str:
        return files.mkdir(conn, share, path)

    with audit.operation("files.mkdir", target=f"{share}\\{path}"):
        created = await srv_write(worker, session, _write, label="files.mkdir")

    return {"share": share, "path": created, "status": "created"}
