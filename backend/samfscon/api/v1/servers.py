"""Choosing which file server to sign in to.

Both endpoints answer before authentication, because the sign-in form needs
them. The probe therefore opens outbound connections for an unauthenticated
caller — it is rate limited, and the port it touches is fixed in code so it
cannot be turned into a port scanner.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from samfscon.auth.deps import client_ip
from samfscon.config import get_settings
from samfscon.core.errors import InvalidRequest
from samfscon.core.ratelimit import probe_limiter
from samfscon.schemas.requests import ProbeRequest
from samfscon.srv import discovery, targets

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("")
def list_servers() -> dict[str, Any]:
    """Configured profiles and the default server, for the sign-in form."""
    return targets.describe_profiles(get_settings())


@router.post("/probe")
async def probe_server(payload: ProbeRequest, request: Request) -> dict[str, Any]:
    """Identify the server behind an address.

    Reads the LSA policy without authenticating, which yields the server's own
    name, its account domain and — for a domain member — the Kerberos realm.
    That is what makes entering a bare IP work: Kerberos needs a realm and a
    service principal, and neither can be derived from an address.

    The answer also says whether the mode could be decided at all. A server
    that refuses unauthenticated queries leaves it open, and the form then asks
    rather than guessing — the notes explain why, so "choose one" is not a
    prompt somebody answers by coin flip.
    """
    settings = get_settings()
    if not settings.allow_custom_servers and not payload.profile_id:
        raise InvalidRequest(
            "This installation only allows the configured servers.",
            code="custom_servers_disabled",
        )

    probe_limiter.check(client_ip(request) or "unknown")

    host = payload.host
    if payload.profile_id:
        profile = targets.find_profile(settings, payload.profile_id)
        host = host or profile.host

    if not host:
        raise InvalidRequest("No server address was given.", code="missing_server")

    found = await run_in_threadpool(discovery.probe, discovery.normalise_host(host), settings)

    result = found.describe()
    # The form greys the standalone option out rather than letting somebody
    # fill the whole thing in and be refused at the end.
    result["allow_standalone"] = settings.allow_standalone
    return result
