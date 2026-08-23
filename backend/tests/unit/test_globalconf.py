"""The global option catalogue, and the refusals that keep somebody in.

Two kinds of test here and they guard different things.

The catalogue's own invariants — every risky option carries a code, every
read-only one carries a reason, every code is declared — exist because those
fields are what the interface renders. An option classed risky with no code
produces a confirmation dialog with no sentence in it, which trains people to
click through the ones that matter.

The refusals are the other kind, and they are the point of the module. Several
of these options can cut the connection needed to put them back, and the
console has no shell to fall back on. Where the arithmetic decides it, the
refusal is absolute. Where it *cannot* be decided, the refusal is one that a
confirmation lifts — because making that permanent would be reporting
could-not-determine as is-so, which is the same fault as the six already fixed,
wearing the opposite sign.
"""

from __future__ import annotations

import pytest

from samfscon.config import MODE_AD_MEMBER, MODE_STANDALONE
from samfscon.core.errors import Conflict, InvalidRequest, SamfsconError
from samfscon.srv import globalconf as g


def refusal(call, **kwargs) -> SamfsconError:
    """Any refusal, whichever family it belongs to.

    The family is asserted where it is the point rather than here: a helper
    that only ever caught one of them would quietly stop covering whichever
    check moved to the other.
    """
    with pytest.raises(SamfsconError) as raised:
        call(**kwargs)
    return raised.value


# ===========================================================================
# The catalogue as data
# ===========================================================================


def test_every_option_says_what_it_does_in_both_languages() -> None:
    """A form field with no explanation is a field people leave alone."""
    for option in g.CATALOGUE:
        assert option.doc, f"{option.name} has no English description"
        assert option.doc_de, f"{option.name} has no German description"


def test_every_risky_option_carries_a_declared_code() -> None:
    """Without one the confirmation dialog has no sentence in it."""
    for option in g.CATALOGUE:
        if option.safety == g.RISKY:
            assert option.risk, f"{option.name} is risky and names no risk"
            assert option.risk in g.RISK_CODES, f"{option.risk} is not declared"


def test_every_read_only_option_says_why_it_is_read_only() -> None:
    """Eight options refused with one shared sentence would be eight puzzles."""
    for option in g.CATALOGUE:
        if option.safety == g.READ_ONLY:
            assert option.read_only_reason in g.READ_ONLY_REASONS, option.name
    for option in g.CATALOGUE:
        for _mode, reason in option.read_only_in:
            assert reason in g.READ_ONLY_REASONS, option.name


def test_an_option_with_no_default_says_why_there_is_none() -> None:
    """ "Samba works it out from the host name" and "it is a build option" send
    a reader to two different places, so they are two codes."""
    for option in g.CATALOGUE:
        if option.default is None and option.type != g.TYPE_LIST:
            has_reason = option.default_note in g.DEFAULT_NOTES
            # A genuinely unset-by-default text option needs no note.
            assert has_reason or option.type == g.TYPE_TEXT, option.name


def test_every_option_belongs_to_a_declared_tab() -> None:
    for option in g.CATALOGUE:
        assert option.group in g.GROUPS, option.name


def test_a_choice_option_offers_choices_and_others_do_not() -> None:
    for option in g.CATALOGUE:
        if option.type == g.TYPE_CHOICE:
            assert option.choices, option.name
        else:
            assert not option.choices, option.name


def test_a_stated_default_is_one_of_the_choices() -> None:
    """A default the field cannot be set to would be a form that opens invalid."""
    for option in g.CATALOGUE:
        if option.type == g.TYPE_CHOICE and option.default is not None:
            assert option.default in option.choices, option.name


def test_no_option_duplicates_one_the_share_catalogue_owns_differently() -> None:
    """Some names exist in both, and that is right — `wide links` is a global
    default and a per-share override. What must not differ is the type, or the
    two forms would disagree about what a legal value is."""
    from samfscon.srv import shareconf

    for option in g.CATALOGUE:
        twin = shareconf.BY_NAME.get(option.name)
        if twin is not None:
            assert twin.type == option.type, option.name


# ===========================================================================
# The catalogue as this server sees it
# ===========================================================================


