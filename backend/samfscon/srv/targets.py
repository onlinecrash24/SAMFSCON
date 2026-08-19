"""Turning what the sign-in form sends into a connection target.

Three sources, in this order:

1. an explicit server address — its mode and realm discovered from the server,
2. a configured profile,
3. the container's default server.

Resolution touches the network (the probe), so it belongs on a worker thread
like every other Samba call.

The one thing this module refuses to do is guess a mode. If the server would
not say and nobody chose, resolution fails with a message that asks — because
guessing "standalone" against a domain member would offer to hold a password
that Kerberos made unnecessary, and guessing the other way would try for a
ticket no KDC will ever issue.
"""

from __future__ import annotations

import logging
from typing import Any

from samfscon.config import (
    MODE_AD_MEMBER,
    MODE_AUTO,
    MODE_STANDALONE,
    ServerProfile,
    Settings,
)
from samfscon.core.errors import InvalidRequest, NotFound
from samfscon.srv import discovery
from samfscon.srv.target import ServerTarget

logger = logging.getLogger(__name__)


def list_profiles(settings: Settings) -> list[ServerProfile]:
    return settings.load_profiles()


def find_profile(settings: Settings, profile_id: str) -> ServerProfile:
    for profile in list_profiles(settings):
        if profile.id == profile_id:
            return profile
    raise NotFound(
        "The selected server profile does not exist.",
        code="unknown_server_profile",
        context={"profile_id": profile_id},
    )


def describe_profiles(settings: Settings) -> dict[str, Any]:
    """Server list for the sign-in form.

    Answers before anyone has authenticated, so it carries only what the form
    needs to draw itself — never a path from the container's file system.
    """
    profiles = [
        {
            "id": profile.id,
            "label": profile.label or profile.host or profile.id,
            "host": profile.host,
            "mode": profile.mode,
            "realm": profile.realm,
            "workgroup": profile.workgroup,
        }
        for profile in list_profiles(settings)
    ]

    default = settings.default_target
    return {
        "profiles": profiles,
        "default": (
            {
                "host": default.host,
                "mode": default.mode,
                "realm": default.realm,
                "workgroup": default.workgroup,
            }
            if default is not None
            else None
        ),
        "allow_custom_servers": settings.allow_custom_servers,
        "allow_standalone": settings.allow_standalone,
    }


def resolve_target(
    settings: Settings,
    *,
    server: str | None = None,
    mode: str | None = None,
    realm: str | None = None,
    profile_id: str | None = None,
) -> ServerTarget:
    """Build the target to sign in against. Runs in a worker thread.

    ``mode`` is what the administrator picked in the form, and it wins over
    discovery: somebody who knows their server is a domain member should not
    have to argue with a probe that a firewall silenced.
    """
    if profile_id:
        target = _from_profile(settings, profile_id, mode=mode, realm=realm)
    elif server:
        target = _from_address(settings, server, mode=mode, realm=realm)
    else:
        target = _from_default(settings, mode=mode, realm=realm)

    return _require_decision(settings, target)


def _from_profile(
    settings: Settings, profile_id: str, *, mode: str | None, realm: str | None
) -> ServerTarget:
    profile = find_profile(settings, profile_id)
    if not profile.host:
        raise InvalidRequest(
            "The server profile names no host.",
            code="incomplete_server_profile",
            context={"profile_id": profile_id},
        )

    target = ServerTarget(
        host=profile.host,
        mode=_pick_mode(mode, profile.mode),
        realm=realm or profile.realm,
        workgroup=profile.workgroup,
        kdcs=tuple(settings.kdc_hosts),
        label=profile.label,
        profile_id=profile.id,
    )
    # Probed even when the profile says everything: the server's own FQDN comes
    # from here, and that is what a Kerberos ticket has to be asked for. Not
    # required — a profile that names the mode is usable without it.
    return _enrich(settings, target, required=not target.decided)


def _from_address(
    settings: Settings, server: str, *, mode: str | None, realm: str | None
) -> ServerTarget:
    if not settings.allow_custom_servers:
        raise InvalidRequest(
            "This installation only allows the configured servers.",
            code="custom_servers_disabled",
            hint="Pick one of the offered servers.",
        )

    host = discovery.normalise_host(server)
    target = ServerTarget(
        host=host,
        mode=_pick_mode(mode, MODE_AUTO),
        realm=realm,
        kdcs=tuple(settings.kdc_hosts),
    )
    # A typed address tells us nothing on its own, so the probe is required
    # unless the administrator already said which mode this is.
    return _enrich(settings, target, required=not target.decided)


