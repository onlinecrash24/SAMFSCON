"""Sign-in, sign-out and session state."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Request, Response

from samfscon.auth import kerberos
from samfscon.auth.deps import CurrentSession, client_ip
from samfscon.auth.session import SessionSecret, get_store, get_throttle
from samfscon.config import get_settings
from samfscon.core.audit import get_audit
from samfscon.core.errors import SamfsconError
from samfscon.core.executor import get_registry
from samfscon.schemas.requests import LoginRequest
from samfscon.srv import targets
from samfscon.srv.access import srv_read

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, Any]:
    """Open a session against the chosen file server.

    Which server, and in which mode, comes from the request rather than from
    the container's configuration: an address, a configured profile, or the
    default. Resolving it may involve an unauthenticated probe to learn the
    server's realm and its own name — that is what lets an administrator type
    a bare IP address.

    What happens with the password then depends on the mode, and the difference
    is the whole security story of this application:

    * **Domain member** — it goes into the KDC exchange and is out of scope
      immediately. Everything afterwards runs off the resulting ticket.
    * **Standalone** — there is no ticket to run off. NTLMSSP needs it at every
      connection setup, so it is kept in memory for the session's lifetime, in
      a :class:`~samfscon.auth.session.SessionSecret` and nowhere else.
    """
    settings = get_settings()
    store = get_store()
    throttle = get_throttle()
    audit = get_audit()
    address = client_ip(request)

    session_id = store.new_id()
    registry = get_registry()
    worker = registry.get(session_id)
    ccache = None

    def _fail(exc: SamfsconError, principal_name: str | None, target: Any = None) -> None:
        registry.drop(session_id)
        if ccache is not None:
            kerberos.destroy_ticket(ccache)
        if principal_name:
            throttle.record_failure(principal_name, address)
        audit.record(
            action="auth.login",
            actor=principal_name,
            result="error",
            error=exc.message,
            error_code=exc.code,
            client_ip=address,
            extra={"server": target.display_name} if target is not None else None,
        )

    # Resolving the target probes the network, so it runs on the worker thread.
    try:
        target = await worker.run(
            targets.resolve_target,
            settings,
            server=payload.server,
            mode=payload.mode,
            realm=payload.realm,
            profile_id=payload.profile_id,
            label="server.resolve",
            timeout=30,
        )
    except SamfsconError as exc:
        _fail(exc, None)
        raise

    # A standalone server qualifies accounts with its own NetBIOS name; a domain
    # member with the realm. Either way this is what an unqualified user name
    # gets completed to.
    default_realm = target.realm if target.uses_kerberos else (target.netbios_name or "")
    principal = kerberos.parse_principal(payload.username, default_realm or "")

    try:
        throttle.check(principal.username, address)
    except SamfsconError as exc:
        registry.drop(session_id)
        raise exc

    secret: SessionSecret | None = None
    if target.uses_kerberos:
        ccache = kerberos.ccache_path_for(settings, session_id)
        try:
            # Ticket acquisition blocks on the network, so it belongs on the
            # session's worker thread like every other Samba call.
            await worker.run(
                kerberos.acquire_ticket,
                principal,
                payload.password,
                ccache,
                settings,
                target,
                label="kerberos.kinit",
                timeout=45,
            )
        except SamfsconError as exc:
            _fail(exc, principal.username, target)
            raise
        expires_hard_at = kerberos.ticket_expiry(ccache) or kerberos.default_expiry()
    else:
        # No KDC, so nothing to acquire and nothing that expires on its own.
        # The hard limit is set here instead, from the same lifetime a ticket
        # would have had: a password living in this process should not do so
        # indefinitely just because nobody closed the tab.
        secret = SessionSecret(payload.password)
        expires_hard_at = datetime.now(UTC) + timedelta(
            minutes=max(settings.session_idle_minutes, 1) * 10
        )

    session = store.create(
        session_id=session_id,
        principal=principal,
        target=target,
        ccache=ccache,
        secret=secret,
        expires_hard_at=expires_hard_at,
        client_ip=address,
        user_agent=request.headers.get("user-agent"),
    )

    # Connect straight away: credentials the server will not accept should
    # surface here, not on the user's first click.
    try:
        facts = await srv_read(
            worker,
            session,
            lambda conn: {
                "server": conn.info.describe(),
                "connection": conn.transport.describe(),
            },
            label="smb.connect",
        )
    except SamfsconError as exc:
        store.drop(session_id, reason="connect_failed")
        throttle.record_failure(principal.username, address)
        audit.record(
            action="auth.login",
            actor=principal.full,
            result="error",
            error=exc.message,
            error_code=exc.code,
            client_ip=address,
            extra={"server": target.display_name},
        )
        raise

    throttle.record_success(principal.username, address)
    audit.record(
        action="auth.login",
        actor=principal.full,
        result="ok",
        session_id=session_id,
        client_ip=address,
        # Which server and how it was authenticated — the question every audit
        # trail gets asked once more than one server is in play, and the one
        # place the NTLM sessions can be told from the Kerberos ones after the
        # fact.
        extra={
            "server": target.display_name,
            "mode": target.mode,
            "auth": facts["connection"]["auth"],
            "encrypted": facts["connection"]["encrypted"],
        },
    )

    _set_session_cookie(response, session_id)
    return {
        "principal": principal.full,
        "username": principal.username,
        "realm": principal.realm,
        "csrf_token": session.csrf_token,
        "expires_at": session.expires_at,
        "server": facts["server"],
        "connection": facts["connection"],
        "target": target.describe(),
        # Said out loud rather than left to be inferred from the mode. The
        # interface shows it in the session bar for as long as the session
        # lasts, because it is the one thing about a standalone session an
        # administrator should not have to remember on their own.
        "holds_password": session.secret is not None,
    }


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict[str, Any]:
    """End the session, destroying its ticket or clearing its password."""
    settings = get_settings()
    session_id = request.cookies.get(settings.cookie_name)

    if session_id:
        store = get_store()
        try:
            session = store.get(session_id)
            actor = session.principal.full
        except SamfsconError:
            actor = None
        store.drop(session_id, reason="logout")
        get_audit().record(
            action="auth.logout",
            actor=actor,
            session_id=session_id,
            client_ip=client_ip(request),
        )

    response.delete_cookie(
        settings.cookie_name,
        path="/",
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
    )
    return {"status": "signed_out"}


@router.get("/session")
async def session_info(session: CurrentSession) -> dict[str, Any]:
    """Current session, for restoring state after a page reload."""
    worker = get_registry().get(session.id)
    facts = await srv_read(
        worker,
        session,
        lambda conn: {
            "server": conn.info.describe(),
            "connection": conn.transport.describe(),
        },
        label="smb.info",
    )
    return {
        "principal": session.principal.full,
        "username": session.principal.username,
        "realm": session.principal.realm,
        "csrf_token": session.csrf_token,
        "expires_at": session.expires_at,
        "expires_hard_at": session.expires_hard_at,
        "created_at": session.created_at,
        "server": facts["server"],
        "connection": facts["connection"],
        "target": session.target.describe(),
        "holds_password": session.secret is not None,
    }


@router.get("/whoami")
async def whoami(session: CurrentSession) -> dict[str, Any]:
    """Who the server thinks we are, and what that account may do here.

    Useful when an administrator wonders why an action is refused: this reports
    the account as the server resolved it, together with the two capabilities
    every refusal on this console comes down to — whether shares can be created
    at all on this server, and whether this account holds the privilege to do
    it. Answering both in one place is what turns "access denied" from a dead
    end into something actionable.
    """
    from samfscon.srv import diagnostics

    worker = get_registry().get(session.id)
    return await srv_read(worker, session, diagnostics.whoami, label="srv.whoami")


def _cookie_secure() -> bool:
    settings = get_settings()
    # dev_mode exists so the container can be reached over plain http on
    # localhost; a Secure cookie would never be sent back in that case.
    return settings.cookie_secure and not settings.dev_mode


def _set_session_cookie(response: Response, session_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.cookie_name,
        session_id,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        path="/",
        # No max-age: a session cookie disappears when the browser closes, and
        # the server-side expiry is authoritative anyway.
    )
