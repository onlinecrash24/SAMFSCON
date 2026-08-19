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
    probe = _decide(
        account_policy_read=True,
        dns_policy_read=True,
        realm="EXAMPLE.LAN",
        workgroup="EXAMPLE",
        netbios_name="FS1",
    )
    assert probe.mode == MODE_AD_MEMBER
    assert probe.decided is True


def test_a_member_gets_the_name_kerberos_will_ask_for() -> None:
    """Without this the connection falls back to whatever was typed.

    Against a bare address Kerberos cannot build the cifs/<host> principal at
    all, and the bind fails with NT_STATUS_INVALID_PARAMETER long after the
    ticket was obtained without complaint. The name is derivable from the two
    facts the policy query already gave us, so it is derived.
    """
    probe = _decide(
        account_policy_read=True,
        dns_policy_read=True,
        realm="EXAMPLE.LAN",
        workgroup="EXAMPLE",
        netbios_name="FS1",
    )
    assert probe.server_fqdn == "fs1.example.lan"


def test_a_standalone_server_is_its_own_account_domain() -> None:
    probe = _decide(
        account_policy_read=True,
        dns_policy_read=True,
        realm="FS1",
        workgroup="FS1",
        netbios_name="FS1",
    )
    assert probe.mode == MODE_STANDALONE


def test_a_server_that_reports_no_realm_cannot_use_kerberos() -> None:
    """The DNS level answered and carried no domain — a positive statement.

    An NT4-style member lands here too, and NTLM is genuinely its only option.
    """
    probe = _decide(
        account_policy_read=True,
        dns_policy_read=True,
        workgroup="WORKGROUP",
        netbios_name="FS1",
    )
    assert probe.mode == MODE_STANDALONE


def test_a_refused_dns_query_decides_nothing() -> None:
    """The regression that made this console try NTLM against a domain member.

    An AD member with `restrict anonymous` answers neither policy query. Reading
    that silence as "no realm, therefore standalone" produced a sign-in with a
    domain password over NTLM, a logon failure that named the wrong problem, and
    an offer to hold a password in memory that Kerberos had made unnecessary.

    A refused query is not an answer. It has to decide nothing.
    """
    probe = _decide(account_policy_read=True, netbios_name="FS1")

    assert probe.mode == MODE_AUTO
    assert probe.decided is False
    assert any("refused" in note or "by hand" in note for note in probe.notes)


def test_a_silent_server_leaves_the_mode_open() -> None:
    """'restrict anonymous' is common, and guessing here is the worst option."""
    probe = _decide()
    assert probe.mode == MODE_AUTO
    assert probe.decided is False
    assert probe.notes  # and it says why, rather than shrugging


def test_a_half_answered_policy_decides_nothing() -> None:
    """One name without the other cannot be compared, so it is not guessed at."""
    probe = _decide(dns_policy_read=True, realm="EXAMPLE.LAN", workgroup="EXAMPLE")
    assert probe.mode == MODE_AUTO


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
            account_policy_read=True,
            dns_policy_read=True,
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


