"""Connected users, and the files they have open."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from samfscon.api.common import Audit, ShareQuery
from samfscon.auth.deps import CurrentSession, VerifiedSession, VerifiedWorker, Worker
from samfscon.schemas.requests import CloseFileRequest
from samfscon.srv import sessions as srv_sessions
from samfscon.srv.access import srv_read, srv_write
from samfscon.srv.connection import ServerConnection

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(
    session: CurrentSession,
    worker: Worker,
    client: str | None = None,
    user: str | None = None,
) -> dict[str, Any]:
    """Everyone connected to the server right now."""

    def _read(conn: ServerConnection) -> dict[str, Any]:
        found = srv_sessions.list_sessions(conn, client=client, user=user)
        return {"entries": [entry.describe() for entry in found]}

    return await srv_read(worker, session, _read, label="sessions.list")


@router.get("/files")
async def list_open_files(
    session: CurrentSession,
    worker: Worker,
    path: str | None = None,
    user: str | None = None,
) -> dict[str, Any]:
    """Every open handle on the server.

    ``path`` narrows it the way the protocol does — by prefix, against the
    server's own path, not against the share name. That is worth knowing when
    the filter appears to match nothing: the answer is in the *server's*
    file system layout, which the share list shows.
    """

    def _read(conn: ServerConnection) -> dict[str, Any]:
        found = srv_sessions.list_open_files(conn, path=path, user=user)
        return {"entries": [entry.describe() for entry in found]}

    return await srv_read(worker, session, _read, label="sessions.files")


@router.get("/connections")
async def list_connections(
    share: ShareQuery, session: CurrentSession, worker: Worker
) -> dict[str, Any]:
    """Who has one share open.

    The share is required rather than optional: srvsvc takes it as the
    qualifier for this call, and there is no "all of them" form of it.
    """

    def _read(conn: ServerConnection) -> dict[str, Any]:
        found = srv_sessions.list_connections(conn, share)
        return {"share": share, "entries": [entry.describe() for entry in found]}

    return await srv_read(worker, session, _read, label="sessions.connections")


@router.post("/files/close")
async def close_file(
    payload: CloseFileRequest,
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
) -> dict[str, Any]:
    """Force one open handle closed.

    The one destructive call in this part of the console: the client holding
    the file is not asked, and loses whatever it had not written. Recorded in
    the audit log with the file and the account that had it — which is the
    least a person deserves when their document is closed from underneath them.
    """

    def _read(conn: ServerConnection) -> dict[str, Any] | None:
        # Read before writing, so the audit entry can name what was closed. The
        # id alone would record nothing anyone could act on later.
        for entry in srv_sessions.list_open_files(conn):
            if entry.id == payload.file_id:
                return entry.describe()
        return None

    def _write(conn: ServerConnection) -> None:
        srv_sessions.close_file(conn, payload.file_id)

    victim = await srv_read(worker, session, _read, label="sessions.file")

    with audit.operation("file.close", target=str(payload.file_id)) as record:
        await srv_write(worker, session, _write, label="sessions.close")
        if victim is not None:
            record["path"] = victim.get("path")
            record["user"] = victim.get("user")

    return {"file_id": payload.file_id, "status": "closed", "file": victim}
