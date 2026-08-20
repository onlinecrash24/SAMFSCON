"""SDDL, and the two permission levels that get confused for one another.

The round-trip is the property that matters: a descriptor that goes through
this editor unchanged must come out unchanged. A parser that quietly drops an
entry it does not understand is how permissions widen without anybody
approving it.
"""

from __future__ import annotations

import pytest

from samfscon.core.errors import InvalidRequest
from samfscon.srv import acl

# A share root as Samba actually leaves one: administrators explicit, users
# inheriting, and one deny that exists on purpose.
REAL_SDDL = (
    "O:BAG:BA"
    "D:(A;OICI;FA;;;BA)"
    "(A;OICIID;0x001200a9;;;BU)"
    "(D;OICI;FW;;;S-1-5-21-1-2-3-1013)"
)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def test_owner_and_group_are_read() -> None:
    parsed = acl.parse(REAL_SDDL)
    assert parsed.owner == "BA"
    assert parsed.group == "BA"


def test_every_ace_survives_parsing() -> None:
    """An entry lost here is a permission nobody notices going missing."""
    parsed = acl.parse(REAL_SDDL)
    assert [entry.trustee for entry in parsed.aces] == ["BA", "BU", "S-1-5-21-1-2-3-1013"]


def test_deny_entries_keep_their_kind() -> None:
    """Getting this backwards turns a prohibition into a grant."""
    parsed = acl.parse(REAL_SDDL)
    kinds = {entry.trustee: entry.kind for entry in parsed.aces}
    assert kinds["BA"] == "allow"
    assert kinds["S-1-5-21-1-2-3-1013"] == "deny"


def test_an_inherited_entry_is_marked_as_such() -> None:
    """Inherited entries are not editable in place: they belong to the parent."""
    parsed = acl.parse(REAL_SDDL)
    by_trustee = {entry.trustee: entry for entry in parsed.aces}
    assert by_trustee["BU"].inherited is True
    assert by_trustee["BA"].inherited is False


def test_a_hexadecimal_mask_is_read_exactly() -> None:
    """Samba writes one whenever the letters cannot express the mask."""
    parsed = acl.parse("D:(A;;0x001200a9;;;BU)")
    assert parsed.aces[0].mask == 0x001200A9


def test_a_descriptor_without_a_dacl_is_refused() -> None:
    """One that grants nothing to anybody is not something to edit silently."""
    with pytest.raises(InvalidRequest) as caught:
        acl.parse("O:BAG:BA")
    assert caught.value.code == "no_dacl"


def test_a_malformed_ace_is_skipped_rather_than_crashing() -> None:
    """One unreadable entry must not cost the administrator the whole dialog."""
    parsed = acl.parse("D:(A;;FA;;;BA)(nonsense)(A;;FR;;;BU)")
    assert [entry.trustee for entry in parsed.aces] == ["BA", "BU"]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_a_descriptor_round_trips() -> None:
    """Parse, build, parse: the entries that are ours must come back identical."""
    once = acl.parse(REAL_SDDL)
    twice = acl.parse(acl.build(once))

    ours = [entry for entry in once.aces if not entry.inherited]
    assert len(twice.aces) == len(ours)
    for before, after in zip(ours, twice.aces, strict=True):
        assert (before.trustee, before.kind, before.mask, before.flags) == (
            after.trustee,
            after.kind,
            after.mask,
            after.flags,
        )


def test_inherited_entries_are_not_written_back() -> None:
    """Writing them back freezes a copy that stops tracking the parent."""
    built = acl.build(acl.parse(REAL_SDDL))
    assert "BU" not in built
    assert "BA" in built


def test_the_inherited_flag_is_never_written() -> None:
    """It is the server's statement about origin, not ours to claim."""
    descriptor = acl.parse("D:(A;OICI;FA;;;BA)")
    descriptor.aces[0].flags |= acl.INHERITED_ACE
    assert "ID" not in acl.render_flags(descriptor.aces[0].flags)


def test_an_exact_mask_renders_as_its_letters() -> None:
    assert acl.render_rights(acl.FILE_ALL_ACCESS) == "FA"
    assert acl.render_rights(acl.FILE_GENERIC_READ) == "FR"


def test_an_inexact_mask_renders_as_hexadecimal() -> None:
    """Rounding it to the nearest named combination would change the permission."""
    assert acl.render_rights(0x001200A9) == "0x001200a9"


def test_a_protected_dacl_survives_the_round_trip() -> None:
    """Protection is what stops the parent's entries flowing in."""
    assert acl.parse("D:P(A;;FA;;;BA)").protected is True
    assert acl.build(acl.parse("D:P(A;;FA;;;BA)")).startswith("D:P")


# ---------------------------------------------------------------------------
# What a mask means
# ---------------------------------------------------------------------------


