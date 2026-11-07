"""The sign-in throttle, and what it has to stop before anything else runs.

Signing in resolves its target first, and resolving may probe the network — an
unauthenticated SMB and LSA exchange with whatever host the form named. Two
things were wrong with the order. The throttle was consulted only after that
probe, so a caller already over the limit still made the container talk to a
host of its choosing. And a failure *during* resolution had no account name to
count against, so it was not counted at all: the form could be used to probe
host after host without ever meeting the throttle.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from samfscon.auth.session import LoginThrottle, get_throttle, reset_auth_state
from samfscon.core.errors import InvalidRequest
from samfscon.main import app


@pytest.fixture
def client():
    reset_auth_state()
    with TestClient(app) as test_client:
        yield test_client
    reset_auth_state()


@pytest.fixture
def resolutions(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Counts every attempt to resolve a target — the step that probes."""
    from samfscon.srv import targets

    attempts: list[str] = []

    def refuse(*_args, **kwargs):
        attempts.append(kwargs.get("server") or "")
        raise InvalidRequest("No such server.", code="server_unreachable")

    monkeypatch.setattr(targets, "resolve_target", refuse)
    return attempts


def sign_in(client: TestClient, server: str = "fs1.example.lan"):
    return client.post(
        "/api/v1/auth/login",
        json={"username": "x", "password": "x", "server": server},
    )


# ---------------------------------------------------------------------------
# The throttle itself
# ---------------------------------------------------------------------------


def test_an_address_over_the_limit_is_refused_on_its_own() -> None:
    throttle = LoginThrottle(max_attempts=2, lockout_minutes=5)
    throttle.record_address_failure("10.0.0.9")
    throttle.record_address_failure("10.0.0.9")

    with pytest.raises(Exception) as raised:
        throttle.check_address("10.0.0.9")
    assert getattr(raised.value, "code", None) == "login_throttled"


def test_another_address_is_not_affected() -> None:
    throttle = LoginThrottle(max_attempts=2, lockout_minutes=5)
    throttle.record_address_failure("10.0.0.9")
    throttle.record_address_failure("10.0.0.9")
    throttle.check_address("10.0.0.10")


def test_an_address_failure_counts_towards_the_full_check() -> None:
    """One counter per address, whichever stage the failure happened at."""
    throttle = LoginThrottle(max_attempts=2, lockout_minutes=5)
    throttle.record_address_failure("10.0.0.9")
    throttle.record_failure("alice", "10.0.0.9")

    with pytest.raises(Exception) as raised:
        throttle.check("bob", "10.0.0.9")
    assert getattr(raised.value, "code", None) == "login_throttled"


# ---------------------------------------------------------------------------
# Through the sign-in route
# ---------------------------------------------------------------------------


def test_a_failed_resolution_is_counted(client: TestClient, resolutions: list[str]) -> None:
    """Before: no account name, no record — the probe loop never met the throttle."""
    limit = get_throttle().max_attempts
    for index in range(limit):
        assert sign_in(client, f"host{index}.example.lan").status_code != 429

    assert sign_in(client, "one-more.example.lan").status_code == 429


def test_a_throttled_caller_causes_no_probe(client: TestClient, resolutions: list[str]) -> None:
    """Over the limit, the request stops before the step that talks to a host."""
    limit = get_throttle().max_attempts
    for index in range(limit):
        sign_in(client, f"host{index}.example.lan")
    probed = len(resolutions)

    assert sign_in(client, "after-the-limit.example.lan").status_code == 429
    assert len(resolutions) == probed, "a throttled sign-in still resolved its target"


# ---------------------------------------------------------------------------
# One answer for an unknown account and a wrong password
# ---------------------------------------------------------------------------


@pytest.fixture
def kerberos_refuses(monkeypatch: pytest.MonkeyPatch):
    """A member server that resolves, and a KDC that refuses with *status*."""
    from samfscon.api.v1 import auth as auth_route
    from samfscon.auth import kerberos
    from samfscon.core import audit as audit_module
    from samfscon.srv import targets
    from samfscon.srv.target import ServerTarget

    recorded: list[dict] = []

    class Audit:
        def record(self, **kwargs):
            recorded.append(kwargs)

    monkeypatch.setattr(
        targets,
        "resolve_target",
        lambda *_a, **_k: ServerTarget(
            host="fs1.example.lan", mode="ad_member", realm="EXAMPLE.LAN",
            server_fqdn="fs1.example.lan",
        ),
    )
    monkeypatch.setattr(auth_route, "get_audit", lambda: Audit())
    monkeypatch.setattr(audit_module, "get_audit", lambda: Audit())

    def arrange(raw: str) -> None:
        from samfscon.core.errors import translate

        def refuse(*_args, **_kwargs):
            raise translate(RuntimeError(raw))

        monkeypatch.setattr(kerberos, "acquire_ticket", refuse)

    return arrange, recorded


@pytest.mark.parametrize(
    "raw",
    [
        "Client 'nobody@EXAMPLE.LAN' not found in Kerberos database",
        "kinit: Preauthentication failed while getting initial credentials",
        "NT_STATUS_NO_SUCH_USER",
        "NT_STATUS_WRONG_PASSWORD",
    ],
)
def test_the_answer_does_not_say_whether_the_account_exists(
    client: TestClient, kerberos_refuses, raw: str
) -> None:
    """Otherwise the sign-in page lists the domain's accounts, one guess at a
    time, without anybody knowing a password."""
    arrange, _recorded = kerberos_refuses
    arrange(raw)

    response = sign_in(client)
    body = response.json()
    assert response.status_code == 401, body
    error = body.get("error", body)
    assert error["code"] == "invalid_credentials"
    assert error["message"] == "Wrong user name or password."
    # Nothing beside it that names the real cause.
    assert raw not in response.text
    assert "not found" not in response.text.lower()


def test_the_real_cause_still_reaches_the_audit_log(client: TestClient, kerberos_refuses) -> None:
    """Merged for the caller, never for the operator."""
    arrange, recorded = kerberos_refuses
    arrange("Client 'nobody@EXAMPLE.LAN' not found in Kerberos database")

    sign_in(client)
    assert any(entry.get("error_code") == "kerberos_principal_unknown" for entry in recorded)
