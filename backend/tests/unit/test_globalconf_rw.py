"""Reading the global section, and the gate in front of writing it.

The feature lives or dies on one thing: **the common case is a server whose
`[global]` lives entirely in its text smb.conf.** Such a server accepts every
write made here and honours none of them, and a console that stayed quiet about
that would leave somebody certain they had changed something.

So there are two halves to test. The cross-check that can *sometimes* establish
whether the registry global section is read at all — narrow on purpose, and
returning "cannot tell" in four distinct ways rather than guessing. And the gate
in front of the write, whose three-state section check exists because "could not
read the section list" must be treated as neither "there is one" nor "there is
none".
"""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from samfscon.config import MODE_AD_MEMBER, MODE_STANDALONE
from samfscon.core.errors import InvalidRequest, NotConfigured
from samfscon.srv import globalconf as g


def live(option: str, value: str | None, readable: bool = True) -> g.LiveValue:
    return g.LiveValue(option, value, readable, "srvsvc.comment")


# ===========================================================================
# split — four buckets, and two of them are things we must show and not offer
# ===========================================================================


def test_the_stored_values_are_sorted_into_what_the_view_does_with_each() -> None:
    known, extra, not_applicable, idmap = g.split(
        {
            "server string": "Dateiserver",
            "some option nobody catalogued": "x",
            "template shell": "/bin/sh",
            "idmap config EXAMPLE : range": "10000-20000",
        },
        MODE_STANDALONE,
    )

    assert known == {"server string": "Dateiserver"}
    assert extra == {"some option nobody catalogued": "x"}
    # Catalogued, and meaningless on a standalone server. Shown read-only
    # rather than dropped: hiding half a configuration is lying about the
    # other half.
    assert not_applicable == {"template shell": "/bin/sh"}
    # Generated names, so there is no single field they could be.
    assert idmap == {"idmap config EXAMPLE : range": "10000-20000"}


def test_a_domain_option_is_editable_on_a_member() -> None:
    known, _extra, not_applicable, _idmap = g.split({"template shell": "/bin/sh"}, MODE_AD_MEMBER)
    assert known == {"template shell": "/bin/sh"}
    assert not_applicable == {}


# ===========================================================================
# in_force — the only decidable evidence there is, and its four blind spots
# ===========================================================================


def test_a_matching_server_string_confirms_the_registry_is_read() -> None:
    decided, evidence = g.in_force_check(
        {"server string": "Dateiserver"}, [live("server string", "Dateiserver")]
    )
    assert decided is True
    assert evidence[-1]["verdict"] == "confirms"


def test_a_differing_server_string_says_it_is_not() -> None:
    decided, evidence = g.in_force_check(
        {"server string": "Dateiserver"}, [live("server string", "Samba")]
    )
    assert decided is False
    assert evidence[-1]["verdict"] == "contradicts"


@pytest.mark.parametrize(
    ("stored", "reported", "readable", "reason"),
    [
        ({}, "Samba", True, "not_stored"),
        # %h and %v are expanded by the time NetSrvGetInfo answers, so a literal
        # comparison would report a healthy server as ignoring its registry.
        ({"server string": "%h (Samba %v)"}, "fs1 (Samba 4.19)", True, "variable_expansion"),
        # Agreement on the default proves nothing: both sides could be Samba's
        # compiled-in value with nothing reading anything.
        ({"server string": "Samba"}, "Samba", True, "indistinguishable_from_default"),
        ({"server string": "Dateiserver"}, None, False, "live_unreadable"),
    ],
)
def test_the_four_ways_the_check_proves_nothing(
    stored: dict, reported: str | None, readable: bool, reason: str
) -> None:
    decided, evidence = g.in_force_check(stored, [live("server string", reported, readable)])
    assert decided is None
    # Recorded rather than silently skipped: a reader has to see the question
    # was asked.
    assert evidence[-1]["reason"] == reason


def test_serving_registry_shares_is_recorded_and_proves_nothing() -> None:
    """Samba's `registry shares = yes` activates share sections independently
    of `include = registry`. Leaning on it would be the whole detection
    mechanism resting on an unrelated option."""
    _decided, evidence = g.in_force_check(
        {},
        [
            live("server string", "Samba"),
            g.LiveValue("registry shares", "yes", True, "observed.registry_shares_served"),
        ],
    )
    served = next(item for item in evidence if item["check"] == "registry_shares_served")
    assert served["verdict"] == "proves_nothing"


# ===========================================================================
# own_client_address — the address hosts allow is matched against
# ===========================================================================


