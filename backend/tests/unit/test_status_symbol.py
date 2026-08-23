"""Getting the status symbol back out, and knowing when you have not.

``translate`` turns NT_STATUS_BAD_NETWORK_NAME into "the share does not exist"
and drops the symbol, which is right for anything a person reads. A caller
deciding what to do next needs the other one: BAD_NETWORK_NAME and ACCESS_DENIED
are "there is no such share" and "there is one and you may not open it", and a
probe that cannot tell them apart reports a share as missing when it is only
forbidden.

The half worth testing carefully is the ``None``. It is the honest answer for an
exception with no status in it — and it is *also* the answer for a status that
arrived as a number this module does not map, and for any number at all on a
host without the Samba bindings. A caller reading None as "not that status"
would be reading a gap in a table as a fact about a server, which is the fault
this codebase keeps finding in itself.
"""

from __future__ import annotations

import pytest

from samfscon.core.errors import _numeric_nt_status, status_symbol


class NTSTATUSError(Exception):
    """What the bindings raise: a number and a sentence, never the symbol."""


# ---------------------------------------------------------------------------
# In the message
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "symbol",
    [
        "NT_STATUS_BAD_NETWORK_NAME",
        "NT_STATUS_ACCESS_DENIED",
        "NT_STATUS_OBJECT_NAME_NOT_FOUND",
        "WERR_ACCESS_DENIED",
        "WERR_NO_MORE_ITEMS",
    ],
)
def test_a_symbol_in_the_message_comes_back(symbol: str) -> None:
    assert status_symbol(Exception(f"{symbol} (0x00000005)")) == symbol


def test_an_unmapped_symbol_comes_back_too() -> None:
    """It is still the thing an administrator would look up.

    translate() only names statuses it has a message for; this does not have to
    care, because it hands back a symbol rather than a sentence.
    """
    assert status_symbol(Exception("NT_STATUS_SOMETHING_NOBODY_MAPPED")) == (
        "NT_STATUS_SOMETHING_NOBODY_MAPPED"
    )


def test_the_first_symbol_wins_when_a_message_carries_two() -> None:
    # Nested exceptions stringify into one another. The outermost is the one
    # the caller asked about.
    assert (
        status_symbol(
            Exception("NT_STATUS_ACCESS_DENIED while handling NT_STATUS_BAD_NETWORK_NAME")
        )
        == "NT_STATUS_ACCESS_DENIED"
    )


# ---------------------------------------------------------------------------
# Not a status at all
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc",
    [
        TimeoutError("the KDC did not answer"),
        ConnectionRefusedError("445"),
        ValueError("that is not a share name"),
        Exception(""),
    ],
)
def test_an_exception_with_no_status_has_none(exc: BaseException) -> None:
    assert status_symbol(exc) is None


# ---------------------------------------------------------------------------
# The number, and the limit
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _numeric_nt_status(),
    reason="the numeric tables are read out of samba.ntstatus, which is not installed here",
)
def test_a_number_is_looked_up_when_the_bindings_are_present() -> None:
    # 0xC000000D — NT_STATUS_INVALID_PARAMETER, one of the mapped symbols.
    assert status_symbol(NTSTATUSError((0xC000000D, "An invalid parameter was passed"))) == (
        "NT_STATUS_INVALID_PARAMETER"
    )


def test_a_number_answers_nothing_without_the_bindings() -> None:
    """Named rather than left to be discovered.

    Without samba installed the numeric tables are empty, so every
    number-only exception answers None. That is a fact about this host and not
    about the server, and it is why the docstring says so — a caller branching
    on `status_symbol(exc) == X` behaves differently inside the container and
    outside it.
    """
    result = status_symbol(NTSTATUSError((0xC000000D, "An invalid parameter was passed")))
    assert result in {None, "NT_STATUS_INVALID_PARAMETER"}
    if not _numeric_nt_status():
        assert result is None
