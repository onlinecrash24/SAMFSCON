"""SMB and RPC credentials for a session, in either mode.

Everything below :mod:`samfscon.srv` calls :func:`credentials_for` and does not
care whether the file server is a domain member or standalone. This is the only
module that knows the difference, and it is deliberately small enough to read
in one sitting — it is the module a security review looks at first.

Two loadparm contexts exist and must not be swapped. ``libsmb`` and the DCE/RPC
bindings are built on the **source3** code base and want a
``samba.samba3.param`` context; the ``samba.param.LoadParm`` that the ticket
request takes produces ``NT_STATUS_INVALID_PARAMETER_MIX`` here — a status that
names neither the parameter nor the mix. Samba's own tooling says as much in a
one-line comment in ``samba/netcmd/gpcommon.py``, and does what happens below.
"""

from __future__ import annotations

import logging
from typing import Any

from samfscon.config import Settings
from samfscon.core.errors import AuthenticationError, SamfsconError
from samfscon.srv.target import ServerTarget

logger = logging.getLogger(__name__)

# enum smb_signing_setting, in case the binding does not export it.
SMB_SIGNING_REQUIRED = 3
# enum smb_encryption_setting.
SMB_ENCRYPTION_DESIRED = 3
SMB_ENCRYPTION_REQUIRED = 4


def _signing_required() -> int:
    try:
        from samba import credentials
    except ImportError:  # pragma: no cover - the image always has it
        return SMB_SIGNING_REQUIRED
    return int(getattr(credentials, "SMB_SIGNING_REQUIRED", SMB_SIGNING_REQUIRED))


def _encryption(setting: str) -> int:
    try:
        from samba import credentials
    except ImportError:  # pragma: no cover
        return SMB_ENCRYPTION_REQUIRED if setting == "required" else SMB_ENCRYPTION_DESIRED
    if setting == "required":
        return int(getattr(credentials, "SMB_ENCRYPTION_REQUIRED", SMB_ENCRYPTION_REQUIRED))
    return int(getattr(credentials, "SMB_ENCRYPTION_DESIRED", SMB_ENCRYPTION_DESIRED))


def smb_loadparm(settings: Settings, target: ServerTarget) -> Any:
    """The source3 loadparm context the SMB and RPC bindings need.

    Realm and workgroup are deliberately *not* written into it. The s3 context
    is process-global, so a session's realm would reach into every other session
    signed in elsewhere — including one signed in to a different server in a
    different mode. Kerberos takes the principal from the ticket and NTLM takes
    it from the credentials object; neither needs the global.
    """
    from samba.samba3 import param as s3param

    lp = s3param.get_context()
    if settings.smb_conf.exists():
        lp.load(str(settings.smb_conf))
    else:
        lp.load_default()

    # Client-side floors, applied per connection rather than left to smb.conf so
    # that raising SAMFSCON_SAMBA_LOG_LEVEL or tightening the dialect takes
    # effect without rebuilding the container.
    _try_set(lp, "client min protocol", settings.smb_min_protocol)
    _try_set(lp, "client signing", "mandatory")
    if settings.smb_encrypt:
        _try_set(lp, "client smb encrypt", "required")
    if settings.samba_log_level:
        _try_set(lp, "log level", str(settings.samba_log_level))
    return lp


def _try_set(lp: Any, option: str, value: str) -> None:
    """Set a loadparm option, ignoring ones this Samba build does not know."""
    try:
        lp.set(option, value)
    except Exception:  # noqa: BLE001 — an unknown tuning option is not fatal
        logger.debug("s3 loadparm does not accept %r", option)


def credentials_for(session: Any, lp: Any, settings: Settings) -> Any:
    """Build SMB/RPC credentials for *session*.

    A fresh object each time rather than one cached on the session: Samba's
    credentials carry negotiated state, and handing a used one to a second
    protocol stack is not something the bindings promise to support. Building
    one is cheap; debugging a reused one is not.
    """
    from samba.credentials import Credentials

    creds = Credentials()
    creds.guess(lp)
    creds.set_smb_signing(_signing_required())
    if settings.smb_encrypt:
        creds.set_smb_encryption(_encryption("required"))

    if session.target.uses_kerberos:
        return _kerberos_credentials(creds, session, lp)
    return _ntlm_credentials(creds, session, settings)


def _kerberos_credentials(creds: Any, session: Any, lp: Any) -> Any:
    """Attach the session's ticket. The password never enters this path."""
    from samba.credentials import MUST_USE_KERBEROS

    from samfscon.auth.kerberos import CRED_SPECIFIED, ccache_url

    if session.ccache is None:
        raise SamfsconError(
            "This session carries no Kerberos ticket.",
            code="no_ticket",
            hint="The session was opened for a standalone server; sign in again.",
        )

    creds.set_kerberos_state(MUST_USE_KERBEROS)

    # The binding's signature has changed across Samba releases; try the
    # documented forms in order instead of pinning one. Two details that are
    # easy to get wrong and fail identically — with NT_STATUS_INVALID_PARAMETER
    # at connect time, long after the ticket was obtained without complaint:
    # the cache name needs its "FILE:" type prefix, and "obtained" must be
    # CRED_SPECIFIED (6, not 3 — 3 is CRED_GUESS_ENV, which leaves the cache at
    # guess priority and lets other sources win).
    name = ccache_url(session.ccache)
    errors: list[str] = []
    for attempt in (
        lambda: creds.set_named_ccache(name, CRED_SPECIFIED, lp),
        lambda: creds.set_named_ccache(name, lp),
        lambda: creds.set_named_ccache(name),
    ):
        try:
            attempt()
            return creds
        except (TypeError, AttributeError) as exc:
            # A wrong signature, or a type this Samba build does not have.
            errors.append(f"{type(exc).__name__}: {exc}")
            continue

    raise SamfsconError(
        "The Kerberos credential cache could not be attached to the connection.",
        code="ccache_unsupported",
        detail="; ".join(errors),
        hint="Samba's Credentials.set_named_ccache has an unexpected signature in this build.",
    )


def _ntlm_credentials(creds: Any, session: Any, settings: Settings) -> Any:
    """Attach the standalone session's user name and password.

    This is the point the whole standalone trade comes down to: NTLMSSP has no
    ticket to present, so the password is needed again at every connection
    setup, and it therefore lives in the session for as long as the session
    does. :class:`~samfscon.auth.session.SessionSecret` holds it; it is revealed
    here, handed straight to the bindings, and not kept.
    """
    from samba.credentials import DONT_USE_KERBEROS

    if not settings.allow_standalone:
        raise AuthenticationError(
            "Standalone servers are not enabled on this installation.",
            code="standalone_disabled",
            status_code=403,
            hint="SAMFSCON_ALLOW_STANDALONE=0 refuses sign-ins that would hold a password.",
        )
    if session.secret is None:
        raise SamfsconError(
            "This session carries no credentials for the server.",
            code="no_credentials",
            hint="The session was opened for a domain member; sign in again.",
        )

    creds.set_kerberos_state(DONT_USE_KERBEROS)
    creds.set_username(session.principal.username)
    # The workgroup is what qualifies a local account. Samba accepts the
    # server's own NetBIOS name here, which is what a standalone server calls
    # its account domain.
    domain = session.target.netbios_name or session.target.workgroup or ""
    if domain:
        creds.set_domain(domain)
    creds.set_password(session.secret.reveal())
    return creds
