"""The share option catalogue, and the values it refuses.

Validation lives on this side of the wire for a reason worth restating: Samba
accepts a great many nonsense values without complaint and then behaves oddly.
``create mask = 999`` is not an error to the smb.conf parser and is not what
anyone meant. The refusal is only useful where it can name the option and say
what was wrong with it.
"""

from __future__ import annotations

import pytest

from samfscon.core.errors import InvalidRequest
from samfscon.srv import shareconf

# ---------------------------------------------------------------------------
# The catalogue itself
# ---------------------------------------------------------------------------


def test_every_option_has_a_sentence_saying_what_it_does() -> None:
    """A form field with no explanation is a field people leave alone."""
    for option in shareconf.CATALOGUE:
        assert option.doc, f"{option.name} has no English description"
        assert option.doc_de, f"{option.name} has no German description"


def test_no_option_duplicates_what_srvsvc_already_owns() -> None:
    """Two places to set one value is two places to disagree."""
    names = {option.name for option in shareconf.CATALOGUE}
    assert not (names & shareconf.SRVSVC_OWNED)


def test_choice_options_declare_their_choices() -> None:
    for option in shareconf.CATALOGUE:
        if option.type == shareconf.TYPE_CHOICE:
            assert option.choices, f"{option.name} is a choice with no choices"
            if option.default is not None:
                assert option.default in option.choices


def test_the_catalogue_is_translated_on_request() -> None:
    english = {item["name"]: item["doc"] for item in shareconf.describe_catalogue("en")}
    german = {item["name"]: item["doc"] for item in shareconf.describe_catalogue("de")}
    assert english["read only"] != german["read only"]
    assert german["read only"].startswith("Ob die Freigabe")


# ---------------------------------------------------------------------------
# Booleans
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["yes", "YES", "true", "1", "on", " yes "])
def test_truthy_spellings_normalise_to_yes(value: str) -> None:
    """People type all of these; smb.conf should end up with one of them."""
    assert shareconf.validate({"read only": value}) == {"read only": "yes"}


@pytest.mark.parametrize("value", ["no", "FALSE", "0", "off"])
def test_falsy_spellings_normalise_to_no(value: str) -> None:
    assert shareconf.validate({"read only": value}) == {"read only": "no"}


def test_a_boolean_that_is_neither_is_refused() -> None:
    with pytest.raises(InvalidRequest) as caught:
        shareconf.validate({"read only": "maybe"})
    assert caught.value.code == "invalid_option_value"
    assert caught.value.context["option"] == "read only"


# ---------------------------------------------------------------------------
# Permission masks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("given", "stored"), [("0750", "0750"), ("750", "0750"), ("0644", "0644")])
def test_masks_are_normalised_to_four_octal_digits(given: str, stored: str) -> None:
    assert shareconf.validate({"create mask": given}) == {"create mask": stored}


@pytest.mark.parametrize("value", ["999", "0888", "rwxr-x---", "0o750", ""])
def test_a_mask_that_is_not_octal_is_refused(value: str) -> None:
    """The value Samba would accept and then not do what was meant."""
    with pytest.raises(InvalidRequest):
        shareconf.validate({"create mask": value})


# ---------------------------------------------------------------------------
# Lists, numbers and choices
# ---------------------------------------------------------------------------


def test_lists_are_normalised_to_the_separator_samba_writes() -> None:
    """So a value written here reads the same as one `net conf` shows."""
    result = shareconf.validate({"valid users": "alice, @staff,  bob"})
    assert result == {"valid users": "alice @staff bob"}


def test_vfs_objects_keeps_its_order() -> None:
    """Order is meaning here: each module sees what the previous passed on."""
    result = shareconf.validate({"vfs objects": "full_audit recycle shadow_copy2"})
    assert result == {"vfs objects": "full_audit recycle shadow_copy2"}


def test_numbers_are_checked() -> None:
    assert shareconf.validate({"max connections": " 12 "}) == {"max connections": "12"}
    with pytest.raises(InvalidRequest):
        shareconf.validate({"max connections": "twelve"})
    with pytest.raises(InvalidRequest):
        shareconf.validate({"max connections": "-1"})


def test_choices_are_checked_and_listed_in_the_refusal() -> None:
    assert shareconf.validate({"shadow:sort": "ASC"}) == {"shadow:sort": "asc"}
    with pytest.raises(InvalidRequest) as caught:
        shareconf.validate({"shadow:sort": "sideways"})
    assert caught.value.context["allowed"] == ["asc", "desc"]


# ---------------------------------------------------------------------------
# The edges that matter
# ---------------------------------------------------------------------------


def test_option_names_are_normalised_the_way_samba_spells_them() -> None:
    """`vfs_objects` and `vfs objects` are one option, and people type both."""
    assert shareconf.validate({"VFS_Objects": "recycle"}) == {"vfs objects": "recycle"}


