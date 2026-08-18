"""Error model and translation of Samba/SMB/RPC failures.

Raw NT_STATUS and WERROR values are useless in a user interface. Everything
raised below the API layer is funnelled through :func:`translate`, which
produces a :class:`SamfsconError` carrying

* a stable machine-readable ``code`` (the front end translates it to DE/EN),
* a technical English ``message`` for logs and for admins who want the detail,
* an optional ``hint`` naming the usual cause.

This module deliberately does not import the samba bindings at module level so
the translation logic stays unit-testable on machines without python3-samba.

Two families of status arrive here, and mixing them up costs an afternoon:
NT_STATUS comes from SMB and from the SAMR/LSA pipes, WERROR from srvsvc and
winreg. They number the same conditions differently — "access denied" is
``NT_STATUS_ACCESS_DENIED`` on one pipe and ``WERR_ACCESS_DENIED`` on the next —
so both are mapped, onto the same codes where they mean the same thing.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class SamfsconError(Exception):
    """Base class for everything the API layer turns into an HTTP response."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        hint: str | None = None,
        detail: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.hint = hint
        self.detail = detail
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.hint:
            payload["hint"] = self.hint
        if self.detail:
            payload["detail"] = self.detail
        if self.context:
            payload["context"] = self.context
        return payload


class AuthenticationError(SamfsconError):
    status_code = 401
    code = "authentication_failed"


class SessionExpired(SamfsconError):
    status_code = 401
    code = "session_expired"


class PermissionDenied(SamfsconError):
    status_code = 403
    code = "insufficient_access"


class NotFound(SamfsconError):
    status_code = 404
    code = "not_found"


class Conflict(SamfsconError):
    status_code = 409
    code = "conflict"


class InvalidRequest(SamfsconError):
    status_code = 400
    code = "invalid_request"


class ConstraintViolation(SamfsconError):
    status_code = 400
    code = "constraint_violation"


class UpstreamUnavailable(SamfsconError):
    status_code = 502
    code = "server_unavailable"


class OperationTimeout(SamfsconError):
    status_code = 504
    code = "timeout"


class NotConfigured(SamfsconError):
    """The server can do this, but has not been set up for it.

    Distinct from :class:`PermissionDenied` on purpose. Samba refuses a share
    creation with ACCESS_DENIED both when the account lacks
    SeDiskOperatorPrivilege and when registry configuration is switched off —
    two problems with nothing in common but the status code, and the advice for
    one sends the reader entirely the wrong way for the other.
    """

    status_code = 409
    code = "not_configured"


# ---------------------------------------------------------------------------
# The two status families
# ---------------------------------------------------------------------------

