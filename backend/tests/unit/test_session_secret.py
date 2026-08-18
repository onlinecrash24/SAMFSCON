"""The standalone password must not leak, by any of the usual routes.

SAMFSCON holds a password in memory for standalone sessions, which is the one
place it departs from SAMADCON's "the password is used once and forgotten".
That trade is only acceptable if the password stays where it was put, so the
ways it could get out are tested rather than reviewed.

Every case here corresponds to a real way secrets escape: a repr in a log line,
a dataclass serialised on its way to the front end, a pickle in a cache, an
audit record built from the session object.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import pickle

import pytest

from samfscon.auth.kerberos import Principal
from samfscon.auth.session import Session, SessionSecret, SessionStore
from samfscon.config import MODE_STANDALONE
from samfscon.core.errors import SessionExpired
from samfscon.srv.target import ServerTarget

# A test value, not a credential.
PASSWORD = "correct-horse-battery-staple"


def _session(store: SessionStore) -> Session:
    from datetime import UTC, datetime, timedelta

    return store.create(
        session_id="test-session-id",
        principal=Principal(username="admin", realm="FS1"),
        target=ServerTarget(host="fs1.example.lan", mode=MODE_STANDALONE, workgroup="FS1"),
        secret=SessionSecret(PASSWORD),
        expires_hard_at=datetime.now(UTC) + timedelta(hours=1),
    )


def test_reveal_returns_the_password() -> None:
    """The point of the wrapper is to hand the password to the bindings."""
    assert SessionSecret(PASSWORD).reveal() == PASSWORD


def test_repr_hides_the_password() -> None:
    secret = SessionSecret(PASSWORD)
    assert PASSWORD not in repr(secret)
    assert PASSWORD not in str(secret)
    assert PASSWORD not in f"{secret}"


def test_session_repr_hides_the_password() -> None:
    """A dataclass prints its fields, and a session is logged by repr in places."""
    store = SessionStore()
    session = _session(store)
    assert PASSWORD not in repr(session)


def test_session_is_not_serialisable_with_the_password() -> None:
    """asdict() is how a session accidentally becomes an API response."""
    store = SessionStore()
    session = _session(store)

    with pytest.raises((TypeError, ValueError)):
        json.dumps(dataclasses.asdict(session), default=str)


def test_secret_cannot_be_pickled() -> None:
    """A cache that pickles its values would write the password to disk."""
    with pytest.raises(TypeError):
        pickle.dumps(SessionSecret(PASSWORD))


def test_drop_clears_the_secret() -> None:
    """Signing out has to take the password with it."""
    store = SessionStore()
    session = _session(store)
    secret = session.secret
    assert secret is not None

    store.drop(session.id, reason="logout")

    with pytest.raises(SessionExpired):
        secret.reveal()


def test_close_all_clears_every_secret() -> None:
    """Container shutdown is the other way a session ends."""
    store = SessionStore()
    session = _session(store)
    secret = session.secret
    assert secret is not None

    store.close_all()

    with pytest.raises(SessionExpired):
        secret.reveal()


def test_sweep_clears_the_secret_of_an_expired_session() -> None:
    """An abandoned tab must not leave a password in memory indefinitely."""
    from datetime import UTC, datetime, timedelta

    store = SessionStore()
    session = _session(store)
    secret = session.secret
    assert secret is not None

    session.expires_hard_at = datetime.now(UTC) - timedelta(seconds=1)
    assert store.sweep() == 1

    with pytest.raises(SessionExpired):
        secret.reveal()


def test_logging_a_session_does_not_emit_the_password(caplog: pytest.LogCaptureFixture) -> None:
    """The store logs on open and close; neither line may carry it."""
    caplog.set_level(logging.DEBUG)
    store = SessionStore()
    session = _session(store)
    store.drop(session.id)

    assert PASSWORD not in caplog.text


def test_a_kerberos_session_holds_no_secret_at_all() -> None:
    """The domain-member path must not acquire the standalone trade by accident."""
    from datetime import UTC, datetime, timedelta
    from pathlib import Path

    from samfscon.config import MODE_AD_MEMBER

    store = SessionStore()
    session = store.create(
        session_id="kerberos-session",
        principal=Principal(username="admin", realm="EXAMPLE.LAN"),
        target=ServerTarget(
            host="fs1.example.lan", mode=MODE_AD_MEMBER, realm="EXAMPLE.LAN"
        ),
        ccache=Path("/dev/shm/samfscon-ccache/tkt-test"),
        expires_hard_at=datetime.now(UTC) + timedelta(hours=1),
    )
    assert session.secret is None