def test_none_deletes_rather_than_setting_an_empty_value() -> None:
    """Different things: one restores the server's default, one sets a value.

    An empty string is a value the smb.conf parser will honour, so conflating
    the two would silently change behaviour on every "clear this field".
    """
    assert shareconf.validate({"create mask": None}) == {"create mask": None}
    assert shareconf.validate({"veto files": ""}) == {"veto files": ""}


def test_srvsvc_owned_options_are_refused_with_a_reason() -> None:
    """The path is set through the share itself; two routes would disagree."""
    with pytest.raises(InvalidRequest) as caught:
        shareconf.validate({"path": "/srv/elsewhere"})
    assert caught.value.code == "option_not_editable"


def test_uncatalogued_options_pass_through_unchanged() -> None:
    """A server configured by hand is not wrong, and must survive an edit here.

    Refusing what the catalogue does not describe would make SAMFSCON unable to
    preserve a configuration it did not write — which is a worse failure than
    not validating it.
    """
    result = shareconf.validate({"some future option": "  a value  "})
    assert result == {"some future option": "a value"}


def test_split_separates_the_known_from_the_rest() -> None:
    stored = {
        "read only": "no",
        "vfs objects": "recycle",
        "an option we do not describe": "42",
        "path": "/srv/shares/x",
    }
    options = shareconf.split(stored)

    assert options.known == {"read only": "no", "vfs objects": "recycle"}
    assert options.extra == {"an option we do not describe": "42"}
    # srvsvc reports the path; showing it a second time invites disagreement.
    assert "path" not in options.known
    assert "path" not in options.extra


def test_vfs_modules_are_read_in_order() -> None:
    """The interface greys out recycle:* until the module is actually loaded."""
    assert shareconf.vfs_modules({"vfs objects": "recycle, shadow_copy2"}) == [
        "recycle",
        "shadow_copy2",
    ]
    assert shareconf.vfs_modules({}) == []


# ---------------------------------------------------------------------------
# The catalogue's defaults are what an unset option actually does
#
# The interface shows them for a share that stores nothing, so a wrong one here
# is the console asserting a behaviour the server does not have. These are the
# four on the first tab, checked against smb.conf's own documented defaults.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("option", "default"),
    [
        ("read only", "yes"),
        ("browseable", "yes"),
        ("guest ok", "no"),
        ("available", "yes"),
    ],
)
def test_the_first_tab_options_carry_samba_s_defaults(option: str, default: str) -> None:
    assert shareconf.BY_NAME[option].default == default


def test_every_boolean_option_declares_a_default() -> None:
    """An unset checkbox has to show something, and it must not be a guess.

    Without a default the interface falls back to "no", which is wrong for
    every option Samba enables by default — and an unchecked box then claims
    this share turned something off that it never mentioned.
    """
    for option in shareconf.CATALOGUE:
        if option.type == shareconf.TYPE_BOOL:
            assert option.default in ("yes", "no"), f"{option.name} has no usable default"


# ---------------------------------------------------------------------------
# What "the share is not there" looks like on the wire
# ---------------------------------------------------------------------------


def test_an_unused_name_reads_as_missing_not_as_invalid() -> None:
    """Samba answers WERR_INVALID_NAME for a share that does not exist.

    _srvsvc_NetShareGetInfo returns it when find_service() comes up empty, so a
    perfectly good name that is simply unused arrives as "invalid name". The
    existence check treated that as a refusal and raised, NetShareAdd was never
    reached, and every attempt to create a share told the person their name was
    not allowed — right after they typed "test".
    """
    from samfscon.core.errors import translate
    from samfscon.srv import shares

    assert shares._missing(translate(RuntimeError("WERR_INVALID_NAME"))) is True
    assert shares._missing(translate(RuntimeError("WERR_NERR_NETNAMENOTFOUND"))) is True


def test_a_refusal_is_still_a_refusal() -> None:
    """A share we may not look at is not a share that is not there.

    Reading it as absent would let a creation proceed and fail again one call
    later, less clearly.
    """
    from samfscon.core.errors import translate
    from samfscon.srv import shares

    assert shares._missing(translate(RuntimeError("WERR_ACCESS_DENIED"))) is False
    assert shares._missing(translate(RuntimeError("NT_STATUS_ACCESS_DENIED"))) is False


# ---------------------------------------------------------------------------
# The rule that keeps costing round trips
#
# pidl leaves out of the python signature anything the wire format can work out
# for itself: an [out] parameter, and the count of a size_is() array. Three
# calls have been wrong for exactly this reason — `domains` in every LSA lookup,
# `size` in winreg SetValue, and `num_names` in LookupNames — so it is written
# down as a rule rather than rediscovered per call.
# ---------------------------------------------------------------------------


