"""One failed read costs one section, and says so.

The gatherer's whole job beyond fetching is what it does when a fetch fails.
Two wrong behaviours are available and both are quiet: taking the page down for
one refused call, or shrinking the report and letting the absence read as a
clean result.

So every section is tried on its own, and what could not be read is named in
``unreadable`` — beside the findings, never inside them. These tests drive each
section into failure one at a time and check that the rest of the report
survives and that the gap is named.
"""

from __future__ import annotations

from typing import Any

import pytest

from samfscon.core import findings_source


class Facts:
    def __init__(self, **values: Any) -> None:
        self._values = values

    def describe(self) -> dict[str, Any]:
        return dict(self._values)


class Connection:
    """Enough of a connection for the gatherer to read its two free facts."""

    def __init__(self) -> None:
        self.info = Facts(name="FS1", mode="standalone")
        self.transport = Facts(
            auth="kerberos", signed=True, encrypted=False, identity_verified=True
        )


class Share:
    def __init__(self, name: str, path: str = "/tank/x", editable: bool = True) -> None:
        self.name = name
        self._path = path
        self._editable = editable

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "disk",
            "path": self._path,
            "comment": None,
            "editable": self._editable,
        }


class Session:
    def __init__(self, **values: Any) -> None:
        self._values = values

    def describe(self) -> dict[str, Any]:
        return dict(self._values)


class Capabilities:
    def __init__(self, **values: Any) -> None:
        self._values = values

    def describe(self) -> dict[str, Any]:
        base = {
            "registry_config": True,
            "has_disk_operator": True,
            "disk_operators": [],
            "disk_operator_sids": [],
            "notes": [],
        }
        base.update(self._values)
        return base


BOOM = RuntimeError("NT_STATUS_ACCESS_DENIED")


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch):
    """Every section the gatherer reads, each independently breakable."""
    from samfscon.srv import diagnostics, registry, sessions, shares

    state: dict[str, Any] = {
        "capabilities": Capabilities(),
        "facts": {"name": "FS1"},
        "shares": [Share("projects"), Share("archive", path="/tank/archive")],
        "registry": {"projects": {"guest ok": "yes"}, "global": {"workgroup": "X"}},
        "sessions": [Session(guest=False, client="10.0.0.1")],
    }

    def maybe(key: str) -> Any:
        value = state[key]
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(diagnostics, "capabilities", lambda _c, **_k: maybe("capabilities"))
    monkeypatch.setattr(diagnostics, "server_facts", lambda _c: maybe("facts"))
    monkeypatch.setattr(shares, "list_shares", lambda _c, **_k: maybe("shares"))
    monkeypatch.setattr(registry, "read_all", lambda _c: maybe("registry"))
    monkeypatch.setattr(sessions, "list_sessions", lambda _c, **_k: maybe("sessions"))
    return state


def reasons(result: dict[str, Any]) -> set[str]:
    return {item["reason"] for item in result["unreadable"]}


# ---------------------------------------------------------------------------
# The whole report, when everything answers
# ---------------------------------------------------------------------------


def test_a_complete_reading_carries_its_own_values(world) -> None:
    result = findings_source.collect(Connection())

    # The findings and what they were decided from, in one payload. A report
    # assembled from a second set of reads would carry a timestamp true of
    # none of it.
    assert result["generated_at"].endswith("+00:00")
    assert result["server"]["name"] == "FS1"
    assert result["transport"]["auth"] == "kerberos"
    assert [share["name"] for share in result["shares"]] == ["projects", "archive"]

    # The rules ran: `projects` stores guest ok = yes.
    assert "share_guest_ok" in {item["id"] for item in result["findings"]}


def test_a_share_with_no_registry_key_is_named_rather_than_passed(world) -> None:
    """`archive` has no section, so no option rule may speak for it."""
    result = findings_source.collect(Connection())

    archive = next(share for share in result["shares"] if share["name"] == "archive")
    assert archive["config_readable"] is False
    assert ("shares", "archive") in {
        (item["area"], item["subject"]) for item in result["unreadable"]
    }
    assert result["coverage"]["shares_with_readable_configuration"] == 1
    assert result["coverage"]["shares_without_readable_configuration"] == 1


def test_the_global_section_is_not_counted_as_a_share_section(world) -> None:
    result = findings_source.collect(Connection())
    assert result["registry"]["share_sections"] == ["projects"]
    assert result["registry"]["global_section_present"] is True
    assert result["registry"]["served"] is True


