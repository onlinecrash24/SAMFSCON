"""Working out which server to sign in to, and refusing to guess the mode.

The mode decides whether a password is held in memory for an hour or discarded
after one KDC exchange. Getting it wrong by guessing is the failure these tests
exist to prevent, so the "could not decide" paths are tested as carefully as
the successful ones.
"""

from __future__ import annotations

import pytest

from samfscon.config import MODE_AD_MEMBER, MODE_AUTO, MODE_STANDALONE, Settings
from samfscon.core.errors import InvalidRequest
from samfscon.srv import discovery, targets
from samfscon.srv.discovery import ServerProbe
from samfscon.srv.target import ServerTarget

# ---------------------------------------------------------------------------
# What people type into the address field
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("fs1.example.lan", "fs1.example.lan"),
        ("  fs1.example.lan  ", "fs1.example.lan"),
        ("fs1.example.lan.", "fs1.example.lan"),
        ("\\\\fs1.example.lan", "fs1.example.lan"),
        ("\\\\fs1.example.lan\\projects", "fs1.example.lan"),
        ("//fs1.example.lan/projects", "fs1.example.lan"),
        ("smb://fs1.example.lan/projects", "fs1.example.lan"),
        ("cifs://fs1.example.lan", "fs1.example.lan"),
        ("fs1.example.lan:445", "fs1.example.lan"),
        ("192.168.1.50", "192.168.1.50"),
    ],
)
def test_normalise_host(typed: str, expected: str) -> None:
    """People paste UNC paths and URLs, because that is what they have."""
    assert discovery.normalise_host(typed) == expected


def test_an_ipv6_literal_keeps_its_colons() -> None:
    """Stripping a port must not dismantle an address that is mostly colons."""
    assert discovery.normalise_host("[fe80::1]") == "[fe80::1]"


def test_an_empty_address_is_refused() -> None:
    with pytest.raises(InvalidRequest):
        discovery.normalise_host("   ")


def test_is_address_tells_names_from_literals() -> None:
    """Kerberos needs a name; this is the check that says whether we have one."""
    assert discovery.is_address("192.168.1.50") is True
    assert discovery.is_address("fe80::1") is True
    assert discovery.is_address("fs1.example.lan") is False


# ---------------------------------------------------------------------------
# Telling the two modes apart
# ---------------------------------------------------------------------------


def _decide(**kwargs) -> ServerProbe:
    probe = ServerProbe(host="fs1.example.lan", reachable=True, **kwargs)
    discovery._decide_mode(probe)
    return probe


def test_a_member_has_accounts_in_a_domain_that_is_not_itself() -> None:
    probe = _decide(realm="EXAMPLE.LAN", workgroup="EXAMPLE", netbios_name="FS1")
    assert probe.mode == MODE_AD_MEMBER
    assert probe.decided is True


def test_a_standalone_server_is_its_own_account_domain() -> None:
    probe = _decide(realm="FS1", workgroup="FS1", netbios_name="FS1")
    assert probe.mode == MODE_STANDALONE


def test_a_server_without_a_realm_cannot_use_kerberos() -> None:
    """An NT4-style member lands here, and NTLM is genuinely its only option."""
    probe = _decide(workgroup="WORKGROUP", netbios_name="FS1")
    assert probe.mode == MODE_STANDALONE


def test_a_silent_server_leaves_the_mode_open() -> None:
    """'restrict anonymous' is common, and guessing here is the worst option."""
    probe = _decide()
    assert probe.mode == MODE_AUTO
    assert probe.decided is False
    assert probe.notes  # and it says why, rather than shrugging


# ---------------------------------------------------------------------------
# Resolution, with the probe stubbed out
# ---------------------------------------------------------------------------


@pytest.fixture
def settings() -> Settings:
    return Settings()


def _stub_probe(monkeypatch: pytest.MonkeyPatch, probe: ServerProbe | Exception) -> None:
    def _probe(host: str, settings: Settings) -> ServerProbe:
        if isinstance(probe, Exception):
            raise probe
        return probe

    monkeypatch.setattr(targets.discovery, "probe", _probe)


