"""Shares.

Every write goes through the capability check first
(:func:`samfscon.srv.diagnostics.require_share_management`). Not because the
server would not refuse it anyway — it would — but because its refusal is a bare
access-denied that names neither of the two things that actually cause it.
Checking here is what lets the answer say which one, and what command fixes it.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from samfscon.api.common import Audit, LanguageQuery, SharePath
from samfscon.auth.deps import CurrentSession, VerifiedSession, VerifiedWorker, Worker
from samfscon.schemas.requests import ShareCreateRequest, ShareUpdateRequest
from samfscon.srv import diagnostics, shareconf, shares
from samfscon.srv.access import srv_read, srv_write
from samfscon.srv.connection import ServerConnection

router = APIRouter(prefix="/shares", tags=["shares"])


@router.get("")
async def list_shares(
    session: CurrentSession,
    worker: Worker,
    administrative: bool = False,
) -> dict[str, Any]:
    """Every share on the server.

    The administrative ones (IPC$, ADMIN$, print$) are left out by default.
    They belong to Samba, this console cannot change them, and a list that
    opens with three rows nobody may touch buries the ones that matter.
    """

    def _read(conn: ServerConnection) -> dict[str, Any]:
        found = shares.list_shares(conn, include_administrative=administrative)
        caps = diagnostics.capabilities(conn)
        return {
            "entries": [share.describe() for share in found],
            # Sent with the list so the interface can decide up front whether
            # to offer a "new share" button at all, rather than offering one
            # that always fails.
            "capabilities": caps.describe(),
        }

    return await srv_read(worker, session, _read, label="shares.list")


@router.get("/catalogue")
async def option_catalogue(
    session: CurrentSession, language: LanguageQuery = "en"
) -> dict[str, Any]:
    """The share options the interface can build forms from.

    Static, and deliberately not behind a server round trip: it describes what
    SAMFSCON knows how to edit, not what one particular server has.
    """
    return {"options": shareconf.describe_catalogue(language)}


@router.get("/{name}")
async def get_share(name: SharePath, session: CurrentSession, worker: Worker) -> dict[str, Any]:
    """One share, with its stored options."""

    def _read(conn: ServerConnection) -> dict[str, Any]:
        share = shares.get_share(conn, name)
        return share.describe()

    return await srv_read(worker, session, _read, label="shares.get")


@router.post("")
async def create_share(
    payload: ShareCreateRequest,
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
) -> dict[str, Any]:
    """Create a share.

    The three switches on the first tab — read only, browseable, guest ok — are
    ordinary smb.conf options and travel with the rest. They have their own
    fields in the request because every console has them on its first tab, not
    because the protocol treats them differently.
    """
    options = dict(payload.options)
    options["read only"] = "yes" if payload.read_only else "no"
    options["browseable"] = "yes" if payload.browseable else "no"
    options["guest ok"] = "yes" if payload.guest_ok else "no"

    def _write(conn: ServerConnection) -> dict[str, Any]:
        diagnostics.require_share_management(diagnostics.capabilities(conn))
        return shares.create_share(
            conn,
            name=payload.name,
            path=payload.path,
            comment=payload.comment,
            options=options,
        )

    with audit.operation("share.create", target=payload.name) as record:
        result = await srv_write(worker, session, _write, label="shares.create")
        record["path"] = payload.path
        record["options"] = result.get("options")

    return result


@router.patch("/{name}")
async def update_share(
    name: SharePath,
    payload: ShareUpdateRequest,
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
) -> dict[str, Any]:
    """Change a share. Only what was sent is changed."""
    options: dict[str, str | None] = dict(payload.options or {})
    for field_name, option in (
        ("read_only", "read only"),
        ("browseable", "browseable"),
        ("guest_ok", "guest ok"),
    ):
        value = getattr(payload, field_name)
        if value is not None:
            options[option] = "yes" if value else "no"

    def _write(conn: ServerConnection) -> dict[str, Any]:
        diagnostics.require_share_management(diagnostics.capabilities(conn))
        return shares.update_share(
            conn,
            name,
            path=payload.path,
            comment=payload.comment,
            options=options,
        )

    with audit.operation("share.update", target=name) as record:
        changes = await srv_write(worker, session, _write, label="shares.update")
        record["changes"] = changes

    return {"name": name, "changes": changes}


@router.delete("/{name}")
async def delete_share(
    name: SharePath,
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
) -> dict[str, Any]:
    """Remove a share, and the configuration that belongs to it.

    The directory on the server is left alone. Deleting a share is a
    configuration change; deleting the data behind it is not something a
    console should do as a side effect of one, and SAMFSCON could not do it
    over these protocols anyway.
    """

    def _write(conn: ServerConnection) -> None:
        diagnostics.require_share_management(diagnostics.capabilities(conn))
        shares.delete_share(conn, name)

    with audit.operation("share.delete", target=name):
        await srv_write(worker, session, _write, label="shares.delete")

    return {"name": name, "status": "deleted"}
