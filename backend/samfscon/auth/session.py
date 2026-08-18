"""Session store, the standalone secret, and login throttling.

A session is little more than a pointer to the credentials the file server will
accept, plus the metadata needed to expire it. It lives in memory only:
restarting the container invalidates every session, which is the honest
behaviour given that Kerberos caches live on tmpfs and are gone anyway.

Which credentials those are depends on the server:

* **Domain member** — a Kerberos ticket in a session-private cache on tmpfs,
  exactly as SAMADCON does it. The password is used once, to get the ticket.
* **Standalone** — there is no KDC and therefore no ticket. NTLMSSP needs the
  password at every connection setup, so the session holds it, in this process
  and nowhere else. :class:`SessionSecret` is the only place it lives; it is
  never serialised, never logged, never returned to the front end, and it is
  overwritten when the session ends.

That second case is a real trade, and it is named rather than hidden — in the
sign-in form, in the README, and here.
"""

from __future__ import annotations

import ctypes
import logging
import secrets
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from samfscon.auth.kerberos import Principal, destroy_ticket
from samfscon.core.errors import AuthenticationError, SessionExpired
from samfscon.core.executor import get_registry
from samfscon.srv.target import ServerTarget

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


class SessionSecret:
    """A password held for the lifetime of one standalone session.

    Deliberately not a plain ``str`` on the session dataclass. A string would
    be printed by ``repr()``, copied into an audit record by a careless
    ``asdict()``, and serialised by anything that reaches for
    ``dataclasses.asdict`` on the way to the front end. This wrapper closes all
    three by construction rather than by discipline.

    ``clear()`` overwrites the buffer before dropping it. Python offers no
    guarantee that no copy was made along the way — the bindings take one, for
    a start — so this narrows the window rather than closing it. Claiming
    otherwise would be exactly the kind of security promise this project is
    written to avoid.
    """

    __slots__ = ("_buffer",)

    def __init__(self, password: str) -> None:
        self._buffer: bytearray | None = bytearray(password.encode("utf-8"))

    def reveal(self) -> str:
        if self._buffer is None:
            raise SessionExpired(
                "The session's credentials have been cleared.",
                code="secret_cleared",
                hint="Sign in again.",
            )
        return self._buffer.decode("utf-8")

    def clear(self) -> None:
        buffer, self._buffer = self._buffer, None
        if buffer is None:
            return
        # bytearray storage is mutable and contiguous, so this overwrites the
        # bytes rather than rebinding a name.
        ctypes.memset((ctypes.c_char * len(buffer)).from_buffer(buffer), 0, len(buffer))

    # The three ways a secret leaks by accident, closed explicitly.
    def __repr__(self) -> str:
        return "<SessionSecret hidden>"

    __str__ = __repr__

    def __reduce__(self):
        raise TypeError("a SessionSecret must not be serialised")


@dataclass
class Session:
    id: str
    principal: Principal
    # The file server this session is signed in to. Chosen at sign-in, not at
    # container start — different sessions may target different servers, in
    # different modes.
    target: ServerTarget
    csrf_token: str
    expires_hard_at: datetime
    idle_timeout: timedelta
    # Set for a domain member, None for a standalone server.
    ccache: Path | None = None
    # Set for a standalone server, None for a domain member. Never both.
    secret: SessionSecret | None = field(default=None, repr=False)
    created_at: datetime = field(default_factory=_now)
    last_seen: datetime = field(default_factory=_now)
    client_ip: str | None = None
    user_agent: str | None = None

    @property
    def expires_at(self) -> datetime:
        """Whichever comes first: the hard limit or the idle timeout.

        For a domain member the hard limit is the Kerberos ticket's end. A
        standalone session has no ticket to expire, so the hard limit is set at
        sign-in from the configured lifetime — a password living in memory
        should not do so indefinitely just because nobody closed the tab.
        """
        return min(self.expires_hard_at, self.last_seen + self.idle_timeout)

    def is_expired(self, now: datetime | None = None) -> bool:
        return self.expires_at <= (now or _now())

    def touch(self) -> None:
        self.last_seen = _now()


