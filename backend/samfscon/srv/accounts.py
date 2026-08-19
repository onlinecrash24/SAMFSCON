"""Local users and groups, over SAMR.

The accounts a **standalone** server owns — the ones `pdbedit -L` lists and
`smbpasswd` changes. On a domain member this module has nothing to do: its
accounts come from the domain, are managed there, and the interface says so
rather than offering an empty list.

SAMR is a handle protocol, and that shapes everything here. Nothing is addressed
by name: connect to the server, open the domain, look a name up to get its RID,
open the object by RID, act, close. Every call below therefore acquires handles
and gives them back — a handle left open holds a reference on the server for as
long as the pipe lives, which for a session is hours.

**Passwords go over the wire encrypted by the session key**, which is what
``SetUserInfo`` level 24 does with the SMB3 session already established. They are
never written to the audit log, never logged at any level, and the request
schema is the only place one appears.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from samfscon.core.errors import Conflict, InvalidRequest, NotFound, SamfsconError, translate
from samfscon.srv.connection import ServerConnection

logger = logging.getLogger(__name__)

# ACB flags (MS-SAMR 2.2.1.12), the ones a console actually shows.
ACB_DISABLED = 0x00000001
ACB_HOMDIRREQ = 0x00000002
ACB_PWNOTREQ = 0x00000004
ACB_NORMAL = 0x00000010
ACB_DONT_EXPIRE_PASSWD = 0x00000200
ACB_AUTOLOCK = 0x00000400

# SAMR object types for the enumeration calls.
ACCT_USER = 0x00000010
ACCT_ALIAS = 0x00000004

# SEC_FLAG_MAXIMUM_ALLOWED — ask for everything the account may have, and let
# the server decide. Asking for a fixed mask means guessing which rights this
# particular operation needs, and guessing high turns a read into a refusal.
MAXIMUM_ALLOWED = 0x02000000

# The two accounts a standalone Samba server owns. Listed, never offered for
# deletion: removing the guest account or the built-in administrator is not a
# thing a console should make one click away.
PROTECTED_ACCOUNTS = frozenset({"root", "nobody", "guest", "administrator"})


@dataclass
class Account:
    """One local user."""

    name: str
    rid: int
    sid: str | None
    full_name: str | None
    description: str | None
    flags: int

    @property
    def disabled(self) -> bool:
        return bool(self.flags & ACB_DISABLED)

    @property
    def locked_out(self) -> bool:
        return bool(self.flags & ACB_AUTOLOCK)

    @property
    def password_never_expires(self) -> bool:
        return bool(self.flags & ACB_DONT_EXPIRE_PASSWD)

    @property
    def protected(self) -> bool:
        return self.name.lower() in PROTECTED_ACCOUNTS

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "rid": self.rid,
            "sid": self.sid,
            "full_name": self.full_name,
            "description": self.description,
            "disabled": self.disabled,
            "locked_out": self.locked_out,
            "password_never_expires": self.password_never_expires,
            "protected": self.protected,
        }


@dataclass
class Group:
    """One local group — an alias, in SAMR's vocabulary."""

    name: str
    rid: int
    sid: str | None
    description: str | None
    members: list[str]

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "rid": self.rid,
            "sid": self.sid,
            "description": self.description,
            "members": list(self.members),
        }


# ---------------------------------------------------------------------------
# The handle dance, in one place
# ---------------------------------------------------------------------------


