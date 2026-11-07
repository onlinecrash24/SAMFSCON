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

import ipaddress
import re
from dataclasses import dataclass, replace

from samfscon.config import MODE_AD_MEMBER, MODE_AUTO, MODE_STANDALONE
from samfscon.core.errors import InvalidRequest

# A realm, and the hosts that serve it, end up as lines in the krb5.conf this
# process writes (:mod:`samfscon.auth.krb5conf`) — rendered into `[realms]` and,
# lower-cased, into `[domain_realm]`. Until this check existed, the only thing
# between an unauthenticated request body and that file was `max_length=255` in
# the schema and `strip().upper()` here. A newline was enough to put a line of
# the caller's choosing into a process-wide configuration file, where it stayed
# until restart.
#
# So the shape is pinned here, in the value object, rather than at one of the
# three call sites that build one. A DNS label: letters, digits and inner
# hyphens, joined by single dots. That is what a realm is (RFC 1035 §2.3.1 by
# way of RFC 4120 §6.1), and nothing of that alphabet can open a line, close a
# block, start a comment or make an assignment.
_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_DNS_NAME_RE = re.compile(rf"^{_LABEL}(?:\.{_LABEL})*$")
# 253 is the length of a domain name in presentation form (RFC 1035 §2.3.4 as
# 255 octets, which is 253 characters once the length bytes are accounted for).
_MAX_NAME = 253

# NetBIOS, which is a different alphabet and a much shorter one: 15 characters,
# no dots. Checked for the same reason — it reaches smb.conf-shaped settings.
_NETBIOS_RE = re.compile(r"^[A-Za-z0-9!@#$%^()\-'{}.~_]{1,15}$")


def _checked_name(value: str, *, code: str, field: str, what: str) -> str:
    text = value.strip()
    if not text or len(text) > _MAX_NAME or not _DNS_NAME_RE.match(text):
        raise InvalidRequest(
            f"{what} is not a usable name.",
            code=code,
            hint=(
                "Letters, digits and hyphens, in parts separated by single "
                "dots — the shape of a DNS name."
            ),
            context={field: value},
        )
    return text


def _is_address(host: str) -> bool:
    """Whether *host* is a literal address rather than a name.

    Duplicated from :mod:`samfscon.srv.discovery` rather than imported: this
    module is the one everything else imports, and a dependency on the probe
    would put a network module underneath a value object.
    """
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return True


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
            checked = _checked_name(
                self.realm, code="invalid_realm", field="realm", what="The realm"
            )
            object.__setattr__(self, "realm", checked.upper())

        if self.workgroup:
            workgroup = self.workgroup.strip()
            if not _NETBIOS_RE.match(workgroup):
                raise InvalidRequest(
                    "The workgroup is not a usable NetBIOS name.",
                    code="invalid_workgroup",
                    hint="At most 15 characters, and no dots or spaces.",
                    context={"workgroup": self.workgroup},
                )
            object.__setattr__(self, "workgroup", workgroup.upper())

        if self.kdcs:
            # Each becomes its own `kdc = …` line beside the realm. A literal
            # address is a legitimate KDC and is not a DNS name, so it is
            # checked as what it is rather than forced through the same regex.
            checked_kdcs = []
            for kdc in self.kdcs:
                text = (kdc or "").strip()
                if _is_address(text):
                    checked_kdcs.append(text)
                    continue
                checked_kdcs.append(
                    _checked_name(
                        text, code="invalid_kdc_host", field="kdc", what="A key distribution centre"
                    )
                )
            object.__setattr__(self, "kdcs", tuple(checked_kdcs))

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

        Kerberos issues tickets for ``cifs/<hostname>@REALM``, and for a bare
        address no such principal exists — the bind then fails with
        NT_STATUS_INVALID_PARAMETER long after the ticket was obtained without
        complaint. This is the same trap SAMADCON hits on the LDAP side, for
        the same reason.

        Three sources, in descending order of trust:

        1. the name the server reported (or that reverse DNS supplied),
        2. its NetBIOS name in its realm — and the realm may well come from the
           administrator rather than from the probe, which is exactly the case
           on a server that answers srvsvc and refuses the LSA policy query,
        3. whatever was typed, which is only usable if it is already a name.
        """
        if self.server_fqdn:
            return self.server_fqdn
        if self.netbios_name and self.realm and _is_address(self.host):
            return f"{self.netbios_name.lower()}.{self.realm.lower()}"
        return self.host

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