# NT_STATUS reaches us through SMB, Kerberos, SAMR and LSA.
_NT_STATUS: dict[str, tuple[type[SamfsconError], str, str, str | None]] = {
    "NT_STATUS_LOGON_FAILURE": (
        AuthenticationError,
        "invalid_credentials",
        "Wrong user name or password.",
        None,
    ),
    "NT_STATUS_ACCOUNT_LOCKED_OUT": (
        AuthenticationError,
        "account_locked_out",
        "The account is locked out.",
        None,
    ),
    "NT_STATUS_ACCOUNT_DISABLED": (
        AuthenticationError,
        "account_disabled",
        "The account is disabled.",
        None,
    ),
    "NT_STATUS_ACCOUNT_EXPIRED": (
        AuthenticationError,
        "account_expired",
        "The account has expired.",
        None,
    ),
    "NT_STATUS_PASSWORD_EXPIRED": (
        AuthenticationError,
        "password_expired",
        "The password has expired.",
        None,
    ),
    "NT_STATUS_PASSWORD_MUST_CHANGE": (
        AuthenticationError,
        "password_must_change",
        "The password must be changed before this account can be used.",
        None,
    ),
    "NT_STATUS_ACCESS_DENIED": (
        PermissionDenied,
        "insufficient_access",
        "Access denied.",
        "Your account lacks the required permission on the target.",
    ),
    "NT_STATUS_NETWORK_ACCESS_DENIED": (
        PermissionDenied,
        "insufficient_access",
        "The server refused this operation for your account.",
        (
            "Managing shares needs SeDiskOperatorPrivilege on the file server: "
            "net rpc rights grant '<group>' SeDiskOperatorPrivilege -U <admin>"
        ),
    ),
    "NT_STATUS_OBJECT_NAME_NOT_FOUND": (
        NotFound,
        "not_found",
        "The file or directory does not exist.",
        None,
    ),
    "NT_STATUS_OBJECT_PATH_NOT_FOUND": (
        NotFound,
        "not_found",
        "The path does not exist on the share.",
        None,
    ),
    "NT_STATUS_OBJECT_NAME_COLLISION": (
        Conflict,
        "already_exists",
        "The file or directory already exists.",
        None,
    ),
    "NT_STATUS_SHARING_VIOLATION": (
        Conflict,
        "file_in_use",
        "The file is currently in use.",
        "Someone has it open. The session view shows who.",
    ),
    "NT_STATUS_DIRECTORY_NOT_EMPTY": (
        Conflict,
        "not_empty",
        "The directory is not empty.",
        None,
    ),
    "NT_STATUS_CONNECTION_REFUSED": (
        UpstreamUnavailable,
        "server_unreachable",
        "The file server refused the connection.",
        None,
    ),
    "NT_STATUS_HOST_UNREACHABLE": (
        UpstreamUnavailable,
        "server_unreachable",
        "The file server is unreachable.",
        None,
    ),
    "NT_STATUS_NETWORK_UNREACHABLE": (
        UpstreamUnavailable,
        "server_unreachable",
        "The file server is unreachable.",
        None,
    ),
    "NT_STATUS_IO_TIMEOUT": (
        OperationTimeout,
        "server_timeout",
        "The file server did not answer in time.",
        None,
    ),
    "NT_STATUS_BAD_NETWORK_NAME": (
        NotFound,
        "share_not_found",
        "The share does not exist on this server.",
        None,
    ),
    "NT_STATUS_INVALID_PARAMETER": (
        InvalidRequest,
        "invalid_parameter",
        "The server rejected a parameter of the request.",
        None,
    ),
    "NT_STATUS_PASSWORD_RESTRICTION": (
        ConstraintViolation,
        "password_policy_violation",
        "The password does not satisfy the server's password policy.",
        "Check length, complexity, minimum age and password history.",
    ),
    "NT_STATUS_WRONG_PASSWORD": (
        AuthenticationError,
        "invalid_credentials",
        "Wrong password.",
        None,
    ),
    "NT_STATUS_NO_SUCH_USER": (
        AuthenticationError,
        "user_not_found",
        "No such account on this server.",
        None,
    ),
    "NT_STATUS_USER_EXISTS": (
        Conflict,
        "already_exists",
        "An account with this name already exists.",
        None,
    ),
    "NT_STATUS_GROUP_EXISTS": (
        Conflict,
        "already_exists",
        "A group with this name already exists.",
        None,
    ),
    "NT_STATUS_MEMBER_IN_GROUP": (
        Conflict,
        "already_member",
        "The account is already a member of this group.",
        None,
    ),
    "NT_STATUS_MEMBER_NOT_IN_GROUP": (
        NotFound,
        "not_a_member",
        "The account is not a member of this group.",
        None,
    ),
    "NT_STATUS_NONE_MAPPED": (
        NotFound,
        "sid_not_resolved",
        "The name could not be resolved to an account.",
        "Spell it as it exists on the server, or as DOMAIN\\name for a domain account.",
    ),
    "NT_STATUS_TIME_DIFFERENCE_AT_DC": (
        AuthenticationError,
        "clock_skew",
        "The clocks of SAMFSCON and the domain controller differ too much.",
        "Kerberos tolerates about five minutes — synchronise the container's clock via NTP.",
    ),
    "NT_STATUS_NOT_SUPPORTED": (
        SamfsconError,
        "not_supported",
        "The server does not support this operation.",
        None,
    ),
    "NT_STATUS_INVALID_INFO_CLASS": (
        SamfsconError,
        "unsupported_info_level",
        "The server does not support this information level.",
        "The Samba version on the server is probably older than SAMFSCON expects.",
    ),
    "NT_STATUS_REVISION_MISMATCH": (
        SamfsconError,
        "smb_dialect_mismatch",
        "The call is not available over the negotiated SMB dialect.",
        None,
    ),
}