class _Domain:
    """An open handle to the server's account domain, and its SID.

    A context manager because SAMR handles have to be given back, and because
    every operation in this module needs the same two — opening them once per
    call and closing them afterwards keeps that from being remembered.
    """

    def __init__(self, conn: ServerConnection) -> None:
        self.conn = conn
        self.pipe = conn.samr
        self.handle: Any = None
        self.domain: Any = None
        self.sid: Any = None

    def __enter__(self) -> _Domain:
        try:
            self.handle = _attempt(
                lambda: self.pipe.Connect2(None, MAXIMUM_ALLOWED),
                lambda: self.pipe.Connect5(None, MAXIMUM_ALLOWED, 1, None),
            )
            # The server's own account domain, not BUILTIN: that is where a
            # standalone server's users live. EnumDomains returns both, and
            # LookupDomain by the server's NetBIOS name picks the right one.
            name = self.conn.info.name
            self.sid = _attempt(lambda: self.pipe.LookupDomain(self.handle, _string(name)))
            self.domain = _attempt(
                lambda: self.pipe.OpenDomain(self.handle, MAXIMUM_ALLOWED, self.sid)
            )
        except Exception as exc:
            self.__exit__(None, None, None)
            raise translate(exc) from exc
        return self

    def __exit__(self, *_: Any) -> None:
        for handle in (self.domain, self.handle):
            if handle is not None:
                try:
                    self.pipe.Close(handle)
                except Exception:  # teardown must not raise
                    logger.debug("closing a SAMR handle failed", exc_info=True)
        self.domain = None
        self.handle = None

    def sid_for(self, rid: int) -> str | None:
        try:
            return f"{self.sid}-{rid}"
        except Exception:  # noqa: BLE001
            return None

    def rid_of(self, name: str) -> int:
        """The RID behind a name, or a NotFound naming what was looked for."""
        try:
            result = _attempt(lambda: self.pipe.LookupNames(self.domain, [_string(name)]))
        except Exception as exc:
            error = translate(exc)
            if error.status_code == 404 or error.code in ("not_found", "user_not_found"):
                raise NotFound(
                    "No such account on this server.",
                    code="user_not_found",
                    context={"name": name},
                ) from exc
            raise error from exc

        rids = _ids(result)
        if not rids:
            raise NotFound(
                "No such account on this server.",
                code="user_not_found",
                context={"name": name},
            )
        return rids[0]


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def list_users(conn: ServerConnection) -> list[Account]:
    """Every local user account."""
    _require_standalone(conn)

    with _Domain(conn) as domain:
        entries = _enumerate(
            lambda resume: domain.pipe.EnumDomainUsers(
                domain.domain, resume, ACCT_NORMAL_FILTER, -1
            )
        )
        accounts = []
        for rid, name in entries:
            accounts.append(_read_user(domain, rid, name))

    accounts.sort(key=lambda item: item.name.lower())
    return accounts


def list_groups(conn: ServerConnection) -> list[Group]:
    """Every local group, with its members' SIDs."""
    _require_standalone(conn)

    with _Domain(conn) as domain:
        entries = _enumerate(
            lambda resume: domain.pipe.EnumDomainAliases(domain.domain, resume, -1)
        )
        groups = []
        for rid, name in entries:
            groups.append(_read_group(domain, rid, name))

    groups.sort(key=lambda item: item.name.lower())
    return groups


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def create_user(
    conn: ServerConnection,
    *,
    name: str,
    password: str,
    full_name: str | None = None,
    description: str | None = None,
    disabled: bool = False,
    password_never_expires: bool = False,
) -> dict[str, Any]:
    """Create an account, set its password, then apply its flags.

    That order is not arbitrary. ``CreateUser2`` makes the account **disabled
    and with no password**, which is the only safe intermediate state: an
    account that existed for a moment with an empty password and login enabled
    is an account somebody could have used. Enabling it is the last step, and
    only if it was asked for.

    A failure after creation rolls the account back rather than leaving that
    half-made state behind.
    """
    _require_standalone(conn)

    with _Domain(conn) as domain:
        try:
            result = _attempt(
                lambda: domain.pipe.CreateUser2(
                    domain.domain, _string(name), ACB_NORMAL, MAXIMUM_ALLOWED
                )
            )
        except Exception as exc:
            error = translate(exc)
            if error.code == "already_exists":
                raise Conflict(
                    "An account with this name already exists.",
                    code="already_exists",
                    context={"name": name},
                ) from exc
            raise error from exc

        user, rid = _user_and_rid(result)

        try:
            _set_password(domain.pipe, user, password)

            flags = ACB_NORMAL
            if disabled:
                flags |= ACB_DISABLED
            if password_never_expires:
                flags |= ACB_DONT_EXPIRE_PASSWD
            _set_flags(domain.pipe, user, flags)

            if full_name or description:
                _set_text(domain.pipe, user, full_name=full_name, description=description)
        except Exception as exc:
            logger.warning("setting up the new account %s failed; removing it again", name)
            try:
                domain.pipe.DeleteUser(user)
            except Exception:  # noqa: BLE001 — the original failure is the one to report
                logger.error(
                    "could not roll back the account %s — it exists half-configured", name
                )
            raise translate(exc) from exc
        finally:
            _close(domain.pipe, user)

    logger.info("local account created: %s", name)
    return {"name": name, "rid": rid, "disabled": disabled}


