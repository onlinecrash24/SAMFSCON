"""Bridge between the async API layer and the per-session server connection.

Routers never touch :class:`~samfscon.srv.connection.ServerConnection`
directly. They hand a plain function to :func:`srv_read` or :func:`srv_write`,
which runs it on the session's worker thread with a live connection as its
first argument.

The read/write split exists for one reason: a lost connection may be retried
transparently for a listing, but never for a modification — a write that failed
halfway must surface, not be replayed. Creating a share twice because the first
attempt's reply was lost is exactly the failure this prevents.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from samfscon.auth.session import Session
from samfscon.config import Settings, get_settings
from samfscon.core.errors import OperationTimeout, UpstreamUnavailable
from samfscon.core.executor import SessionWorker
from samfscon.srv.connection import ServerConnection, connect

logger = logging.getLogger(__name__)

T = TypeVar("T")

STATE_KEY = "server"


def _connection(worker: SessionWorker, session: Session, settings: Settings) -> ServerConnection:
    """Return the session's connection, opening one if needed.

    Only ever called from inside the worker thread. The target comes from the
    session, so each signed-in administrator talks to the server they chose,
    with their own credentials.
    """
    conn = worker.state.get(STATE_KEY)
    if conn is None:
        conn = connect(session, settings)
        worker.state[STATE_KEY] = conn
    return conn


def _reconnect(worker: SessionWorker, session: Session, settings: Settings) -> ServerConnection:
    stale = worker.state.pop(STATE_KEY, None)
    if stale is not None:
        # Close the old one first. Its SMB trees still hold handles on the
        # server, and leaving them behind is what makes the next write to the
        # same file fail with a sharing violation from a connection nobody is
        # using any more.
        try:
            stale.close()
        except Exception:  # teardown of a broken connection
            logger.debug("closing the stale connection failed", exc_info=True)

    conn = connect(session, settings)
    worker.state[STATE_KEY] = conn
    return conn


async def srv_read(
    worker: SessionWorker,
    session: Session,
    func: Callable[..., T],
    *args: Any,
    label: str | None = None,
    timeout: float | None = None,
    settings: Settings | None = None,
    **kwargs: Any,
) -> T:
    """Run a read-only operation, reconnecting once if the server drops."""
    resolved = settings or get_settings()

    def _run() -> T:
        conn = _connection(worker, session, resolved)
        try:
            return func(conn, *args, **kwargs)
        except (UpstreamUnavailable, OperationTimeout):
            logger.info("connection lost, reconnecting for %s", label or func.__name__)
            conn = _reconnect(worker, session, resolved)
            return func(conn, *args, **kwargs)

    return await worker.run(
        _run, label=label or getattr(func, "__name__", "srv.read"), timeout=timeout
    )


async def srv_write(
    worker: SessionWorker,
    session: Session,
    func: Callable[..., T],
    *args: Any,
    label: str | None = None,
    timeout: float | None = None,
    settings: Settings | None = None,
    **kwargs: Any,
) -> T:
    """Run a modifying operation. Never retried."""
    resolved = settings or get_settings()

    def _run() -> T:
        conn = _connection(worker, session, resolved)
        return func(conn, *args, **kwargs)

    return await worker.run(
        _run, label=label or getattr(func, "__name__", "srv.write"), timeout=timeout
    )
