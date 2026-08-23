"""Samba's configuration, over the winreg pipe.

srvsvc knows a share's path, comment and a handful of flags. Everything else a
Samba share can be — ``vfs objects``, ``hosts allow``, ``create mask``, the
recycle bin, shadow copies, auditing — is an smb.conf option, and there is no
RPC interface for smb.conf.

There is one for the **registry**, though, and Samba can keep its configuration
there: with ``include = registry`` in the global section it reads the tree below
``HKLM\\SOFTWARE\\Samba\\smbconf``, one key per share, one value per option.
That is what ``net conf`` and ``net rpc conf`` edit, and it is what this module
edits — the same store, through the same interface, so a share SAMFSCON writes
is one ``net conf list`` shows.

Two consequences worth stating plainly, because they are the ones that surprise
people:

* A server **without** registry configuration is fully readable and not
  writable. SAMFSCON says so rather than failing obscurely
  (:func:`samfscon.srv.diagnostics.require_share_management`).
* Options written here take effect on the server's next configuration reload,
  which for Samba is within a minute and immediate for new connections. This
  module does not restart anything — it has no way to, and pretending otherwise
  would be the one place a management console must not guess.

The exact call signatures of ``samba.dcerpc.winreg`` have varied across Samba
releases. Every call below therefore goes through a small helper that tries the
known shapes in order, the same treatment ``set_named_ccache`` gets in
:mod:`samfscon.auth.credentials`.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator
from typing import Any

from samfscon.core.errors import NotFound, SamfsconError, translate
from samfscon.srv.connection import ServerConnection

logger = logging.getLogger(__name__)

SMBCONF_KEY = "SOFTWARE\\Samba\\smbconf"

# winreg access masks (MS-RRP 2.2.2).
KEY_QUERY_VALUE = 0x00000001
KEY_SET_VALUE = 0x00000002
KEY_CREATE_SUB_KEY = 0x00000004
KEY_ENUMERATE_SUB_KEYS = 0x00000008
DELETE = 0x00010000
READ_CONTROL = 0x00020000

KEY_READ = READ_CONTROL | KEY_QUERY_VALUE | KEY_ENUMERATE_SUB_KEYS
KEY_WRITE = READ_CONTROL | KEY_SET_VALUE | KEY_CREATE_SUB_KEY | DELETE

# Registry value types (MS-RRP 2.2.9). Samba stores every smb.conf option as a
# string, including the numeric ones — the parser on the other side is the
# smb.conf parser, which takes text.
REG_SZ = 1
REG_MULTI_SZ = 7

# The section name Samba uses for the [global] block inside the store.
GLOBAL_SECTION = "global"


# ---------------------------------------------------------------------------
# Opening the store
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def open_smbconf(conn: ServerConnection, *, write: bool = False) -> Iterator[Any]:
    """Open ``HKLM\\SOFTWARE\\Samba\\smbconf``.

    Yields the key handle and closes it afterwards. A handle left open holds a
    reference on the server for as long as the pipe lives, which for a session
    is hours.
    """
    pipe = conn.winreg
    access = KEY_WRITE | KEY_READ if write else KEY_READ

    hive = _call(
        pipe,
        "OpenHKLM",
        (lambda: pipe.OpenHKLM(None, access),),
        what="the registry",
    )
    key = None
    try:
        key = _open_key(pipe, hive, SMBCONF_KEY, access)
        yield key
    finally:
        for handle in (key, hive):
            if handle is not None:
                with contextlib.suppress(Exception):
                    pipe.CloseKey(handle)


@contextlib.contextmanager
def open_section(
    conn: ServerConnection, section: str, *, write: bool = False, create: bool = False
) -> Iterator[Any]:
    """Open one share's key — or ``global`` — inside the store."""
    pipe = conn.winreg
    access = KEY_WRITE | KEY_READ if write else KEY_READ

    with open_smbconf(conn, write=write) as root:
        key = None
        try:
            if create:
                key = _create_key(pipe, root, section, access)
            else:
                key = _open_key(pipe, root, section, access)
            yield key
        finally:
            if key is not None:
                with contextlib.suppress(Exception):
                    pipe.CloseKey(key)


# ---------------------------------------------------------------------------
# Reading and writing options
# ---------------------------------------------------------------------------


