"""Names that need no server.

Every SID here appeared in the descriptor of a live Samba AD member whose LSA
lookups this console could not get an answer out of. The column of raw SIDs that
produced is what these names exist to prevent — and none of them is a guess: the
specification fixes all of them (MS-DTYP 2.4.2.4).
"""

from __future__ import annotations

import pytest

from samfscon.srv import identity


@pytest.mark.parametrize(
    ("sid", "name"),
    [
        ("S-1-1-0", "Everyone"),
        ("S-1-3-0", "Creator Owner"),
        ("S-1-3-1", "Creator Group"),
        ("S-1-5-11", "Authenticated Users"),
        ("S-1-5-18", "SYSTEM"),
        ("S-1-5-32-544", "Administrators"),
        ("S-1-5-32-545", "Users"),
    ],
)
def test_universal_sids_are_named(sid: str, name: str) -> None:
    found = identity.well_known_name(sid)
    assert found is not None
    assert found["name"] == name
    assert found["derived"] is True


@pytest.mark.parametrize(
    ("rid", "name"),
    [(500, "Administrator"), (512, "Domain Admins"), (513, "Domain Users")],
)
def test_domain_rids_are_named_whichever_domain_they_are_in(rid: int, name: str) -> None:
    """The domain part varies; the RID does not.

    These three are the ones the live share's descriptor actually carried.
    """
    sid = f"S-1-5-21-1067335908-1822738269-3252190750-{rid}"
    found = identity.well_known_name(sid)
    assert found is not None
    assert found["name"] == name


def test_an_ordinary_domain_account_is_not_invented() -> None:
    """RID 1013 is somebody, and only the server knows who."""
    assert identity.well_known_name("S-1-5-21-1-2-3-1013") is None


def test_a_unix_mapping_is_left_to_the_code_that_knows_about_it() -> None:
    """S-1-22-* is Samba's, not the specification's."""
    assert identity.well_known_name("S-1-22-2-0") is None


def test_a_malformed_sid_is_not_forced_into_a_name() -> None:
    assert identity.well_known_name("S-1-5-21-not-a-number") is None
    assert identity.well_known_name("") is None


def test_derived_names_are_marked_as_derived() -> None:
    """A name read off a SID is correct, and is a weaker kind of correct.

    Only the server's answer proves the account still exists, and somebody
    deciding a permission should be able to tell the two apart.
    """
    found = identity.well_known_name("S-1-5-32-544")
    assert found is not None
    assert found.get("derived") is True


# ---------------------------------------------------------------------------
# What the bindings hand back is not always what it looks like
# ---------------------------------------------------------------------------


class _Pointer:
    """An NDR pointer, as the bindings produce for a [unique] parameter."""

    def __init__(self, value: object) -> None:
        self.value = value

    def __repr__(self) -> str:  # what leaked into the interface
        return "<base.ndr_pointer talloc based object at 0x350f1e20>"


class _LsaString:
    def __init__(self, string: str) -> None:
        self.string = string


def test_an_lsa_string_gives_up_its_text() -> None:
    assert identity._lsa_text(_LsaString("Administrator")) == "Administrator"


def test_a_pointer_is_stepped_through_rather_than_printed() -> None:
    """The live failure, exactly.

    `samfsconctl check` reported an authority of
    "<base.ndr_pointer talloc based object at 0x350f1e20>", which then travelled
    on as half of a qualified name — so an account the console had already
    identified became one it could not look up.
    """
    assert identity._lsa_text(_Pointer(_LsaString("SPAM-DENY"))) == "SPAM-DENY"


def test_a_repr_is_never_returned_as_a_value() -> None:
    """Better nothing than an address in a field printed as a domain."""
    assert identity._lsa_text(_Pointer(object())) is None


def test_plain_text_passes_through() -> None:
    assert identity._lsa_text("WORKGROUP") == "WORKGROUP"
    assert identity._lsa_text(b"WORKGROUP") == "WORKGROUP"
    assert identity._lsa_text(None) is None


def test_a_cycle_cannot_hang_the_walk() -> None:
    """A pointer that points at itself is a bug somewhere, not a reason to spin."""
    loop = _Pointer(None)
    loop.value = loop
    assert identity._lsa_text(loop) is None


