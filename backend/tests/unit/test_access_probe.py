"""Asking the server what this account may do, instead of working it out.

The arithmetic next door — :func:`acl.effective_access` — reads the entries
that name one SID and says so: it knows nothing about the groups that SID is
in. On a directory whose only entry is for Domain Admins it answers "no
access" to a member of Domain Admins. That is a wrong answer with a confident
face, and it is the answer a "you cannot write here" warning would have been
built on.

So the probe opens a handle with the access the operation needs and lets the
server evaluate the whole token. Three answers, and the third is the one this
file mostly exists for: a question that could not be put is not a permission
problem.
"""

from __future__ import annotations

from typing import Any

import pytest

from samfscon.core.errors import NotFound, PermissionDenied
from samfscon.srv import acl


class Tree:
    """A share that answers `create` however the test wants it to."""

    def __init__(self, answer: Any = None, *, accepts_keywords: bool = True) -> None:
        self.answer = answer
        self.accepts_keywords = accepts_keywords
        self.asked: list[dict[str, Any]] = []
        self.closed: list[Any] = []

    def create(self, name: str, *positional: Any, **keywords: Any) -> Any:
        if keywords and not self.accepts_keywords:
            raise TypeError("create() got an unexpected keyword argument")
        self.asked.append({"name": name, "positional": positional, **keywords})
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer

    def close(self, handle: Any) -> None:
        self.closed.append(handle)


class Conn:
    def __init__(self, tree: Tree | Exception) -> None:
        self._tree = tree

    def tree(self, _share: str) -> Tree:
        if isinstance(self._tree, Exception):
            raise self._tree
        return self._tree


def test_an_open_that_succeeds_means_the_account_may(monkeypatch: pytest.MonkeyPatch) -> None:
    tree = Tree(answer=42)
    assert acl.probe_access(Conn(tree), "share", "", acl.PROBE_CREATE) is True
    # And the handle is given back. A probe that leaked one would hold the
    # directory open on the server for the life of the session.
    assert tree.closed == [42]


def test_a_refusal_means_the_account_may_not() -> None:
    tree = Tree(answer=RuntimeError("NT_STATUS_ACCESS_DENIED"))
    assert acl.probe_access(Conn(tree), "share", "", acl.PROBE_CREATE) is False


def test_anything_that_is_not_a_refusal_is_not_an_answer() -> None:
    """The distinction the whole design rests on.

    A missing directory, a dropped connection and a binding that does not
    understand the call are not permission problems. Rendered as `False` they
    would each become "this account may not write here" — a fault reported
    where none was found.
    """
    for failure in (
        RuntimeError("NT_STATUS_OBJECT_NAME_NOT_FOUND"),
        RuntimeError("NT_STATUS_CONNECTION_DISCONNECTED"),
        RuntimeError("something nobody mapped"),
    ):
        assert acl.probe_access(Conn(Tree(answer=failure)), "share", "", acl.PROBE_CREATE) is None


def test_a_binding_that_refuses_the_keywords_is_tried_the_other_way() -> None:
    """`libsmb`'s create has changed shape between releases, the way Conn's
    constructor has. A TypeError is a signature mismatch, not an answer."""
    tree = Tree(answer=7, accepts_keywords=False)
    assert acl.probe_access(Conn(tree), "share", "", acl.PROBE_CREATE) is True
    assert tree.asked[0]["positional"] == (0, tree.asked[0]["positional"][1])


def test_a_share_that_will_not_open_answers_nothing() -> None:
    assert acl.probe_access(Conn(RuntimeError("boom")), "share", "", acl.PROBE_CREATE) is None


def test_creating_asks_for_both_of_the_rights_it_needs() -> None:
    """A folder needs add-file and add-subdirectory. Asking for one would
    answer a narrower question than the button that follows it offers.

    Against the numbers from MS-DTYP 2.4.3, not against the module's own
    constants: comparing the code to itself would pass however wrong the pair
    was, and 0x2/0x4 are the values a network capture shows.
    """
    tree = Tree(answer=1)
    acl.probe_access(Conn(tree), "share", "Projekte", acl.PROBE_CREATE)
    wanted = tree.asked[0]["DesiredAccess"]
    assert wanted & 0x00000002, "add file"
    assert wanted & 0x00000004, "add subdirectory"