def test_domain_options_are_absent_on_a_standalone_server() -> None:
    names = {option["name"] for option in g.describe_catalogue(MODE_STANDALONE)}
    assert "winbind use default domain" not in names
    assert "template shell" not in names


def test_the_workgroup_is_editable_standalone_and_shown_on_a_member() -> None:
    """The reason safety is resolved per mode rather than stored as a field.

    On a standalone server it is a rename. On a member it *is* the machine
    account's trust with the domain, and changing it breaks the join.
    """
    standalone = _option(g.describe_catalogue(MODE_STANDALONE), "workgroup")
    assert standalone["safety"] == g.RISKY
    assert standalone["risk"] == "standalone_domain_rename"

    member = _option(g.describe_catalogue(MODE_AD_MEMBER), "workgroup")
    assert member["safety"] == g.READ_ONLY
    assert member["read_only_reason"] == "member_workgroup_is_the_join"


def test_the_catalogue_speaks_the_language_it_was_asked_for() -> None:
    english = _option(g.describe_catalogue(MODE_STANDALONE, "en"), "wide links")
    german = _option(g.describe_catalogue(MODE_STANDALONE, "de"), "wide links")
    assert english["doc"] != german["doc"]
    assert "symlink" in english["doc"].lower()
    assert "link" in german["doc"].lower()


def _option(described: list[dict], name: str) -> dict:
    return next(item for item in described if item["name"] == name)


# ===========================================================================
# Validation
# ===========================================================================


@pytest.mark.parametrize(("sent", "stored"), [("YES", "yes"), ("1", "yes"), ("off", "no")])
def test_a_boolean_is_normalised_to_what_smb_conf_writes(sent: str, stored: str) -> None:
    assert g.validate({"load printers": sent}, mode=MODE_STANDALONE) == {"load printers": stored}


def test_a_choice_comes_back_in_the_catalogue_spelling() -> None:
    """Samba accepts either case; `net conf list` then shows the documented
    form rather than whatever somebody typed."""
    checked = g.validate(
        {"map to guest": "bad password"}, mode=MODE_STANDALONE, confirm=frozenset({"map to guest"})
    )
    assert checked == {"map to guest": "Bad Password"}


def test_a_choice_that_is_not_one_is_refused_with_the_list() -> None:
    error = refusal(
        g.validate,
        options={"printing": "postscript"},
        mode=MODE_STANDALONE,
    )
    assert error.code == "invalid_option_value"
    assert "cups" in error.context["allowed"]


def test_a_list_is_normalised_to_spaces() -> None:
    checked = g.validate(
        {"hosts allow": "10.0.0.0/8,  192.168.1.5"},
        mode=MODE_STANDALONE,
        confirm=frozenset({"hosts allow"}),
    )
    assert checked == {"hosts allow": "10.0.0.0/8 192.168.1.5"}


def test_a_negative_number_is_refused() -> None:
    assert refusal(g.validate, options={"max log size": "-1"}, mode=MODE_STANDALONE).code == (
        "invalid_option_value"
    )


# ===========================================================================
# What is never offered
# ===========================================================================


@pytest.mark.parametrize(
    "name",
    ["netbios name", "security", "interfaces", "socket options", "include", "config backend"],
)
def test_a_read_only_option_is_refused_with_its_own_reason(name: str) -> None:
    error = refusal(g.validate, options={name: "x"}, mode=MODE_STANDALONE)
    assert error.code == "option_not_editable"
    # Its own reason, not a shared one.
    assert error.context["reason"] in g.READ_ONLY_REASONS


def test_the_workgroup_is_refused_on_a_member_and_allowed_standalone() -> None:
    assert refusal(g.validate, options={"workgroup": "X"}, mode=MODE_AD_MEMBER).code == (
        "option_not_editable"
    )
    assert g.validate({"workgroup": "X"}, mode=MODE_STANDALONE, confirm=frozenset({"workgroup"}))


def test_an_idmap_setting_is_refused_by_prefix() -> None:
    """Its stored names are generated, so there is no single field to offer."""
    error = refusal(
        g.validate, options={"idmap config EXAMPLE : range": "1-2"}, mode=MODE_AD_MEMBER
    )
    assert error.code == "option_not_editable"
    assert error.context["reason"] == "idmap_remaps_existing_files"


