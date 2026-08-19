"""Who is connected, and what they have open.

``smbstatus`` reads this from the server's own tdb files. srvsvc publishes the
same facts over the network, which is how the Windows "Shared Folders" console
shows them and how SAMFSCON gets them without touching the server's disk.

Three lists, and they answer different questions:

* **Sessions** (``NetSessEnum``) — one per authenticated user on one client. The
  question "who is on the server right now".
* **Connections** (``NetConnEnum``) — one per share a session has open. The
  question "who is using this share".
* **Open files** (``NetFileEnum``) — one per open handle, with its locks. The
  question that actually gets asked: "who has this document open, because I
  cannot save it."

Only one thing here writes: ``NetFileClose``, which force-closes somebody else's
handle. It is destructive in a way a listing is not — the client holding it
loses unsaved work — and it is treated as such, right down to the audit entry
naming the file and the person who had it.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import Any

from samfscon.core.errors import NotFound, SamfsconError, translate
from samfscon.srv.connection import ServerConnection

logger = logging.getLogger(__name__)

# "As much as you have" for the Net*Enum buffer size. Written as the unsigned
# value rather than as -1: the field is a uint32 on the wire, and the binding
# rejects a negative Python int with "can't convert negative int to unsigned"
# — an exception that comes from the marshalling layer, names no call, and is
# therefore reported as an unexpected error. The share enumeration used the
# unsigned form from the start and worked; these three did not and did not.
MAX_BUFFER = 0xFFFFFFFF

# NetFileEnum permission bits (MS-SRVS 2.2.2.10).
PERM_FILE_READ = 0x01
PERM_FILE_WRITE = 0x02
PERM_FILE_CREATE = 0x04


@dataclass
class Session:
    """One authenticated user on one client machine."""

    user: str | None
    client: str | None
    open_files: int | None
    connected_seconds: int | None
    idle_seconds: int | None
    guest: bool

    def describe(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "client": self.client,
            "open_files": self.open_files,
            "connected_seconds": self.connected_seconds,
            "idle_seconds": self.idle_seconds,
            "guest": self.guest,
        }


@dataclass
class Connection:
    """One share a session has open."""

    id: int | None
    share: str | None
    user: str | None
    client: str | None
    open_files: int | None
    connected_seconds: int | None

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "share": self.share,
            "user": self.user,
            "client": self.client,
            "open_files": self.open_files,
            "connected_seconds": self.connected_seconds,
        }


@dataclass
class OpenFile:
    """One open handle, with what it is allowed to do and how it is locked."""

    id: int | None
    path: str | None
    user: str | None
    locks: int | None
    permissions: list[str]

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "user": self.user,
            "locks": self.locks,
            "permissions": list(self.permissions),
        }


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def list_sessions(
    conn: ServerConnection, *, client: str | None = None, user: str | None = None
) -> list[Session]:
    """Everyone currently connected.

    Level 1 first: it carries the user, the client, the open count, the
    connected time and the idle time — every field this view shows. Level 2
    adds only the client's type, which nobody has asked for, and a real server
    refused it outright with WERR_INVALID_LEVEL. Level 0 is the floor and knows
    the client and nothing else.
    """
    from samba.dcerpc import srvsvc

    def make(level: int) -> Any:
        return _ctr(
            srvsvc.NetSessInfoCtr(),
            level,
            {0: srvsvc.NetSessCtr0, 1: srvsvc.NetSessCtr1, 2: srvsvc.NetSessCtr2}[level](),
        )

    entries, _ = _enumerate_levels(
        conn,
        (1, 2, 0),
        make,
        lambda pipe, ctr, resume: pipe.NetSessEnum(
            None, client, user, ctr, MAX_BUFFER, resume
        ),
    )
    return [_session_from(entry) for entry in entries]


def list_connections(conn: ServerConnection, share: str) -> list[Connection]:
    """Who has this share open.

    The ``share`` argument is required by the protocol and is not a filter we
    apply afterwards: srvsvc wants a share or a client name as the "qualifier",
    and passing nothing is not one of the options.
    """
    from samba.dcerpc import srvsvc

    def make(level: int) -> Any:
        return _ctr(
            srvsvc.NetConnInfoCtr(),
            level,
            {0: srvsvc.NetConnCtr0, 1: srvsvc.NetConnCtr1}[level](),
        )

    entries, _ = _enumerate_levels(
        conn,
        (1, 0),
        make,
        lambda pipe, ctr, resume: pipe.NetConnEnum(None, share, ctr, MAX_BUFFER, resume),
    )
    return [_connection_from(entry, share) for entry in entries]


def list_open_files(
    conn: ServerConnection, *, path: str | None = None, user: str | None = None
) -> list[OpenFile]:
    """Every open handle, optionally narrowed to a path or a user.

    Level 3 carries the path and the user, which are the two fields that make
    this list worth showing at all. Level 2 knows only the handle id, and an id
    on its own answers nothing — but a list of ids still beats an error box, so
    it is the fallback rather than a refusal.
    """
    from samba.dcerpc import srvsvc

    def make(level: int) -> Any:
        return _ctr(
            srvsvc.NetFileInfoCtr(),
            level,
            {2: srvsvc.NetFileCtr2, 3: srvsvc.NetFileCtr3}[level](),
        )

    entries, _ = _enumerate_levels(
        conn,
        (3, 2),
        make,
        lambda pipe, ctr, resume: pipe.NetFileEnum(
            None, path, user, ctr, MAX_BUFFER, resume
        ),
    )
    return [_file_from(entry) for entry in entries]


# ---------------------------------------------------------------------------
# Writing — the one call here that takes something away from somebody
# ---------------------------------------------------------------------------


def close_file(conn: ServerConnection, file_id: int) -> None:
    """Force a handle closed.

    Destructive in a way nothing else in this module is: the client holding it
    is not asked and loses whatever it had not written. The caller is expected
    to have confirmed, and the audit log records who did it and to whom.

    A handle that is already gone reports as not found rather than as success.
    The two look the same on the wire and mean different things to the person
    who clicked: one of them means somebody else got there first, and the list
    they are looking at is out of date.
    """
    pipe = conn.srvsvc
    try:
        _attempt(
            lambda: pipe.NetFileClose(None, file_id),
            lambda: pipe.NetFileClose(None, file_id, 0),
        )
    except Exception as exc:
        error = translate(exc)
        if error.status_code == 404 or error.code in ("not_found", "session_not_found"):
            raise NotFound(
                "That file is no longer open.",
                code="file_not_open",
                hint="Somebody closed it, or the listing is out of date. Refresh and look again.",
                context={"file_id": file_id},
            ) from exc
        raise error from exc

    logger.info("open file %s was force-closed", file_id)


# ---------------------------------------------------------------------------
# The srvsvc enumeration shape, in one place
# ---------------------------------------------------------------------------


def _ctr(container: Any, level: int, inner: Any) -> Any:
    """Fill in an info container for one level.

    The union member has two spellings across Samba releases — assigned by name
    (``ctr.ctr1``) or as a whole (``ctr = ...``) — and getting it wrong marshals
    a container that does not match the level beside it. Both are tried, by
    name first because that is the form Samba's own tests use.

    The count and the array are set explicitly rather than left at whatever the
    constructor produced: an unset array is not the same as an empty one to the
    marshaller.
    """
    for field, value in (("count", 0), ("array", [])):
        # A level that has no such field is not a problem to report.
        with contextlib.suppress(AttributeError, TypeError):
            setattr(inner, field, value)

    container.level = level
    try:
        setattr(container.ctr, f"ctr{level}", inner)
    except (AttributeError, TypeError):
        container.ctr = inner
    return container


def _enumerate_levels(
    conn: ServerConnection, levels: tuple[int, ...], make_ctr: Any, call: Any
) -> tuple[list[Any], int]:
    """Ask at the most informative level the server actually supports.

    A server that does not implement a level answers WERR_INVALID_LEVEL, and
    treating that as a failure put a red box above an empty table — for a
    question the server would have answered perfectly well one level down. It
    is not an error, it is a negotiation, so it is negotiated: the levels are
    tried in order and the first that answers wins. Fields the winning level
    does not carry come back as None, which the interface already renders as a
    dash.

    Only WERR_INVALID_LEVEL moves to the next candidate. Access denied, or a
    server that is simply gone, is the caller's to hear about.
    """
    last: SamfsconError | None = None

    for level in levels:
        try:
            entries = _enumerate(conn, call, lambda level=level: make_ctr(level))
        except SamfsconError as exc:
            if exc.code != "unsupported_info_level":
                raise
            logger.info("the server declined information level %d; trying the next", level)
            last = exc
            continue
        if level != levels[0]:
            logger.info("using information level %d", level)
        return entries, level

    assert last is not None  # the loop cannot end without either a return or one
    raise last


def _enumerate(conn: ServerConnection, call: Any, make_ctr: Any) -> list[Any]:
    """Run one of the Net*Enum calls, following the resume handle.

    All three share this shape: a container that says which level is wanted, a
    resume handle, and a reply carrying the next batch. Ignoring the handle
    works right up to the server with more entries than fit in one buffer, and
    then a session is simply missing from the list with no error at all.
    """
    pipe = conn.srvsvc
    found: list[Any] = []
    resume = 0

    while True:
        container = make_ctr()
        try:
            result = call(pipe, container, resume)
        except Exception as exc:
            raise translate(exc) from exc

        ctr, total, resume_out = _unpack(result)
        batch = list(getattr(ctr, "array", None) or [])
        found.extend(batch)

        if not batch or resume_out in (None, 0, resume) or len(found) >= (total or 0):
            break
        resume = resume_out

    return found


def _unpack(result: Any) -> tuple[Any, int | None, int | None]:
    if not isinstance(result, tuple):
        return getattr(result, "ctr", result), None, None

    ctr = None
    numbers: list[int] = []
    for item in result:
        if hasattr(item, "ctr"):
            ctr = item.ctr
        elif hasattr(item, "array"):
            ctr = item
        elif isinstance(item, int):
            numbers.append(item)

    return ctr, (numbers[0] if numbers else None), (numbers[1] if len(numbers) > 1 else None)


def _session_from(entry: Any) -> Session:
    from samfscon.srv.discovery import _text

    flags = int(getattr(entry, "user_flags", 0) or 0)
    return Session(
        user=_text(getattr(entry, "user", None)),
        client=_text(getattr(entry, "client", None)),
        open_files=_number(getattr(entry, "num_open", None)),
        connected_seconds=_number(getattr(entry, "time", None)),
        idle_seconds=_number(getattr(entry, "idle_time", None)),
        # SESS_GUEST — worth surfacing on its own, because a guest session is
        # usually a surprise rather than a configuration somebody remembers.
        guest=bool(flags & 0x1),
    )


def _connection_from(entry: Any, share: str) -> Connection:
    from samfscon.srv.discovery import _text

    return Connection(
        id=_number(getattr(entry, "conn_id", None)),
        share=share,
        user=_text(getattr(entry, "user", None)),
        client=_text(getattr(entry, "client", None)),
        open_files=_number(getattr(entry, "num_open", None)),
        connected_seconds=_number(getattr(entry, "conn_time", None)),
    )


def _file_from(entry: Any) -> OpenFile:
    from samfscon.srv.discovery import _text

    permissions = int(getattr(entry, "permissions", 0) or 0)
    names = []
    if permissions & PERM_FILE_READ:
        names.append("read")
    if permissions & PERM_FILE_WRITE:
        names.append("write")
    if permissions & PERM_FILE_CREATE:
        names.append("create")

    return OpenFile(
        id=_number(getattr(entry, "fid", None)),
        path=_text(getattr(entry, "path", None)),
        user=_text(getattr(entry, "user", None)),
        locks=_number(getattr(entry, "num_locks", None)),
        permissions=names,
    )


def _number(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _attempt(*attempts: Any) -> Any:
    """Run the first call shape this binding accepts."""
    errors: list[str] = []
    for attempt in attempts:
        try:
            return attempt()
        except (TypeError, AttributeError) as exc:
            # A wrong signature, or a type this Samba build does not have.
            # Both mean "not this shape"; neither came from the server.
            errors.append(f"{type(exc).__name__}: {exc}")
            continue
    raise TypeError("; ".join(errors))