def test_the_probe_never_creates_anything() -> None:
    """FILE_OPEN, and a directory at that. A probe that created the thing it
    was asking about would answer the question by changing it."""
    tree = Tree(answer=1)
    acl.probe_access(Conn(tree), "share", "Projekte", acl.PROBE_CREATE)
    assert tree.asked[0]["CreateDisposition"] == acl.FILE_OPEN
    assert tree.asked[0]["CreateOptions"] == acl.FILE_DIRECTORY_FILE


def test_taking_ownership_and_changing_permissions_are_different_questions() -> None:
    """Which is the point of offering the first when the second is refused."""
    tree = Tree(answer=1)
    acl.probe_access(Conn(tree), "share", "", acl.PROBE_TAKE_OWNERSHIP)
    acl.probe_access(Conn(tree), "share", "", acl.PROBE_CHANGE_PERMISSIONS)
    assert tree.asked[0]["DesiredAccess"] == 0x00080000, "WRITE_OWNER"
    assert tree.asked[1]["DesiredAccess"] == 0x00040000, "WRITE_DAC"


def test_an_unknown_question_is_refused_rather_than_guessed() -> None:
    from samfscon.core.errors import InvalidRequest

    with pytest.raises(InvalidRequest):
        acl.probe_access(Conn(Tree()), "share", "", "whatever")


# ---------------------------------------------------------------------------
# Taking ownership
# ---------------------------------------------------------------------------


class AclTree(Tree):
    def __init__(self) -> None:
        super().__init__()
        self.written: list[tuple[str, Any, int]] = []

    def set_acl(self, path: str, descriptor: Any, info: int) -> None:
        self.written.append((path, descriptor, info))


def test_taking_ownership_sends_the_owner_and_nothing_else(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reason it is a separate call.

    The ordinary descriptor write asks for OWNER, GROUP and DACL together, so
    it needs WRITE_DAC — which is exactly the right somebody is trying to
    obtain by taking ownership. Sending the whole descriptor would refuse the
    one operation that could have unblocked them.
    """
    tree = AclTree()
    monkeypatch.setattr(acl, "to_descriptor", lambda _conn, sddl: sddl)

    acl.take_ownership(Conn(tree), "share", "Projekte", "S-1-5-21-1-2-3-500")

    path, descriptor, info = tree.written[0]
    assert path == "Projekte"
    assert descriptor == "O:S-1-5-21-1-2-3-500"
    # OWNER and nothing else, by the numbers rather than by the constants this
    # module defines: 0x1 owner, 0x2 group, 0x4 DACL (MS-DTYP 2.4.7).
    assert info == 0x00000001
    assert not info & 0x00000004, "the DACL, which is the right being sought"
    assert not info & 0x00000002


def test_a_refused_ownership_change_arrives_as_a_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Refusing(AclTree):
        def set_acl(self, path: str, descriptor: Any, info: int) -> None:
            raise RuntimeError("NT_STATUS_ACCESS_DENIED")

    monkeypatch.setattr(acl, "to_descriptor", lambda _conn, sddl: sddl)
    with pytest.raises(PermissionDenied):
        acl.take_ownership(Conn(Refusing()), "share", "", "S-1-5-21-1-2-3-500")


def test_a_missing_path_is_not_a_permission_problem(monkeypatch: pytest.MonkeyPatch) -> None:
    class Missing(AclTree):
        def set_acl(self, path: str, descriptor: Any, info: int) -> None:
            raise RuntimeError("NT_STATUS_OBJECT_NAME_NOT_FOUND")

    monkeypatch.setattr(acl, "to_descriptor", lambda _conn, sddl: sddl)
    with pytest.raises(NotFound):
        acl.take_ownership(Conn(Missing()), "share", "", "S-1-5-21-1-2-3-500")
