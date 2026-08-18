"""Configuration, and the environment shapes docker compose actually produces."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from samfscon.config import MODE_AD_MEMBER, MODE_AUTO, MODE_STANDALONE, Settings


def test_defaults_need_no_server() -> None:
    """An empty configuration is a valid one: the form asks for an address."""
    settings = Settings()
    assert settings.server_host == ""
    assert settings.server_mode == MODE_AUTO
    assert settings.default_target is None
    assert settings.allow_custom_servers is True
    assert settings.allow_standalone is True


def test_realm_and_workgroup_are_upper_cased(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAMFSCON_REALM", " example.lan ")
    monkeypatch.setenv("SAMFSCON_WORKGROUP", "wrkgrp")
    settings = Settings()
    assert settings.realm == "EXAMPLE.LAN"
    assert settings.workgroup == "WRKGRP"


def test_kdc_hosts_take_a_comma_separated_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """Compose passes a plain string; pydantic would otherwise try JSON on it.

    This is the failure that stops the container at startup rather than at use,
    which is why it has a test of its own.
    """
    monkeypatch.setenv("SAMFSCON_KDC_HOSTS", "dc1.example.lan, dc2.example.lan ,")
    settings = Settings()
    assert settings.kdc_hosts == ["dc1.example.lan", "dc2.example.lan"]


def test_an_empty_servers_file_is_not_a_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Compose substitutes an unset variable with "", and Path("") is Path(".").

    Without this, an unset SAMFSCON_SERVERS_FILE would make the container try to
    read its working directory as JSON.
    """
    monkeypatch.setenv("SAMFSCON_SERVERS_FILE", "  ")
    assert Settings().servers_file is None


def test_an_unknown_mode_falls_back_to_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    """A typo in the environment must not stop the container from starting."""
    monkeypatch.setenv("SAMFSCON_SERVER_MODE", "kerberos-please")
    assert Settings().server_mode == MODE_AUTO


def test_default_target_carries_the_configured_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAMFSCON_SERVER_HOST", "fs1.example.lan")
    monkeypatch.setenv("SAMFSCON_SERVER_MODE", "ad_member")
    monkeypatch.setenv("SAMFSCON_REALM", "example.lan")

    target = Settings().default_target
    assert target is not None
    assert target.host == "fs1.example.lan"
    assert target.mode == MODE_AD_MEMBER
    assert target.realm == "EXAMPLE.LAN"
    assert target.uses_kerberos is True


def test_profiles_survive_one_broken_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One malformed profile must not cost the administrator the other three."""
    path = tmp_path / "servers.json"
    path.write_text(
        json.dumps(
            [
                {"id": "fs1", "host": "fs1.example.lan", "mode": "ad_member"},
                {"id": "broken", "host": "nas.example.lan", "mode": "telepathy"},
                {"id": "nas", "host": "nas.example.lan", "mode": "standalone"},
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SAMFSCON_SERVERS_FILE", str(path))

    profiles = Settings().load_profiles()
    assert [p.id for p in profiles] == ["fs1", "nas"]
    assert profiles[1].mode == MODE_STANDALONE


def test_an_unreadable_profile_file_is_logged_not_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "servers.json"
    path.write_text("{ this is not json", encoding="utf-8")
    monkeypatch.setenv("SAMFSCON_SERVERS_FILE", str(path))
    assert Settings().load_profiles() == []


def test_a_missing_profile_file_is_not_fatal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAMFSCON_SERVERS_FILE", "/nonexistent/servers.json")
    assert Settings().load_profiles() == []
