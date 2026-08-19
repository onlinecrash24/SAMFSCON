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