def test_generic_bits_expand_to_the_same_rights_as_the_specific_ones() -> None:
    """GR and FR mean the same to the server; the editor must agree."""
    assert acl.rights_of(acl.GENERIC_READ) == acl.rights_of(acl.FILE_GENERIC_READ)


def test_full_control_includes_taking_ownership() -> None:
    rights = acl.rights_of(acl.preset_mask("full"))
    assert "take_ownership" in rights
    assert "change_permissions" in rights


def test_read_does_not_include_write() -> None:
    assert "write" not in acl.rights_of(acl.preset_mask("read"))


def test_an_unknown_preset_is_refused_with_the_list() -> None:
    with pytest.raises(InvalidRequest) as caught:
        acl.preset_mask("almost-full")
    assert "full" in caught.value.context["allowed"]


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        (0, "this_only"),
        (acl.OBJECT_INHERIT | acl.CONTAINER_INHERIT, "this_and_children"),
        (acl.OBJECT_INHERIT | acl.CONTAINER_INHERIT | acl.INHERIT_ONLY, "children_only"),
        (acl.CONTAINER_INHERIT, "folders"),
        (acl.OBJECT_INHERIT, "files"),
    ],
)
def test_inheritance_is_described_the_way_the_dialogs_word_it(flags: int, expected: str) -> None:
    assert acl._applies_to(flags) == expected


# ---------------------------------------------------------------------------
# The intersection — the number neither descriptor gives on its own
# ---------------------------------------------------------------------------


def test_the_share_permission_bounds_the_file_permission() -> None:
    """A read-only share makes a writable file ACL irrelevant.

    This is the case that produces the screenshot saying Full Control next to a
    client saying access denied.
    """
    result = acl.effective_access(acl.FILE_GENERIC_READ, acl.FILE_ALL_ACCESS)
    assert "write" not in result["rights"]
    assert result["limited_by_share"] is True


def test_the_file_permission_bounds_the_share_permission() -> None:
    """The usual Samba arrangement: share wide open, files doing the work."""
    result = acl.effective_access(acl.FILE_ALL_ACCESS, acl.FILE_GENERIC_READ)
    assert "write" not in result["rights"]
    assert result["limited_by_share"] is False


def test_both_permitting_means_permitted() -> None:
    result = acl.effective_access(acl.FILE_ALL_ACCESS, acl.FILE_ALL_ACCESS)
    assert "write" in result["rights"]
    assert result["limited_by_share"] is False


def test_generic_and_specific_masks_intersect_correctly() -> None:
    """A share written with GA and a file written with FA are the same ceiling."""
    generic = acl.effective_access(acl.GENERIC_ALL, acl.FILE_GENERIC_WRITE)
    specific = acl.effective_access(acl.FILE_ALL_ACCESS, acl.FILE_GENERIC_WRITE)
    assert generic["rights"] == specific["rights"]


# ---------------------------------------------------------------------------
# A mask nobody could read must not be reported as a confident zero
#
# A live share root showed four rows as "0x00000000" in the permission level
# column — a number that says "this entry grants nothing", for entries that
# plainly granted something. Whatever the rights field held, the parser did not
# understand it and said so in the one way a reader would believe.
# ---------------------------------------------------------------------------


def test_a_decimal_mask_is_read() -> None:
    """The format allows one, even though Samba writes hex."""
    assert acl._parse_rights("2032127") == (0x001F01FF, True)


def test_an_unknown_letter_pair_is_admitted_rather_than_hidden() -> None:
    """Half a mask silently is the problem; half a mask *labelled* is not.

    What was recognised is kept — it is strictly more than nothing, and the
    effective-access calculation is already honest about being partial. What
    must not happen is the entry being presented as understood, because then a
    permission narrower than the real one reads as authoritative, and that is
    the direction that locks somebody out.
    """
    mask, understood = acl._parse_rights("FRZZ")

    assert understood is False
    assert mask == acl.FILE_GENERIC_READ  # the half that was legible


def test_an_odd_length_rights_field_is_not_guessed_at() -> None:
    assert acl._parse_rights("FRF") == (0, False)


def test_a_field_that_is_understood_says_so() -> None:
    assert acl._parse_rights("FA") == (acl.FILE_ALL_ACCESS, True)
    assert acl._parse_rights("0x001200a9") == (0x001200A9, True)
    assert acl._parse_rights("") == (0, True)


def test_an_unreadable_entry_is_written_back_exactly_as_it_arrived() -> None:
    """The editor was opened to change a different row.

    Re-rendering an entry from a mask the parser admits is incomplete would
    rewrite a permission nobody touched, on the way through a save that was
    about something else entirely.
    """
    descriptor = acl.parse("D:(A;;FRZZ;;;BA)(A;;FA;;;BU)")
    unreadable, ordinary = descriptor.aces

    assert unreadable.understood is False
    assert unreadable.raw_rights == "FRZZ"
    assert ordinary.understood is True

    built = acl.build(descriptor)
    assert "FRZZ" in built  # untouched
    assert "FA" in built  # re-rendered from the mask, as normal