def read_options(conn: ServerConnection, section: str) -> dict[str, str]:
    """Every option stored for *section*, as smb.conf would spell them.

    A section that does not exist is not an error: a share defined in the text
    smb.conf has no registry key, and asking about its options should report
    "none stored here", not "no such share". Whether the share exists at all is
    srvsvc's question, and it has already been asked by the time this runs.
    """
    pipe = conn.winreg
    try:
        with open_section(conn, section) as key:
            return dict(_enumerate_values(pipe, key))
    except NotFound:
        return {}


def read_all(conn: ServerConnection) -> dict[str, dict[str, str]]:
    """Every section's values, in one pass over the store.

    :func:`read_options` opens the hive, opens the smbconf key and opens the
    section, once per call. Reading a whole server through it is three opens per
    section for data ``net conf list`` prints in one go. This holds the hive and
    the smbconf key open and opens each section under them once — N + 2 rather
    than N x 3. MS-RRP has no call that enumerates a subkey's values from the
    parent handle, so the per-section open stays; it is the repeated hive walk
    that goes.

    A section whose values could not be read is **absent from the result**,
    never present and empty. Those two would be indistinguishable to a caller,
    and the difference is the difference between "this share stores no options"
    and "we could not find out what it stores" — the first is a fact about the
    server and the second is a fact about this session.

    Names come back exactly as the registry spells them, ``global`` included.
    A caller comparing them against share names has to exclude it: see
    :func:`samfscon.srv.shares.registry_shares_served` for what happens when
    one does not.
    """
    pipe = conn.winreg
    sections: dict[str, dict[str, str]] = {}

    with open_smbconf(conn) as root:
        for name in _enumerate_keys(pipe, root):
            key = None
            try:
                key = _open_key(pipe, root, name, KEY_READ)
                sections[name] = dict(_enumerate_values(pipe, key))
            except Exception:  # one bad section must not end the sweep
                logger.warning(
                    "the registry section %s could not be read; it is reported as "
                    "unreadable rather than as empty",
                    name,
                )
                logger.debug("section %s failed", name, exc_info=True)
            finally:
                if key is not None:
                    with contextlib.suppress(Exception):
                        pipe.CloseKey(key)

    return sections


def read_sections(conn: ServerConnection) -> list[str]:
    """The share names that have registry configuration."""
    pipe = conn.winreg
    with open_smbconf(conn) as root:
        return list(_enumerate_keys(pipe, root))


def write_options(
    conn: ServerConnection, section: str, options: dict[str, str | None]
) -> dict[str, dict[str, str | None]]:
    """Set or remove options on *section*.

    A value of ``None`` deletes the option, which is how it goes back to the
    server's default — deliberately different from setting it to an empty
    string, which is a value the smb.conf parser will happily honour.

    Returns the applied changes with their previous values, ready for the audit
    log. Options whose value is already what was asked for are left alone and
    do not appear: a no-op write would still count as a change in the trail.
    """
    pipe = conn.winreg
    applied: dict[str, dict[str, str | None]] = {}

    with open_section(conn, section, write=True, create=True) as key:
        current = dict(_enumerate_values(pipe, key))

        for name, value in options.items():
            option = normalise_option(name)
            old = current.get(option)

            if value is None:
                if old is None:
                    continue
                _delete_value(pipe, key, option)
                applied[option] = {"old": old, "new": None}
                continue

            if old == value:
                continue
            _set_value(pipe, key, option, value)
            applied[option] = {"old": old, "new": value}

    return applied


def delete_section(conn: ServerConnection, section: str) -> None:
    """Remove a share's whole key.

    Called when a share is deleted. srvsvc's NetShareDel removes the share
    itself; without this, its options would linger and be inherited by the next
    share created under the same name — which is the kind of surprise that gets
    blamed on the wrong thing entirely.
    """
    pipe = conn.winreg
    with open_smbconf(conn, write=True) as root:
        try:
            _call(
                pipe,
                "DeleteKey",
                (lambda: pipe.DeleteKey(root, _string(section)),),
                what=f"the configuration of {section}",
            )
        except NotFound:
            return  # nothing stored for it, which is a fine outcome


def normalise_option(name: str) -> str:
    """smb.conf option names as Samba writes them: lower case, spaces kept.

    ``vfs objects`` and ``vfs_objects`` are the same option to the parser, and
    people type both. Normalising here means the catalogue, the audit log and
    the comparison against the current value all agree on one spelling.
    """
    return name.strip().lower().replace("_", " ")


