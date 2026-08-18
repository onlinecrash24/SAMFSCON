"""Request bodies.

Kept in one place so the shapes the API accepts can be read without opening
every router, and so the validation that protects the Samba layer sits in front
of it rather than scattered through it.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from samfscon.config import MODE_AD_MEMBER, MODE_AUTO, MODE_STANDALONE

# Share names Samba will not accept, and two it accepts but SAMFSCON will not
# create: IPC$ and ADMIN$ are the server's own, and a console that offers to
# redefine them is offering to lock its user out.
RESERVED_SHARES = frozenset({"ipc$", "admin$", "global", "printers", "print$"})


class LoginRequest(BaseModel):
    """Sign in to one file server.

    ``server``, ``profile_id`` and neither-of-them are the three ways to say
    which server; they are resolved in that order by
    :func:`samfscon.srv.targets.resolve_target`.
    """

    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=1024)
    server: str | None = Field(default=None, max_length=255)
    profile_id: str | None = Field(default=None, max_length=64)
    # What the administrator picked when the probe could not decide. Wins over
    # discovery — see samfscon.srv.targets.
    mode: str | None = Field(default=None)
    realm: str | None = Field(default=None, max_length=255)

    @field_validator("mode", mode="after")
    @classmethod
    def _known_mode(cls, value: str | None) -> str | None:
        if value is None:
            return None
        mode = value.strip().lower()
        if mode not in (MODE_AUTO, MODE_AD_MEMBER, MODE_STANDALONE):
            raise ValueError(f"mode must be {MODE_AD_MEMBER}, {MODE_STANDALONE} or {MODE_AUTO}")
        return mode


class ProbeRequest(BaseModel):
    """Ask a server what it is, before signing in."""

    host: str | None = Field(default=None, max_length=255)
    profile_id: str | None = Field(default=None, max_length=64)


class ShareCreateRequest(BaseModel):
    """A new share.

    ``path`` must already exist on the server. SAMFSCON manages it over the
    network and has no way to create a directory that is not inside a share it
    can already reach — which is a limit worth failing on clearly rather than
    working around badly.
    """

    name: str = Field(min_length=1, max_length=80)
    path: str = Field(min_length=1, max_length=4096)
    comment: str | None = Field(default=None, max_length=256)
    # The options every console offers on the first tab. Everything beyond this
    # goes through `options`, which is validated against the catalogue.
    read_only: bool = False
    browseable: bool = True
    guest_ok: bool = False
    options: dict[str, str] = Field(default_factory=dict)

    @field_validator("name", mode="after")
    @classmethod
    def _usable_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("the share name is empty")
        if name.lower() in RESERVED_SHARES:
            raise ValueError(f"{name} is reserved by the server")
        # The characters SMB itself cannot carry in a share name. Checked here
        # so the refusal names the character, rather than arriving from the
        # server as WERR_INVALID_NAME with nothing to go on.
        forbidden = set('\\/:*?"<>|') & set(name)
        if forbidden:
            raise ValueError(f"the share name must not contain {' '.join(sorted(forbidden))}")
        return name

    @field_validator("path", mode="after")
    @classmethod
    def _absolute_path(cls, value: str) -> str:
        path = value.strip().replace("\\", "/")
        if not path.startswith("/"):
            raise ValueError("the path must be absolute on the server, e.g. /srv/shares/projects")
        return path.rstrip("/") or "/"


class ShareUpdateRequest(BaseModel):
    """A change to an existing share. Only what is sent is changed."""

    path: str | None = Field(default=None, max_length=4096)
    comment: str | None = Field(default=None, max_length=256)
    read_only: bool | None = None
    browseable: bool | None = None
    guest_ok: bool | None = None
    # A key set to null is removed from the share's configuration, which is how
    # an option goes back to the server's default. An empty dict changes nothing.
    options: dict[str, str | None] | None = None

    @field_validator("path", mode="after")
    @classmethod
    def _absolute_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return ShareCreateRequest._absolute_path(value)


class SecurityDescriptorRequest(BaseModel):
    """Replace a security descriptor, share-level or on a file.

    SDDL rather than a structure of our own: it is the format Samba parses and
    renders losslessly, it is what ``smbcacls`` prints, and it is therefore the
    one an administrator can check the result against outside this console.
    """

    sddl: str = Field(min_length=1, max_length=65536)
    # Applies to files and directories only, and only where the caller means it:
    # replacing a tree's permissions is not something to do as a side effect of
    # editing one directory.
    apply_to_children: bool = False


class CloseFileRequest(BaseModel):
    """Close one file another session has open."""

    file_id: int = Field(ge=0)


class AccountCreateRequest(BaseModel):
    """A new local account on a standalone server."""

    name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)
    full_name: str | None = Field(default=None, max_length=256)
    description: str | None = Field(default=None, max_length=256)
    disabled: bool = False
    password_never_expires: bool = False

    @field_validator("name", mode="after")
    @classmethod
    def _usable_name(cls, value: str) -> str:
        name = value.strip()
        forbidden = set('\\/:*?"<>|[];,+=') & set(name)
        if forbidden:
            raise ValueError(f"the account name must not contain {' '.join(sorted(forbidden))}")
        return name


class AccountUpdateRequest(BaseModel):
    """A change to a local account. Only what is sent is changed."""

    full_name: str | None = Field(default=None, max_length=256)
    description: str | None = Field(default=None, max_length=256)
    disabled: bool | None = None
    password_never_expires: bool | None = None


class PasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


class MembershipRequest(BaseModel):
    """Add or remove group members, by SID."""

    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)


class LookupRequest(BaseModel):
    """Resolve names to SIDs, for the permission editor's object picker."""

    names: list[str] = Field(default_factory=list, max_length=64)
    sids: list[str] = Field(default_factory=list, max_length=64)


def as_dict(model: BaseModel) -> dict[str, Any]:
    """Only the fields that were actually sent.

    ``exclude_unset`` is what makes a partial update partial: without it, every
    unmentioned field arrives as its default and a request that meant to change
    a comment would also switch browsing off.
    """
    return model.model_dump(exclude_unset=True)
