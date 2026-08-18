"""Liveness and readiness."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from samfscon import __version__
from samfscon.auth.session import get_store
from samfscon.config import MODE_AUTO, get_settings
from samfscon.core.executor import get_registry

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, Any]:
    """Cheap liveness probe — never touches a file server."""
    return {"status": "ok", "version": __version__}


@router.get("/info")
def info() -> dict[str, Any]:
    """What the front end needs before anyone signs in."""
    settings = get_settings()
    return {
        "version": __version__,
        # Empty when no default server is configured — the sign-in form then
        # asks for an address.
        "server_host": settings.server_host or None,
        "server_mode": settings.server_mode,
        "realm": settings.realm or None,
        "workgroup": settings.netbios_name or None,
        "allow_custom_servers": settings.allow_custom_servers,
        # The sign-in form greys out the standalone option when this is false,
        # rather than letting someone fill the form in and be refused at the end.
        "allow_standalone": settings.allow_standalone,
        "has_server_profiles": bool(settings.servers_file),
        "mode_is_discovered": settings.server_mode == MODE_AUTO,
        "smb": {
            "min_protocol": settings.smb_min_protocol,
            "encrypt": settings.smb_encrypt,
        },
        "sessions": {
            "active": get_store().count(),
            "workers": get_registry().active_sessions(),
            "idle_timeout_minutes": settings.session_idle_minutes,
        },
    }
