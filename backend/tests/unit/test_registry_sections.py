"""Which registry sections are shares, and which are not.

``HKLM\\Software\\Samba\\smbconf`` holds one key per *section*, and a section is
not the same thing as a share: ``global`` lives there too, and on a server
configured with nothing but ``include = registry`` it is the only key there.

Counting it as a share was wrong in a way that took a button away. The section
set was not empty, so :func:`registry_shares_served` did not answer "nothing to
compare"; it intersected the live share list nowhere, so it answered "this
server ignores its registry" — and the console stopped offering to create a
share on a server that would have served one perfectly well.

The failure is worth a test rather than a fix alone, because both of the wrong
answers here are quiet. One removes an ability the account has; the other would
offer an ability it does not.
"""

from __future__ import annotations

from typing import Any

import pytest

from samfscon.srv import shares


class Connection:
    """Enough of a connection for the two functions under test."""


@pytest.fixture
def sections(monkeypatch: pytest.MonkeyPatch):
    """Control what the registry appears to hold."""
    holder: dict[str, Any] = {"names": [], "error": None}

    def read_sections(_conn: Any) -> list[str]:
        if holder["error"] is not None:
            raise holder["error"]
        return list(holder["names"])

    monkeypatch.setattr(shares.registry, "read_sections", read_sections)
    return holder


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch):
    """Control what the server appears to publish."""
    holder: dict[str, Any] = {"names": [], "error": None}

    def enumerate_names(_conn: Any) -> list[shares.Share]:
        if holder["error"] is not None:
            raise holder["error"]
        return [
            shares.Share(name=name, type="disk", path=None, comment=None, special=False)
            for name in holder["names"]
        ]

    monkeypatch.setattr(shares, "_enumerate_names", enumerate_names)
    return holder


# ---------------------------------------------------------------------------
# global is a section, not a share
# ---------------------------------------------------------------------------


def test_the_global_section_is_not_a_share(sections) -> None:
    sections["names"] = ["global", "projects"]
    assert shares._registry_sections(Connection()) == {"projects"}


def test_a_registry_holding_only_global_holds_no_shares(sections) -> None:
    # What `include = registry` on its own produces, and the case that was
    # being read as "this server ignores its registry".
    sections["names"] = ["global"]
    assert shares._registry_sections(Connection()) == set()


def test_the_section_name_is_matched_without_regard_to_case(sections) -> None:
    sections["names"] = ["Global"]
    assert shares._registry_sections(Connection()) == set()


def test_a_registry_that_cannot_be_read_is_not_a_registry_with_nothing_in_it(
    sections,
) -> None:
    """None, never an empty set.

    An empty set would report every share as uneditable — as a fact about the
    server rather than as a consequence of not having looked.
    """
    sections["error"] = RuntimeError("WERR_ACCESS_DENIED")
    assert shares._registry_sections(Connection()) is None


# ---------------------------------------------------------------------------
# What that means for the button
# ---------------------------------------------------------------------------


def test_global_alone_decides_nothing_about_registry_shares(sections, live) -> None:
    """The regression. It answered False and disabled creating a share."""
    sections["names"] = ["global"]
    live["names"] = ["share", "print$"]

    assert shares.registry_shares_served(Connection()) is None


def test_a_registry_share_the_server_publishes_proves_it_serves_them(sections, live) -> None:
    sections["names"] = ["global", "projects"]
    live["names"] = ["projects", "share"]

    assert shares.registry_shares_served(Connection()) is True


def test_a_registry_share_the_server_does_not_publish_proves_it_does_not(sections, live) -> None:
    # The finding this function exists for: configuration written and ignored.
    sections["names"] = ["projects"]
    live["names"] = ["share"]

    assert shares.registry_shares_served(Connection()) is False


def test_an_unreadable_share_list_decides_nothing(sections, live) -> None:
    sections["names"] = ["projects"]
    live["error"] = RuntimeError("WERR_ACCESS_DENIED")

    assert shares.registry_shares_served(Connection()) is None


def test_an_unreadable_registry_decides_nothing(sections, live) -> None:
    sections["error"] = RuntimeError("WERR_ACCESS_DENIED")
    live["names"] = ["share"]

    assert shares.registry_shares_served(Connection()) is None