def _from_default(settings: Settings, *, mode: str | None, realm: str | None) -> ServerTarget:
    default = settings.default_target
    if default is None:
        raise InvalidRequest(
            "No server was given and this installation has no default.",
            code="no_target",
            hint="Enter the address of a file server.",
        )

    target = default
    if mode or realm:
        target = target.with_discovery(mode=_pick_mode(mode, target.mode), realm=realm)
    # Probed for the same reason as everything else: the configured host may be
    # an IP address, and Kerberos needs the name behind it.
    return _enrich(settings, target, required=not target.decided)


def _enrich(settings: Settings, target: ServerTarget, *, required: bool) -> ServerTarget:
    """Fill in mode, realm and the server's own name from the server itself."""
    try:
        found = discovery.probe(target.host, settings)
    except Exception as exc:
        if required:
            raise
        # With the reason. Without it this line reads as a network hiccup, and
        # the catch is wide enough to swallow a mistake in our own code and
        # report it the same way — which is how a sign-in ends up failing later,
        # at the connect, over a name that was never fetched.
        logger.warning(
            "probe of %s failed (%s: %s); continuing with the configured values",
            target.host,
            type(exc).__name__,
            exc,
        )
        return target

    # What the administrator or the profile already decided stays decided; the
    # probe only fills gaps.
    return target.with_discovery(
        mode=target.mode if target.decided else found.mode,
        realm=target.realm or found.realm,
        workgroup=target.workgroup or found.workgroup,
        netbios_name=found.netbios_name,
        server_fqdn=found.server_fqdn,
        os_version=found.os_version,
    )


def _require_decision(settings: Settings, target: ServerTarget) -> ServerTarget:
    """Refuse to sign in against a server whose mode nobody settled."""
    if target.mode == MODE_AUTO:
        raise InvalidRequest(
            "SAMFSCON could not tell whether this server is a domain member.",
            code="mode_undecided",
            hint=(
                "The server answered no unauthenticated query — usually "
                "'restrict anonymous'. Choose 'domain member' or 'standalone' "
                "in the sign-in form."
            ),
            context={"host": target.host},
        )

    if target.mode == MODE_AD_MEMBER and discovery.is_address(target.kerberos_host):
        # Refused here rather than at the connect, where it arrives as
        # NT_STATUS_INVALID_PARAMETER after a ticket was obtained without
        # complaint. Kerberos issues tickets for cifs/<hostname>; for a bare
        # address there is no such principal and no amount of retrying makes
        # one.
        raise InvalidRequest(
            "Kerberos needs the server's name, and only its address is known.",
            code="kerberos_needs_a_name",
            hint=(
                "Enter the server's name instead of its address, or let SAMFSCON "
                "learn it: the name comes from an unauthenticated policy query "
                "that this server refused. Whichever name is used, the container "
                "has to be able to resolve it — add it to extra_hosts if DNS does "
                "not."
            ),
            context={"host": target.host, "realm": target.realm},
        )

    if target.mode == MODE_AD_MEMBER and not target.realm:
        raise InvalidRequest(
            "This server was chosen as a domain member, but no Kerberos realm is known.",
            code="missing_realm",
            hint="Enter the realm, or sign in as user@REALM.",
            context={"host": target.host},
        )

    if target.mode == MODE_STANDALONE and not settings.allow_standalone:
        raise InvalidRequest(
            "Standalone servers are not enabled on this installation.",
            code="standalone_disabled",
            hint=(
                "A standalone session has to hold the password in memory, and "
                "SAMFSCON_ALLOW_STANDALONE=0 refuses that trade."
            ),
            context={"host": target.host},
        )

    return target


def _pick_mode(chosen: str | None, fallback: str) -> str:
    value = (chosen or "").strip().lower()
    if value in (MODE_AD_MEMBER, MODE_STANDALONE):
        return value
    if value and value != MODE_AUTO:
        raise InvalidRequest(
            "Unknown server mode.",
            code="invalid_mode",
            context={"mode": chosen, "allowed": [MODE_AD_MEMBER, MODE_STANDALONE, MODE_AUTO]},
        )
    return fallback