def test_discovery_fills_in_what_the_form_did_not_say(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    _stub_probe(
        monkeypatch,
        ServerProbe(
            host="192.168.1.50",
            reachable=True,
            mode=MODE_AD_MEMBER,
            realm="EXAMPLE.LAN",
            workgroup="EXAMPLE",
            netbios_name="FS1",
            server_fqdn="fs1.example.lan",
        ),
    )

    target = targets.resolve_target(settings, server="192.168.1.50")
    assert target.mode == MODE_AD_MEMBER
    assert target.realm == "EXAMPLE.LAN"
    # The name, not the address: a ticket for cifs/192.168.1.50 does not exist.
    assert target.kerberos_host == "fs1.example.lan"


def test_the_administrators_choice_beats_the_probe(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    """Somebody who knows their server should not have to argue with a firewall."""
    _stub_probe(
        monkeypatch,
        ServerProbe(host="fs1.example.lan", reachable=True, mode=MODE_STANDALONE),
    )

    target = targets.resolve_target(
        settings, server="fs1.example.lan", mode=MODE_AD_MEMBER, realm="EXAMPLE.LAN"
    )
    assert target.mode == MODE_AD_MEMBER


def test_an_undecided_mode_is_refused_rather_than_guessed(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    _stub_probe(monkeypatch, ServerProbe(host="fs1.example.lan", reachable=True, mode=MODE_AUTO))

    with pytest.raises(InvalidRequest) as caught:
        targets.resolve_target(settings, server="fs1.example.lan")

    assert caught.value.code == "mode_undecided"
    assert caught.value.hint is not None
    assert "restrict anonymous" in caught.value.hint


def test_a_member_without_a_realm_is_refused(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    """Kerberos with no realm is a ticket request nobody can answer."""
    _stub_probe(monkeypatch, ServerProbe(host="fs1.example.lan", reachable=True))

    with pytest.raises(InvalidRequest) as caught:
        targets.resolve_target(settings, server="fs1.example.lan", mode=MODE_AD_MEMBER)

    assert caught.value.code == "missing_realm"


def test_standalone_is_refused_when_the_installation_forbids_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The switch exists so an installation can decline the memory trade."""
    monkeypatch.setenv("SAMFSCON_ALLOW_STANDALONE", "0")
    settings = Settings()
    _stub_probe(monkeypatch, ServerProbe(host="nas.local", reachable=True, mode=MODE_STANDALONE))

    with pytest.raises(InvalidRequest) as caught:
        targets.resolve_target(settings, server="nas.local")

    assert caught.value.code == "standalone_disabled"


def test_a_failed_probe_is_fatal_only_when_nothing_else_decided(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    """A probe is how an unknown server is identified — and only then required."""
    from samfscon.core.errors import UpstreamUnavailable

    _stub_probe(monkeypatch, UpstreamUnavailable("nope", code="server_unreachable"))

    with pytest.raises(UpstreamUnavailable):
        targets.resolve_target(settings, server="fs1.example.lan")

    # With the mode and realm already given, the probe is decoration and its
    # failure must not block a sign-in that would otherwise work.
    target = targets.resolve_target(
        settings, server="fs1.example.lan", mode=MODE_AD_MEMBER, realm="EXAMPLE.LAN"
    )
    assert target.mode == MODE_AD_MEMBER


def test_custom_addresses_can_be_switched_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAMFSCON_ALLOW_CUSTOM_SERVERS", "0")
    settings = Settings()

    with pytest.raises(InvalidRequest) as caught:
        targets.resolve_target(settings, server="fs1.example.lan")

    assert caught.value.code == "custom_servers_disabled"


def test_no_server_and_no_default_says_so(settings: Settings) -> None:
    with pytest.raises(InvalidRequest) as caught:
        targets.resolve_target(settings)

    assert caught.value.code == "no_target"


# ---------------------------------------------------------------------------
# The target itself
# ---------------------------------------------------------------------------


def test_a_target_without_a_host_is_refused() -> None:
    with pytest.raises(InvalidRequest):
        ServerTarget(host="   ")


def test_describe_carries_no_secret() -> None:
    """describe() goes to the front end and into the audit log."""
    target = ServerTarget(host="fs1.example.lan", mode=MODE_AD_MEMBER, realm="example.lan")
    described = target.describe()
    assert described["realm"] == "EXAMPLE.LAN"
    assert "password" not in described
    assert "secret" not in described
