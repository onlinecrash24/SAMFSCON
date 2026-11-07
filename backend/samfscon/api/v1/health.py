"""Liveness and readiness."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from samfscon import __version__
from samfscon.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, Any]:
    """Cheap liveness probe — never touches a file server."""
    return {"status": "ok", "version": __version__}


@router.get("/info")
def info() -> dict[str, Any]:
    """What the sign-in form reads before anyone signs in — and nothing else.

    Reachable without a session, so it carries only what the form actually
    uses: the version, which the source-code notice the AGPL requires shows on
    the sign-in page, and whether standalone servers are permitted, which greys
    out that option rather than letting somebody fill the form in and be
    refused at the end.

    It used to carry the default server's address, its realm and workgroup, the
    SMB floor, whether profiles exist, and a live count of signed-in
    administrators and workers. The front end read none of it. To anybody else
    it was a description of the deployment and of who was using it right now —
    SAMADCON dropped the same fields for the same reason. What the form needs
    about a server comes from /servers, which is shaped for exactly that.
    """
    settings = get_settings()
    return {
        "version": __version__,
        "allow_standalone": settings.allow_standalone,
    }