# WERROR reaches us through srvsvc (shares, sessions, open files) and winreg
# (the registry configuration). Mapped onto the same codes as their NT_STATUS
# counterparts wherever they mean the same thing: the front end translates by
# code, and one condition with two spellings would need two translations.
_WERROR: dict[str, tuple[type[SamfsconError], str, str, str | None]] = {
    "WERR_ACCESS_DENIED": (
        PermissionDenied,
        "insufficient_access",
        "The server refused this operation for your account.",
        (
            "Managing shares needs SeDiskOperatorPrivilege on the file server: "
            "net rpc rights grant '<group>' SeDiskOperatorPrivilege -U <admin>"
        ),
    ),
    "WERR_FILE_NOT_FOUND": (
        NotFound,
        "not_found",
        "The server did not find what the request named.",
        None,
    ),
    "WERR_PATH_NOT_FOUND": (
        NotFound,
        "path_not_found",
        "The path does not exist on the server.",
        None,
    ),
    "WERR_INVALID_NAME": (
        InvalidRequest,
        "invalid_name",
        "The name is not valid for this server.",
        None,
    ),
    "WERR_INVALID_PARAMETER": (
        InvalidRequest,
        "invalid_parameter",
        "The server rejected a parameter of the request.",
        None,
    ),
    "WERR_INVALID_LEVEL": (
        SamfsconError,
        "unsupported_info_level",
        "The server does not support this information level.",
        "The Samba version on the server is probably older than SAMFSCON expects.",
    ),
    "WERR_NOT_SUPPORTED": (
        SamfsconError,
        "not_supported",
        "The server does not support this operation.",
        None,
    ),
    "WERR_BAD_NETPATH": (
        UpstreamUnavailable,
        "server_unreachable",
        "The server could not be reached under this name.",
        None,
    ),
    "WERR_NERR_NETNAMENOTFOUND": (
        NotFound,
        "share_not_found",
        "The share does not exist on this server.",
        None,
    ),
    "WERR_NERR_DUPLICATESHARE": (
        Conflict,
        "share_exists",
        "A share with this name already exists.",
        None,
    ),
    "WERR_NERR_UNKNOWNDEVDIR": (
        InvalidRequest,
        "share_path_missing",
        "The directory the share should publish does not exist on the server.",
        (
            "SAMFSCON manages the server over the network and cannot create a "
            "directory outside an existing share. Create it on the server first."
        ),
    ),
    "WERR_NERR_REDIRECTEDPATH": (
        InvalidRequest,
        "share_path_redirected",
        "The path is already redirected and cannot be shared.",
        None,
    ),
    "WERR_NERR_USERNOTFOUND": (
        NotFound,
        "user_not_found",
        "No such account on this server.",
        None,
    ),
    "WERR_NERR_CLIENTNAMENOTFOUND": (
        NotFound,
        "session_not_found",
        "The session no longer exists.",
        "It probably ended between the listing and this request.",
    ),
}

# Kerberos failures surface as plain text, not as a status code.
_KRB_PATTERNS: list[tuple[re.Pattern[str], type[SamfsconError], str, str, str | None]] = [
    (
        re.compile(r"clock skew", re.I),
        AuthenticationError,
        "clock_skew",
        "The clocks of SAMFSCON and the domain controller differ too much.",
        "Kerberos tolerates about five minutes — synchronise the container's clock via NTP.",
    ),
    (
        re.compile(r"pre-?authentication fail", re.I),
        AuthenticationError,
        "invalid_credentials",
        "Wrong user name or password.",
        None,
    ),
    (
        re.compile(r"(cannot|unable to) (contact|find|reach) any? ?kdc", re.I),
        UpstreamUnavailable,
        "kdc_unreachable",
        "No key distribution centre could be reached.",
        "Check SAMFSCON_KDC_HOSTS, DNS SRV records and that port 88 is open.",
    ),
    (
        re.compile(r"\bclient\b.*?not found in kerberos database", re.I),
        AuthenticationError,
        "user_not_found",
        "No such account in this realm.",
        "Sign in as user@REALM and check the realm spelling.",
    ),
    (
        re.compile(r"\b(server|principal)\b.*?not found in kerberos database", re.I),
        UpstreamUnavailable,
        "spn_not_found",
        "The file server has no service principal in this realm.",
        (
            "Kerberos issues tickets for cifs/<hostname>. Use the server's own "
            "name rather than an address, and check that it is still joined."
        ),
    ),
    (
        re.compile(r"ticket expired|credentials? (have )?expired", re.I),
        SessionExpired,
        "session_expired",
        "The Kerberos ticket has expired.",
        "Sign in again.",
    ),
]