def update_user(
    conn: ServerConnection,
    name: str,
    *,
    full_name: str | None = None,
    description: str | None = None,
    disabled: bool | None = None,
    password_never_expires: bool | None = None,
) -> dict[str, Any]:
    """Change an account. Only what was sent is changed."""
    _require_standalone(conn)
    changes: dict[str, Any] = {}

    with _Domain(conn) as domain:
        rid = domain.rid_of(name)
        current = _read_user(domain, rid, name)
        user = _open_user(domain, rid)

        try:
            if full_name is not None or description is not None:
                _set_text(domain.pipe, user, full_name=full_name, description=description)
                if full_name is not None:
                    changes["full_name"] = {"old": current.full_name, "new": full_name}
                if description is not None:
                    changes["description"] = {"old": current.description, "new": description}

            if disabled is not None or password_never_expires is not None:
                flags = current.flags
                if disabled is not None:
                    flags = flags | ACB_DISABLED if disabled else flags & ~ACB_DISABLED
                    changes["disabled"] = {"old": current.disabled, "new": disabled}
                if password_never_expires is not None:
                    flags = (
                        flags | ACB_DONT_EXPIRE_PASSWD
                        if password_never_expires
                        else flags & ~ACB_DONT_EXPIRE_PASSWD
                    )
                    changes["password_never_expires"] = {
                        "old": current.password_never_expires,
                        "new": password_never_expires,
                    }
                _set_flags(domain.pipe, user, flags)
        finally:
            _close(domain.pipe, user)

    return changes


def set_password(conn: ServerConnection, name: str, password: str) -> None:
    """Set an account's password.

    Level 24 of ``SetUserInfo``: the password travels encrypted by the SMB
    session key, so it is protected by the same connection everything else uses
    and never appears in a log, an audit record or an error message.
    """
    _require_standalone(conn)

    with _Domain(conn) as domain:
        rid = domain.rid_of(name)
        user = _open_user(domain, rid)
        try:
            _set_password(domain.pipe, user, password)
        finally:
            _close(domain.pipe, user)

    logger.info("password set for the local account %s", name)


def delete_user(conn: ServerConnection, name: str) -> None:
    """Remove a local account.

    The server's own accounts are refused. Deleting the guest account or the
    built-in administrator is not something to leave one click away in a
    console — and the second one is how somebody locks themselves out.
    """
    _require_standalone(conn)

    if name.lower() in PROTECTED_ACCOUNTS:
        raise InvalidRequest(
            "This account belongs to the server itself.",
            code="protected_account",
            hint="Disable it instead if it should not be usable.",
            context={"name": name},
        )

    with _Domain(conn) as domain:
        rid = domain.rid_of(name)
        user = _open_user(domain, rid)
        try:
            _attempt(lambda: domain.pipe.DeleteUser(user))
        except Exception as exc:
            _close(domain.pipe, user)
            raise translate(exc) from exc

    logger.info("local account deleted: %s", name)


