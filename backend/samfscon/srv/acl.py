"""Security descriptors, as SDDL.

The same editor serves three places, because they are the same structure:

* **share permissions** — the descriptor srvsvc carries at level 502,
* **directory permissions** — the descriptor SMB reads off the share's root,
* **file permissions** — the same, one level down.

SDDL is manipulated as text rather than through the binary structure. That is
the choice SAMADCON made for AD and it holds here for the same three reasons:
it is what Samba parses and renders losslessly, it is what ``smbcacls`` prints —
so a result can be checked outside this console — and building an ACE as text is
far less error-prone than assembling an NDR structure by hand.

**The two descriptors are not interchangeable, and the difference is the thing
administrators get wrong.** A share permission is checked once, when the share
is opened; a file permission is checked on every operation, and the *effective*
right is the intersection of the two. A share granting Everyone full control
tells you nothing on its own, and neither does a file ACL that grants a group
write access on a read-only share. :func:`effective_access` computes the
intersection, because it is the only number that answers "may Alice write this".
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from samfscon.core.errors import InvalidRequest, SamfsconError
from samfscon.srv.connection import ServerConnection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Access mask bits (MS-DTYP 2.4.3), the file-system set
# ---------------------------------------------------------------------------

FILE_READ_DATA = 0x00000001
FILE_WRITE_DATA = 0x00000002
FILE_APPEND_DATA = 0x00000004
FILE_READ_EA = 0x00000008
FILE_WRITE_EA = 0x00000010
FILE_EXECUTE = 0x00000020
FILE_DELETE_CHILD = 0x00000040
FILE_READ_ATTRIBUTES = 0x00000080
FILE_WRITE_ATTRIBUTES = 0x00000100

DELETE = 0x00010000
READ_CONTROL = 0x00020000
WRITE_DAC = 0x00040000
WRITE_OWNER = 0x00080000
SYNCHRONIZE = 0x00100000

GENERIC_ALL = 0x10000000
GENERIC_EXECUTE = 0x20000000
GENERIC_WRITE = 0x40000000
GENERIC_READ = 0x80000000

FILE_GENERIC_READ = (
    READ_CONTROL | FILE_READ_DATA | FILE_READ_ATTRIBUTES | FILE_READ_EA | SYNCHRONIZE
)
FILE_GENERIC_WRITE = (
    READ_CONTROL
    | FILE_WRITE_DATA
    | FILE_WRITE_ATTRIBUTES
    | FILE_WRITE_EA
    | FILE_APPEND_DATA
    | SYNCHRONIZE
)
FILE_GENERIC_EXECUTE = READ_CONTROL | FILE_READ_ATTRIBUTES | FILE_EXECUTE | SYNCHRONIZE
FILE_ALL_ACCESS = 0x001F01FF

# The five rows every permissions dialog has, in the order they appear there.
# Not a simplification of the mask — the mask stays authoritative — but the
# rungs people actually think in, so the editor can offer them and still show
# the exact bits underneath.
PRESETS: tuple[tuple[str, int], ...] = (
    ("full", FILE_ALL_ACCESS | DELETE | WRITE_DAC | WRITE_OWNER),
    ("modify", FILE_GENERIC_READ | FILE_GENERIC_WRITE | FILE_GENERIC_EXECUTE | DELETE),
    ("read_execute", FILE_GENERIC_READ | FILE_GENERIC_EXECUTE),
    ("read", FILE_GENERIC_READ),
    ("write", FILE_GENERIC_WRITE),
)

# SDDL writes the common trustees as two-letter aliases rather than as SIDs
# (MS-DTYP 2.4.4.3). An editor that showed "WD" in the account column would be
# showing the wire format to somebody who wants to know who may read a file.
# Only the ones a file server's descriptors actually contain — the AD-specific
# half of the table has no business here.
SDDL_ALIASES: dict[str, str] = {
    "WD": "S-1-1-0",  # Everyone
    "AN": "S-1-5-7",  # Anonymous
    "AU": "S-1-5-11",  # Authenticated Users
    "IU": "S-1-5-4",  # Interactive
    "NU": "S-1-5-2",  # Network
    "SY": "S-1-5-18",  # Local System
    "LS": "S-1-5-19",  # Local Service
    "NS": "S-1-5-20",  # Network Service
    "CO": "S-1-3-0",  # Creator Owner
    "CG": "S-1-3-1",  # Creator Group
    "OW": "S-1-3-4",  # Owner Rights
    "BA": "S-1-5-32-544",  # Administrators
    "BU": "S-1-5-32-545",  # Users
    "BG": "S-1-5-32-546",  # Guests
    "PU": "S-1-5-32-547",  # Power Users
    "BO": "S-1-5-32-551",  # Backup Operators
    "DA": None,  # Domain Admins — relative to the domain, resolved by the server
    "DU": None,  # Domain Users
    "DG": None,  # Domain Guests
}

# Samba's own mapping of Unix identities into the SID space (idmap, and the
# `S-1-22` authority). No LSA lookup resolves these — they are not accounts the
# server has, they are uids and gids wearing a SID — so they are named here or
# they are named nowhere.
UNIX_USER_PREFIX = "S-1-22-1-"
UNIX_GROUP_PREFIX = "S-1-22-2-"

# ACE flags (MS-DTYP 2.4.4.1), the inheritance half.
OBJECT_INHERIT = 0x01
CONTAINER_INHERIT = 0x02
NO_PROPAGATE_INHERIT = 0x04
INHERIT_ONLY = 0x08
INHERITED_ACE = 0x10

# Descriptor control bits that matter to the editor.
SE_DACL_PROTECTED = 0x1000

# What to write back. The SACL is deliberately absent: auditing is configured
# through the full_audit VFS module on a Samba server, not through the SACL,
# and sending SECINFO_SACL asks for a privilege most accounts do not have —
# turning an ordinary permission change into an access-denied for no gain.
SECINFO_OWNER = 0x00000001
SECINFO_GROUP = 0x00000002
SECINFO_DACL = 0x00000004
SECINFO_PROTECTED_DACL = 0x80000000


@dataclass
class Ace:
    """One entry, in the terms the editor works in."""

    trustee: str
    kind: str  # "allow" or "deny"
    mask: int
    flags: int
    # The rights field exactly as the descriptor spelled it, and whether this
    # parser understood all of it. A mask it could not read is shown as the text
    # it came from — a confident 0x00000000 in a permissions dialog is a lie
    # about who may do what.
    raw_rights: str = ""
    understood: bool = True

    @property
    def inherited(self) -> bool:
        """Whether this entry came from a parent directory.

        An inherited entry is not editable here — changing it means changing
        the parent, and an editor that let somebody edit it in place would
        silently break the inheritance it came from.
        """
        return bool(self.flags & INHERITED_ACE)

    @property
    def preset(self) -> str | None:
        """The named rung this mask sits on, if it sits exactly on one."""
        for name, value in PRESETS:
            if self.mask == value:
                return name
        return None

    def describe(self) -> dict[str, Any]:
        return {
            "trustee": self.trustee,
            "kind": self.kind,
            "mask": self.mask,
            "flags": self.flags,
            "inherited": self.inherited,
            "preset": self.preset,
            "raw_rights": self.raw_rights,
            "understood": self.understood,
            "rights": rights_of(self.mask),
            "applies_to": _applies_to(self.flags),
        }


@dataclass
class SecurityDescriptor:
    """A descriptor, rendered for the editor and kept as SDDL."""

    sddl: str
    owner: str | None
    group: str | None
    aces: list[Ace]
    protected: bool

    def describe(self) -> dict[str, Any]:
        return {
            "sddl": self.sddl,
            "owner": self.owner,
            "group": self.group,
            "protected": self.protected,
            "aces": [ace.describe() for ace in self.aces],
        }


# ---------------------------------------------------------------------------
# Parsing and rendering
# ---------------------------------------------------------------------------

# One ACE: (type;flags;rights;object_guid;inherit_guid;trustee[;extra]).
_ACE_RE = re.compile(r"\(([^()]*)\)")
# The owner and group fields run until the next section marker, and there is no
# separator between them: "O:BAG:BA" is owner BA, group BA. A character class
# that merely excludes ":" reads the owner as "BAG", which is a SID abbreviation
# that does not exist — and the descriptor is then written back with an owner
# nobody has. Hence the lookahead: a field ends where the next section begins.
_OWNER_RE = re.compile(r"O:(.+?)(?=[GDS]:|$)")
_GROUP_RE = re.compile(r"G:(.+?)(?=[DS]:|$)")


def parse(sddl: str) -> SecurityDescriptor:
    """Read an SDDL string into something the editor can render.

    Deliberately tolerant. An ACE this parser does not understand keeps its
    text and is reported as unparsed rather than dropped — a descriptor that
    loses an entry on the way through an editor is how permissions quietly
    widen.
    """
    prefix, aces_text, _ = _split_dacl(sddl)

    owner_match = _OWNER_RE.search(sddl)
    group_match = _GROUP_RE.search(sddl)

    aces: list[Ace] = []
    for text in aces_text:
        parsed = _parse_ace(text)
        if parsed is not None:
            aces.append(parsed)

    return SecurityDescriptor(
        sddl=sddl,
        owner=owner_match.group(1) if owner_match else None,
        group=group_match.group(1) if group_match else None,
        aces=aces,
        protected="D:P" in prefix or prefix.rstrip().endswith("P"),
    )


# The SDDL aliases that are a RID against a domain rather than a whole SID
# (MS-DTYP 2.4.2.4). ``DA`` is 512 in *some* domain; which one is not in the
# text, it is an argument to the parser. Parsed against the wrong domain every
# one of these yields a well-formed SID that belongs to nobody — no error, no
# warning, just an entry for an account that does not exist.
#
# Kept apart from SDDL_ALIASES above, which is for display. These are the ones
# a write has to be careful about, and the rights aliases share letters with
# them (``DC`` is Delete Child in a rights field and Domain Computers in a
# trustee field), so they are only ever matched against a parsed trustee.
DOMAIN_RELATIVE_ALIASES = frozenset(
    {
        "DA",  # Domain Admins
        "DU",  # Domain Users
        "DG",  # Domain Guests
        "DD",  # Domain Controllers
        "DC",  # Domain Computers
        "EA",  # Enterprise Admins
        "SA",  # Schema Admins
        "CA",  # Cert Publishers
        "PA",  # Group Policy Creator Owners
        "RS",  # RAS Servers
        "RO",  # Enterprise Read-only Domain Controllers
        "CN",  # Cloneable Domain Controllers
        "AP",  # Protected Users
        "KA",  # Key Admins
        "EK",  # Enterprise Key Admins
        "LA",  # the domain's built-in Administrator, RID 500
        "LG",  # the domain's built-in Guest, RID 501
    }
)


def domain_relative_trustees(sddl: str) -> list[str]:
    """Which domain-relative aliases this descriptor names, in order.

    Found by parsing rather than by scanning the text: an alias only means an
    account in the owner, the group, or an ACE's trustee field, and the same
    two letters mean a right somewhere else.
    """
    descriptor = parse(sddl)
    candidates = [descriptor.owner, descriptor.group]
    candidates.extend(ace.trustee for ace in descriptor.aces)

    found: list[str] = []
    for candidate in candidates:
        token = (candidate or "").strip().upper()
        if token in DOMAIN_RELATIVE_ALIASES and token not in found:
            found.append(token)
    return found


def to_descriptor(conn: ServerConnection, sddl: str) -> Any:
    """Turn SDDL from the client into a descriptor, against the right domain.

    Both write paths come through here — the share descriptor and the file one
    — because both take SDDL as text from whoever is at the keyboard, and both
    hints in this codebase invite them to paste it from ``smbcacls`` or
    ``net rpc share getsecurity``. Output from either can contain ``DA``.

    The domain the aliases belong to is asked of the server. If it will not say
    and the descriptor needs one, this refuses instead of substituting a domain
    it happens to have: expanding ``DA`` against BUILTIN yields S-1-5-32-512,
    which is a valid SID, is nobody, and would be written without complaint.
    Refusing is worse to read and better to live with — the alternative is a
    permission change that reports success and grants nothing.
    """
    from samba.dcerpc import security

    from samfscon.srv import identity

    relative = domain_relative_trustees(sddl)
    domain = identity.domain_sid(conn)

    if relative and domain is None:
        raise InvalidRequest(
            "This server does not say which domain these entries belong to.",
            code="sddl_domain_unknown",
            detail=", ".join(relative),
            hint=(
                "The descriptor names " + ", ".join(relative) + ", which SDDL "
                "writes as a number relative to a domain rather than as a whole "
                r"SID. Write the SID out in full instead — `wbinfo -n 'DOMAIN\Domain "
                "Admins'` prints it — or pick the account from the list."
            ),
            context={"aliases": relative},
        )

    # With no relative alias in it the domain is never consulted, so an
    # unknown one costs nothing and BUILTIN stands in as the argument the
    # signature insists on.
    try:
        return security.descriptor.from_sddl(sddl, security.dom_sid(domain or "S-1-5-32"))
    except Exception as exc:
        raise InvalidRequest(
            "This is not a valid security descriptor.",
            code="invalid_sddl",
            detail=str(exc),
            hint="Check the SDDL — smbcacls prints the same format for comparison.",
        ) from exc


def _parse_ace(text: str) -> Ace | None:
    parts = text.split(";")
    if len(parts) < 6:
        logger.debug("skipping an ACE with %d fields: %r", len(parts), text)
        return None

    ace_type, flags_text, rights_text = parts[0], parts[1], parts[2]
    trustee = parts[5].strip()

    kind = "deny" if ace_type.strip().upper().startswith("D") else "allow"
    mask, understood = _parse_rights(rights_text)
    if not understood:
        logger.info("an ACE's rights field was not fully understood: %r", rights_text)
    return Ace(
        trustee=trustee,
        kind=kind,
        mask=mask,
        flags=_parse_flags(flags_text),
        raw_rights=rights_text.strip(),
        understood=understood,
    )


# The SDDL letters for the rights this editor writes, and the bit each stands
# for. Rendered back out in this order, which is the order Windows writes them.
_RIGHT_LETTERS: tuple[tuple[str, int], ...] = (
    ("GA", GENERIC_ALL),
    ("GR", GENERIC_READ),
    ("GW", GENERIC_WRITE),
    ("GX", GENERIC_EXECUTE),
    ("SD", DELETE),
    ("RC", READ_CONTROL),
    ("WD", WRITE_DAC),
    ("WO", WRITE_OWNER),
    ("FA", FILE_ALL_ACCESS),
    ("FR", FILE_GENERIC_READ),
    ("FW", FILE_GENERIC_WRITE),
    ("FX", FILE_GENERIC_EXECUTE),
)

_FLAG_LETTERS: tuple[tuple[str, int], ...] = (
    ("OI", OBJECT_INHERIT),
    ("CI", CONTAINER_INHERIT),
    ("NP", NO_PROPAGATE_INHERIT),
    ("IO", INHERIT_ONLY),
    ("ID", INHERITED_ACE),
)


def _parse_rights(text: str) -> tuple[int, bool]:
    """The mask a rights field carries, and whether it was fully understood.

    Three forms are legal (MS-DTYP 2.5.1.1): a hexadecimal mask, a decimal one,
    and a run of two-letter codes. The second flag is what stops a
    half-recognised run of letters being reported as a confident number: a mask
    assembled from the codes we knew and silently missing the ones we did not is
    a permission that reads as narrower than it is, which is the direction that
    gets somebody locked out.
    """
    raw = text.strip().upper()
    if not raw:
        return 0, True

    if raw.startswith("0X"):
        try:
            return int(raw, 16), True
        except ValueError:
            return 0, False

    # Samba writes hex, but the format allows a plain number and a descriptor
    # that arrived from elsewhere may use one.
    if raw.isdigit():
        return int(raw), True

    if len(raw) % 2:
        return 0, False

    known = dict(_RIGHT_LETTERS)
    mask = 0
    understood = True
    for index in range(0, len(raw), 2):
        value = known.get(raw[index : index + 2])
        if value is None:
            understood = False
            continue
        mask |= value
    return mask, understood


def _parse_flags(text: str) -> int:
    text = text.strip().upper()
    flags = 0
    for index in range(0, len(text) - 1, 2):
        pair = text[index : index + 2]
        for letter, value in _FLAG_LETTERS:
            if pair == letter:
                flags |= value
                break
    return flags


def render_rights(mask: int) -> str:
    """The SDDL form of a mask.

    Hexadecimal unless the mask is exactly one of the named combinations. That
    is not laziness: writing ``FRFW`` for a mask that is *nearly* those two
    would quietly change the permission, and a hexadecimal mask is exact,
    round-trips, and is what ``smbcacls`` shows too.
    """
    for letter, value in _RIGHT_LETTERS:
        if mask == value:
            return letter
    return f"0x{mask:08x}"


def render_flags(flags: int) -> str:
    # INHERITED_ACE is never written: it is the server's statement about where
    # an entry came from, not ours. Writing it would claim an entry was
    # inherited when it was typed in by hand two seconds earlier.
    out = ""
    for letter, value in _FLAG_LETTERS:
        if value == INHERITED_ACE:
            continue
        if flags & value:
            out += letter
    return out


def build(descriptor: SecurityDescriptor) -> str:
    """Render a descriptor back to SDDL.

    Inherited entries are left out on purpose: they are not this descriptor's
    to carry. The server re-applies them from the parent, and writing them back
    as explicit entries is how an inheritance chain turns into a set of frozen
    copies that stop tracking the parent.
    """
    parts = []
    if descriptor.owner:
        parts.append(f"O:{descriptor.owner}")
    if descriptor.group:
        parts.append(f"G:{descriptor.group}")

    dacl = "D:"
    if descriptor.protected:
        dacl += "P"
    for ace in descriptor.aces:
        if ace.inherited:
            continue
        letter = "D" if ace.kind == "deny" else "A"
        # An entry this parser could not read is written back exactly as it
        # arrived. Re-rendering it from a mask we admit is incomplete would
        # quietly rewrite somebody's permission on the way through an editor
        # that was only ever opened to look at a different row.
        rights = ace.raw_rights if not ace.understood else render_rights(ace.mask)
        dacl += f"({letter};{render_flags(ace.flags)};{rights};;;{ace.trustee})"

    parts.append(dacl)
    return "".join(parts)


def _split_dacl(sddl: str) -> tuple[str, list[str], str]:
    """Split an SDDL string into (prefix, ace strings, suffix)."""
    marker = sddl.find("D:")
    if marker < 0:
        raise InvalidRequest(
            "The security descriptor has no DACL.",
            code="no_dacl",
            hint="A descriptor without one grants nothing to anybody.",
        )

    cursor = marker + 2
    while cursor < len(sddl) and sddl[cursor] not in "(S":
        cursor += 1
    prefix = sddl[:cursor]

    rest = sddl[cursor:]
    sacl = rest.find("S:")
    body = rest[:sacl] if sacl >= 0 else rest
    suffix = rest[sacl:] if sacl >= 0 else ""

    return prefix, [match.group(1) for match in _ACE_RE.finditer(body)], suffix


# ---------------------------------------------------------------------------
# What a mask means, in words
# ---------------------------------------------------------------------------

_RIGHT_NAMES: tuple[tuple[str, int], ...] = (
    ("read", FILE_READ_DATA),
    ("write", FILE_WRITE_DATA),
    ("append", FILE_APPEND_DATA),
    ("execute", FILE_EXECUTE),
    ("delete", DELETE),
    ("delete_child", FILE_DELETE_CHILD),
    ("read_attributes", FILE_READ_ATTRIBUTES),
    ("write_attributes", FILE_WRITE_ATTRIBUTES),
    ("read_permissions", READ_CONTROL),
    ("change_permissions", WRITE_DAC),
    ("take_ownership", WRITE_OWNER),
)


def rights_of(mask: int) -> list[str]:
    """The individual rights a mask carries, for the detail view.

    Generic bits are expanded first: ``GR`` and ``FR`` mean the same thing to
    the server, and an editor that showed one as "read" and the other as
    nothing would be describing the same permission two different ways.
    """
    expanded = expand_generic(mask)
    return [name for name, bit in _RIGHT_NAMES if expanded & bit]


def expand_generic(mask: int) -> int:
    """Map the generic bits onto the file-system bits they stand for."""
    expanded = mask & ~(GENERIC_ALL | GENERIC_READ | GENERIC_WRITE | GENERIC_EXECUTE)
    if mask & GENERIC_ALL:
        expanded |= FILE_ALL_ACCESS | DELETE | WRITE_DAC | WRITE_OWNER
    if mask & GENERIC_READ:
        expanded |= FILE_GENERIC_READ
    if mask & GENERIC_WRITE:
        expanded |= FILE_GENERIC_WRITE
    if mask & GENERIC_EXECUTE:
        expanded |= FILE_GENERIC_EXECUTE
    return expanded


def _applies_to(flags: int) -> str:
    """The inheritance shape, as the dialogs word it."""
    object_inherit = bool(flags & OBJECT_INHERIT)
    container_inherit = bool(flags & CONTAINER_INHERIT)
    inherit_only = bool(flags & INHERIT_ONLY)

    if not object_inherit and not container_inherit:
        return "this_only"
    if object_inherit and container_inherit:
        return "this_and_children" if not inherit_only else "children_only"
    if container_inherit:
        return "folders"
    return "files"


def canonical_sid(trustee: str) -> str | None:
    """The SID behind a trustee string, when one can be had without asking.

    Returns None for an alias that only means something relative to a domain
    (``DA`` is whichever domain this server belongs to), which is exactly the
    case worth handing to the server rather than guessing at.
    """
    text = trustee.strip()
    if text.upper().startswith("S-"):
        return text
    return SDDL_ALIASES.get(text.upper())


def unix_identity(sid: str) -> dict[str, Any] | None:
    """Name a Samba Unix-mapped SID, which no lookup will resolve.

    ``S-1-22-1-1000`` is uid 1000 and ``S-1-22-2-100`` is gid 100. They appear
    in the descriptors of a share backed by POSIX ACLs, they are not accounts
    the server knows by name, and left alone they show as a raw SID in a column
    headed "account".
    """
    if sid.startswith(UNIX_USER_PREFIX):
        return {"kind": "unix_user", "id": sid[len(UNIX_USER_PREFIX) :]}
    if sid.startswith(UNIX_GROUP_PREFIX):
        return {"kind": "unix_group", "id": sid[len(UNIX_GROUP_PREFIX) :]}
    return None


def preset_mask(name: str) -> int:
    for preset, value in PRESETS:
        if preset == name:
            return value
    raise InvalidRequest(
        "Unknown permission level.",
        code="unknown_preset",
        context={"preset": name, "allowed": [preset for preset, _ in PRESETS]},
    )


def effective_access(share_mask: int, file_mask: int) -> dict[str, Any]:
    """What is actually permitted, given both descriptors.

    The intersection, because that is how SMB decides: the share permission is
    checked when the share is opened and bounds everything that follows, and
    the file permission is checked on every operation within it. Neither number
    answers the question on its own, which is why a console that shows only one
    of them is a console people end up arguing with.
    """
    share = expand_generic(share_mask)
    file = expand_generic(file_mask)
    combined = share & file
    return {
        "share_mask": share_mask,
        "file_mask": file_mask,
        "effective_mask": combined,
        "rights": rights_of(combined),
        # Named separately because it is the case that confuses people: the
        # file ACL says yes and the share says no, so the answer is no.
        "limited_by_share": bool(file & ~share),
    }


# ---------------------------------------------------------------------------
# Reading and writing a file's descriptor over SMB
# ---------------------------------------------------------------------------


def read_path_sddl(conn: ServerConnection, share: str, path: str) -> str:
    """The security descriptor of one path inside a share."""
    from samba.dcerpc import security

    tree = conn.tree(share)
    info = security.SECINFO_OWNER | security.SECINFO_GROUP | security.SECINFO_DACL

    try:
        descriptor = tree.get_acl(path, info)
    except Exception as exc:
        from samfscon.core.errors import translate

        raise translate(exc) from exc

    try:
        return descriptor.as_sddl()
    except Exception as exc:  # pragma: no cover — a descriptor Samba cannot render
        raise SamfsconError(
            "The security descriptor could not be rendered.",
            code="sddl_unrenderable",
            detail=str(exc),
        ) from exc


def write_path_sddl(
    conn: ServerConnection, share: str, path: str, sddl: str, *, protected: bool | None = None
) -> None:
    """Replace the security descriptor of one path.

    ``protected`` decides whether the parent's entries keep flowing in. Passing
    None leaves it as the descriptor's own SDDL says, which is what an editor
    that round-tripped the value should do — the flag is a property of the
    descriptor, not of the write.
    """
    from samba.dcerpc import security

    from samfscon.core.errors import translate

    tree = conn.tree(share)
    descriptor = to_descriptor(conn, sddl)

    info = security.SECINFO_OWNER | security.SECINFO_GROUP | security.SECINFO_DACL
    if protected:
        info |= security.SECINFO_PROTECTED_DACL

    try:
        tree.set_acl(path, descriptor, info)
    except Exception as exc:
        raise translate(exc) from exc
