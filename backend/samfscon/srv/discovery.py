"""Asking a file server what it is, before anyone signs in.

SAMADCON reads a domain controller's rootDSE anonymously to learn the realm and
the DC's own name. This is the same idea against a file server, and it exists
for the same reason: an administrator should be able to type an **IP address**
into the sign-in form. Kerberos issues tickets for ``cifs/<hostname>@REALM``,
and for a bare address no such principal exists — so the name and the realm
have to come from the server itself.

The authoritative source is the LSA policy, which every SMB server exposes:

* ``LSA_POLICY_INFO_ACCOUNT_DOMAIN`` — the domain the server's *own* accounts
  live in. On a standalone server that is the server itself.
* ``LSA_POLICY_INFO_DNS`` — the primary domain, with its DNS name. On a domain
  member that is the AD domain, and its DNS name is the Kerberos realm.

Comparing the two is what tells the modes apart, and it is how Samba's own
tooling answers the same question. Everything else here is decoration: a
version string for the interface, a comment, the negotiated dialect.

**Every step is best-effort.** A server with ``restrict anonymous = 2`` answers
none of it, and that is not an error — it means the sign-in form has to ask
which mode to use instead of knowing. A probe that guesses would be worse than
one that admits it does not know: guessing standalone against a domain member
means offering to hold a password that was never needed.
"""

from __future__ import annotations

import ipaddress
import logging
from dataclasses import dataclass, field
from typing import Any

from samfscon.config import MODE_AD_MEMBER, MODE_AUTO, MODE_STANDALONE, Settings
from samfscon.core.errors import InvalidRequest, UpstreamUnavailable, translate

logger = logging.getLogger(__name__)

# LSA policy information levels (MS-LSAD 2.2.4.1). Mirrored as literals so this
# module can be reasoned about without the bindings open alongside.
LSA_POLICY_INFO_ACCOUNT_DOMAIN = 5
LSA_POLICY_INFO_DNS = 12

# srvsvc server type flags (MS-SRVS 2.2.2.7), only the ones that say something
# about the server's role.
SV_TYPE_DOMAIN_CTRL = 0x00000008
SV_TYPE_DOMAIN_BAKCTRL = 0x00000010
SV_TYPE_SERVER_NT = 0x00008000


@dataclass
class ServerProbe:
    """What could be learned about a server without credentials."""

    host: str
    reachable: bool = False
    # ad_member, standalone, or auto when it could not be decided.
    mode: str = MODE_AUTO
    realm: str | None = None
    workgroup: str | None = None
    netbios_name: str | None = None
    server_fqdn: str | None = None
    os_version: str | None = None
    comment: str | None = None
    is_domain_controller: bool = False
    # Why the mode is what it is, and what could not be read. Shown in the
    # sign-in form when the mode stayed undecided, because "pick one" without a
    # reason is the kind of prompt people answer wrongly.
    notes: list[str] = field(default_factory=list)

    @property
    def decided(self) -> bool:
        return self.mode in (MODE_AD_MEMBER, MODE_STANDALONE)

    def describe(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "reachable": self.reachable,
            "mode": self.mode,
            "decided": self.decided,
            "realm": self.realm,
            "workgroup": self.workgroup,
            "netbios_name": self.netbios_name,
            "server_fqdn": self.server_fqdn,
            "os_version": self.os_version,
            "comment": self.comment,
            "is_domain_controller": self.is_domain_controller,
            "notes": list(self.notes),
        }