def set_members(
    conn: ServerConnection, group: str, *, add: list[str], remove: list[str]
) -> dict[str, Any]:
    """Add and remove group members, by SID.

    By SID rather than by name because a local group on a member server can
    contain domain accounts, and those have no local RID to address them by.
    The object picker resolves names to SIDs before they get here.
    """
    _require_standalone(conn)
    applied: dict[str, list[str]] = {"added": [], "removed": []}

    from samba.dcerpc import security

    with _Domain(conn) as domain:
        rid = domain.rid_of(group)
        alias = _attempt(
            lambda: domain.pipe.OpenAlias(domain.domain, MAXIMUM_ALLOWED, rid)
        )
        try:
            for sid in add:
                try:
                    _attempt(lambda s=sid: domain.pipe.AddAliasMember(alias, security.dom_sid(s)))
                    applied["added"].append(sid)
                except Exception as exc:
                    error = translate(exc)
                    # Already a member is not a failure of the request as a
                    # whole: the desired state is reached either way.
                    if error.code != "already_member":
                        raise error from exc

            for sid in remove:
                try:
                    _attempt(
                        lambda s=sid: domain.pipe.DeleteAliasMember(alias, security.dom_sid(s))
                    )
                    applied["removed"].append(sid)
                except Exception as exc:
                    error = translate(exc)
                    if error.code != "not_a_member":
                        raise error from exc
        finally:
            _close(domain.pipe, alias)

    return applied


# ---------------------------------------------------------------------------
# The binding shapes
# ---------------------------------------------------------------------------

# EnumDomainUsers takes an ACB filter. ACB_NORMAL alone is what a console
# wants: it leaves out the machine trust accounts, which are not people and
# would otherwise fill the list on a server that has any.
ACCT_NORMAL_FILTER = ACB_NORMAL


def _require_standalone(conn: ServerConnection) -> None:
    """Refuse on a domain member, where these accounts are not the real ones.

    A member server does have a local SAM, and it is almost always empty and
    entirely beside the point — its users come from the domain. Offering to
    edit it would be offering the wrong thing convincingly.
    """
    if conn.target.uses_kerberos:
        raise InvalidRequest(
            "This server is a domain member; its accounts come from the domain.",
            code="not_standalone",
            hint=(
                "Domain users and groups are managed on a domain controller — "
                "with SAMADCON, or with the Windows tools."
            ),
            context={"server": conn.info.name, "domain": conn.info.realm},
        )


def _read_user(domain: _Domain, rid: int, name: str) -> Account:
    """Level 21 carries everything the list shows, in one call per account."""
    user = _open_user(domain, rid)
    try:
        info = _attempt(lambda: domain.pipe.QueryUserInfo(user, 21))
    except SamfsconError:
        # An account we may not read still belongs in the list, with what the
        # enumeration already told us. Dropping it would report the server as
        # having fewer accounts than it has.
        return Account(name=name, rid=rid, sid=domain.sid_for(rid), full_name=None,
                       description=None, flags=0)
    finally:
        _close(domain.pipe, user)

    from samfscon.srv.discovery import _text

    return Account(
        name=_text(getattr(getattr(info, "account_name", None), "string", None)) or name,
        rid=rid,
        sid=domain.sid_for(rid),
        full_name=_text(getattr(getattr(info, "full_name", None), "string", None)),
        description=_text(getattr(getattr(info, "description", None), "string", None)),
        flags=int(getattr(info, "acct_flags", 0) or 0),
    )


def _read_group(domain: _Domain, rid: int, name: str) -> Group:
    alias = _attempt(lambda: domain.pipe.OpenAlias(domain.domain, MAXIMUM_ALLOWED, rid))
    try:
        info = _attempt(lambda: domain.pipe.QueryAliasInfo(alias, 1))
        members = _attempt(lambda: domain.pipe.GetMembersInAlias(alias))
    except SamfsconError:
        return Group(name=name, rid=rid, sid=domain.sid_for(rid), description=None, members=[])
    finally:
        _close(domain.pipe, alias)

    from samfscon.srv.discovery import _text

    sids = []
    for entry in getattr(members, "sids", None) or []:
        sid = getattr(entry, "sid", entry)
        if sid is not None:
            sids.append(str(sid))

    return Group(
        name=_text(getattr(getattr(info, "name", None), "string", None)) or name,
        rid=rid,
        sid=domain.sid_for(rid),
        description=_text(getattr(getattr(info, "description", None), "string", None)),
        members=sids,
    )