def test_an_option_nobody_catalogued_is_refused_rather_than_written() -> None:
    """A curated catalogue that quietly accepted anything would be a text
    editor with extra steps."""
    assert refusal(g.validate, options={"invented option": "x"}, mode=MODE_STANDALONE).code == (
        "unknown_option"
    )


def test_a_domain_option_is_refused_on_a_standalone_server() -> None:
    error = refusal(g.validate, options={"template shell": "/bin/sh"}, mode=MODE_STANDALONE)
    assert error.code == "option_not_applicable"
    assert error.context["only_on"] == MODE_AD_MEMBER


# ===========================================================================
# Confirmation
# ===========================================================================


def test_a_risky_option_is_refused_until_it_is_confirmed() -> None:
    error = refusal(g.validate, options={"wide links": "yes"}, mode=MODE_STANDALONE)
    assert error.code == "confirmation_required"
    # The code the interface needs to show the right sentence.
    assert error.context["risk"] == "exposure_wide_links"
    # And the family it needs to decide whether to offer a button at all.
    # Nothing about the request is wrong; it is waiting for an answer.
    assert isinstance(error, Conflict)
    assert error.status_code == 409


def test_a_value_that_is_simply_wrong_is_the_other_family() -> None:
    """The distinction the status carries, from the side that must not move.

    Both of these refuse a change to the same option. One is answered by
    clicking through and the other never is, and an interface that could not
    tell them apart would either offer a button that always fails or hide the
    one that works.
    """
    error = refusal(
        g.validate,
        options={"server max protocol": "SMB9"},
        mode=MODE_STANDALONE,
        confirm=frozenset({"server max protocol"}),
    )
    assert error.code == "invalid_option_value"
    assert isinstance(error, InvalidRequest)
    assert error.status_code == 400


def test_a_confirmed_risky_option_goes_through() -> None:
    checked = g.validate(
        {"wide links": "yes"}, mode=MODE_STANDALONE, confirm=frozenset({"wide links"})
    )
    assert checked == {"wide links": "yes"}


def test_confirming_one_option_does_not_confirm_another() -> None:
    error = refusal(
        g.validate,
        options={"wide links": "yes", "deadtime": "1"},
        mode=MODE_STANDALONE,
        confirm=frozenset({"wide links"}),
    )
    assert error.context["option"] == "deadtime"


def test_clearing_a_risky_option_needs_no_confirmation() -> None:
    """Removing a value this console wrote can only restore whatever the text
    smb.conf or Samba's default says — the state the server was in before."""
    assert g.validate({"wide links": None}, mode=MODE_STANDALONE) == {"wide links": None}


# ===========================================================================
# The dialect arithmetic — refused outright, never confirmable
# ===========================================================================


def test_the_dialect_aliases_are_pinned() -> None:
    """Which concrete dialect a family name means has moved between Samba
    releases, and this module resolves to the floor reading because
    `min protocol` means "the lowest I will accept". Pinned rather than
    assumed, so a change is a failing test and not a silent shift.
    """
    assert g.dialect_index("SMB3") == g.DIALECTS.index("SMB3_00")
    assert g.dialect_index("SMB2") == g.DIALECTS.index("SMB2_02")
    assert g.dialect_index("SMB1") == g.DIALECTS.index("NT1")
    assert g.dialect_index("smb3_11") == g.DIALECTS.index("SMB3_11")


def test_an_unrecognised_dialect_decides_nothing() -> None:
    assert g.dialect_index("SMB9") is None


def test_a_floor_above_the_ceiling_is_refused_outright() -> None:
    """The server would accept nothing from anyone, the person who typed it
    included. No confirmation makes that recoverable from here."""
    error = refusal(
        g.validate,
        options={"server min protocol": "SMB3_11", "server max protocol": "SMB2_02"},
        mode=MODE_STANDALONE,
        confirm=frozenset({"server min protocol", "server max protocol"}),
    )
    assert error.code == "dialect_window_empty"
    # Both spellings, so an alias resolving unexpectedly is visible.
    assert error.context["resolved_min"] == "SMB3_11"


