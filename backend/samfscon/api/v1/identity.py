"""Names and SIDs, for the permission editor's object picker."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from samfscon.auth.deps import CurrentSession, Worker
from samfscon.schemas.requests import LookupRequest
from samfscon.srv import identity
from samfscon.srv.access import srv_read
from samfscon.srv.connection import ServerConnection

router = APIRouter(prefix="/identity", tags=["identity"])


@router.post("/names")
async def lookup_names(
    payload: LookupRequest, session: CurrentSession, worker: Worker
) -> dict[str, Any]:
    """Resolve names to SIDs.

    Answered by the **file server**, not by a domain controller. That is the
    whole point: a member server resolves its own local groups and the domain's
    accounts through one interface, with the same answer it would use when
    deciding access — which is not always the answer a DC would give.
    """

    def _read(conn: ServerConnection) -> dict[str, Any]:
        return {"entries": identity.lookup_names(conn, payload.names)}

    return await srv_read(worker, session, _read, label="identity.names")


@router.post("/sids")
async def lookup_sids(
    payload: LookupRequest, session: CurrentSession, worker: Worker
) -> dict[str, Any]:
    """Resolve SIDs to names, for rendering an ACL.

    A SID that resolves to nothing comes back unresolved rather than omitted:
    an ACE naming an account that has since been deleted is exactly what an
    administrator opened the editor to find.
    """

    def _read(conn: ServerConnection) -> dict[str, Any]:
        return {"entries": identity.lookup_sids(conn, payload.sids)}

    return await srv_read(worker, session, _read, label="identity.sids")


@router.get("/well-known")
async def well_known(session: CurrentSession, worker: Worker) -> dict[str, Any]:
    """The trustees the picker offers before anyone types anything."""

    def _read(conn: ServerConnection) -> dict[str, Any]:
        return {"entries": identity.well_known(conn)}

    return await srv_read(worker, session, _read, label="identity.wellKnown")