def test_kerberos_against_a_bare_address_is_refused_before_the_password(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    """The failure seen against a live AD member, caught where it can be explained.

    Forcing "domain member" against an address whose name could not be learned
    used to acquire a ticket, then fail at the connect with
    NT_STATUS_INVALID_PARAMETER — after the password had been typed and sent.
    There is no arrangement of retries that makes cifs/192.168.1.41 exist, so it
    is refused up front with what to do instead.
    """
    _stub_probe(monkeypatch, ServerProbe(host="192.168.1.41", reachable=True))

    with pytest.raises(InvalidRequest) as caught:
        targets.resolve_target(
            settings, server="192.168.1.41", mode=MODE_AD_MEMBER, realm="EXAMPLE.LAN"
        )

    assert caught.value.code == "kerberos_needs_a_name"
    assert caught.value.hint is not None
    assert "extra_hosts" in caught.value.hint


def test_a_discovered_name_makes_an_address_usable(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    """The same sign-in works once the probe supplies the server's own name."""
    _stub_probe(
        monkeypatch,
        ServerProbe(
            host="192.168.1.41",
            reachable=True,
            account_policy_read=True,
            dns_policy_read=True,
            mode=MODE_AD_MEMBER,
            realm="SPAM-DENY.LOCAL",
            workgroup="SPAM-DENY",
            netbios_name="FS1",
            server_fqdn="fs1.spam-deny.local",
        ),
    )

    target = targets.resolve_target(settings, server="192.168.1.41")
    assert target.mode == MODE_AD_MEMBER
    assert target.kerberos_host == "fs1.spam-deny.local"


# ---------------------------------------------------------------------------
# The name Kerberos needs, from whichever of the three sources answers
# ---------------------------------------------------------------------------


def test_reverse_dns_supplies_a_name_when_the_server_will_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The last source, for a server that refuses every anonymous query."""
    import socket

    monkeypatch.setattr(
        socket, "gethostbyaddr", lambda address: ("FS1.spam-deny.local.", [], [address])
    )
    probe = ServerProbe(host="192.168.1.41", reachable=True)
    discovery._reverse_lookup(probe)

    assert probe.server_fqdn == "fs1.spam-deny.local"
    # Said out loud: this name came from DNS, not from the server itself.
    assert any("reverse DNS" in note for note in probe.notes)


def test_reverse_dns_never_overrides_what_the_server_said() -> None:
    """The server's own account of itself outranks a PTR record."""
    probe = ServerProbe(host="192.168.1.41", reachable=True, server_fqdn="fs1.example.lan")
    discovery._reverse_lookup(probe)
    assert probe.server_fqdn == "fs1.example.lan"


def test_reverse_dns_is_not_attempted_for_a_name() -> None:
    probe = ServerProbe(host="fs1.example.lan", reachable=True)
    discovery._reverse_lookup(probe)
    assert probe.server_fqdn is None


def test_a_missing_ptr_record_is_reported_rather_than_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A server with no PTR record is common and is not an error."""
    import socket

    def _fail(address: str):
        raise OSError("no PTR record")

    monkeypatch.setattr(socket, "gethostbyaddr", _fail)
    probe = ServerProbe(host="192.168.1.41", reachable=True)
    discovery._reverse_lookup(probe)

    assert probe.server_fqdn is None
    assert any("reverse DNS" in note for note in probe.notes)


# ---------------------------------------------------------------------------
# The server that answers srvsvc and refuses the policy query
#
# Modelled on a real one: a Samba AD member that reported its account domain and
# its comment, and declined the LSA DNS-domain query. Every assertion here comes
# from that probe's actual output.
# ---------------------------------------------------------------------------


def test_srvsvc_answers_the_question_the_policy_query_refused() -> None:
    """SV_TYPE_DOMAIN_MEMBER is the server saying so in its own words."""
    probe = _decide(
        account_policy_read=True,
        netbios_name="ZMB-MEMBER",
        server_type=discovery.SV_TYPE_DOMAIN_MEMBER | discovery.SV_TYPE_SERVER_NT,
    )

    assert probe.mode == MODE_AD_MEMBER
    # The realm is still unknown — the query that names it was refused — so the
    # note has to say that rather than leave a member with no realm looking fine.
    assert probe.realm is None
    assert any("realm has to be given" in note for note in probe.notes)


def test_an_absent_member_flag_decides_nothing() -> None:
    """Positive evidence decides; absence of evidence does not.

    The same rule as everywhere else here, and the one that keeps this from
    repeating the mistake of reading silence as "standalone".
    """
    probe = _decide(
        account_policy_read=True,
        netbios_name="FS1",
        server_type=discovery.SV_TYPE_SERVER_NT,
    )
    assert probe.mode == MODE_AUTO


def test_a_server_that_answered_neither_still_decides_nothing() -> None:
    probe = _decide(account_policy_read=True, netbios_name="FS1")
    assert probe.mode == MODE_AUTO


def test_the_realm_the_administrator_supplies_completes_the_name(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    """The whole live failure, end to end, in the shape it actually occurred.

    The probe knows the server is ZMB-MEMBER and a domain member; it cannot know
    the realm, because that query was refused, and there is no PTR record. The
    administrator supplies SPAM-DENY.LOCAL, and the two halves compose into the
    name Kerberos can actually be asked for.
    """
    _stub_probe(
        monkeypatch,
        ServerProbe(
            host="192.168.1.41",
            reachable=True,
            mode=MODE_AD_MEMBER,
            account_policy_read=True,
            netbios_name="ZMB-MEMBER",
            server_type=discovery.SV_TYPE_DOMAIN_MEMBER,
        ),
    )

    target = targets.resolve_target(
        settings, server="192.168.1.41", realm="SPAM-DENY.LOCAL"
    )

    assert target.mode == MODE_AD_MEMBER
    assert target.kerberos_host == "zmb-member.spam-deny.local"


def test_a_typed_name_is_never_second_guessed() -> None:
    """Composition is only for an address. A name given is a name used."""
    target = ServerTarget(
        host="fileserver.example.lan",
        mode=MODE_AD_MEMBER,
        realm="EXAMPLE.LAN",
        netbios_name="FS1",
    )
    assert target.kerberos_host == "fileserver.example.lan"


def test_the_undecided_hint_works_from_the_command_line_too(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    """It used to say "in the sign-in form" to somebody running samfsconctl."""
    _stub_probe(monkeypatch, ServerProbe(host="192.168.1.41", reachable=True))

    with pytest.raises(InvalidRequest) as caught:
        targets.resolve_target(settings, server="192.168.1.41")

    assert caught.value.hint is not None
    assert "--mode" in caught.value.hint
