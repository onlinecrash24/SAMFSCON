"""The server's global configuration.

Everything here goes through ``registry.GLOBAL_SECTION`` — the same store the
shares use, the same pipe, the same limits. The one thing this router does that
the shares router does not is refuse to create a section the server may not be
reading: a console that silently wrote a global block into a registry nothing
includes would leave an administrator certain they had changed something.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from samfscon.api.common import Audit, LanguageQuery
from samfscon.auth.deps import CurrentSession, VerifiedSession, VerifiedWorker, Worker
from samfscon.config import get_settings
from samfscon.schemas.requests import GlobalConfigUpdateRequest
from samfscon.srv import globalconf, registry
from samfscon.srv.access import srv_read, srv_write
from samfscon.srv.connection import ServerConnection

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/catalogue")
async def option_catalogue(
    session: CurrentSession,
    language: LanguageQuery = "en",
) -> dict[str, Any]:
    """The global options the interface can build forms from.

    Static and deliberately not behind a server round trip, exactly like
    ``GET /shares/catalogue``: it describes what SAMFSCON knows how to edit,
    not what one server has. The mode comes from the session rather than from a
    parameter — the caller cannot choose which kind of server it is signed in
    to, and a mode in the query string would be a fact with two owners.
    """
    return {
        "options": globalconf.describe_catalogue(session.target.mode, language),
        "mode": session.target.mode,
    }


@router.get("")
async def get_config(session: CurrentSession, worker: Worker) -> dict[str, Any]:
    """What the registry's global section holds, and what the server reports.

    One read for both. Asking separately would let the screen show a stored
    value from one moment and an effective value from another, and the
    difference between the two is the only thing this view is for.
    """

    def _read(conn: ServerConnection) -> dict[str, Any]:
        return globalconf.read(conn).describe()

    return await srv_read(worker, session, _read, label="config.get")


@router.patch("")
async def update_config(
    payload: GlobalConfigUpdateRequest,
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
) -> dict[str, Any]:
    """Change global options. Only what was sent is changed.

    ``confirm`` names the risky options the caller is accepting, one by one. A
    single boolean would have been shorter and would have let a client written
    today blanket-confirm an option added to the catalogue next month.
    """
    console_min = get_settings().smb_min_protocol

    def _write(conn: ServerConnection) -> dict[str, Any]:
        return globalconf.write(
            conn,
            dict(payload.options),
            confirm=frozenset(payload.confirm),
            create_section=payload.create_section,
            console_min_protocol=console_min,
        )

    with audit.operation("config.update", target=registry.GLOBAL_SECTION) as record:
        # srv_write is never retried: a half-failed configuration write must
        # surface, not be replayed.
        result = await srv_write(worker, session, _write, label="config.update")
        # `changes` and `extra` are the two keys AuditLog.operation reads
        # (core/audit.py:186 and :190). Four existing sites set keys it never
        # looks at, and their detail is dropped from the trail without a word.
        record["changes"] = result["applied"]
        record["extra"]["confirmed"] = sorted(payload.confirm)
        record["extra"]["section_created"] = result["section_created"]

    return result