# ---------------------------------------------------------------------------
# The binding, isolated
# ---------------------------------------------------------------------------


def _string(value: str) -> Any:
    """A winreg.String, which is what every name argument wants.

    Passing a bare ``str`` works on some builds and raises a TypeError on
    others; wrapping works where the type exists. Where it does not, the bare
    string is the only thing left to try — and a call that then fails says so
    through the candidate chain rather than through an AttributeError raised
    while assembling an argument.
    """
    from samba.dcerpc import winreg

    try:
        name = winreg.String()
    except AttributeError:  # pragma: no cover - depends on the build
        return value
    name.name = value
    return name


def _open_key(pipe: Any, parent: Any, path: str, access: int) -> Any:
    return _call(
        pipe,
        "OpenKey",
        (
            lambda: pipe.OpenKey(parent, _string(path), 0, access),
            lambda: pipe.OpenKey(parent, _string(path), access),
        ),
        what=path,
    )


def _create_key(pipe: Any, parent: Any, path: str, access: int) -> Any:
    """Create a key, or open the one that is already there.

    ``action_taken`` is [in,out,unique] in the IDL, so None is a legal value and
    the server simply does not report which of the two it did — which is fine,
    because either outcome is the one wanted. The first version of this tried to
    construct a ``winreg.CreateAction`` to receive it; that type does not exist
    in every build, and the AttributeError took the whole call down.
    """
    result = _call(
        pipe,
        "CreateKey",
        (
            lambda: pipe.CreateKey(parent, _string(path), _string(""), 0, access, None, None),
            # A build that wants the field present rather than absent.
            lambda: pipe.CreateKey(parent, _string(path), _string(""), 0, access, None, 0),
        ),
        what=path,
    )
    # Some builds return (handle, action_taken), others just the handle.
    if isinstance(result, tuple):
        return result[0]
    return result


# How much room to give EnumValue for one value's data. smb.conf options are
# short — the longest realistic one is a `veto files` list — and a value that
# does not fit is reported rather than silently truncated.
VALUE_BUFFER = 8192

# And for a name. Registry key and value names are short; this is generous.
NAME_BUFFER = 1024


def _name_buffer(kind: str) -> Any:
    """An empty name buffer for one of the enumeration calls to fill.

    The two calls want different types — ``winreg_StringBuf`` for EnumKey,
    ``winreg_ValNameBuf`` for EnumValue — and handing over the wrong one is a
    TypeError before the call leaves, which is what stopped every value read.

    All three members are set. ``size`` alone is not enough: the server was
    answering WERR_INVALID_PARAMETER for a buffer whose ``name`` and ``length``
    were whatever the constructor left behind, which is the same "unset is not
    empty" lesson the srvsvc containers taught twice.
    """
    from samba.dcerpc import winreg

    for attribute in ("ValNameBuf", "StringBuf") if kind == "value" else ("StringBuf",):
        factory = getattr(winreg, attribute, None)
        if factory is None:
            continue
        buffer = factory()
        with contextlib.suppress(AttributeError, TypeError):
            buffer.name = ""
        with contextlib.suppress(AttributeError, TypeError):
            buffer.size = NAME_BUFFER
        with contextlib.suppress(AttributeError, TypeError):
            buffer.length = 0
        return buffer

    raise SamfsconError(
        "This Samba build exposes no registry name buffer type.",
        code="winreg_unsupported",
        detail=f"neither winreg.ValNameBuf nor winreg.StringBuf for a {kind} name",
    )


