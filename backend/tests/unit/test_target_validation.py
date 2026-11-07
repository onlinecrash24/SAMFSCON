"""What may reach the Kerberos configuration, and what a profile owns.

A realm travels from an unauthenticated request body into a file this process
writes and the Kerberos library reads (`auth/krb5conf.py`): the value is
rendered into `[realms]` and, lower-cased, into `[domain_realm]`. Nothing
between the two ends was checking what it contained — `max_length=255` in the
schema and `strip().upper()` in the target, and that is all. A newline there
puts a line of the caller's choosing into a process-wide configuration file
that keeps it until restart.

The second half is this console's own: a sign-in that names a *profile* was
letting the request body override the profile's realm. A profile exists so an
administrator decides where the console may go; a field in the request that
quietly replaces part of it undoes that.
"""

from __future__ import annotations

import pytest

from samfscon.core.errors import InvalidRequest
from samfscon.srv.target import ServerTarget


def refusal(**kwargs) -> InvalidRequest:
    with pytest.raises(InvalidRequest) as raised:
        ServerTarget(host="fs1.example.lan", **kwargs)
    return raised.value


# ---------------------------------------------------------------------------
# What a realm may be
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "realm",
    [
        "EXAMPLE.LAN",
        "A.B.C.EXAMPLE.CO.UK",
        "EXAMPLE-WEST.LAN",
        "X",
        "123.EXAMPLE.LAN",
    ],
)
def test_ordinary_realms_are_accepted(realm: str) -> None:
    """The check must not cost anybody a realm they really have."""
    assert ServerTarget(host="fs1.example.lan", realm=realm).realm == realm.upper()


@pytest.mark.parametrize(
    ("realm", "what"),
    [
        ("A\nB", "a newline, which writes a second line into krb5.conf"),
        ("A\r\nB", "the same with a carriage return"),
        ("A B", "a space, which ends the value in the file's grammar"),
        ("A = B", "an assignment of the caller's choosing"),
        ("A}", "a brace, which closes the realm block early"),
        ("A{", "and one that opens another"),
        ("A#B", "a comment marker"),
        ("A\tB", "a tab"),
        ("-A.LAN", "a leading dash"),
        (".A.LAN", "a leading dot"),
        ("A..LAN", "an empty label"),
        ("A/B", "a separator that is not one here"),
        ("A" * 254, "longer than a realm can be"),
    ],
)
def test_a_realm_that_could_write_a_line_is_refused(realm: str, what: str) -> None:
    error = refusal(realm=realm)
    assert error.code == "invalid_realm", what


def test_the_refusal_names_the_value() -> None:
    """So somebody who typed a realm with a stray space can see which one."""
    error = refusal(realm="EXAMPLE LAN")
    assert "EXAMPLE LAN" in str(error.context.get("realm", ""))


# ---------------------------------------------------------------------------
# The same gate for everything else that reaches that file
# ---------------------------------------------------------------------------


def test_a_kdc_host_is_checked_too() -> None:
    """KDCs are rendered into the same file, one `kdc = …` line each."""
    error = refusal(realm="EXAMPLE.LAN", kdcs=("dc1.example.lan", "dc2\n    admin_server = evil"))
    assert error.code == "invalid_kdc_host"


def test_an_ordinary_kdc_list_is_accepted() -> None:
    target = ServerTarget(
        host="fs1.example.lan",
        realm="EXAMPLE.LAN",
        kdcs=("dc1.example.lan", "192.168.1.10", "[2001:db8::1]"),
    )
    assert len(target.kdcs) == 3


def test_a_workgroup_is_checked() -> None:
    """It is rendered into smb.conf-shaped settings by the same kind of code."""
    error = refusal(workgroup="A\nB")
    assert error.code == "invalid_workgroup"


@pytest.mark.parametrize("workgroup", ["EXAMPLE", "WORKGROUP", "ZMB-MEMBER", "A1"])
def test_ordinary_workgroups_are_accepted(workgroup: str) -> None:
    assert ServerTarget(host="fs1.example.lan", workgroup=workgroup).workgroup == workgroup


