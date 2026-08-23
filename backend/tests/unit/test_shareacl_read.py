"""Absent, and unreadable, are not the same descriptor.

A share with no security descriptor is unrestricted at the share level, and
rendering the default for it is right. A share that *has* one this code could
not read is a share whose permissions are unknown — and the two used to produce
the same screen: Everyone, full control.

That is "could not determine" reported as "is not restricted", in the widest
direction available. And it did not stop at the screen. The permission editor
writes back what it shows, so a single change saved on top of a fabricated
Everyone-full-control would have replaced a real descriptor that nobody ever
saw, on a share nobody knew was affected.

These tests exist to keep the five ways through `_sddl_from` distinguishable,
because four of them look identical from the outside and only one of them means
"unrestricted".
"""

from __future__ import annotations

from typing import Any

import pytest

from samfscon.core.errors import SamfsconError
from samfscon.srv import shareacl


class Reply:
    """A level-502 NetShareGetInfo reply, in one of the shapes it arrives in."""

    def __init__(self, sd_buf: Any) -> None:
        self.sd_buf = sd_buf


class Buffer:
    def __init__(self, sd: Any) -> None:
        self.sd = sd


class Renderable:
    """A descriptor object the bindings unpacked for us."""

    def __init__(self, sddl: str) -> None:
        self._sddl = sddl

    def as_sddl(self) -> str:
        return self._sddl


class Unrenderable:
    """A descriptor object that refuses to render."""

    def as_sddl(self) -> str:
        raise ValueError("unsupported ACE type")


# ---------------------------------------------------------------------------
# Genuinely absent
# ---------------------------------------------------------------------------


def test_no_buffer_at_all_is_no_descriptor() -> None:
    assert shareacl._sddl_from(Reply(None)) is None


def test_a_buffer_holding_nothing_is_no_descriptor() -> None:
    assert shareacl._sddl_from(Reply(Buffer(None))) is None


# ---------------------------------------------------------------------------
# Present and readable
# ---------------------------------------------------------------------------


def test_a_descriptor_the_bindings_unpacked_is_returned() -> None:
    reply = Reply(Buffer(Renderable("O:BAG:BAD:(A;;FA;;;BA)")))
    assert shareacl._sddl_from(reply) == "O:BAG:BAD:(A;;FA;;;BA)"


# ---------------------------------------------------------------------------
# Present and not readable — each of these used to answer "absent"
# ---------------------------------------------------------------------------


def test_a_descriptor_that_will_not_render_is_not_reported_as_absent() -> None:
    with pytest.raises(SamfsconError) as raised:
        shareacl._sddl_from(Reply(Buffer(Unrenderable())))

    assert raised.value.code == "sddl_unrenderable"
    # The reason travels with it. "Could not be rendered" on its own sends
    # somebody to the wrong place.
    assert "unsupported ACE type" in (raised.value.detail or "")


def test_a_blob_that_will_not_unpack_is_not_reported_as_absent() -> None:
    with pytest.raises(SamfsconError) as raised:
        # Not a valid NDR security descriptor; ndr_unpack refuses it.
        shareacl._sddl_from(Reply(Buffer(b"\x01\x02\x03")))

    assert raised.value.code == "sddl_unrenderable"


def test_a_shape_nobody_anticipated_is_not_reported_as_absent() -> None:
    """The one that would go unnoticed longest.

    A future Samba returning something that is neither renderable nor bytes
    fell straight through to `return None`, which the caller read as
    "unrestricted" — an answer invented out of not knowing what arrived.
    """
    with pytest.raises(SamfsconError) as raised:
        shareacl._sddl_from(Reply(Buffer(42)))

    assert raised.value.code == "sddl_unrenderable"
    assert "int" in (raised.value.detail or "")


# ---------------------------------------------------------------------------
# What the caller does with each
# ---------------------------------------------------------------------------


def test_read_renders_the_default_only_for_a_share_that_has_none() -> None:
    class Pipe:
        # The name is the wire method's, so it cannot be lower-cased.
        def NetShareGetInfo(self, *_args: Any) -> Reply:  # noqa: N802
            return Reply(None)

    class Connection:
        srvsvc = Pipe()

    descriptor = shareacl.read(Connection(), "projects")

    # Everyone, full control — which is what a share with no descriptor
    # actually enforces, and the reason the default exists at all.
    assert descriptor.sddl == shareacl.DEFAULT_SDDL


def test_read_refuses_rather_than_inventing_one() -> None:
    class Pipe:
        # The name is the wire method's, so it cannot be lower-cased.
        def NetShareGetInfo(self, *_args: Any) -> Reply:  # noqa: N802
            return Reply(Buffer(Unrenderable()))

    class Connection:
        srvsvc = Pipe()

    with pytest.raises(SamfsconError) as raised:
        shareacl.read(Connection(), "projects")

    assert raised.value.code == "sddl_unrenderable"
    # The hint names the command that prints the same descriptor, because the
    # console has just admitted it cannot.
    assert "getsecurity" in (raised.value.hint or "")
