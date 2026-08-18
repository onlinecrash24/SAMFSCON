"""Browsing a share, over SMB.

Everything else in SAMFSCON speaks RPC. This module is the exception: the
contents of a share are files, and no RPC interface lists them.

The share is opened with the signed-in administrator's credentials, the same
ones every other call uses — so file permissions apply exactly as they would to
that person at any other client, and nothing here runs with rights the
administrator does not have. A directory they may not read is a directory this
console cannot list either, which is the correct behaviour and not a limitation
to work around.

Paths inside this module are share-relative and use backslashes, because that is
what the SMB client expects: ``Projects\\2026\\budget.xlsx``. The empty string
is the share root, and it is a valid path — it is the one the share's
permissions tab edits.

The mechanics here are lifted from SAMADCON's SYSVOL module, which is already
hardened against the two cases that catch people out: files Windows marks
hidden, which a plain listing silently omits, and files somebody else has open,
which refuse a plain overwrite.
"""

from __future__ import annotations

import logging
from typing import Any

from samfscon.core.errors import InvalidRequest, translate
from samfscon.srv.connection import ServerConnection

logger = logging.getLogger(__name__)

# What a directory listing must ask for. Windows marks a good deal hidden —
# desktop.ini, Thumbs.db, and anything a user chose to hide — and a listing that
# omits them reports a directory as emptier than it is. Worse, the permissions
# view then cannot reach a file that is genuinely there. The same mask Samba's
# own tooling passes: read-only, hidden, system, directory, archive.
LISTING_ATTRIBUTES = 0x1 | 0x2 | 0x4 | 0x10 | 0x20

FILE_ATTRIBUTE_DIRECTORY = 0x10
FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_READONLY = 0x1
FILE_ATTRIBUTE_SYSTEM = 0x4

# A listing of a directory with tens of thousands of entries is not a listing
# anyone reads; it is a request that times out. Truncated with a flag, the way
# SAMADCON bounds a directory search, so the interface can say so.
MAX_ENTRIES = 2000


def normalise(path: str | None) -> str:
    """Turn what the API received into what SMB wants.

    Rejects the two forms that would leave the share: an absolute path and any
    ``..`` component. The server would refuse them too, but refusing here means
    the answer names the problem instead of returning a status that reads like
    a permission error.
    """
    text = (path or "").strip().replace("/", "\\").strip("\\")
    if not text:
        return ""

    parts = [part for part in text.split("\\") if part and part != "."]
    if any(part == ".." for part in parts):
        raise InvalidRequest(
            "A path may not step outside its share.",
            code="path_escapes_share",
            context={"path": path},
        )
    return "\\".join(parts)


def join(*parts: str) -> str:
    return "\\".join(part.strip("\\") for part in parts if part)


def listdir(conn: ServerConnection, share: str, path: str = "") -> dict[str, Any]:
    """Entries directly below *path*, without ``.`` and ``..``.

    Directories first, then files, each alphabetically — the order every file
    manager uses, because it is the order people scan in.
    """
    relative = normalise(path)
    tree = conn.tree(share)

    try:
        raw = _list(tree, relative)
    except Exception as exc:
        raise translate(exc) from exc

    entries: list[dict[str, Any]] = []
    for entry in raw:
        name = entry["name"] if isinstance(entry, dict) else getattr(entry, "name", None)
        if name in (None, ".", ".."):
            continue

        attributes = entry.get("attrib", 0) if isinstance(entry, dict) else 0
        entries.append(
            {
                "name": name,
                "path": join(relative, str(name)),
                "is_directory": bool(attributes & FILE_ATTRIBUTE_DIRECTORY),
                "size": entry.get("size", 0) if isinstance(entry, dict) else 0,
                "modified": _timestamp(entry),
                # Shown because they explain behaviour people otherwise blame
                # on permissions: a read-only file refuses a write that the
                # ACL allows, and a hidden one is missing from Explorer.
                "hidden": bool(attributes & FILE_ATTRIBUTE_HIDDEN),
                "read_only": bool(attributes & FILE_ATTRIBUTE_READONLY),
                "system": bool(attributes & FILE_ATTRIBUTE_SYSTEM),
                "attributes": attributes,
            }
        )

    truncated = len(entries) > MAX_ENTRIES
    if truncated:
        logger.info("listing of %s\\%s truncated at %d entries", share, relative, MAX_ENTRIES)
        entries = entries[:MAX_ENTRIES]

    entries.sort(key=lambda item: (not item["is_directory"], str(item["name"]).lower()))
    return {"share": share, "path": relative, "entries": entries, "truncated": truncated}


def is_directory(conn: ServerConnection, share: str, path: str) -> bool:
    """Whether *path* is a directory.

    ``chkpath`` answers exactly that: on a file it fails with
    NT_STATUS_NOT_A_DIRECTORY. It therefore cannot double as an existence
    check, which is why nothing here uses it as one.
    """
    relative = normalise(path)
    if not relative:
        return True  # the share root always is

    try:
        return bool(conn.tree(share).chkpath(relative))
    except Exception:  # noqa: BLE001 — missing, a file, or unreadable: none is a directory
        return False


def mkdir(conn: ServerConnection, share: str, path: str) -> str:
    """Create one directory inside a share.

    The one creation SAMFSCON can perform on a server's file system, and it is
    available precisely because it happens *inside* an existing share — which
    is also why a new share's path has to exist beforehand.
    """
    relative = normalise(path)
    if not relative:
        raise InvalidRequest("No directory name was given.", code="missing_path")

    try:
        conn.tree(share).mkdir(relative)
    except Exception as exc:
        raise translate(exc) from exc
    return relative


def _list(tree: Any, path: str) -> list[Any]:
    """Ask for hidden and system entries too, on whichever binding this is.

    An older binding without the keyword falls back to the plain call: its
    default may already include them, and either way that is better than not
    listing at all.
    """
    try:
        return list(tree.list(path, attribs=LISTING_ATTRIBUTES))
    except TypeError:
        return list(tree.list(path))


def _timestamp(entry: Any) -> Any:
    """Whatever timestamp this build offers, under one name."""
    if not isinstance(entry, dict):
        return None
    for field in ("mtime", "write_time", "change_time"):
        if entry.get(field):
            return entry[field]
    return None