class Session:
    def __init__(self, user: str | None, client: str | None) -> None:
        self.user = user
        self.client = client


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch):
    from samfscon.srv import identity, sessions

    state: dict[str, Any] = {
        "account": {"name": "SPAM-DENY\\Administrator"},
        "sessions": [Session("Administrator", "172.19.0.4")],
    }

    def resolve(_conn: Any) -> dict:
        value = state["account"]
        if isinstance(value, Exception):
            raise value
        return value

    def listed(_conn: Any, **_k: Any) -> list[Session]:
        value = state["sessions"]
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(identity, "current_account", resolve)
    monkeypatch.setattr(sessions, "list_sessions", listed)
    return state


def test_one_session_for_this_account_gives_a_usable_address(world) -> None:
    assert g.own_client_address(object()) == ("172.19.0.4", "one_session")


def test_several_addresses_give_none_rather_than_a_guess(world) -> None:
    """Naming the wrong one would be worse than naming none: the refusal text
    tells somebody to add that address to their list."""
    world["sessions"] = [
        Session("Administrator", "172.19.0.4"),
        Session("Administrator", "10.0.0.9"),
    ]
    assert g.own_client_address(object()) == (None, "several")


def test_other_accounts_sessions_are_not_ours(world) -> None:
    world["sessions"] = [Session("anna", "10.0.0.9")]
    assert g.own_client_address(object()) == (None, "unknown")


@pytest.mark.parametrize("failure", ["account", "sessions"])
def test_a_refused_read_is_unknown_and_not_an_error(world, failure: str) -> None:
    world[failure] = RuntimeError("NT_STATUS_ACCESS_DENIED")
    assert g.own_client_address(object()) == (None, "unknown")


# ===========================================================================
# The write gate
# ===========================================================================


class Capabilities:
    registry_config = True
    registry_writable = True
    notes: ClassVar[list] = []


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch):
    """A writable server whose global section can be posed in three states."""
    from samfscon.srv import diagnostics, globalconf, registry

    state: dict[str, Any] = {
        "config": g.GlobalConfig(
            section_present=True,
            stored={},
            known={},
            extra={},
            not_applicable={},
            idmap={},
            live=[],
            in_force=None,
            in_force_evidence=[],
            own_client_address="172.19.0.4",
            own_client_address_confidence="one_session",
            mode=MODE_STANDALONE,
            notes=[],
        ),
        "written": None,
    }

    def write_options(_conn: Any, _section: str, options: dict) -> dict:
        state["written"] = options
        return {name: {"old": None, "new": value} for name, value in options.items()}

    monkeypatch.setattr(diagnostics, "capabilities", lambda _c, **_k: Capabilities())
    monkeypatch.setattr(diagnostics, "require_share_management", lambda _caps: None)
    monkeypatch.setattr(globalconf, "read", lambda _c: state["config"])
    monkeypatch.setattr(registry, "write_options", write_options)
    monkeypatch.setattr(globalconf, "live_values", lambda _c: [])
    return state


def test_a_write_reaches_the_registry(server) -> None:
    result = g.write(object(), {"server string": "Dateiserver"})
    assert server["written"] == {"server string": "Dateiserver"}
    assert result["section_created"] is False


def test_an_absent_section_is_refused_until_creating_it_is_asked_for(server) -> None:
    """Creating it changes nothing unless the server's smb.conf includes the
    registry before the lines setting the same options — which cannot be read
    from here, so it is stated and confirmed rather than done quietly."""
    server["config"].section_present = False

    with pytest.raises(NotConfigured) as raised:
        g.write(object(), {"server string": "X"})
    assert raised.value.code == "global_section_absent"

    result = g.write(object(), {"server string": "X"}, create_section=True)
    assert result["section_created"] is True


def test_an_unknown_section_state_is_refused_and_not_guessed(server) -> None:
    """The row that matters. "Could not read the section list" is neither
    "there is one" nor "there is none", and confirming does not make it
    either."""
    server["config"].section_present = None

    for kwargs in ({}, {"create_section": True}):
        with pytest.raises(NotConfigured) as raised:
            g.write(object(), {"server string": "X"}, **kwargs)
        assert raised.value.code == "global_section_unknown"

    assert server["written"] is None


# ---------------------------------------------------------------------------
# hosts allow, at the gate
# ---------------------------------------------------------------------------


def test_a_hosts_list_that_shuts_this_console_out_is_refused(server) -> None:
    with pytest.raises(InvalidRequest) as raised:
        g.write(
            object(),
            {"hosts allow": "192.168.1.0/24"},
            confirm=frozenset({"hosts allow"}),
        )

    error = raised.value
    assert error.code == "hosts_allow_excludes_console"
    # The address the *server* sees, which is the backend's and not the
    # workstation's. Naming it is the entire mitigation.
    assert error.context["address"] == "172.19.0.4"
    assert server["written"] is None


