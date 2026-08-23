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


def test_one_code_never_carries_two_hints() -> None:
    """The invariant the note above _WERROR states, asserted rather than hoped.

    The interface translates by code: `error.<code>` and `error.<code>.hint`.
    So a code that means two things in two entries can only be given one
    sentence, and whichever one is written down is then shown for both. Three
    entries shared `insufficient_access` and two of them advised granting
    SeDiskOperatorPrivilege — which is right for managing a share and cannot
    create a folder, so that is what the folder dialog said.

    Advice about a specific cause belongs at the call site that knows the
    cause, not in a table that only knows the status number.
    """
    from collections import defaultdict

    from samfscon.core import errors

    hints: dict[str, set[str]] = defaultdict(set)
    for table in (errors._NT_STATUS, errors._WERROR):
        for _symbol, (_cls, code, _message, hint) in table.items():
            if hint is not None:
                hints[code].add(hint)
    # The Kerberos patterns too: they answer the same interface with the same
    # keys, and one of them carried sign-in advice under a code the accounts
    # console also raised.
    for _pattern, _cls, code, _message, hint in errors._KRB_PATTERNS:
        if hint is not None:
            hints[code].add(hint)

    conflicting = {code: sorted(found) for code, found in hints.items() if len(found) > 1}
    assert not conflicting, f"one code, two hints: {sorted(conflicting)}"


def test_one_code_never_carries_two_classes() -> None:
    """The same rule for the status: 403 and 404 for one code would leave the
    interface deciding what happened from a number that changes underneath it."""
    from collections import defaultdict

    from samfscon.core import errors

    classes: dict[str, set[str]] = defaultdict(set)
    for table in (errors._NT_STATUS, errors._WERROR):
        for _symbol, (cls, code, _message, _hint) in table.items():
            classes[code].add(cls.__name__)
    for _pattern, cls, code, _message, _hint in errors._KRB_PATTERNS:
        classes[code].add(cls.__name__)

    conflicting = {code: sorted(found) for code, found in classes.items() if len(found) > 1}
    assert not conflicting, f"one code, two classes: {sorted(conflicting)}"


def test_a_refused_mkdir_says_what_it_actually_needs() -> None:
    """The refusal an administrator saw, and the advice that could not help.

    Creating a folder inside a share is an ordinary file access. It was
    answered with the generic access-denied hint, which advised granting
    SeDiskOperatorPrivilege — a privilege that governs managing shares and
    cannot create a folder. Following it grants a broad right and leaves the
    original problem exactly where it was.
    """
    import pytest

    from samfscon.core.errors import PermissionDenied
    from samfscon.srv import files

    class Tree:
        def mkdir(self, _path):
            raise RuntimeError("NT_STATUS_ACCESS_DENIED")

    class Conn:
        def tree(self, _share):
            return Tree()

    with pytest.raises(PermissionDenied) as raised:
        files.mkdir(Conn(), "share", "Projekte")

    error = raised.value
    assert error.code == "directory_create_denied"
    assert error.context["share"] == "share"
    # It names the permission that applies, and says the privilege does not —
    # because anyone who saw the old message will come looking for it.
    assert "write permission" in (error.hint or "")
    assert "does not apply" in (error.hint or "")


def test_a_refused_mkdir_that_is_not_a_permission_problem_keeps_its_own_answer() -> None:
    """The branch must not swallow everything. A missing parent directory is
    not a permission problem, and answering it with advice about permissions
    would send somebody to check an ACL that is perfectly correct."""
    import pytest

    from samfscon.core.errors import NotFound
    from samfscon.srv import files

    class Tree:
        def mkdir(self, _path):
            raise RuntimeError("NT_STATUS_OBJECT_PATH_NOT_FOUND")

    class Conn:
        def tree(self, _share):
            return Tree()

    with pytest.raises(NotFound):
        files.mkdir(Conn(), "share", "Projekte/Unterordner")

