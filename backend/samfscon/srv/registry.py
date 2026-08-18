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
    others; wrapping always works.
    """
    from samba.dcerpc import winreg

    name = winreg.String()
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
    from samba.dcerpc import winreg

    def _with_action():
        action = winreg.CreateAction()
        return pipe.CreateKey(parent, _string(path), _string(""), 0, access, None, action)

    result = _call(
        pipe,
        "CreateKey",
        (
            _with_action,
            lambda: pipe.CreateKey(parent, _string(path), _string(""), 0, access, None, None),
        ),
        what=path,
    )
    # Some builds return (handle, action), others just the handle.
    if isinstance(result, tuple):
        return result[0]
    return result


def _enumerate_values(pipe: Any, key: Any) -> list[tuple[str, str]]:
    """Every value under *key*, as (name, text).

    ``EnumValue`` is an index walk that ends with WERR_NO_MORE_ITEMS, and the
    buffer sizes it wants are arguments rather than something it works out — a
    detail that has moved between Samba releases more than once, which is why
    the shapes are tried rather than assumed.
    """
    from samba.dcerpc import winreg

    values: list[tuple[str, str]] = []
    index = 0
    while True:
        name = winreg.StringBuf()
        name.size = 1024
        try:
            result = pipe.EnumValue(key, index, name, None, None, None, None)
        except Exception:  # noqa: BLE001 — the documented end of the walk
            break

        entry = _decode_value(result, name)
        if entry is not None:
            values.append(entry)
        index += 1
        if index > 4096:  # pragma: no cover — a runaway server, not a real case
            logger.warning("stopping registry enumeration after 4096 values")
            break
    return values


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
    data = _encode_text(value)
    _call(
        pipe,
        "SetValue",
        (
            lambda: pipe.SetValue(key, _string(name), REG_SZ, data, len(data)),
            lambda: pipe.SetValue(key, _string(name), REG_SZ, list(data), len(data)),
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
    from samba.dcerpc import winreg

    names: list[str] = []
    index = 0
    while True:
        name = winreg.StringBuf()
        name.size = 1024
        try:
            result = pipe.EnumKey(key, index, name, None, None)
        except Exception:  # noqa: BLE001 — the documented end of the walk
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

    A ``TypeError`` means the signature was wrong and the next shape is worth
    trying. Anything else came from the server and is translated — trying
    another argument order against a server that already said "access denied"
    would only ask it twice.
    """
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
        f"The registry call {operation} is not supported by this Samba build.",
        code="winreg_unsupported",
        detail="; ".join(errors),
        context={"target": what},
    )