def test_confirming_does_not_lift_a_decided_exclusion(server) -> None:
    """We checked, and it locks the console out. No dialog makes that
    recoverable when recovery needs a shell on the server."""
    with pytest.raises(InvalidRequest):
        g.write(
            object(),
            {"hosts allow": "192.168.1.0/24"},
            confirm=frozenset({"hosts allow", g.UNDECIDABLE_CONFIRM}),
        )


def test_a_list_that_covers_this_console_goes_through(server) -> None:
    g.write(object(), {"hosts allow": "172.19.0.0/24"}, confirm=frozenset({"hosts allow"}))
    assert server["written"] == {"hosts allow": "172.19.0.0/24"}


def test_an_undecidable_list_is_refused_once_and_then_allowed(server) -> None:
    """The asymmetry. Refusing permanently on "we could not check" would be
    could-not-determine reported as is-so."""
    with pytest.raises(InvalidRequest) as raised:
        g.write(object(), {"hosts allow": "fs1.example.lan"}, confirm=frozenset({"hosts allow"}))

    error = raised.value
    assert error.code == "hosts_allow_undecidable"
    assert error.context["undecidable_entries"] == ["fs1.example.lan"]
    # Its own token, not the option's. Confirming the option says "I know what
    # it does"; this says "I accept you could not check whether it shuts me
    # out", and one standing for the other would waive the check every time.
    assert error.context["confirm_with"] == g.UNDECIDABLE_CONFIRM

    g.write(
        object(),
        {"hosts allow": "fs1.example.lan"},
        confirm=frozenset({"hosts allow", g.UNDECIDABLE_CONFIRM}),
    )


def test_an_unknown_own_address_makes_every_list_undecidable(server) -> None:
    server["config"].own_client_address = None
    server["config"].own_client_address_confidence = "unknown"

    with pytest.raises(InvalidRequest) as raised:
        g.write(object(), {"hosts allow": "192.168.1.0/24"}, confirm=frozenset({"hosts allow"}))
    # Undecidable, never excluded: we do not know what address we are.
    assert raised.value.code == "hosts_allow_undecidable"


def test_clearing_the_list_is_never_a_lockout(server) -> None:
    """An empty hosts allow admits everyone, this console included."""
    g.write(object(), {"hosts allow": None})
    assert server["written"] == {"hosts allow": None}


# ---------------------------------------------------------------------------
# The console's own floor
# ---------------------------------------------------------------------------


def test_a_ceiling_below_this_console_is_refused_at_the_gate(server) -> None:
    with pytest.raises(InvalidRequest) as raised:
        g.write(
            object(),
            {"server max protocol": "SMB2_10"},
            confirm=frozenset({"server max protocol"}),
            console_min_protocol="SMB3",
        )
    assert raised.value.code == "dialect_below_console_floor"
    assert server["written"] is None


# ===========================================================================
# Verification — three outcomes, and no code meaning "the write failed"
# ===========================================================================


def test_a_reported_value_confirms_the_write(server, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(g, "live_values", lambda _c: [live("server string", "Dateiserver")])
    result = g.write(object(), {"server string": "Dateiserver"})
    assert result["verification"]["code"] == "applied_confirmed"


def test_an_old_value_is_not_yet_visible_rather_than_failed(
    server, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two causes and this console can distinguish neither: smbd has not
    re-read its configuration, or the text smb.conf overrides it. Calling that
    a failure would name one of them without evidence."""
    monkeypatch.setattr(g, "live_values", lambda _c: [live("server string", "Samba")])
    result = g.write(object(), {"server string": "Dateiserver"})

    assert result["verification"]["code"] == "not_yet_visible"
    assert result["verification"]["stored"] == "Dateiserver"
    assert result["verification"]["live"] == "Samba"


@pytest.mark.parametrize(
    ("options", "reason"),
    [
        ({"deadtime": "60"}, "no_live_source_among_written_options"),
        ({"server string": "%h server"}, "variable_expansion"),
    ],
)
def test_what_cannot_be_compared_says_so(
    server, monkeypatch: pytest.MonkeyPatch, options: dict, reason: str
) -> None:
    monkeypatch.setattr(g, "live_values", lambda _c: [live("server string", "Samba")])
    result = g.write(object(), options, confirm=frozenset(options))
    assert result["verification"]["code"] == "not_comparable"
    assert result["verification"]["reason"] == reason