def _enumerate_values(pipe: Any, key: Any) -> list[tuple[str, str]]:
    """Every value under *key*, as (name, text).

    ``EnumValue`` is an index walk that ends with WERR_NO_MORE_ITEMS, and it
    fills buffers the caller provides: passing None for the data, its size and
    its length asks the server for a value and gives it nowhere to put one.

    Which shape the bindings want has moved between releases, so the candidates
    are tried on the first index and the one that answers is used for the rest —
    re-deciding on every value would turn a walk of ten into thirty calls.

    The end of the walk is one specific status. Everything else is a failure and
    is logged: this loop used to treat any exception as "that was all", which
    reported a key whose values could not be read as a key with no values.
    """
    values: list[tuple[str, str]] = []
    shape: Any = None
    index = 0

    while index <= 4096:
        name = _name_buffer("value")
        candidates = _enum_value_shapes(pipe, key, index, name)
        try:
            if shape is None:
                result, shape = _first_shape(candidates)
            else:
                result = candidates[shape]()
        except Exception as exc:  # noqa: BLE001 — one bad key must not end a listing
            if _is_walk_end(exc):
                break
            # With the detail. "No known form was accepted" on its own says
            # nothing; the argument counts inside it name the mismatch, and
            # that is the whole reason the chain records them.
            logger.warning(
                "reading registry value %d failed (%s); detail: %s; "
                "the ones already read stand",
                index,
                exc,
                getattr(exc, "detail", None) or "-",
            )
            break

        entry = _decode_value(result, name)
        if entry is not None:
            values.append(entry)
        index += 1

    if index > 4096:  # pragma: no cover — a runaway server, not a real case
        logger.warning("stopping registry enumeration after 4096 values")
    return values


class _WalkFinished(Exception):
    """WERR_NO_MORE_ITEMS: the documented end, not a failure."""


def _is_walk_end(exc: BaseException) -> bool:
    """Whether this is the enumeration saying "that was all".

    Checked in both places a walk can end, which it was not: the shape is
    decided on the first index and reused, so from the second index onwards the
    ordinary end of every enumeration went to the failure handler and was logged
    as a warning. Five values read perfectly and one warning per listing to show
    for it.
    """
    return isinstance(exc, _WalkFinished) or "NO_MORE_ITEMS" in str(exc).upper()


def _enum_value_shapes(pipe: Any, key: Any, index: int, name: Any) -> list[Any]:
    """The call shapes for one EnumValue, most likely first.

    The IDL declares seven in/out parameters, and `size` and `length` are
    in/out in their own right rather than only being the array's bounds — so
    seven is the expected count. The shorter forms are here because that
    expectation has been wrong twice in this file already, and one extra
    candidate costs a TypeError while one extra round of testing costs a day.
    """
    return [
        lambda: pipe.EnumValue(key, index, name, 0, [], VALUE_BUFFER, 0),
        lambda: pipe.EnumValue(key, index, name, 0, b"", VALUE_BUFFER, 0),
        lambda: pipe.EnumValue(key, index, name, None, None, VALUE_BUFFER, 0),
        lambda: pipe.EnumValue(key, index, name, None, None, None, None),
        # Counts other than seven, in case one of the trailing pair is derived.
        lambda: pipe.EnumValue(key, index, name, 0, [], VALUE_BUFFER),
        lambda: pipe.EnumValue(key, index, name, 0, []),
        lambda: pipe.EnumValue(key, index, name),
    ]


