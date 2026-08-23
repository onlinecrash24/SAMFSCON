"""Reading the whole store at once, and what a missing section means.

``read_all`` exists for the sweep the diagnostics view needs: judging every
share's options through ``read_options`` is three key opens per share, and a
server with forty shares would spend a hundred and twenty round trips on data
``net conf list`` prints in one go.

The property worth pinning down is not the saving. It is that a section whose
values could not be read is **absent** from the result rather than present and
empty. Those two are indistinguishable to a caller, and the difference decides
whether a rule reports "this share stores no options" — a fact about the server
— or stays silent because nobody could look, which is a fact about the session.

Getting that backwards would make every unreadable share pass every option rule
silently, which is the failure this project keeps finding in itself.
"""

from __future__ import annotations

from typing import Any

import pytest

from samfscon.srv import registry


class Pipe:
    """The winreg pipe, as far as read_all uses it."""

    def __init__(self) -> None:
        self.closed: list[Any] = []

    def CloseKey(self, key: Any) -> None:  # noqa: N802 - the wire method's name
        self.closed.append(key)


class Connection:
    def __init__(self) -> None:
        self.winreg = Pipe()


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch):
    """A fake registry: section name -> values, or an exception to raise."""
    holder: dict[str, Any] = {"sections": {}}

    import contextlib

    @contextlib.contextmanager
    def open_smbconf(_conn: Any, *, write: bool = False):
        yield "ROOT"

    def enumerate_keys(_pipe: Any, _root: Any) -> list[str]:
        return list(holder["sections"])

    def open_key(_pipe: Any, _root: Any, name: str, _access: int) -> str:
        value = holder["sections"][name]
        if isinstance(value, Exception) and getattr(value, "on_open", False):
            raise value
        return f"KEY:{name}"

    def enumerate_values(_pipe: Any, key: str) -> list[tuple[str, str]]:
        name = key.split(":", 1)[1]
        value = holder["sections"][name]
        if isinstance(value, Exception):
            raise value
        return list(value.items())

    monkeypatch.setattr(registry, "open_smbconf", open_smbconf)
    monkeypatch.setattr(registry, "_enumerate_keys", enumerate_keys)
    monkeypatch.setattr(registry, "_open_key", open_key)
    monkeypatch.setattr(registry, "_enumerate_values", enumerate_values)
    return holder


def test_every_section_comes_back_with_its_values(store) -> None:
    store["sections"] = {
        "global": {"workgroup": "SPAM-DENY"},
        "projects": {"path": "/tank/projects", "read only": "no"},
    }

    assert registry.read_all(Connection()) == {
        "global": {"workgroup": "SPAM-DENY"},
        "projects": {"path": "/tank/projects", "read only": "no"},
    }


def test_a_section_that_stores_nothing_comes_back_empty(store) -> None:
    # A real state: a key created and not yet written to. It is present.
    store["sections"] = {"projects": {}}

    result = registry.read_all(Connection())
    assert "projects" in result
    assert result["projects"] == {}


def test_a_section_whose_values_refuse_is_absent_rather_than_empty(store) -> None:
    """The distinction the whole function is written around."""
    store["sections"] = {
        "projects": {"path": "/tank/projects"},
        "secrets": PermissionError("WERR_ACCESS_DENIED"),
    }

    result = registry.read_all(Connection())
    assert "secrets" not in result
    # And the sweep carried on rather than losing the sections after it.
    assert result["projects"] == {"path": "/tank/projects"}


def test_a_section_that_will_not_open_is_absent_too(store) -> None:
    failure = PermissionError("WERR_ACCESS_DENIED")
    failure.on_open = True  # type: ignore[attr-defined]
    store["sections"] = {"secrets": failure, "projects": {"path": "/tank"}}

    result = registry.read_all(Connection())
    assert set(result) == {"projects"}


def test_the_global_section_comes_back_like_any_other(store) -> None:
    """It is a section in this store, and callers exclude it themselves.

    Filtering it here would take it away from the settings console, which
    wants exactly that key.
    """
    store["sections"] = {"global": {"security": "ads"}}
    assert "global" in registry.read_all(Connection())


def test_every_key_that_was_opened_is_closed(store) -> None:
    store["sections"] = {
        "a": {"path": "/a"},
        "b": PermissionError("WERR_ACCESS_DENIED"),
        "c": {"path": "/c"},
    }

    conn = Connection()
    registry.read_all(conn)

    # Including the one whose values failed: a handle left open is a handle the
    # server holds for the life of the session.
    assert conn.winreg.closed == ["KEY:a", "KEY:b", "KEY:c"]


def test_an_empty_store_is_an_empty_result(store) -> None:
    store["sections"] = {}
    assert registry.read_all(Connection()) == {}
