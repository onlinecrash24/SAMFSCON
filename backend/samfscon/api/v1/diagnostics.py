"""What stands out on this server, and what this account may do.

Read-only throughout, and deliberately so. Everything this view could offer to
fix is either a line in the text smb.conf, which nothing SAMFSCON speaks can
write, or a global option that belongs to the Server settings console. A button
here would be a promise the endpoint cannot keep.

There is no ``area`` parameter either. SAMFSCON's areas come out of one pass
over one share list, so splitting the fetch by area would read that list five
times or read it once and throw four fifths away. Filtering by area belongs to
the interface, over findings it already has.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from samfscon.auth.deps import CurrentSession, Worker
from samfscon.core import findings_source
from samfscon.core.errors import SamfsconError
from samfscon.srv import diagnostics
from samfscon.srv.access import srv_read
from samfscon.srv.connection import ServerConnection

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("")
async def overview(session: CurrentSession, worker: Worker) -> dict[str, Any]:
    """Who this account is, what the server says it is, and what may be done here."""

    def _read(conn: ServerConnection) -> dict[str, Any]:
        result = diagnostics.whoami(conn)
        result["unreadable"] = []
        try:
            result["facts"] = diagnostics.server_facts(conn)
        except SamfsconError:
            # Level 102 needs more rights than 101, and this is the only
            # function in that module that raises. One permission gap costs
            # this block and not the page — the same rule the gatherer follows.
            result["facts"] = None
            result["unreadable"].append(
                {"area": "management", "subject": "", "reason": "server_facts_unreadable"}
            )
        return result

    return await srv_read(worker, session, _read, label="diagnostics.overview")


@router.get("/findings")
async def server_findings(session: CurrentSession, worker: Worker) -> dict[str, Any]:
    """What is worth telling an administrator about this server.

    One collection. Asking separately for the findings and for what could not
    be read would read the same sections twice and describe two moments.
    """

    def _read(conn: ServerConnection) -> dict[str, Any]:
        collected = findings_source.collect(conn)
        return {
            "generated_at": collected["generated_at"],
            "findings": collected["findings"],
            # Always a list, never absent: the interface must not have to
            # branch on undefined to decide whether anything was missed.
            "unreadable": collected["unreadable"],
            "coverage": collected["coverage"],
        }

    return await srv_read(worker, session, _read, label="diagnostics.findings")


@router.get("/report")
async def server_report(session: CurrentSession, worker: Worker) -> dict[str, Any]:
    """The findings and every value they were decided from, as one reading."""

    def _read(conn: ServerConnection) -> dict[str, Any]:
        return findings_source.collect(conn)

    return await srv_read(worker, session, _read, label="diagnostics.report")
