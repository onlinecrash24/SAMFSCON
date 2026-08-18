"""Translating what the server says into what the interface shows.

Two status families arrive here and they number the same conditions
differently. Both spellings — the symbol in the message text, and the bare
number in the exception's args — have to be recognised, because which one turns
up depends on which binding raised it.
"""

from __future__ import annotations

import pytest

from samfscon.core.errors import (
    AuthenticationError,
    Conflict,
    InvalidRequest,
    NotFound,
    OperationTimeout,
    PermissionDenied,
    SamfsconError,
    UpstreamUnavailable,
    translate,
)


def test_a_samfscon_error_passes_through_unchanged() -> None:
    """Translation must be idempotent: the layers below already translate."""
    original = NotFound("gone", code="share_not_found")
    assert translate(original) is original


@pytest.mark.parametrize(
    ("text", "expected_type", "expected_code"),
    [
        ("NT_STATUS_LOGON_FAILURE", AuthenticationError, "invalid_credentials"),
        ("NT_STATUS_ACCESS_DENIED", PermissionDenied, "insufficient_access"),
        ("NT_STATUS_BAD_NETWORK_NAME", NotFound, "share_not_found"),
        ("NT_STATUS_SHARING_VIOLATION", Conflict, "file_in_use"),
        ("NT_STATUS_IO_TIMEOUT", OperationTimeout, "server_timeout"),
        ("NT_STATUS_HOST_UNREACHABLE", UpstreamUnavailable, "server_unreachable"),
    ],
)
def test_nt_status_by_name(text: str, expected_type: type, expected_code: str) -> None:
    error = translate(RuntimeError(f"failed: {text}"))
    assert isinstance(error, expected_type)
    assert error.code == expected_code


@pytest.mark.parametrize(
    ("text", "expected_type", "expected_code"),
    [
        ("WERR_ACCESS_DENIED", PermissionDenied, "insufficient_access"),
        ("WERR_NERR_DUPLICATESHARE", Conflict, "share_exists"),
        ("WERR_NERR_NETNAMENOTFOUND", NotFound, "share_not_found"),
        ("WERR_NERR_UNKNOWNDEVDIR", InvalidRequest, "share_path_missing"),
        ("WERR_INVALID_NAME", InvalidRequest, "invalid_name"),
    ],
)
def test_werror_by_name(text: str, expected_type: type, expected_code: str) -> None:
    error = translate(RuntimeError(f"NetShareAdd failed: {text}"))
    assert isinstance(error, expected_type)
    assert error.code == expected_code


def test_the_two_families_agree_on_shared_codes() -> None:
    """Access denied is one condition with two spellings.

    The front end translates by code, so both must land on the same one or the
    same refusal needs two translations and eventually gets one.
    """
    nt = translate(RuntimeError("NT_STATUS_ACCESS_DENIED"))
    werr = translate(RuntimeError("WERR_ACCESS_DENIED"))
    assert nt.code == werr.code == "insufficient_access"


def test_share_management_hints_name_the_command() -> None:
    """A refusal an administrator cannot act on is only half an error message."""
    error = translate(RuntimeError("WERR_ACCESS_DENIED"))
    assert error.hint is not None
    assert "SeDiskOperatorPrivilege" in error.hint


def test_missing_directory_says_why_samfscon_cannot_fix_it() -> None:
    """The limit of managing a server over the network, stated where it bites."""
    error = translate(RuntimeError("WERR_NERR_UNKNOWNDEVDIR"))
    assert error.hint is not None
    assert "create it on the server first" in error.hint.lower()


def test_an_unmapped_status_still_names_itself() -> None:
    """A symbol an administrator can look up beats "unexpected error"."""
    error = translate(RuntimeError("NT_STATUS_SOMETHING_WE_DID_NOT_MAP"))
    assert error.code == "server_error"
    assert error.context["status"] == "NT_STATUS_SOMETHING_WE_DID_NOT_MAP"


def test_numeric_status_without_the_symbol() -> None:
    """The SMB bindings raise (number, sentence) and never the symbol.

    Without the numeric lookup every SMB failure arrives as "an unexpected
    error occurred". The mapping is built from samba.ntstatus, so on a machine
    without the bindings there is nothing to look up — and the test says so
    rather than pretending to pass.
    """
    pytest.importorskip("samba.ntstatus")
    from samba import ntstatus

    exc = Exception(
        ntstatus.NT_STATUS_SHARING_VIOLATION,
        "A file cannot be opened because the share access flags are incompatible.",
    )
    error = translate(exc)
    assert error.code == "file_in_use"


def test_kerberos_text_is_recognised() -> None:
    """Kerberos failures carry no status code at all, only prose."""
    error = translate(RuntimeError("kinit: Clock skew too great while getting initial credentials"))
    assert isinstance(error, AuthenticationError)
    assert error.code == "clock_skew"


def test_kerberos_spn_hint_explains_the_bare_address_trap() -> None:
    error = translate(
        RuntimeError("Server not found in Kerberos database while getting initial credentials")
    )
    assert error.code == "spn_not_found"
    assert error.hint is not None
    assert "cifs/" in error.hint


def test_connection_errors_become_upstream_failures() -> None:
    error = translate(ConnectionRefusedError("connection refused"))
    assert isinstance(error, UpstreamUnavailable)
    assert error.code == "server_unreachable"


def test_timeouts_keep_their_meaning() -> None:
    error = translate(TimeoutError("took too long"))
    assert isinstance(error, OperationTimeout)


def test_anything_else_is_reported_without_guessing() -> None:
    error = translate(ValueError("something entirely unrelated"))
    assert type(error) is SamfsconError
    assert error.detail == "something entirely unrelated"


def test_error_payload_carries_hint_and_context() -> None:
    """What to_dict() emits is what the front end translates and renders."""
    error = PermissionDenied(
        "no", code="missing_disk_operator", hint="grant it", context={"holders": ["Admins"]}
    )
    payload = error.to_dict()
    assert payload == {
        "code": "missing_disk_operator",
        "message": "no",
        "hint": "grant it",
        "context": {"holders": ["Admins"]},
    }