class SessionStore:
    def __init__(self, idle_minutes: int = 60) -> None:
        self.idle_timeout = timedelta(minutes=idle_minutes)
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(
        self,
        *,
        session_id: str,
        principal: Principal,
        target: ServerTarget,
        expires_hard_at: datetime,
        ccache: Path | None = None,
        secret: SessionSecret | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> Session:
        session = Session(
            id=session_id,
            principal=principal,
            target=target,
            ccache=ccache,
            secret=secret,
            csrf_token=secrets.token_urlsafe(32),
            expires_hard_at=expires_hard_at,
            idle_timeout=self.idle_timeout,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        with self._lock:
            self._sessions[session_id] = session
        logger.info(
            "session opened",
            extra={
                "session": session_id[:8],
                "actor": principal.full,
                "server": target.display_name,
                "mode": target.mode,
            },
        )
        return session

    def get(self, session_id: str | None) -> Session:
        if not session_id:
            raise SessionExpired("Not signed in.", code="not_authenticated")

        with self._lock:
            session = self._sessions.get(session_id)

        if session is None:
            raise SessionExpired("The session is unknown or has ended.")
        if session.is_expired():
            self.drop(session_id, reason="expired")
            raise SessionExpired("The session has expired.", hint="Sign in again.")

        session.touch()
        return session

    def drop(self, session_id: str, *, reason: str = "logout") -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)

        if session is None:
            return

        # Order matters: release the Samba handles on their own worker thread
        # first, then remove the credentials they authenticate with. The other
        # way round, a teardown that still has to talk to the server — an SMB
        # session hanging up politely — would find nothing to authenticate with.
        get_registry().drop(session_id)
        if session.ccache is not None:
            destroy_ticket(session.ccache)
        if session.secret is not None:
            session.secret.clear()
        logger.info(
            "session closed",
            extra={"session": session_id[:8], "actor": session.principal.full, "reason": reason},
        )

    def sweep(self) -> int:
        """Drop expired sessions. Returns how many were removed."""
        now = _now()
        with self._lock:
            stale = [sid for sid, s in self._sessions.items() if s.is_expired(now)]
        for session_id in stale:
            self.drop(session_id, reason="expired")
        return len(stale)

    def close_all(self) -> None:
        for session_id in list(self._sessions):
            self.drop(session_id, reason="shutdown")

    def count(self) -> int:
        return len(self._sessions)

    @staticmethod
    def new_id() -> str:
        return secrets.token_urlsafe(32)


class LoginThrottle:
    """Stops repeated failures before they reach the server.

    Without this, the sign-in form would be a convenient way to lock out every
    account the server knows. Accounts and source addresses are counted
    separately, so an attacker from one address cannot lock an administrator
    out from a different one — the account counter still protects the accounts,
    but the address counter is what usually trips first.
    """

    def __init__(self, max_attempts: int = 5, lockout_minutes: int = 5) -> None:
        self.max_attempts = max_attempts
        self.lockout = timedelta(minutes=lockout_minutes)
        self._failures: dict[str, tuple[int, datetime]] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        """Zero for either setting turns throttling off.

        Without this, a lockout window of zero would compare ``now - last > 0``
        against a clock whose resolution is coarser than the two calls, and
        block forever instead of never.
        """
        return self.max_attempts > 0 and self.lockout > timedelta(0)

    def _keys(self, username: str, client_ip: str | None) -> list[str]:
        keys = [f"user:{username.lower()}"]
        if client_ip:
            keys.append(f"ip:{client_ip}")
        return keys

    def check(self, username: str, client_ip: str | None = None) -> None:
        if not self.enabled:
            return
        now = _now()
        with self._lock:
            for key in self._keys(username, client_ip):
                entry = self._failures.get(key)
                if entry is None:
                    continue
                count, last = entry
                if now - last > self.lockout:
                    del self._failures[key]
                    continue
                if count >= self.max_attempts:
                    remaining = int((self.lockout - (now - last)).total_seconds())
                    raise AuthenticationError(
                        "Too many failed sign-in attempts.",
                        code="login_throttled",
                        status_code=429,
                        hint=(
                            "SAMFSCON pauses further attempts so the account is "
                            "not locked out."
                        ),
                        context={"retry_after_seconds": max(remaining, 1)},
                    )

    def record_failure(self, username: str, client_ip: str | None = None) -> None:
        if not self.enabled:
            return
        now = _now()
        with self._lock:
            for key in self._keys(username, client_ip):
                count, last = self._failures.get(key, (0, now))
                if now - last > self.lockout:
                    count = 0
                self._failures[key] = (count + 1, now)

    def record_success(self, username: str, client_ip: str | None = None) -> None:
        with self._lock:
            for key in self._keys(username, client_ip):
                self._failures.pop(key, None)


_store: SessionStore | None = None
_throttle: LoginThrottle | None = None


def get_store() -> SessionStore:
    global _store
    if _store is None:
        from samfscon.config import get_settings

        _store = SessionStore(idle_minutes=get_settings().session_idle_minutes)
    return _store


def get_throttle() -> LoginThrottle:
    global _throttle
    if _throttle is None:
        from samfscon.config import get_settings

        settings = get_settings()
        _throttle = LoginThrottle(
            max_attempts=settings.login_max_attempts,
            lockout_minutes=settings.login_lockout_minutes,
        )
    return _throttle


def reset_auth_state() -> None:
    """Test hook."""
    global _store, _throttle
    if _store is not None:
        _store.close_all()
    _store = None
    _throttle = None