# ---------------------------------------------------------------------------
# Finding the signed-in account on a domain member
# ---------------------------------------------------------------------------


class _Target:
    def __init__(self, realm: str | None, workgroup: str | None) -> None:
        self.realm = realm
        self.workgroup = workgroup


class _Conn:
    def __init__(self, realm: str | None = None, workgroup: str | None = None) -> None:
        self.target = _Target(realm, workgroup)


def test_the_realm_supplies_a_spelling_the_account_domain_cannot() -> None:
    r"""The live failure.

    On a domain member the LSA account domain is the server itself —
    ZMB-MEMBER — while the person signed in is SPAM-DENY\Administrator.
    Qualifying with the account domain asks about a local account that does not
    exist, and that was the only spelling this ever tried.
    """
    candidates = identity._own_name_candidates(
        _Conn(realm="SPAM-DENY.LOCAL"), "Administrator", "ZMB-MEMBER"
    )

    assert r"ZMB-MEMBER\Administrator" in candidates  # what the server said, first
    assert r"SPAM-DENY\Administrator" in candidates  # what actually resolves
    assert "Administrator" in candidates  # for a server that qualifies nothing


def test_what_the_server_said_is_tried_first() -> None:
    """It is the only one of these that is not a guess."""
    candidates = identity._own_name_candidates(
        _Conn(realm="EXAMPLE.LAN"), "alice", "EXAMPLE"
    )
    assert candidates[0] == r"EXAMPLE\alice"


def test_no_spelling_is_offered_twice() -> None:
    """The authority and the realm's first label are often the same word."""
    candidates = identity._own_name_candidates(
        _Conn(realm="EXAMPLE.LAN", workgroup="EXAMPLE"), "alice", "EXAMPLE"
    )
    assert len(candidates) == len(set(candidates))


def test_a_standalone_server_still_gets_its_bare_name() -> None:
    """No realm, no workgroup, nothing to qualify with — and that is fine."""
    assert identity._own_name_candidates(_Conn(), "admin", None) == ["admin"]


# ---------------------------------------------------------------------------
# The capability check has to look the account up itself
# ---------------------------------------------------------------------------


class _CapConn:
    """Enough of a connection for the capability probes to run against."""

    def __init__(self, sid: str | None) -> None:
        self._sid = sid
        self.lookups = 0
        self.target = _Target("EXAMPLE.LAN", None)


def test_the_capability_check_resolves_the_account_when_nobody_passes_one(
    monkeypatch,
) -> None:
    """The banner's actual cause.

    Every caller but one passed no SID, and the privilege check then reported it
    as unknown — true, and thoroughly misleading, because nobody had asked. The
    lookup that would have answered it sat on a path only `samfsconctl check`
    ever took.
    """
    from samfscon.srv import diagnostics, identity

    conn = _CapConn("S-1-5-21-1-2-3-500")

    def _account(c):
        c.lookups += 1
        return {"sid": c._sid}

    monkeypatch.setattr(identity, "current_account", _account)
    assert diagnostics._own_sid(conn) == "S-1-5-21-1-2-3-500"
    assert conn.lookups == 1


def test_the_account_is_resolved_once_per_connection(monkeypatch) -> None:
    """It is the identity the connection was opened with; it cannot change.

    The privilege check runs on every share write as well as every listing, and
    three LSA round trips per click buys nothing.
    """
    from samfscon.srv import diagnostics, identity

    conn = _CapConn("S-1-5-21-1-2-3-500")
    monkeypatch.setattr(
        identity, "current_account", lambda c: (setattr(c, "lookups", c.lookups + 1), {"sid": c._sid})[1]
    )

    for _ in range(4):
        diagnostics._own_sid(conn)
    assert conn.lookups == 1


def test_an_unresolvable_account_is_cached_as_unresolved(monkeypatch) -> None:
    """None is an answer too, and asking again four times will not change it."""
    from samfscon.srv import diagnostics, identity

    conn = _CapConn(None)
    monkeypatch.setattr(
        identity, "current_account", lambda c: (setattr(c, "lookups", c.lookups + 1), {"sid": None})[1]
    )

    assert diagnostics._own_sid(conn) is None
    assert diagnostics._own_sid(conn) is None
    assert conn.lookups == 1


