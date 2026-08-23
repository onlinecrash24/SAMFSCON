"""Kerberos ticket handling, for file servers that are domain members.

Each such session gets its own credential cache below /dev/shm. All later SMB
and RPC work runs from that cache, so every operation carries the rights of the
administrator who signed in — SAMFSCON itself never needs a privileged account.
The password is used once, to obtain the ticket, and is never written anywhere.

A **standalone** server has no KDC and never reaches this module; it
authenticates with NTLMSSP from :mod:`samfscon.auth.credentials`, which is the
one place the two modes are told apart.

One trap is worth naming up front, because it costs a whole debugging session:
the KDC is a **domain controller**, not the file server. The file server only
tells us which realm it belongs to. Pointing the realm's ``kdc =`` at the file
server produces a ticket request that times out against a host running no KDC.

Two ways to acquire a ticket are implemented:

1. ``Credentials.get_named_ccache()`` from the Samba bindings — preferred,
   because it is the same code path samba-tool uses.
2. ``kinit`` as a subprocess with the password on stdin — fallback for Samba
   builds whose binding signature differs.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from samfscon.config import Settings
from samfscon.core.errors import AuthenticationError, SamfsconError, translate
from samfscon.srv.target import ServerTarget

logger = logging.getLogger(__name__)

# samba's enum credentials_obtained. Spelled out because the numeric values are
# easy to mix up: CRED_GUESS_ENV is 3, and passing that instead leaves the
# credential cache at guess priority — the bind then fails with a parameter
# error rather than saying what is wrong. Read from the bindings when they are
# available so a future renumbering cannot silently break us.
try:  # pragma: no cover - depends on python3-samba being installed
    from samba.credentials import CRED_SPECIFIED
except ImportError:  # pragma: no cover
    CRED_SPECIFIED = 6

# Anything else is not a valid sAMAccountName / UPN local part and is rejected
# before it reaches the KDC.
_PRINCIPAL_RE = re.compile(r"^[A-Za-z0-9._\-$ ]{1,256}$")
_KLIST_EXPIRY_RE = re.compile(
    r"^\s*(\d{2}/\d{2}/\d{2,4}|\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})\s+"
    r"(\d{2}/\d{2}/\d{2,4}|\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})\s+krbtgt/",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Principal:
    """Who is signed in.

    ``realm`` carries the Kerberos realm for a domain member and the server's
    NetBIOS domain for a standalone server. Both are the thing that qualifies
    the user name, which is what every caller wants from it — and keeping one
    field rather than two is what lets the rest of the application stop caring
    which mode it is in.
    """

    username: str
    realm: str

    @property
    def full(self) -> str:
        return f"{self.username}@{self.realm}" if self.realm else self.username


def parse_principal(raw: str, default_realm: str) -> Principal:
    """Split user input into user and realm.

    Accepts ``user``, ``user@realm`` and ``DOMAIN\\user``.
    """
    value = raw.strip()
    if not value:
        raise AuthenticationError("User name is missing.", code="missing_username")

    if "\\" in value:
        _, _, value = value.partition("\\")

    if "@" in value:
        username, _, realm = value.partition("@")
        realm = realm.upper()
    else:
        username, realm = value, default_realm.upper()

    if not _PRINCIPAL_RE.match(username):
        raise AuthenticationError(
            "The user name contains invalid characters.", code="invalid_username"
        )
    if not username:
        raise AuthenticationError("User name is missing.", code="missing_username")

    return Principal(username=username, realm=realm)


def ccache_path_for(settings: Settings, session_id: str) -> Path:
    return settings.ccache_dir / f"tkt-{session_id}"


def ccache_url(ccache: Path | str) -> str:
    """Credential cache name in the form the Kerberos library expects.

    The type prefix is not decoration: a bare path is rejected, and the bind
    then fails with NT_STATUS_INVALID_PARAMETER long after the ticket was
    obtained successfully. samba-tool's --use-krb5-ccache does the same
    prefixing.
    """
    text = str(ccache)
    # Already carries a type (FILE:, DIR:, KEYRING:, KCM:, ...). A Windows
    # drive letter is not one, hence the second condition.
    if ":" in text and text[1:2] != ":":
        return text
    return f"FILE:{text}"


def kinit_loadparm(settings: Settings, target: ServerTarget) -> Any:
    """The LoadParm the *ticket request* needs.

    Not the one the SMB connection uses. That one is a **source3** context from
    ``samba.samba3.param`` (see :mod:`samfscon.auth.credentials`); handing this
    one to libsmb produces NT_STATUS_INVALID_PARAMETER_MIX, a status naming
    neither the parameter nor the mix. The two live apart on purpose.
    """
    from samba.param import LoadParm

    lp = LoadParm()
    if settings.smb_conf.exists():
        lp.load(str(settings.smb_conf))
    else:
        lp.load_default()

    if target.realm:
        lp.set("realm", target.realm)
    if target.workgroup or target.netbios_name:
        lp.set("workgroup", target.workgroup or target.netbios_name or "")

    # Do not let Samba write its own krb5.conf.
    #
    # With the default (`yes`) the credentials layer generates a private one and
    # locates the KDC for it itself, over DNS SRV — which silently bypasses the
    # file SAMFSCON writes with the KDC addresses already known to answer. A
    # container reached through `extra_hosts` has A-record resolution and no
    # SRV, so the ticket request then fails with NT_STATUS_NO_LOGON_SERVERS:
    # Samba's way of saying it found no domain controller.
    _try_set(lp, "create krb5 conf", "no")

    if settings.samba_log_level:
        lp.set("log level", str(settings.samba_log_level))
    return lp


def _try_set(lp: Any, option: str, value: str) -> None:
    """Set a loadparm option, ignoring ones this Samba build does not know."""
    try:
        lp.set(option, value)
    except Exception:  # noqa: BLE001 — an unknown tuning option is not fatal
        logger.debug("loadparm does not accept %r", option)


def _acquire_via_bindings(
    principal: Principal,
    password: str,
    ccache: Path,
    settings: Settings,
    target: ServerTarget,
) -> bool:
    """Obtain a TGT through the Samba bindings. Returns False if unsupported."""
    try:
        from samba.credentials import MUST_USE_KERBEROS, Credentials
    except ImportError:  # pragma: no cover - only on hosts without python3-samba
        return False

    lp = kinit_loadparm(settings, target)
    creds = Credentials()
    creds.guess(lp)
    creds.set_kerberos_state(MUST_USE_KERBEROS)
    creds.set_username(principal.username)
    creds.set_realm(principal.realm)
    creds.set_password(password)

    try:
        creds.get_named_ccache(lp, ccache_url(ccache))
    except TypeError:
        # Older/newer binding signature — let the caller fall back to kinit
        # rather than guessing at argument orders.
        logger.info("Credentials.get_named_ccache signature mismatch, falling back to kinit")
        return False
    return True


def _krb5_env(ccache: Path | None = None) -> dict[str, str]:
    """The environment every Kerberos command runs in.

    TZ is pinned rather than assumed. klist prints local time, and
    :func:`ticket_expiry` reads what it prints as UTC — an assumption that held
    only for as long as nobody set a timezone on the container. Set here, the
    condition the reader below depends on is part of the call instead of a
    property of the deployment.

    Getting it wrong is quiet and late: with the offset running forwards the
    ticket is thought to last longer than it does, so the session outlives it
    and calls fail partway through somebody's work rather than returning them
    to the sign-in screen.
    """
    from samfscon.auth.krb5conf import get_krb5_configuration

    env = dict(os.environ)
    env["TZ"] = "UTC"
    if ccache is not None:
        env["KRB5CCNAME"] = ccache_url(ccache)
    # The generated configuration knows every realm SAMFSCON has been pointed
    # at, including the KDC addresses that were given explicitly.
    env.update(get_krb5_configuration().environment())
    return env


def _acquire_via_kinit(principal: Principal, password: str, ccache: Path) -> None:
    """Obtain a TGT by running kinit with the password on stdin.

    The password goes through a pipe, never through argv, so it does not show
    up in the process list.
    """
    env = _krb5_env(ccache)

    try:
        result = subprocess.run(
            ["kinit", "-f", "-r", "7d", principal.full],
            input=password.encode("utf-8") + b"\n",
            capture_output=True,
            env=env,
            timeout=30,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SamfsconError(
            "Neither the Samba bindings nor kinit could obtain a Kerberos ticket.",
            code="kerberos_unavailable",
            hint="The container image is incomplete: krb5-user is missing.",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise translate(
            TimeoutError("kinit did not answer; the KDC is probably unreachable")
        ) from exc

    if result.returncode != 0:
        message = (result.stderr or result.stdout).decode("utf-8", "replace").strip()
        raise translate(RuntimeError(message or "kinit failed"))


def acquire_ticket(
    principal: Principal,
    password: str,
    ccache: Path,
    settings: Settings,
    target: ServerTarget,
) -> None:
    """Fetch a TGT for *principal* in *target*'s realm into *ccache*.

    Raises a :class:`~samfscon.core.errors.SamfsconError` subclass on failure;
    the caller must not distinguish between the two acquisition paths.
    """
    from samfscon.auth.krb5conf import get_krb5_configuration

    if not password:
        raise AuthenticationError("Password is missing.", code="missing_password")
    if not target.realm:
        raise AuthenticationError(
            "The file server named no Kerberos realm.",
            code="no_realm",
            hint=(
                "A standalone server has none. If this server is a domain "
                "member, discovery could not read its realm — name it explicitly."
            ),
        )

    # Register the realm before asking for a ticket. Where KDCs were configured
    # they are named explicitly; otherwise Kerberos resolves the realm's SRV
    # records, which is the normal case for a container whose resolver serves
    # the domain.
    get_krb5_configuration().ensure_realm(target.realm, target.kdc_hosts)

    ccache.parent.mkdir(parents=True, exist_ok=True)
    # Create the file with tight permissions before anything writes secrets to
    # it — otherwise there is a window where the umask decides.
    fd = os.open(ccache, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    os.close(fd)

    try:
        if not _acquire_via_bindings(principal, password, ccache, settings, target):
            _acquire_via_kinit(principal, password, ccache)
    except Exception as exc:
        destroy_ticket(ccache)
        raise translate(exc) from exc

    # A cache file exists at this point even when nothing was written to it, and
    # a bind with an empty cache fails later as an opaque handshake error. Ask
    # klist whether a usable ticket is actually in there.
    if has_ticket(ccache) is False:
        destroy_ticket(ccache)
        raise AuthenticationError(
            "No Kerberos ticket was issued.",
            code="no_ticket",
            hint=(
                "The credential cache stayed empty. Check the realm spelling, the "
                "clock difference to the KDC, and that the account exists in this realm."
            ),
        )

    if not ccache.exists() or ccache.stat().st_size == 0:
        destroy_ticket(ccache)
        raise AuthenticationError(
            "No Kerberos ticket was issued.",
            code="no_ticket",
            hint="Check the realm spelling and that the KDC is reachable.",
        )


def has_ticket(ccache: Path) -> bool | None:
    """Whether *ccache* holds a valid ticket.

    ``klist -s`` exits 0 only when there is one, which makes it a cheap and
    reliable check. Returns ``None`` when klist is unavailable — then the caller
    must not treat the outcome as a failure.
    """
    env = _krb5_env()

    try:
        result = subprocess.run(
            ["klist", "-s", "-c", ccache_url(ccache)],
            capture_output=True,
            env=env,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.returncode == 0


def destroy_ticket(ccache: Path) -> None:
    """Remove a credential cache. Never raises."""
    try:
        ccache.unlink(missing_ok=True)
    except OSError as exc:  # pragma: no cover - tmpfs failure
        logger.warning("could not remove ccache %s: %s", ccache, exc)


def ticket_expiry(ccache: Path) -> datetime | None:
    """Read the TGT's expiry time via klist.

    Returns ``None`` when it cannot be determined; the caller then falls back to
    its configured session lifetime.
    """
    env = _krb5_env()

    try:
        result = subprocess.run(
            ["klist", "-c", ccache_url(ccache)],
            capture_output=True,
            env=env,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    match = _KLIST_EXPIRY_RE.search(result.stdout.decode("utf-8", "replace"))
    if match is None:
        return None

    date_part, time_part = match.group(3), match.group(4)
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            naive = datetime.strptime(f"{date_part} {time_part}", fmt)
        except ValueError:
            continue
        # klist printed local time, and _krb5_env made local time UTC.
        return naive.replace(tzinfo=UTC)
    return None


def default_expiry(hours: int = 10) -> datetime:
    return datetime.now(UTC) + timedelta(hours=hours)
