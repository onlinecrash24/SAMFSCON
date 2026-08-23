"""The clock every Kerberos command is read against.

``ticket_expiry`` parses what ``klist`` prints and stamps it UTC. klist prints
*local* time, so that is only correct while the process runs in UTC — which was
true of the container and true of nothing else. A deployment that sets ``TZ``,
or a run outside the container, made the ticket look longer or shorter than it
is; longer is the bad direction, because the session then outlives the ticket
and calls fail partway through somebody's work.

What is tested here is the environment handed to the subprocess, not Kerberos.
That is where the guarantee now lives: pinning TZ makes the reader's assumption
a condition of the call rather than a property of the machine.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from samfscon.auth import kerberos


@pytest.fixture(autouse=True)
def _stub_krb5_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """No generated krb5.conf on a runner, and none needed for this."""

    class Configuration:
        def environment(self) -> dict[str, str]:
            return {"KRB5_CONFIG": "/etc/samfscon/krb5.conf"}

    monkeypatch.setattr("samfscon.auth.krb5conf.get_krb5_configuration", lambda: Configuration())


def test_every_kerberos_command_runs_in_utc() -> None:
    assert kerberos._krb5_env()["TZ"] == "UTC"


def test_the_pin_survives_a_machine_that_says_otherwise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The inherited value is the one being overruled, so set it and look."""
    monkeypatch.setenv("TZ", "Europe/Berlin")
    assert kerberos._krb5_env()["TZ"] == "UTC"


def test_the_rest_of_the_environment_still_comes_along() -> None:
    """Pinning one variable must not mean building the environment afresh."""
    env = kerberos._krb5_env()
    assert env["KRB5_CONFIG"] == "/etc/samfscon/krb5.conf"
    for name in os.environ:
        if name != "TZ":
            assert name in env


def test_a_ccache_is_named_only_when_one_is_given() -> None:
    """klist takes it as an argument; kinit needs it in the environment."""
    assert "KRB5CCNAME" not in kerberos._krb5_env()
    assert kerberos._krb5_env(Path("/dev/shm/samfscon-ccache/abc"))["KRB5CCNAME"]


def test_the_expiry_reader_asks_for_the_environment_it_was_promised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The pin is worth nothing if the call that depends on it does not use it.

    klist's own output is the fixture: a time with no zone in it, which is the
    whole reason the zone has to be decided elsewhere.
    """
    seen: dict[str, Any] = {}

    class Result:
        returncode = 0
        stdout = (
            b"Ticket cache: FILE:/dev/shm/samfscon-ccache/abc\n"
            b"Default principal: administrator@SPAM-DENY.LOCAL\n\n"
            b"Valid starting     Expires            Service principal\n"
            b"08/23/26 09:12:00  08/23/26 19:12:00  krbtgt/SPAM-DENY.LOCAL@SPAM-DENY.LOCAL\n"
        )
        stderr = b""

    def run(command: list[str], **kwargs: Any) -> Result:
        seen.update(kwargs)
        return Result()

    monkeypatch.setattr(kerberos.subprocess, "run", run)

    expiry = kerberos.ticket_expiry(Path("/dev/shm/samfscon-ccache/abc"))

    assert seen["env"]["TZ"] == "UTC"
    assert expiry == datetime(2026, 8, 23, 19, 12, 0, tzinfo=UTC)
