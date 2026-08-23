"""Version 1 of the API."""

from fastapi import APIRouter

from samfscon.api.v1 import (
    accounts,
    auth,
    config,
    diagnostics,
    files,
    health,
    identity,
    permissions,
    servers,
    sessions,
    shares,
)

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(servers.router)
router.include_router(auth.router)
router.include_router(identity.router)
router.include_router(shares.router)
router.include_router(config.router)
router.include_router(permissions.router)
router.include_router(sessions.router)
router.include_router(files.router)
router.include_router(accounts.router)
router.include_router(diagnostics.router)

__all__ = ["router"]
