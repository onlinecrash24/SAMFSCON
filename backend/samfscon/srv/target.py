"""What it takes to reach one file server.

A target travels with the session rather than living in the process-wide
settings: two administrators may be signed in to two different servers, one a
domain member and one standalone, and neither may see anything of the other's.

A target comes from one of three places, in this order of precedence:

1. a server the user typed into the sign-in form (its mode and realm discovered
   from the server itself — see :mod:`samfscon.srv.discovery`),
2. a profile from the server configuration file,
3. the container's default server, if one is configured at all.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from samfscon.config import MODE_AD_MEMBER, MODE_AUTO, MODE_STANDALONE
from samfscon.core.errors import InvalidRequest


@dataclass(frozen=True)
class ServerTarget:
    """One file server, and how to authenticate against it."""

    host: str
    # ad_member, standalone, or auto until discovery has decided.
    mode: str = MODE_AUTO
    realm: str | None = None
    workgroup: str | None = None
    # Explicit KDCs for the realm. Empty means DNS SRV discovery. Only ever
    # used in ad_member mode.
    kdcs: tuple[str, ...] = ()
    label: str | None = None
    profile_id: str | None = None
    # Resolved during discovery, kept for display and for Kerberos.
    netbios_name: str | None = None
    server_fqdn: str | None = None
    os_version: str | None = None

    def __post_init__(self) -> None:
        host = (self.host or "").strip()
        if not host:
            raise InvalidRequest(
                "No file server was given.",
                code="missing_server",
                hint="Enter a server address, or configure SAMFSCON_SERVER_HOST.",
            )
        object.__setattr__(self, "host", host)
        if self.realm:
            object.__setattr__(self, "realm", self.realm.strip().upper())
        if self.workgroup:
            object.__setattr__(self, "workgroup", self.workgroup.strip().upper())

    @property
    def uses_kerberos(self) -> bool:
        return self.mode == MODE_AD_MEMBER

    @property
    def is_standalone(self) -> bool:
        return self.mode == MODE_STANDALONE

    @property
    def decided(self) -> bool:
        """Whether discovery has settled which mode this server is in."""
        return self.mode in (MODE_AD_MEMBER, MODE_STANDALONE)

    @property
    def display_name(self) -> str:
        return self.label or self.server_fqdn or self.host

    @property
    def kerberos_host(self) -> str:
        """The name to build the SMB connection on in ad_member mode.

        The discovered FQDN wins over whatever was typed. Kerberos issues
        tickets for ``cifs/<hostname>@REALM``, and for a bare address no such
        principal exists — the bind then fails with NT_STATUS_INVALID_PARAMETER
        long after the ticket was obtained without complaint. This is the same
        trap SAMADCON hits on the LDAP side, for the same reason.
        """
        return self.server_fqdn or self.host

    @property
    def kdc_hosts(self) -> tuple[str, ...]:
        """Hosts to use as key distribution centres.

        Only meaningful for a domain member. A file server is not a KDC, so
        unlike SAMADCON the server's own address is *not* a candidate here: the
        realm's DCs are, and without an explicit list they are found over DNS.
        """
        return tuple(host for host in self.kdcs if host)

    def with_discovery(
        self,
        *,
        mode: str | None = None,
        realm: str | None = None,
        workgroup: str | None = None,
        netbios_name: str | None = None,
        server_fqdn: str | None = None,
        os_version: str | None = None,
    ) -> ServerTarget:
        """Return a copy enriched with what the server told us about itself."""
        return replace(
            self,
            mode=mode or self.mode,
            realm=(realm or self.realm or "").upper() or None,
            workgroup=(workgroup or self.workgroup or "").upper() or None,
            netbios_name=netbios_name or self.netbios_name,
            server_fqdn=server_fqdn or self.server_fqdn,
            os_version=os_version or self.os_version,
        )

    def describe(self) -> dict[str, object]:
        """Safe to hand to the front end and the audit log.

        Nothing secret passes through here — in particular not the standalone
        password, which lives on the session and never on the target.
        """
        return {
            "host": self.host,
            "mode": self.mode,
            "realm": self.realm,
            "workgroup": self.workgroup,
            "label": self.label,
            "profile_id": self.profile_id,
            "netbios_name": self.netbios_name,
            "server_fqdn": self.server_fqdn,
            "os_version": self.os_version,
            "uses_kerberos": self.uses_kerberos,
        }