def _first_shape(candidates: list[Any]) -> tuple[Any, int]:
    """Run the first shape that is accepted, and say which it was."""
    errors: list[str] = []
    for position, candidate in enumerate(candidates):
        try:
            return candidate(), position
        except (TypeError, AttributeError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            continue
        except Exception as exc:
            # From the server. An empty key answers the very first index this
            # way, which is the ordinary end of a walk that had nothing in it.
            if "NO_MORE_ITEMS" in str(exc).upper():
                raise _WalkFinished from exc
            raise

    raise SamfsconError(
        "No known form of EnumValue was accepted.",
        code="winreg_unsupported",
        detail="; ".join(errors),
    )


def _decode_value(result: Any, name: Any) -> tuple[str, str] | None:
    """Pull (name, text) out of whatever shape EnumValue returned."""
    if not isinstance(result, tuple):
        return None

    key_name = getattr(name, "name", None) or (result[0] if result else None)
    if hasattr(key_name, "name"):
        key_name = key_name.name
    if not key_name:
        return None

    # The data is somewhere in the tail of the tuple, as bytes or as a list of
    # byte values, and its type code sits beside it.
    data = None
    for item in result:
        # Bytes on most builds, a list of byte values on some — the same data,
        # two shapes, and only one of them survives a version upgrade.
        if isinstance(item, (bytes, bytearray)) or (
            isinstance(item, list) and item and all(isinstance(b, int) for b in item)
        ):
            data = bytes(item)
    if data is None:
        return str(key_name), ""

    return str(key_name), _decode_text(data)


def _decode_text(data: bytes) -> str:
    """Registry strings are UTF-16LE with a trailing NUL."""
    try:
        text = data.decode("utf-16-le")
    except UnicodeDecodeError:
        text = data.decode("utf-8", "replace")
    return text.rstrip("\x00")


def _encode_text(value: str) -> bytes:
    return (value + "\x00").encode("utf-16-le")


def _set_value(pipe: Any, key: Any, name: str, value: str) -> None:
    """Write one value.

    The IDL declares five parameters, and the binding takes four: ``size`` is
    ``size_is(size)`` for the data array, and pidl derives it from the array
    rather than accepting it. That is the same rule that made every LSA lookup
    fail — ``domains`` there was ``[out]`` and equally not an argument — and it
    is worth stating once as a rule rather than rediscovering per call: **a
    parameter the wire format can work out for itself is not in the python
    signature.**

    The length-bearing form is kept last for a build that disagrees.
    """
    data = _encode_text(value)
    _call(
        pipe,
        "SetValue",
        (
            lambda: pipe.SetValue(key, _string(name), REG_SZ, data),
            lambda: pipe.SetValue(key, _string(name), REG_SZ, list(data)),
            lambda: pipe.SetValue(key, _string(name), REG_SZ, data, len(data)),
        ),
        what=name,
    )


def _delete_value(pipe: Any, key: Any, name: str) -> None:
    _call(
        pipe,
        "DeleteValue",
        (lambda: pipe.DeleteValue(key, _string(name)),),
        what=name,
    )


def _enumerate_keys(pipe: Any, key: Any) -> list[str]:
    """The subkeys of *key*, which for the smbconf store are the share names.

    ``keyclass`` and ``last_changed_time`` are [in,out,unique], so NULL is legal
    for both — but a server answering WERR_INVALID_PARAMETER to that is a server
    that wants them present, so both forms are offered.
    """
    names: list[str] = []
    shape: Any = None
    index = 0

    while True:
        name = _name_buffer("key")
        # Bound as defaults: a lambda that closes over the loop variables
        # reads them at call time, and these are called on later iterations
        # through the remembered shape.
        candidates = [
            lambda n=name, i=index: pipe.EnumKey(key, i, n, _name_buffer("key"), 0),
            lambda n=name, i=index: pipe.EnumKey(key, i, n, None, None),
            lambda n=name, i=index: pipe.EnumKey(key, i, n, _name_buffer("key"), None),
        ]

        try:
            if shape is None:
                result, shape = _first_shape(candidates)
            else:
                result = candidates[shape]()
        except Exception as exc:  # noqa: BLE001 — one bad key must not end a listing
            if _is_walk_end(exc):
                break
            logger.warning(
                "reading registry key %d failed (%s); detail: %s; "
                "the ones already read stand",
                index,
                exc,
                getattr(exc, "detail", None) or "-",
            )
            break

        found = getattr(name, "name", None)
        if not found and isinstance(result, tuple) and result:
            found = getattr(result[0], "name", result[0])
        if found:
            names.append(str(found))
        index += 1
        if index > 4096:  # pragma: no cover
            logger.warning("stopping registry key enumeration after 4096 keys")
            break
    return names


def _call(pipe: Any, operation: str, attempts: tuple[Any, ...], *, what: str) -> Any:
    """Run the first call shape this binding accepts.

    A ``TypeError`` means the signature was wrong, and an ``AttributeError``
    means a type or method this build does not have — both are "not this shape,
    try the next". Anything else came from the server and is translated: trying
    another argument order against a server that already said "access denied"
    would only ask it twice.

    The AttributeError case is here because it was not, and a
    ``winreg.CreateAction`` that exists in some builds and not others took every
    share creation down with an "unexpected error" instead of moving to the
    candidate beside it.
    """
    errors: list[str] = []
    for attempt in attempts:
        try:
            return attempt()
        except (TypeError, AttributeError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            continue
        except Exception as exc:
            raise translate(exc) from exc

    raise SamfsconError(
        f"No known form of the registry call {operation} was accepted.",
        code="winreg_unsupported",
        detail="; ".join(errors),
        hint=(
            "Every shape SAMFSCON knows for this call was refused by the "
            "bindings before it reached the server. The detail lists what each "
            "one said; the argument counts in it name the mismatch."
        ),
        context={"target": what},
    )