# ---------------------------------------------------------------------------
# Whose realm wins
# ---------------------------------------------------------------------------


def test_a_profile_keeps_its_own_realm(monkeypatch: pytest.MonkeyPatch) -> None:
    """A profile is where an administrator says where the console may go.

    Letting the request body replace half of it means the profile decided the
    host and the caller decided the realm — which is not a profile, it is a
    form with one field pre-filled.
    """
    from samfscon.config import ServerProfile, get_settings
    from samfscon.srv import targets

    profile = ServerProfile(
        id="fs1", label="File server", host="fs1.example.lan", mode="ad_member", realm="EXAMPLE.LAN"
    )
    monkeypatch.setattr(targets, "find_profile", lambda _s, _i: profile)
    monkeypatch.setattr(targets, "_enrich", lambda _s, target, required=False: target)

    target = targets._from_profile(
        get_settings(), "fs1", mode=None, realm="ATTACKER.EXAMPLE.COM"
    )
    assert target.realm == "EXAMPLE.LAN"


def test_a_profile_without_a_realm_still_takes_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refusing outright would break the profile that names only a host —
    which is the shape the documentation shows for a standalone server."""
    from samfscon.config import ServerProfile, get_settings
    from samfscon.srv import targets

    profile = ServerProfile(id="nas", label="NAS", host="nas.example.lan", mode="auto", realm=None)
    monkeypatch.setattr(targets, "find_profile", lambda _s, _i: profile)
    monkeypatch.setattr(targets, "_enrich", lambda _s, target, required=False: target)

    target = targets._from_profile(get_settings(), "nas", mode=None, realm="EXAMPLE.LAN")
    assert target.realm == "EXAMPLE.LAN"


# ---------------------------------------------------------------------------
# The file protects itself, whoever calls
# ---------------------------------------------------------------------------


def krb5(tmp_path):
    from samfscon.auth.krb5conf import Krb5Configuration

    return Krb5Configuration(path=tmp_path / "krb5.conf")


def test_a_bad_realm_never_reaches_the_file(tmp_path) -> None:
    """ServerTarget checks every realm from a request, and one of the two
    callers passes the container's own setting straight through. A module that
    writes a configuration file should not depend on everybody upstream
    remembering."""
    configuration = krb5(tmp_path)
    configuration.ensure_realm("A\n    admin_server = evil.example.com")

    assert configuration.known_realms() == []
    assert "evil.example.com" not in configuration.render()


def test_a_bad_kdc_is_dropped_and_the_realm_survives(tmp_path) -> None:
    """One unusable KDC must not cost the realm its other ones."""
    configuration = krb5(tmp_path)
    configuration.ensure_realm("EXAMPLE.LAN", ("dc1.example.lan", "x\n kdc = evil"))

    rendered = configuration.render()
    assert "kdc = dc1.example.lan" in rendered
    assert "evil" not in rendered


def test_an_address_is_still_a_usable_kdc(tmp_path) -> None:
    """Naming the KDC by address is what makes this module work against a
    domain the container cannot resolve — the reason given at the top of it.
    An IPv6 address carries colons and brackets and passes no name check."""
    configuration = krb5(tmp_path)
    configuration.ensure_realm("EXAMPLE.LAN", ("192.168.1.10", "[2001:db8::1]"))

    rendered = configuration.render()
    assert "kdc = 192.168.1.10" in rendered
    assert "kdc = [2001:db8::1]" in rendered


def test_a_refused_realm_does_not_become_the_default(tmp_path) -> None:
    configuration = krb5(tmp_path)
    configuration.set_default_realm("A}\n[libdefaults]\n    rdns = true")

    assert "rdns = true" not in configuration.render()


def test_the_rendered_file_has_no_line_nobody_wrote(tmp_path) -> None:
    """The end-to-end shape of the finding: every line of the file is one this
    module composed, not one a caller smuggled in."""
    configuration = krb5(tmp_path)
    configuration.ensure_realm("EXAMPLE.LAN", ("dc1.example.lan",))
    configuration.ensure_realm("B\nC")

    for line in configuration.render().splitlines():
        stripped = line.strip()
        assert stripped != "C", "a second line arrived from one value"