def _open_user(domain: _Domain, rid: int) -> Any:
    return _attempt(lambda: domain.pipe.OpenUser(domain.domain, MAXIMUM_ALLOWED, rid))


def _set_password(pipe: Any, user: Any, password: str) -> None:
    """Set a password through ``SetUserInfo`` level 24.

    The wire format is specified rather than improvised (MS-SAMR 2.2.6.21 and
    MS-SAMR 3.1.5.13.7), and both halves of it matter:

    1. A **516-byte buffer**: 512 bytes ending with the password in UTF-16LE,
       preceded by random padding, followed by the password's byte length as a
       little-endian 32-bit integer. The padding is random rather than zeroes
       because the buffer is encrypted with a stream cipher, and a known
       plaintext prefix on every request is exactly what one does not hand an
       observer.
    2. **RC4 with the SMB session key.** Not additional protection on top of
       the transport so much as the protocol's own requirement: a server will
       not accept the structure any other way.

    The plain password exists in this function and nowhere else — not in the
    audit record, not in a log line at any level, not in an error message.
    """
    from samba.dcerpc import samr

    blob = _password_blob(password)
    encrypted = _encrypt_with_session_key(pipe, blob)

    info = samr.UserInfo24()
    info.password = samr.CryptPassword()
    info.password.data = list(encrypted)
    # 0 means "not expired": the account is usable at once. Level 24 carries
    # this in the same structure, so it cannot be forgotten.
    info.password_expired = 0

    try:
        _attempt(
            lambda: pipe.SetUserInfo2(user, 24, info),
            lambda: pipe.SetUserInfo(user, 24, info),
        )
    except TypeError as exc:
        raise SamfsconError(
            "The password could not be set.",
            code="samr_password_unsupported",
            detail=str(exc),
            hint="Samba's SetUserInfo has an unexpected signature in this build.",
        ) from exc
    except Exception as exc:
        raise translate(exc) from exc


def _password_blob(password: str) -> bytes:
    """The 516-byte structure MS-SAMR calls SAMPR_USER_PASSWORD.

    Written out here rather than taken from a helper because the layout is the
    part that goes wrong silently: a buffer assembled the other way round is
    accepted by the encryption and rejected by the server as a wrong password,
    which reads like a policy failure and is not one.
    """
    import os

    encoded = password.encode("utf-16-le")
    if len(encoded) > 512:
        raise InvalidRequest(
            "The password is too long for this protocol.",
            code="password_too_long",
            hint="SAMR carries at most 256 characters.",
        )

    # The password sits at the *end* of the 512-byte buffer, not the start.
    padding = os.urandom(512 - len(encoded))
    return padding + encoded + len(encoded).to_bytes(4, "little")


def _encrypt_with_session_key(pipe: Any, blob: bytes) -> bytes:
    """RC4 the buffer with the connection's session key.

    The key comes from the authenticated SMB session underneath the pipe, so it
    exists only because the caller already signed in — which is what binds the
    password change to that person rather than to the container.

    Where the binding does not expose the key, this fails loudly. Sending the
    buffer unencrypted would be refused by the server anyway; sending it and
    reporting success would be worse than either.
    """
    from samba import crypto

    key = None
    for attribute in ("session_key", "transport_session_key"):
        key = getattr(pipe, attribute, None)
        if key:
            break

    if not key:
        raise SamfsconError(
            "The connection exposes no session key, so a password cannot be encrypted.",
            code="no_session_key",
            hint=(
                "SAMR requires the password to be encrypted with the SMB session "
                "key. This Samba build does not expose it through the python "
                "bindings; set the password on the server with smbpasswd."
            ),
        )

    try:
        return bytes(crypto.arcfour_crypt_blob(blob, bytes(key)))
    except Exception as exc:
        raise SamfsconError(
            "The password could not be encrypted for transport.",
            code="password_encryption_failed",
            detail=str(exc),
        ) from exc