# ---------------------------------------------------------------------------
# The share root of a real Samba AD member
#
# Cross-checked against what `smbcacls //server/share /` printed for the same
# descriptor, which is the only reason the empty masks below are known to be
# real rather than a parsing fault:
#
#   ACL:SPAM-DENY\administrator:ALLOWED/OI|CI/FULL
#   ACL:Unix Group\root:ALLOWED/OI|CI/          <- rights column empty
#   ACL:Everyone:ALLOWED/OI|CI/                 <- rights column empty
#   ACL:SPAM-DENY\Domain Users:ALLOWED/0x0/     <- flags 0, rights empty
# ---------------------------------------------------------------------------

LIVE_SDDL = (
    "O:S-1-5-21-1067335908-1822738269-3252190750-500"
    "G:S-1-5-21-1067335908-1822738269-3252190750-513"
    "D:PAI(A;OICI;FA;;;S-1-5-21-1067335908-1822738269-3252190750-500)"
    "(A;OICI;;;;S-1-22-2-0)"
    "(A;OICI;;;;WD)"
    "(A;;;;;S-1-5-21-1067335908-1822738269-3252190750-513)"
)


def test_an_empty_rights_field_is_a_mask_of_zero_and_not_a_parse_failure() -> None:
    """The entry grants nothing, and that is what the descriptor says.

    Samba builds the NT ACL out of the POSIX one, and a POSIX entry with no
    permission bits becomes an ACE with an empty access mask. Reading that as
    "the parser could not cope" sends somebody hunting for a bug in the wrong
    place — which is exactly where it sent me.
    """
    descriptor = acl.parse(LIVE_SDDL)
    empty = [entry for entry in descriptor.aces if entry.mask == 0]

    assert len(empty) == 3
    for entry in empty:
        assert entry.understood is True  # read correctly, and it says zero
        assert entry.raw_rights == ""


def test_the_owner_and_group_of_a_real_descriptor_are_separate_sids() -> None:
    """Two full SIDs run together with no separator between them."""
    descriptor = acl.parse(LIVE_SDDL)
    assert descriptor.owner == "S-1-5-21-1067335908-1822738269-3252190750-500"
    assert descriptor.group == "S-1-5-21-1067335908-1822738269-3252190750-513"


def test_a_protected_dacl_is_recognised_through_its_other_flags() -> None:
    """`D:PAI` — protected and auto-inherited, which is what smbcacls calls DP."""
    assert acl.parse(LIVE_SDDL).protected is True


def test_an_entry_that_grants_nothing_survives_the_round_trip() -> None:
    """It is in the descriptor, so it stays in the descriptor.

    Dropping an ACE because it grants nothing would be an editor quietly
    rewriting a permission set it was opened only to look at.
    """
    once = acl.parse(LIVE_SDDL)
    twice = acl.parse(acl.build(once))

    assert len(twice.aces) == len(once.aces)
    assert [entry.mask for entry in twice.aces] == [entry.mask for entry in once.aces]


# ---------------------------------------------------------------------------
# Aliases that are a RID, not a SID
# ---------------------------------------------------------------------------


def test_a_descriptor_of_whole_sids_needs_no_domain() -> None:
    """Nothing to expand means nothing to get wrong."""
    assert acl.domain_relative_trustees("O:BAG:BAD:(A;;FA;;;WD)(A;;0x1200a9;;;BU)") == []


def test_domain_relative_aliases_are_found_wherever_they_stand() -> None:
    """Owner, group and trustee are three places one can hide."""
    found = acl.domain_relative_trustees("O:DAG:DUD:(A;;FA;;;BA)(A;;FR;;;DG)")
    assert found == ["DA", "DU", "DG"]


def test_the_same_alias_is_reported_once() -> None:
    assert acl.domain_relative_trustees("O:DAG:DAD:(A;;FA;;;DA)") == ["DA"]


def test_the_rights_field_is_not_searched_for_trustees() -> None:
    """DC is Delete Child here and Domain Computers two fields along.

    The letters are shared, so a text scan would refuse a descriptor that is
    perfectly fine. Only a parsed trustee counts.
    """
    assert acl.domain_relative_trustees("D:(A;;DCLCRPWD;;;BA)") == []
    assert acl.domain_relative_trustees("D:(A;;DCLCRPWD;;;DC)") == ["DC"]


def test_the_local_administrator_alias_counts_as_domain_relative() -> None:
    """LA is RID 500 of a domain, not a fixed SID — the same trap as DA."""
    assert acl.domain_relative_trustees("D:(A;;FA;;;LA)") == ["LA"]