def test_set_value_offers_the_derived_form_first() -> None:
    """winreg_SetValue takes four arguments; the IDL declares five.

    `size` is size_is() for the data array, so pidl derives it. Sending it
    produced "takes at most 4 arguments (5 given)" and nothing was written.
    """
    import inspect

    from samfscon.srv import registry

    source = inspect.getsource(registry._set_value)
    first = source.index("pipe.SetValue")
    assert "REG_SZ, data)" in source[first : first + 120]


def test_the_registry_walk_tells_the_end_from_a_failure() -> None:
    """Any exception used to mean "that was all".

    A key whose values could not be read then reported as a key with no values,
    which is the same silent-absence fault as everywhere else in this codebase.

    And the reverse, which was the second half of it: the shape is decided on
    the first index and reused, so from the second index onwards the ordinary
    end of every enumeration went to the failure handler. Five values read
    correctly and a warning logged for the sixth, every single listing.
    """
    import inspect

    from samfscon.srv import registry

    for walk in (registry._enumerate_values, registry._enumerate_keys):
        source = inspect.getsource(walk)
        assert "_is_walk_end(exc)" in source, f"{walk.__name__} does not check for the end"
        assert "logger.warning" in source, f"{walk.__name__} fails silently"


@pytest.mark.parametrize(
    ("exc", "is_end"),
    [
        (RuntimeError("(259, 'WERR_NO_MORE_ITEMS')"), True),
        (RuntimeError("werr_no_more_items"), True),
        (RuntimeError("(87, 'WERR_INVALID_PARAMETER')"), False),
        (RuntimeError("(5, 'WERR_ACCESS_DENIED')"), False),
    ],
)
def test_only_one_status_ends_a_walk(exc: Exception, is_end: bool) -> None:
    from samfscon.srv import registry

    assert registry._is_walk_end(exc) is is_end


def test_the_two_enumerations_ask_for_the_types_their_calls_declare() -> None:
    """winreg_EnumKey takes a StringBuf; winreg_EnumValue takes a ValNameBuf.

    Handing over the wrong one is a TypeError before the call leaves the
    container, which is what stopped every registry value being read while
    writing them worked perfectly — the share appeared in `net conf list` and
    the console still labelled it "from smb.conf", because reading its section
    back found nothing.
    """
    import inspect

    from samfscon.srv import registry

    source = inspect.getsource(registry._name_buffer)
    assert "ValNameBuf" in source
    assert "StringBuf" in source

    values = inspect.getsource(registry._enumerate_values)
    keys = inspect.getsource(registry._enumerate_keys)
    assert '_name_buffer("value")' in values
    assert '_name_buffer("key")' in keys


def test_a_name_buffer_is_filled_in_rather_than_only_sized() -> None:
    """The server answered WERR_INVALID_PARAMETER to a half-built one.

    `size` alone left `name` and `length` at whatever the constructor produced,
    and unset is not empty to the marshaller — the same lesson the srvsvc
    containers taught twice before this.
    """
    import inspect

    from samfscon.srv import registry

    source = inspect.getsource(registry._name_buffer)
    for member in ("buffer.name", "buffer.size", "buffer.length"):
        assert member in source, f"{member} is not set"


def test_a_choice_is_returned_in_the_catalogue_s_spelling() -> None:
    """Matched without regard to case, stored the way the documentation writes it.

    The share options all spell their choices in lower case, so this is
    behaviour-preserving here and load-bearing next door: `SMB3_11` stored as
    `smb3_11` is the same value to the parser and a different one to every
    document and every `net conf list` output somebody compares it against.
    """
    from samfscon.srv import shareconf

    assert (
        shareconf.validate_value("dialect", shareconf.TYPE_CHOICE, ("SMB3_11", "NT1"), "smb3_11")
        == "SMB3_11"
    )
    assert (
        shareconf.validate_value("order", shareconf.TYPE_CHOICE, ("asc", "desc"), " DESC ")
        == "desc"
    )


def test_validate_value_is_reachable_without_an_option_object() -> None:
    """One normaliser for both catalogues, and it takes primitives.

    Two would let `Yes` round-trip differently between the share sheet and the
    settings sheet — the same word, two stored values, and no way to tell from
    either screen which one is on the server.
    """
    from samfscon.srv import globalconf, shareconf

    assert shareconf.validate_value("a switch", shareconf.TYPE_BOOL, (), "Yes") == "yes"
    assert globalconf._validate_one.__doc__ is not None
    for option in globalconf.CATALOGUE:
        if option.type == shareconf.TYPE_BOOL:
            assert globalconf._validate_one(option, "Yes") == "yes"
            break