def normalise_host(value: str) -> str:
    """Clean up what somebody typed into the address field.

    People paste URLs, UNC paths and trailing share names, because that is what
    they have in front of them. Stripping the decoration here means the error
    for a genuinely wrong address says so, instead of reporting a host name with
    two backslashes in it that nobody would have typed on purpose.
    """
    text = (value or "").strip()
    if not text:
        raise InvalidRequest("No server address was given.", code="missing_server")

    for prefix in ("smb://", "cifs://", "//", "\\\\"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break

    # Anything after the host is a share or a path, and this field is neither.
    for separator in ("/", "\\"):
        head, sep, _ = text.partition(separator)
        if sep:
            text = head

    # A port would be a second way to say 445, which is the only port these
    # protocols use. Dropped rather than honoured, so nobody believes SAMFSCON
    # will follow it. IPv6 literals keep their brackets and their colons.
    if text.count(":") == 1 and not text.startswith("["):
        text = text.split(":", 1)[0]

    text = text.strip().rstrip(".")
    if not text:
        raise InvalidRequest(
            "The server address contains nothing usable.",
            code="invalid_server",
            context={"value": value},
        )
    return text


def is_address(host: str) -> bool:
    """Whether *host* is a literal address rather than a name."""
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return True


def probe(host: str, settings: Settings) -> ServerProbe:
    """Ask *host* what it is. Runs in a worker thread; never raises for a
    server that simply declines to answer.

    Only an unreachable server is an error — that one the administrator has to
    know about before typing a password.
    """
    result = ServerProbe(host=host.strip())
    if not result.host:
        raise UpstreamUnavailable("No server address was given.", code="missing_server")

    lp = _anonymous_loadparm(settings)
    creds = _anonymous_credentials(lp)

    _probe_lsa(result, lp, creds)
    _probe_srvsvc(result, lp, creds)
    _decide_mode(result)

    if not result.reachable:
        raise UpstreamUnavailable(
            "The file server could not be reached.",
            code="server_unreachable",
            hint=(
                "Check that the address is right, that port 445 is open, and "
                "that the server speaks SMB3 — SAMFSCON does not negotiate SMB1."
            ),
            detail="; ".join(result.notes) or None,
            context={"host": result.host},
        )
    return result


# ---------------------------------------------------------------------------
# The probes
# ---------------------------------------------------------------------------


def _anonymous_loadparm(settings: Settings) -> Any:
    from samba.samba3 import param as s3param

    lp = s3param.get_context()
    if settings.smb_conf.exists():
        lp.load(str(settings.smb_conf))
    else:
        lp.load_default()
    try:
        lp.set("client min protocol", settings.smb_min_protocol)
    except Exception:  # noqa: BLE001
        logger.debug("s3 loadparm does not accept 'client min protocol'")
    return lp


def _anonymous_credentials(lp: Any) -> Any:
    """Credentials for a session that presents no account at all.

    ``set_anonymous()`` is the whole point: guessing from the environment would
    pick up whatever the container happens to have, and a probe that
    accidentally authenticates tells us about that account rather than about
    what an unauthenticated caller can see.
    """
    from samba.credentials import Credentials

    creds = Credentials()
    creds.guess(lp)
    creds.set_anonymous()
    return creds


def _probe_lsa(result: ServerProbe, lp: Any, creds: Any) -> None:
    """Read the account domain and the primary domain from the LSA policy."""
    try:
        from samba.dcerpc import lsa
    except ImportError:  # pragma: no cover - only on hosts without the bindings
        result.notes.append("the Samba python bindings are not available")
        return

    try:
        pipe = lsa.lsarpc(_binding(result.host), lp, creds)
    except Exception as exc:  # noqa: BLE001 — an unreachable server is the caller's problem
        error = translate(exc)
        result.notes.append(f"lsarpc: {error.detail or error.message}")
        logger.info("lsarpc probe of %s failed: %s", result.host, error.message)
        return

    # Reaching the pipe at all means SMB negotiated and the server answered.
    result.reachable = True

    handle = _open_policy(pipe)
    if handle is None:
        result.notes.append("the server does not allow an unauthenticated policy query")
        return

    account = _query_policy(pipe, handle, LSA_POLICY_INFO_ACCOUNT_DOMAIN)
    if account is not None:
        # The account domain of a standalone server is the server itself, which
        # is exactly what makes the comparison below work.
        result.netbios_name = _text(getattr(getattr(account, "name", None), "string", None))

    dns = _query_policy(pipe, handle, LSA_POLICY_INFO_DNS)
    if dns is not None:
        result.workgroup = _text(getattr(getattr(dns, "name", None), "string", None))
        realm = _text(getattr(getattr(dns, "dns_domain", None), "string", None))
        result.realm = realm.upper() if realm else None
    elif account is not None:
        # Without the DNS level there is no realm to be had, but the account
        # domain still names the workgroup.
        result.workgroup = result.netbios_name
        result.notes.append("the server did not report a DNS domain")


def _open_policy(pipe: Any) -> Any:
    """Open a policy handle, whichever of the two calls this build offers.

    ``OpenPolicy2`` is the current one; older servers and bindings expose
    ``OpenPolicy``. The attribute and access-mask arguments differ in shape
    between Samba releases, which is why this is a loop over forms rather than
    one pinned call — the same treatment ``set_named_ccache`` gets in
    :mod:`samfscon.auth.credentials`, and for the same reason.
    """
    from samba.dcerpc import lsa

    attr = lsa.ObjectAttribute()
    attr.sec_qos = lsa.QosInfo()
    # LSA_POLICY_VIEW_LOCAL_INFORMATION — the least that answers our two
    # questions. Asking for more is how an anonymous query gets refused.
    access = 0x00000001

    for attempt in (
        lambda: pipe.OpenPolicy2(None, attr, access),
        lambda: pipe.OpenPolicy(None, attr, access),
    ):
        try:
            return attempt()
        except Exception:  # noqa: BLE001 — try the next form, then give up
            continue
    return None


def _query_policy(pipe: Any, handle: Any, level: int) -> Any:
    for attempt in (
        lambda: pipe.QueryInfoPolicy2(handle, level),
        lambda: pipe.QueryInfoPolicy(handle, level),
    ):
        try:
            return attempt()
        except Exception:  # noqa: BLE001
            continue
    return None


def _probe_srvsvc(result: ServerProbe, lp: Any, creds: Any) -> None:
    """Read the server's own name, version and comment.

    Decoration rather than decision — but the FQDN it reports is what a
    Kerberos ticket has to be asked for, so it earns its round trip.
    """
    try:
        from samba.dcerpc import srvsvc
    except ImportError:  # pragma: no cover
        return

    try:
        pipe = srvsvc.srvsvc(_binding(result.host), lp, creds)
        info = pipe.NetSrvGetInfo(None, 101)
    except Exception as exc:  # noqa: BLE001 — anonymous srvsvc is often refused
        error = translate(exc)
        result.notes.append(f"srvsvc: {error.detail or error.message}")
        return

    result.reachable = True
    name = _text(getattr(info, "server_name", None))
    comment = _text(getattr(info, "comment", None))
    major = getattr(info, "version_major", None)
    minor = getattr(info, "version_minor", None)

    if name:
        result.netbios_name = result.netbios_name or name.upper()
        # srvsvc reports the NetBIOS name. The FQDN is that name in the DNS
        # domain, which is only knowable once the realm is: on a standalone
        # server there is no domain to append.
        if result.realm and "." not in name:
            result.server_fqdn = f"{name.lower()}.{result.realm.lower()}"
        elif "." in name:
            result.server_fqdn = name.lower()
    if comment:
        result.comment = comment
    if major is not None and minor is not None:
        result.os_version = f"{major}.{minor}"

    server_type = int(getattr(info, "server_type", 0) or 0)
    result.is_domain_controller = bool(server_type & (SV_TYPE_DOMAIN_CTRL | SV_TYPE_DOMAIN_BAKCTRL))


def _decide_mode(result: ServerProbe) -> None:
    """Tell the two modes apart, or admit that it could not be done.

    The test is whether the server's own account domain is the primary domain.
    A standalone server is its own account domain; a member's accounts live in
    the AD domain it joined, and the two names differ.
    """
    if result.realm and result.workgroup and result.netbios_name:
        if result.workgroup.upper() != result.netbios_name.upper():
            result.mode = MODE_AD_MEMBER
            result.notes.append(
                f"the server's accounts live in {result.workgroup}, not in itself — "
                "so it is a domain member"
            )
            return
        result.mode = MODE_STANDALONE
        result.notes.append(
            "the server is its own account domain — so it is standalone"
        )
        return

    if result.workgroup and result.netbios_name:
        # No DNS domain, so no realm, so Kerberos is not on the table even if
        # the names differ. An NT4-style domain member lands here, and NTLM is
        # genuinely the only option for it.
        result.mode = MODE_STANDALONE
        result.notes.append(
            "the server named no Kerberos realm, so it is managed with user name "
            "and password"
        )
        return

    result.mode = MODE_AUTO
    result.notes.append(
        "the server answered no unauthenticated query, so its mode has to be chosen by hand"
    )


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _binding(host: str) -> str:
    """An RPC binding string for the named pipe transport over SMB.

    ``ncacn_np`` is DCE/RPC over an SMB named pipe — the transport every one of
    these interfaces is published on, and the one Windows itself uses. ``smb2``
    and ``sign`` are asked for explicitly rather than negotiated down: this
    console manages shares and permissions, and doing that over an unsigned SMB1
    connection is not a trade worth offering.
    """
    return f"ncacn_np:{host}[smb2,sign]"


def _text(value: Any) -> str | None:
    """Samba's string types come back as str, bytes or None, depending."""
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    text = str(value).strip()
    return text or None
