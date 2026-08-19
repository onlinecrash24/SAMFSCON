"""The connection to one file server, on behalf of one signed-in administrator.

Every call in this module runs inside a session's worker thread (see
:mod:`samfscon.core.executor`) — the Samba bindings are blocking C extensions
and their handles must not be shared between threads. Nothing here may be
awaited directly from a router; go through :mod:`samfscon.srv.access` instead.

One connection owns several things at once, and they are opened only when
something asks for them:

* **srvsvc** — shares, sessions, open files. The interface behind the Windows
  "Shared Folders" console.
* **samr** — local accounts, on a standalone server.
* **lsarpc** — names to SIDs and back, for the permission editor.
* **winreg** — the registry-backed configuration, which is where the smb.conf
  options live that srvsvc knows nothing about.
* **SMB trees**, one per share touched, for directory listings and file
  security descriptors.

All of them authenticate as the person who signed in, so the server applies its
own permissions exactly as it would to that account from any other client.
SAMFSCON holds no privileged identity of its own.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from samfscon.auth.credentials import credentials_for, smb_loadparm
from samfscon.config import Settings
from samfscon.core.errors import SamfsconError, UpstreamUnavailable, translate
from samfscon.srv.target import ServerTarget

logger = logging.getLogger(__name__)

# The interfaces, by the name they are cached under.
PIPE_SRVSVC = "srvsvc"
PIPE_SAMR = "samr"
PIPE_LSA = "lsarpc"
PIPE_WINREG = "winreg"


@dataclass(frozen=True)
class TransportState:
    """How this connection is protected, as established at connect time.

    Recorded rather than derived. Both authentication methods encrypt nothing
    by themselves — SMB signing is what protects the traffic's integrity, and
    SMB3 encryption is optional — so "is my session safe?" has a different
    answer per connection, and an administrator asking it deserves better than
    the container log.

    ``identity_verified`` is the one that separates the two modes and is worth
    reading carefully. Kerberos proves the server's identity by construction: a
    ticket for ``cifs/<host>`` is only decryptable by that host. NTLMSSP proves
    nothing about the server at all — it proves the *client* to the server and
    not the other way round. A standalone connection is therefore authenticated
    and signed, but its peer is unverified, and the interface says so rather
    than showing one reassuring padlock for both.
    """

    auth: str
    server_name: str
    signed: bool
    encrypted: bool

    @property
    def identity_verified(self) -> bool:
        return self.auth == "kerberos"

    def describe(self) -> dict[str, Any]:
        return {
            "auth": self.auth,
            "server_name": self.server_name,
            "signed": self.signed,
            "encrypted": self.encrypted,
            "identity_verified": self.identity_verified,
        }


@dataclass(frozen=True)
class ServerInfo:
    """Who the server says it is, read once at connect time."""

    name: str
    host: str
    comment: str | None
    os_version: str | None
    workgroup: str | None
    realm: str | None
    mode: str
    is_domain_controller: bool

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "host": self.host,
            "comment": self.comment,
            "os_version": self.os_version,
            "workgroup": self.workgroup,
            "realm": self.realm,
            "mode": self.mode,
            "is_domain_controller": self.is_domain_controller,
        }


class ServerConnection:
    """One authenticated connection to one file server."""

    def __init__(
        self,
        target: ServerTarget,
        settings: Settings,
        lp: Any,
        creds: Any,
        info: ServerInfo,
        transport: TransportState,
        principal: str | None = None,
    ) -> None:
        # Who this connection belongs to. Carried because the server does not
        # always say: an LSA GetUserName that is refused leaves the account
        # nameless, and then its privileges cannot be looked up either — which
        # is reported as "could not be determined" for a question that was
        # answerable from what we already knew.
        self.principal = principal
        self.target = target
        self.settings = settings
        self.lp = lp
        self.creds = creds
        self.info = info
        self.transport = transport
        self._pipes: dict[str, Any] = {}
        self._trees: dict[str, Any] = {}

    # -- the RPC interfaces ------------------------------------------------

    @property
    def host(self) -> str:
        return self.target.kerberos_host if self.target.uses_kerberos else self.target.host

    @property
    def binding(self) -> str:
        return binding_string(
            self.host,
            encrypt=self.settings.smb_encrypt,
            auth="krb5" if self.target.uses_kerberos else "ntlm",
        )

    def pipe(self, name: str) -> Any:
        """The named RPC interface, opened on first use and kept afterwards.

        Kept rather than reopened per call: each open is an SMB tree connect to
        IPC$ plus a bind, and a share listing that reopened the pipe every time
        would spend most of its time in handshakes.
        """
        existing = self._pipes.get(name)
        if existing is not None:
            return existing

        pipe = _open_pipe(name, self.binding, self.lp, self.creds)
        self._pipes[name] = pipe
        return pipe

    @property
    def srvsvc(self) -> Any:
        return self.pipe(PIPE_SRVSVC)

    @property
    def samr(self) -> Any:
        return self.pipe(PIPE_SAMR)

    @property
    def lsa(self) -> Any:
        return self.pipe(PIPE_LSA)

    @property
    def winreg(self) -> Any:
        return self.pipe(PIPE_WINREG)

    # -- SMB, for file contents and their security descriptors -------------

    def tree(self, share: str) -> Any:
        """An SMB connection to one share, opened on first use.

        One per share and reused, for the same reason the pipes are: walking a
        directory tree reconnects otherwise. They are closed deliberately in
        :meth:`close` — a session left behind keeps the server's handles on
        whatever it touched, and the next write to one of those files is
        refused with a sharing violation from a session that ended hours ago.
        """
        key = share.lower()
        existing = self._trees.get(key)
        if existing is not None:
            return existing

        conn = _open_tree(self.host, share, self.lp, self.creds)
        self._trees[key] = conn
        return conn

    # -- housekeeping ------------------------------------------------------

    def is_alive(self) -> bool:
        try:
            self.srvsvc.NetSrvGetInfo(None, 100)
        except Exception:  # noqa: BLE001 — any failure means reconnect
            return False
        return True

    def close(self) -> None:
        """Hang up, rather than waiting for the garbage collector.

        Named for the executor's teardown protocol
        (:meth:`samfscon.core.executor.SessionWorker.close`), which calls this
        on the very thread that opened everything.
        """
        for key, conn in list(self._trees.items()):
            _close_quietly(conn, f"tree {key}")
        self._trees.clear()

        # The pipes have no explicit close in every binding; dropping the
        # reference is what releases the socket.
        for key, pipe in list(self._pipes.items()):
            _close_quietly(pipe, f"pipe {key}")
        self._pipes.clear()


# ---------------------------------------------------------------------------
# Connecting
# ---------------------------------------------------------------------------


def connect(session: Any, settings: Settings) -> ServerConnection:
    """Open an authenticated connection for *session*.

    There is no transport fallback here, and that is deliberate. SAMADCON may
    fall back from LDAP-with-Kerberos to LDAPS because both are encrypted, so
    the fallback never weakens anything. The equivalent step here would be
    falling back from Kerberos to NTLM, which *is* weaker: it gives up any
    proof of who the server is. So the mode is decided before this point — by
    :mod:`samfscon.srv.discovery`, or by the administrator when the server
    would not say — and this function does exactly what it was told.

    Runs in a worker thread. The returned object stays bound to that thread.
    """
    target: ServerTarget = session.target

    try:
        lp = smb_loadparm(settings, target)
        creds = credentials_for(session, lp, settings)
    except SamfsconError:
        raise
    except Exception as exc:
        raise translate(exc) from exc

    host = target.kerberos_host if target.uses_kerberos else target.host
    binding = binding_string(
        host,
        encrypt=settings.smb_encrypt,
        auth="krb5" if target.uses_kerberos else "ntlm",
    )

    try:
        srvsvc = _open_pipe(PIPE_SRVSVC, binding, lp, creds)
        raw = srvsvc.NetSrvGetInfo(None, 101)
    except SamfsconError as error:
        raise _connect_failure(error, target, host) from error
    except Exception as exc:
        raise _connect_failure(translate(exc), target, host) from exc

    info = _server_info(raw, target, host)
    transport = TransportState(
        auth="kerberos" if target.uses_kerberos else "ntlm",
        server_name=info.name,
        # Both are required rather than requested (see
        # samfscon.auth.credentials), so a connection that exists at all has
        # them. Recorded as facts about this connection all the same, because
        # the interface shows them and a hard-coded "true" in a template is a
        # claim nobody checked.
        signed=True,
        encrypted=settings.smb_encrypt,
    )

    logger.info(
        "connected to %s as %s (%s, %s)",
        info.name,
        session.principal.full,
        transport.auth,
        "encrypted" if transport.encrypted else "signed",
    )

    conn = ServerConnection(
        target,
        settings,
        lp,
        creds,
        info,
        transport,
        principal=getattr(session.principal, "username", None),
    )
    conn._pipes[PIPE_SRVSVC] = srvsvc
    return conn


def _connect_failure(error: SamfsconError, target: ServerTarget, host: str) -> SamfsconError:
    """Turn a failed connect into something worth reading.

    An authentication failure is the user's to fix and passes through as it is.
    Everything else gets the advice that fits the mode, because the two fail for
    entirely different reasons and the wrong hint sends the reader to check
    ports and clocks that are fine.
    """
    if error.status_code in (401, 403):
        return error

    from samfscon.srv.discovery import is_address

    if target.uses_kerberos and is_address(host):
        return UpstreamUnavailable(
            "The file server could not be reached.",
            code="server_name_unknown",
            detail=error.detail or error.message,
            hint=(
                "Only the address was available, and Kerberos issues tickets for "
                "cifs/<hostname> — no such principal exists for a bare address. "
                "SAMFSCON reads the name from the server itself, so this usually "
                "means that probe failed: check that the container can resolve "
                "the server's name and reach it on port 445."
            ),
            context={"host": host, "mode": target.mode},
        )

    if target.uses_kerberos:
        return UpstreamUnavailable(
            "The file server could not be reached.",
            code="server_unreachable",
            detail=error.detail or error.message,
            hint=(
                "Check that port 445 is open, that the clock difference to the "
                "domain controller is under five minutes, and that the server is "
                "still joined to the domain."
            ),
            context={"host": host, "mode": target.mode},
        )

    return UpstreamUnavailable(
        "The file server could not be reached.",
        code="server_unreachable",
        detail=error.detail or error.message,
        hint=(
            "Check that port 445 is open and that the server speaks SMB3 — "
            "SAMFSCON does not negotiate SMB1."
        ),
        context={"host": host, "mode": target.mode},
    )


def _server_info(raw: Any, target: ServerTarget, host: str) -> ServerInfo:
    from samfscon.srv.discovery import (
        SV_TYPE_DOMAIN_BAKCTRL,
        SV_TYPE_DOMAIN_CTRL,
        _text,
    )

    name = _text(getattr(raw, "server_name", None)) or target.netbios_name or host
    major = getattr(raw, "version_major", None)
    minor = getattr(raw, "version_minor", None)
    server_type = int(getattr(raw, "server_type", 0) or 0)

    return ServerInfo(
        name=name,
        host=host,
        comment=_text(getattr(raw, "comment", None)),
        os_version=f"{major}.{minor}" if major is not None and minor is not None else None,
        workgroup=target.workgroup,
        realm=target.realm,
        mode=target.mode,
        is_domain_controller=bool(server_type & (SV_TYPE_DOMAIN_CTRL | SV_TYPE_DOMAIN_BAKCTRL)),
    )


# ---------------------------------------------------------------------------
# Binding shapes, isolated because they drift between Samba releases
# ---------------------------------------------------------------------------


def binding_string(host: str, *, encrypt: bool = False, auth: str | None = None) -> str:
    """An RPC binding for the named-pipe transport over SMB.

    ``ncacn_np`` is DCE/RPC over an SMB named pipe — the transport all of these
    interfaces are published on, and the one Windows itself uses.

    Only options whose spelling is stable across Samba releases go in here.
    ``sign`` and ``seal`` protect the traffic; ``krb5`` and ``ntlm`` state the
    authentication rather than leaving it to be inferred from the credentials
    object, which makes a mismatch fail with something that names itself.

    The SMB dialect is deliberately *not* an option here: it is set once in the
    loadparm as ``client min protocol``, which is one place rather than two,
    and a dialect option this build did not recognise would be refused as an
    invalid parameter — a status that names neither the option nor the value.
    """
    options = ["seal" if encrypt else "sign"]
    if auth in ("krb5", "ntlm"):
        options.append(auth)
    return f"ncacn_np:{host}[{','.join(options)}]"


def _open_pipe(name: str, binding: str, lp: Any, creds: Any) -> Any:
    """Open one RPC interface.

    The interface classes live under :mod:`samba.dcerpc`, one module per
    interface, each exposing a class of the same name. Imported by name rather
    than up front so a build missing one interface still serves the others —
    which matters, because a server that answers srvsvc happily may refuse
    winreg entirely.
    """
    modules = {
        PIPE_SRVSVC: ("samba.dcerpc.srvsvc", "srvsvc"),
        PIPE_SAMR: ("samba.dcerpc.samr", "samr"),
        PIPE_LSA: ("samba.dcerpc.lsa", "lsarpc"),
        PIPE_WINREG: ("samba.dcerpc.winreg", "winreg"),
    }
    entry = modules.get(name)
    if entry is None:  # pragma: no cover - a programming error, not a runtime one
        raise SamfsconError(f"unknown RPC interface {name!r}", code="unknown_pipe")

    module_name, class_name = entry
    try:
        module = __import__(module_name, fromlist=[class_name])
        factory = getattr(module, class_name)
    except (ImportError, AttributeError) as exc:  # pragma: no cover
        raise SamfsconError(
            "The Samba python bindings are incomplete.",
            code="samba_missing",
            detail=str(exc),
            hint="The container image must provide python3-samba.",
        ) from exc

    try:
        return factory(binding, lp, creds)
    except Exception as exc:
        raise translate(exc) from exc


def _open_tree(host: str, share: str, lp: Any, creds: Any) -> Any:
    """Open an SMB connection to one share.

    ``libsmb_samba_internal`` is the binding Samba's own tooling uses, and its
    constructor keywords have varied across releases — ``sign`` came and went,
    and ``multi_threaded`` exists only on some builds. Rather than pin one form
    and break on the next distribution upgrade, the known shapes are tried in
    order of preference. This is the same treatment ``set_named_ccache`` gets
    in :mod:`samfscon.auth.credentials`.
    """
    try:
        from samba.samba3 import libsmb_samba_internal as libsmb
    except ImportError as exc:  # pragma: no cover
        raise SamfsconError(
            "The Samba SMB bindings are not available.",
            code="samba_missing",
            detail=str(exc),
            hint="The container image must provide python3-samba.",
        ) from exc

    attempts = (
        lambda: libsmb.Conn(host, share, lp=lp, creds=creds, sign=True),
        lambda: libsmb.Conn(host, share, lp=lp, creds=creds),
        lambda: libsmb.Conn(host, share, lp, creds),
    )
    errors: list[str] = []
    for attempt in attempts:
        try:
            return attempt()
        except TypeError as exc:
            errors.append(str(exc))
            continue
        except Exception as exc:
            raise translate(exc) from exc

    raise SamfsconError(
        "The SMB connection could not be opened.",
        code="smb_binding_unsupported",
        detail="; ".join(errors),
        hint="Samba's libsmb Conn has an unexpected signature in this build.",
    )


def _close_quietly(handle: Any, what: str) -> None:
    """Close whatever this object calls closing. Teardown must not raise."""
    for name in ("disconnect", "close"):
        method = getattr(handle, name, None)
        if callable(method):
            try:
                method()
            except Exception:
                logger.debug("closing %s failed", what, exc_info=True)
            return