def test_a_registry_holding_only_the_global_section_decides_nothing(world) -> None:
    world["registry"] = {"global": {"workgroup": "X"}}
    result = findings_source.collect(Connection())

    # None, not False. This is the case that used to disable the share buttons.
    assert result["registry"]["served"] is None
    assert "registry_shares_not_served" not in {item["id"] for item in result["findings"]}


# ---------------------------------------------------------------------------
# One section at a time, into the ground
# ---------------------------------------------------------------------------


def test_a_refused_capability_probe_costs_the_management_rules_only(world) -> None:
    world["capabilities"] = BOOM
    result = findings_source.collect(Connection())

    assert "capabilities_unreadable" in reasons(result)
    # And the rest of the report is still there.
    assert result["shares"]
    assert result["transport"]["auth"] == "kerberos"


def test_refused_server_facts_cost_one_block(world) -> None:
    """The one function in that module that raises, and level 102 needs
    more rights than 101 — so this is the ordinary case on a locked-down
    server rather than an exotic one."""
    world["facts"] = BOOM
    result = findings_source.collect(Connection())

    assert result["facts"] is None
    assert "server_facts_unreadable" in reasons(result)
    assert result["shares"]


def test_an_unreadable_share_list_skips_everything_downstream(world) -> None:
    world["shares"] = BOOM
    result = findings_source.collect(Connection())

    assert result["shares"] == []
    assert result["registry"] is None
    assert "shares_unreadable" in reasons(result)
    # Not one row per share — there is no share list to have rows for.
    assert len([item for item in result["unreadable"] if item["area"] == "shares"]) == 1
    # And the sections that did answer are still judged.
    assert result["transport"]["auth"] == "kerberos"


def test_an_unreadable_registry_is_one_row_and_not_one_per_share(world) -> None:
    """Thirteen identical lines would bury the findings."""
    world["registry"] = BOOM
    result = findings_source.collect(Connection())

    assert "registry_unreadable" in reasons(result)
    # Every share is uncovered, and each is still named — but the cause is
    # stated once.
    assert all(share["config_readable"] is False for share in result["shares"])
    assert result["coverage"]["shares_with_readable_configuration"] == 0


def test_an_unreadable_session_list_costs_the_session_rules_only(world) -> None:
    world["sessions"] = BOOM
    result = findings_source.collect(Connection())

    assert result["sessions"] == []
    assert "sessions_unreadable" in reasons(result)
    assert result["shares"]


def test_everything_failing_still_produces_a_report(world) -> None:
    """A page that renders nothing is worse than one that says what it missed."""
    for key in ("capabilities", "facts", "shares", "sessions"):
        world[key] = BOOM

    result = findings_source.collect(Connection())

    assert result["findings"] != [] or result["unreadable"] != []
    assert reasons(result) >= {
        "capabilities_unreadable",
        "server_facts_unreadable",
        "shares_unreadable",
        "sessions_unreadable",
    }


# ---------------------------------------------------------------------------
# States that come out of the data rather than out of a failure
# ---------------------------------------------------------------------------


def test_an_unconfirmed_privilege_is_named_even_though_nothing_failed(world) -> None:
    """None means nested membership was in the way, not that nobody holds it.

    Without this row the report is silent on the point, and silence on a
    diagnostics screen reads as "checked, and fine".
    """
    world["capabilities"] = Capabilities(has_disk_operator=None)
    result = findings_source.collect(Connection())

    assert "privilege_unconfirmed" in reasons(result)
    assert "disk_operator_unassigned" not in {item["id"] for item in result["findings"]}


def test_an_unknown_registry_state_is_named_too(world) -> None:
    world["capabilities"] = Capabilities(registry_config=None)
    result = findings_source.collect(Connection())

    assert "registry_state_unknown" in reasons(result)
    assert "registry_config_absent" not in {item["id"] for item in result["findings"]}


# ---------------------------------------------------------------------------
# What the report does not claim
# ---------------------------------------------------------------------------


def test_connectivity_is_reported_as_unexamined_rather_than_as_fine(world) -> None:
    """Nothing here connects to a share.

    So the report says nothing about whether any of them can be opened — and a
    screen listing no broken shares is read as a server with none. The number
    is what stops that.
    """
    result = findings_source.collect(Connection())

    assert result["coverage"]["shares_probed"] == 0
    assert result["coverage"]["connectivity_examined"] is False
    assert result["coverage"]["permissions_examined"] is False