def test_a_sane_dialect_window_goes_through() -> None:
    checked = g.validate(
        {"server min protocol": "SMB2_10", "server max protocol": "SMB3_11"},
        mode=MODE_STANDALONE,
        confirm=frozenset({"server min protocol", "server max protocol"}),
    )
    assert checked["server min protocol"] == "SMB2_10"


def test_a_ceiling_below_this_console_is_refused() -> None:
    """SAMFSCON speaks SMB3 and does not negotiate down, so it could not
    reconnect to put the value back."""
    error = refusal(g.check_console_floor, value="SMB2_10", console_min="SMB3")
    assert error.code == "dialect_below_console_floor"
    # Verbatim beside the resolved constant.
    assert error.context["console_min_protocol"] == "SMB3"
    assert error.context["console_resolved"] == "SMB3_00"


def test_a_ceiling_this_console_can_reach_is_allowed() -> None:
    assert g.check_console_floor("SMB3_11", "SMB3") is None


# ===========================================================================
# hosts allow — and the asymmetry that is the whole design
# ===========================================================================


@pytest.mark.parametrize(
    "value",
    ["172.19.0.4", "172.19.0.0/24", "172.19.0.0/255.255.255.0", "172.19.", "ALL"],
)
def test_a_list_that_covers_this_console_is_safe(value: str) -> None:
    assert g.hosts_verdict(value, "172.19.0.4")["verdict"] == "covered"


def test_an_empty_list_restricts_nothing() -> None:
    assert g.hosts_verdict("", "172.19.0.4")["verdict"] == "covered"


def test_a_list_that_decidably_excludes_this_console_says_so() -> None:
    """Every entry was decidable and none matched. We checked."""
    result = g.hosts_verdict("192.168.1.0/24 10.0.0.5", "172.19.0.4")
    assert result["verdict"] == "excluded"
    assert result["undecidable"] == []


def test_a_host_name_makes_the_answer_undecidable_rather_than_excluding() -> None:
    """The server may resolve that name to us. Treating it as an exclusion
    would refuse a perfectly ordinary list; treating it as coverage would let
    somebody lock the console out."""
    result = g.hosts_verdict("fileserver.example.lan", "172.19.0.4")
    assert result["verdict"] == "undecidable"
    assert result["undecidable"] == ["fileserver.example.lan"]


@pytest.mark.parametrize("value", ["LOCAL", "@netgroup"])
def test_the_forms_that_cannot_be_decided_are_named(value: str) -> None:
    result = g.hosts_verdict(value, "172.19.0.4")
    assert result["verdict"] == "undecidable"
    assert result["undecidable"] == [value]


def test_an_except_anywhere_makes_the_whole_list_undecidable() -> None:
    """The bug this replaces, and it failed in the dangerous direction.

    `ALL EXCEPT 10.0.0.5` matched entry by entry answers "covered" on the first
    token — for an address Samba would refuse. The console would have called
    that safe and written it, and the connection needed to put it back would
    have been the one refused.
    """
    result = g.hosts_verdict("ALL EXCEPT 10.0.0.5", "10.0.0.5")
    assert result["verdict"] == "undecidable"
    assert result["reason"] == "except_clause"

    # And in the other direction: a list that would have covered us still does
    # not get a confident yes while an EXCEPT is in it.
    assert g.hosts_verdict("192.168.1.0/24 EXCEPT 192.168.1.5", "192.168.1.5")["verdict"] == (
        "undecidable"
    )


def test_no_known_address_makes_every_list_undecidable() -> None:
    """Not an exclusion. We could not establish what the server sees us as, and
    refusing permanently on that would be could-not-determine reported as
    is-so."""
    result = g.hosts_verdict("192.168.1.0/24", None)
    assert result["verdict"] == "undecidable"
    assert result["reason"] == "own_address_unknown"


def test_an_ipv6_console_address_is_matched_too() -> None:
    assert g.hosts_verdict("2001:db8::/32", "2001:db8::5")["verdict"] == "covered"
    assert g.hosts_verdict("2001:db8::/32", "2001:db9::5")["verdict"] == "excluded"
