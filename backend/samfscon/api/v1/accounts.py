"""Local users and groups.

Every endpoint here refuses on a domain member, and that refusal is the feature
rather than a limitation. A member server does have a local SAM; it is almost
always empty and entirely beside the point, because its users come from the
domain. A console that offered to edit it would be offering the wrong thing
convincingly — so it says where those accounts actually live instead.

Passwords appear in exactly two places in this file: the request schema and the
call that encrypts one for the wire. Not in a response, not in an audit record,
not in a log line.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Path

from samfscon.api.common import Audit
from samfscon.auth.deps import CurrentSession, VerifiedSession, VerifiedWorker, Worker
from samfscon.schemas.requests import (
    AccountCreateRequest,
    AccountUpdateRequest,
    MembershipRequest,
    PasswordRequest,
)
from samfscon.srv import accounts
from samfscon.srv.access import srv_read, srv_write
from samfscon.srv.connection import ServerConnection

router = APIRouter(prefix="/accounts", tags=["accounts"])

AccountName = Path(min_length=1, max_length=64, description="Account name")


@router.get("/users")
async def list_users(session: CurrentSession, worker: Worker) -> dict[str, Any]:
    """Every local user account on a standalone server."""

    def _read(conn: ServerConnection) -> dict[str, Any]:
        found = accounts.list_users(conn)
        return {"entries": [entry.describe() for entry in found]}

    return await srv_read(worker, session, _read, label="accounts.users")


@router.get("/groups")
async def list_groups(session: CurrentSession, worker: Worker) -> dict[str, Any]:
    """Every local group, with its members' SIDs.

    Members are SIDs rather than names because a local group can contain domain
    accounts, which have no local identity to name them by. The object picker
    resolves them for display.
    """

    def _read(conn: ServerConnection) -> dict[str, Any]:
        found = accounts.list_groups(conn)
        return {"entries": [entry.describe() for entry in found]}

    return await srv_read(worker, session, _read, label="accounts.groups")


@router.post("/users")
async def create_user(
    payload: AccountCreateRequest,
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
) -> dict[str, Any]:
    """Create a local account.

    Created disabled and without a password, then given one, then enabled if
    that was asked for. An account that existed for a moment with an empty
    password and login enabled is an account somebody could have used, so the
    order is not an implementation detail.
    """

    def _write(conn: ServerConnection) -> dict[str, Any]:
        return accounts.create_user(
            conn,
            name=payload.name,
            password=payload.password,
            full_name=payload.full_name,
            description=payload.description,
            disabled=payload.disabled,
            password_never_expires=payload.password_never_expires,
        )

    with audit.operation("account.create", target=payload.name) as record:
        result = await srv_write(worker, session, _write, label="accounts.create")
        # The flags, not the password. The record says what kind of account was
        # made, which is what an audit trail is for.
        record["disabled"] = payload.disabled
        record["password_never_expires"] = payload.password_never_expires

    return result


@router.patch("/users/{name}")
async def update_user(
    payload: AccountUpdateRequest,
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
    name: str = AccountName,
) -> dict[str, Any]:
    """Change a local account. Only what was sent is changed."""

    def _write(conn: ServerConnection) -> dict[str, Any]:
        return accounts.update_user(
            conn,
            name,
            full_name=payload.full_name,
            description=payload.description,
            disabled=payload.disabled,
            password_never_expires=payload.password_never_expires,
        )

    with audit.operation("account.update", target=name) as record:
        changes = await srv_write(worker, session, _write, label="accounts.update")
        record["changes"] = changes

    return {"name": name, "changes": changes}


@router.post("/users/{name}/password")
async def set_password(
    payload: PasswordRequest,
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
    name: str = AccountName,
) -> dict[str, Any]:
    """Set an account's password.

    The audit record says that a password was set and by whom. It does not say
    what it was, and there is no code path here that could make it.
    """

    def _write(conn: ServerConnection) -> None:
        accounts.set_password(conn, name, payload.password)

    with audit.operation("account.password", target=name):
        await srv_write(worker, session, _write, label="accounts.password")

    return {"name": name, "status": "password_set"}


@router.delete("/users/{name}")
async def delete_user(
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
    name: str = AccountName,
) -> dict[str, Any]:
    """Remove a local account.

    The server's own accounts are refused — deleting the built-in administrator
    is how somebody locks themselves out of the server they are managing.
    """

    def _write(conn: ServerConnection) -> None:
        accounts.delete_user(conn, name)

    with audit.operation("account.delete", target=name):
        await srv_write(worker, session, _write, label="accounts.delete")

    return {"name": name, "status": "deleted"}


@router.post("/groups/{name}/members")
async def set_members(
    payload: MembershipRequest,
    session: VerifiedSession,
    worker: VerifiedWorker,
    audit: Audit,
    name: str = AccountName,
) -> dict[str, Any]:
    """Add and remove group members, by SID.

    Adding somebody who is already a member, or removing somebody who is not,
    is not an error: the desired state is reached either way, and a request
    that fails halfway through because one entry was already right is a request
    that leaves the group in neither state.
    """

    def _write(conn: ServerConnection) -> dict[str, Any]:
        return accounts.set_members(conn, name, add=payload.add, remove=payload.remove)

    with audit.operation("group.members", target=name) as record:
        applied = await srv_write(worker, session, _write, label="accounts.members")
        record["applied"] = applied

    return {"group": name, **applied}