_NT_STATUS_RE = re.compile(r"NT_STATUS_[A-Z0-9_]+")
_WERROR_RE = re.compile(r"WERR_[A-Z0-9_]+")


def translate(exc: BaseException) -> SamfsconError:
    """Turn any exception from the Samba layer into a :class:`SamfsconError`."""
    if isinstance(exc, SamfsconError):
        return exc

    text = str(exc)

    name = _status_name(exc, text, _NT_STATUS_RE, _NT_STATUS, _numeric_nt_status)
    if name is not None:
        cls, code, message, hint = _NT_STATUS[name]
        return cls(message, code=code, hint=hint, detail=text)

    name = _status_name(exc, text, _WERROR_RE, _WERROR, _numeric_werror)
    if name is not None:
        cls, code, message, hint = _WERROR[name]
        return cls(message, code=code, hint=hint, detail=text)

    # A status we do not map is still worth naming as one: "the server reported
    # NT_STATUS_..." beats "an unexpected error occurred", because the symbol is
    # something an administrator can look up.
    unmapped = _NT_STATUS_RE.search(text) or _WERROR_RE.search(text)
    if unmapped is not None:
        return SamfsconError(
            "The file server reported an error.",
            code="server_error",
            detail=text,
            context={"status": unmapped.group(0)},
        )

    for pattern, cls, code, message, hint in _KRB_PATTERNS:
        if pattern.search(text):
            return cls(message, code=code, hint=hint, detail=text)

    if isinstance(exc, TimeoutError):
        return OperationTimeout(
            "The operation did not finish in time.", code="timeout", detail=text
        )
    if isinstance(exc, (ConnectionError, OSError)):
        return UpstreamUnavailable(
            "The file server could not be reached.",
            code="server_unreachable",
            detail=text,
        )

    return SamfsconError("An unexpected error occurred.", detail=text)


def _status_name(
    exc: BaseException,
    text: str,
    pattern: re.Pattern[str],
    table: dict[str, Any],
    numeric: Any,
) -> str | None:
    """The status symbol behind an exception, however it spells itself.

    Some bindings put the name in the message. Others do not: an
    ``NTSTATUSError`` reads ``(3221225539, 'A file cannot be opened because the
    share access flags are incompatible.')`` — the number and a sentence, never
    the symbol. ``WERRORError`` behaves the same way. Both forms have to be
    recognised, or half the failures arrive as "an unexpected error occurred".
    """
    match = pattern.search(text)
    if match and match.group(0) in table:
        return match.group(0)

    for arg in getattr(exc, "args", ()):
        # A tuple argument is the (number, message) pair some bindings pass
        # whole rather than spread.
        candidates = arg if isinstance(arg, tuple) else (arg,)
        for candidate in candidates:
            if isinstance(candidate, int):
                found = numeric().get(candidate)
                if found is not None:
                    return found
    return None


def _numeric_table(module_name: str, names: dict[str, Any]) -> dict[int, str]:
    """The numbers behind the symbols we translate, read from Samba itself.

    Derived from the tables above rather than typed out, so a symbol added
    there is recognised in both forms without anyone remembering to look up its
    number.
    """
    mapping: dict[int, str] = {}
    try:
        module = __import__(module_name, fromlist=["*"])
    except ImportError:  # pragma: no cover - only on hosts without the bindings
        return mapping

    for name in names:
        value = getattr(module, name, None)
        try:
            mapping[int(value)] = name  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
    return mapping


_NUMERIC_NT_STATUS: dict[int, str] | None = None
_NUMERIC_WERROR: dict[int, str] | None = None


def _numeric_nt_status() -> dict[int, str]:
    global _NUMERIC_NT_STATUS
    if _NUMERIC_NT_STATUS is None:
        _NUMERIC_NT_STATUS = _numeric_table("samba.ntstatus", _NT_STATUS)
    return _NUMERIC_NT_STATUS


def _numeric_werror() -> dict[int, str]:
    global _NUMERIC_WERROR
    if _NUMERIC_WERROR is None:
        _NUMERIC_WERROR = _numeric_table("samba.werror", _WERROR)
    return _NUMERIC_WERROR