def _set_flags(pipe: Any, user: Any, flags: int) -> None:
    from samba.dcerpc import samr

    info = samr.UserInfo16()
    info.acct_flags = flags
    try:
        _attempt(
            lambda: pipe.SetUserInfo(user, 16, info),
            lambda: pipe.SetUserInfo2(user, 16, info),
        )
    except Exception as exc:
        raise translate(exc) from exc


def _set_text(
    pipe: Any, user: Any, *, full_name: str | None, description: str | None
) -> None:
    """Two separate levels: SAMR has no combined "set the text fields" call."""
    from samba.dcerpc import samr

    if full_name is not None:
        info = samr.UserInfo6()
        info.full_name = _lsa_string(full_name)
        try:
            _attempt(lambda: pipe.SetUserInfo(user, 6, info))
        except Exception as exc:
            raise translate(exc) from exc

    if description is not None:
        info = samr.UserInfo13()
        info.description = _lsa_string(description)
        try:
            _attempt(lambda: pipe.SetUserInfo(user, 13, info))
        except Exception as exc:
            raise translate(exc) from exc


def _close(pipe: Any, handle: Any) -> None:
    if handle is None:
        return
    try:
        pipe.Close(handle)
    except Exception:  # teardown must not raise
        logger.debug("closing a SAMR handle failed", exc_info=True)


def _string(value: str) -> Any:
    from samba.dcerpc import lsa

    entry = lsa.String()
    entry.string = value
    return entry


def _lsa_string(value: str) -> Any:
    from samba.dcerpc import lsa

    entry = lsa.String()
    entry.string = value
    return entry


def _enumerate(call: Any) -> list[tuple[int, str]]:
    """Walk one of the Enum* calls, following its resume handle.

    Returns (rid, name) pairs. A server with more accounts than fit in one
    buffer returns the first batch and expects to be asked again — ignoring
    that works until the server where it does not, and then an account is
    simply missing with no error at all.
    """
    from samfscon.srv.discovery import _text

    found: list[tuple[int, str]] = []
    resume = 0

    while True:
        try:
            result = call(resume)
        except Exception as exc:
            raise translate(exc) from exc

        entries, total, resume_out = _unpack_enum(result)
        for entry in entries:
            rid = getattr(entry, "idx", None)
            name = _text(getattr(getattr(entry, "name", None), "string", None))
            if rid is not None and name:
                found.append((int(rid), name))

        if not entries or resume_out in (None, 0, resume) or len(found) >= (total or 0):
            break
        resume = resume_out

    return found


def _unpack_enum(result: Any) -> tuple[list[Any], int | None, int | None]:
    if not isinstance(result, tuple):
        return list(getattr(result, "entries", None) or []), None, None

    entries: list[Any] = []
    numbers: list[int] = []
    for item in result:
        holder = getattr(item, "entries", None)
        if holder is not None:
            entries = list(holder)
        elif isinstance(item, int):
            numbers.append(item)

    return entries, (numbers[-1] if numbers else None), (numbers[0] if numbers else None)


def _user_and_rid(result: Any) -> tuple[Any, int]:
    """CreateUser2 returns (handle, access_granted, rid) in some order."""
    if not isinstance(result, tuple):
        return result, 0

    handle = result[0]
    rid = 0
    for item in result[1:]:
        if isinstance(item, int):
            rid = item
    return handle, rid


def _ids(result: Any) -> list[int]:
    holder = result
    if isinstance(result, tuple) and result:
        holder = result[0]
    values = getattr(holder, "ids", None) or []
    return [int(value) for value in values]


def _attempt(*attempts: Any) -> Any:
    """Run the first call shape this binding accepts."""
    errors: list[str] = []
    for attempt in attempts:
        try:
            return attempt()
        except TypeError as exc:
            errors.append(str(exc))
            continue
    raise TypeError("; ".join(errors))