def test_a_failing_lookup_does_not_break_the_console(monkeypatch) -> None:
    from samfscon.srv import diagnostics, identity

    def _boom(_conn):
        raise RuntimeError("the server hung up")

    monkeypatch.setattr(identity, "current_account", _boom)
    assert diagnostics._own_sid(_CapConn(None)) is None


# ---------------------------------------------------------------------------
# What the privilege check may and may not conclude
# ---------------------------------------------------------------------------


class _PrivConn:
    def __init__(self, realm: str | None = "SPAM-DENY.LOCAL") -> None:
        self.target = _Target(realm, None)
        self.target.uses_kerberos = realm is not None
        self.principal = "Administrator"

        class _Info:
            name = "ZMB-MEMBER"

        self.info = _Info()


def _caps(monkeypatch, holders, groups):
    from samfscon.srv import diagnostics, identity

    monkeypatch.setattr(identity, "accounts_with_right", lambda c, r: holders)
    monkeypatch.setattr(
        identity, "current_account", lambda c: {"sid": "S-1-5-21-1-2-3-500", "groups": groups}
    )
    caps = diagnostics.Capabilities()
    diagnostics._check_privilege(_PrivConn(), caps, "S-1-5-21-1-2-3-500")
    return caps


def test_holding_it_directly_is_confirmable(monkeypatch) -> None:
    caps = _caps(monkeypatch, [{"sid": "S-1-5-21-1-2-3-500", "name": "Administrator"}], [])
    assert caps.has_disk_operator is True


def test_holding_it_through_a_group_we_can_see_is_confirmable(monkeypatch) -> None:
    caps = _caps(
        monkeypatch,
        [{"sid": "S-1-5-32-544", "name": "Administrators"}],
        [{"sid": "S-1-5-32-544"}],
    )
    assert caps.has_disk_operator is True


def test_a_nested_membership_is_not_reported_as_an_absence(monkeypatch) -> None:
    r"""The live complaint.

    GetAliasMembership finds the groups containing a SID directly. A domain
    administrator is in BUILTIN\Administrators through Domain Admins, and this
    call cannot see that — so "not found" must not become "does not have it".
    Saying otherwise disabled the one button the person came to press.
    """
    caps = _caps(monkeypatch, [{"sid": "S-1-5-32-544", "name": "Administrators"}], [])

    assert caps.has_disk_operator is None  # not False
    assert caps.can_manage_shares is None
    assert any(note.code == "privilege_unconfirmed" for note in caps.notes)


def test_nobody_holding_it_is_an_absence_and_is_reported(monkeypatch) -> None:
    """An empty list is an answer, and the one case worth refusing up front."""
    caps = _caps(monkeypatch, [], [])

    assert caps.has_disk_operator is False
    assert caps.can_manage_shares is False
    assert any(note.code == "no_disk_operators" for note in caps.notes)


def test_the_note_carries_a_command_that_can_be_pasted(monkeypatch) -> None:
    """Placeholders were the complaint: two more things to work out."""
    caps = _caps(monkeypatch, [{"sid": "S-1-5-32-544", "name": "Administrators"}], [])
    command = caps.notes[0].params["command"]

    assert "<group>" not in command and "<admin>" not in command
    assert "SPAM-DENY" in command
    assert "-U Administrator" in command


def test_an_unconfirmed_privilege_does_not_refuse_the_write(monkeypatch) -> None:
    """The server evaluates the whole token; let it answer."""
    from samfscon.srv import diagnostics

    caps = _caps(monkeypatch, [{"sid": "S-1-5-32-544", "name": "Administrators"}], [])
    diagnostics.require_share_management(caps)  # must not raise


def test_a_confirmed_absence_does_refuse_it(monkeypatch) -> None:
    from samfscon.core.errors import PermissionDenied
    from samfscon.srv import diagnostics

    caps = _caps(monkeypatch, [], [])
    with pytest.raises(PermissionDenied) as caught:
        diagnostics.require_share_management(caps)

    assert caught.value.hint is not None
    assert "net rpc rights grant" in caught.value.hint
