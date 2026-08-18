"""Shared fixtures.

The unit suite runs without python3-samba and without a server: everything that
touches the bindings is imported inside a function, so the logic around it —
translation, validation, session handling, SDDL — stays testable on any machine.
That is what lets the CI run it on a stock runner.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """No SAMFSCON_* variable from the developer's shell reaches a test.

    Without this, a machine that happens to export SAMFSCON_SERVER_HOST passes
    tests that fail everywhere else — or worse, fails tests that are fine.
    """
    for name in list(os.environ):
        if name.startswith("SAMFSCON_"):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def fresh_settings() -> None:
    """Settings are cached with lru_cache; a test that changes the environment
    must not inherit the previous test's answer."""
    from samfscon.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
