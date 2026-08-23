"""What is worth telling somebody about this file server, from rules.

Every rule here is a pure function over data somebody else fetched. That keeps a
network round trip out of the rules and makes each one testable on its own,
without a server and without the Samba bindings.

**Facts and conventions are different things, and the severity says which.** A
share whose path is `/etc` is a fact. A share granting write to Everyone is a
convention — somebody may have meant it — so where a rule rests on one, the
threshold travels in the evidence, and a reader who disagrees can disagree with
the number rather than with the finding.

**The one invariant.** A rule may fire on a value that *was read*. It may fire
on the absence of a value only where the absence is itself readable: an empty
privilege-holder list, a share missing from the live list, a registry section
that exists and lacks a key.

That is narrower than it sounds, and it is the whole shape of this module. Every
smb.conf option can also be set in `[global]` in the text file. SAMFSCON reads
winreg, srvsvc and SMB; it reads no file. So *"`guest ok` is not set"* is a fact
about **one registry key**, never about the server — and a rule that treated the
two as the same would report a guest-writable share as clean.

Its consequence bites in the layout rather than in the rules, which is why
:func:`coverage` exists: a report showing nine findings across four shares and
nothing across the other nine reads as *"the other nine are fine"*. The counts
have to sit above the list, and :class:`Unreadable` sits beside the findings and
never inside them.

**Rules deliberately not written.**

* *A share ACL granting Everyone full control over a restrictive file ACL.* On
  most Samba installations that is the usual arrangement — the share permission
  is a ceiling and the file permissions do the real work. A rule firing on it
  would mark nearly every healthy server, and a report that marks every server
  is one nobody opens twice. The fault in the other direction is the one people
  are stuck on, and it is specified and not yet built.
* *`follow symlinks = yes`.* Samba's default, and safe while `wide links` is
  off.
* *`registry writable` being false.* An operational fact about the signed-in
  account, already carried by the capability banner on every share listing.
  Repeating it here would bury the findings that need a decision.
* *Password policy, and replication.* There is no domain policy on a file
  server and no replication partner. Both are SAMADCON's, and neither has a
  reading here.
* *Locked or disabled local accounts.* Operational, not a misconfiguration.
* *An ACE this parser could not fully read.* That is a statement about the
  parser, not about the server, and the editor writes such an ACE back verbatim
  so it is safe to leave alone. Reported as :class:`Unreadable`.

**Negatives are not emitted at all.** There is no `no_guest_access_anywhere`,
no `no_overlapping_shares`, no `paths_all_safe`. Each would rest on a global
this console cannot read, and where a negative *is* knowable it is a number in
:func:`coverage` rather than a finding.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from typing import Any

SEVERITIES = ("high", "medium", "low", "info")

AREAS = ("management", "transport", "shares", "sessions")

# Trustees that mean "anyone who can sign in". A named list rather than an
# inlined set, because a reader who thinks S-1-5-32-545 is fine on their server
# should be able to disagree with the list rather than with the finding.
BROAD_TRUSTEES: tuple[str, ...] = ("S-1-1-0", "S-1-5-11", "S-1-5-32-545")

# Domain Users and Domain Guests, whatever the domain. Matched by RID because
# the domain half differs on every server.
BROAD_RIDS: tuple[int, ...] = (513, 514)
_DOMAIN_SID_RE = re.compile(r"^S-1-5-21-\d+-\d+-\d+-(\d+)$")

# The bit that makes a mode world-writable.
WORLD_WRITE = 0o002
MASK_OPTIONS = ("create mask", "directory mask", "force create mode", "force directory mode")

# Paths a share has no business publishing, and how bad each is. A convention,
# so the whole list travels in the evidence of any finding that rests on it.
SENSITIVE_PATHS: tuple[tuple[str, str], ...] = (
    ("/", "high"),
    ("/etc", "high"),
    ("/root", "high"),
    ("/boot", "high"),
    ("/proc", "high"),
    ("/sys", "high"),
    ("/dev", "high"),
    ("/usr", "medium"),
    ("/var/lib", "medium"),
)

#: Every id any rule below can emit. Declared so the message catalogue and the
#: tests have one list to check against rather than a grep.
IDS: tuple[str, ...] = (
    "registry_config_absent",
    "registry_shares_not_served",
    "disk_operator_unassigned",
    "disk_operator_broadly_granted",
    "transport_peer_unverified",
    "transport_this_session",
    "share_guest_ok",
    "share_guest_writable",
    "share_wide_links",
    "share_create_mask_world_writable",
    "share_force_user",
    "share_force_user_root",
    "share_hosts_allow_unparsable",
    "share_hosts_deny_without_allow",
    "share_hidden_name_browseable",
    "share_vfs_option_without_module",
    "share_path_nested",
    "share_path_duplicate",
    "share_path_sensitive",
    "share_configured_not_served",
    "share_root_not_writable",
    "guest_session_present",
)


@dataclass(frozen=True)
class Finding:
    """One thing worth saying, with what it was decided from.

    ``id`` is stable and is what the interface translates; the text lives with
    the other messages rather than here, so a finding reads in the language the
    console is set to.
    """

    id: str
    severity: str
    area: str
    #: What this is about — a share's name, a client. Empty for findings about
    #: the server itself, which are one of a kind. Share findings are not: six
    #: shares with ``guest ok = yes`` either collapse into one finding or become
    #: six that cannot be told apart.
    subject: str = ""
    #: The values the rule looked at. Present so a finding can be checked rather
    #: than believed. JSON-serialisable throughout, and a key whose value is
    #: ``None`` is never dropped — an absent key reads as "we checked and it was
    #: fine", which for these rules is exactly the wrong thing to say.
    evidence: dict[str, Any] = field(default_factory=dict)

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "area": self.area,
            "subject": self.subject,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class Unreadable:
    """One thing nobody could look at, as a code.

    A code and not a sentence, for the same reason
    :class:`samfscon.srv.diagnostics.Note` carries one: the interface is
    bilingual and this side writes English, and an English clause tacked onto a
    German banner is how that was got wrong once already.

    Returned *beside* the findings and never mixed into them. "We did not look"
    is not a finding about the server, and a section that yielded nothing is not
    a section with nothing in it.
    """

    area: str
    subject: str = ""
    reason: str = ""

    def describe(self) -> dict[str, Any]:
        return {"area": self.area, "subject": self.subject, "reason": self.reason}


def evaluate(
    *,
    capabilities: dict[str, Any] | None = None,
    registry: dict[str, Any] | None = None,
    server: dict[str, Any] | None = None,
    transport: dict[str, Any] | None = None,
    shares: list[dict[str, Any]] | None = None,
    sessions: list[dict[str, Any]] | None = None,
    #: What this session may create in each share's root, as the *server*
    #: answered it. Keyed by share name; a value of None means the question
    #: could not be put and no finding follows from it.
    roots: dict[str, bool | None] | None = None,
) -> list[Finding]:
    """Every finding these inputs support, worst first.

    Each argument may be absent: a caller that could not read one part still
    gets the findings for the parts it could. Reporting nothing about a section
    is honest; guessing at it is not.
    """
    found: list[Finding] = []

    management = _management(capabilities, registry) if capabilities is not None else []
    found.extend(management)

    if transport is not None:
        found.extend(_transport(transport, server or {}))
    if shares is not None:
        # Two findings for one cause is how a report loses its reader. If the
        # server ignores its whole registry, every registry share is missing
        # from the live list and the management finding has already said so.
        suppressed = any(item.id == "registry_shares_not_served" for item in management)
        found.extend(_shares(shares, registry, suppress_not_served=suppressed))
    if sessions is not None:
        found.extend(_sessions(sessions))
    if roots:
        found.extend(_roots(roots))

    order = {name: index for index, name in enumerate(SEVERITIES)}
    # Three parts, not two. Severity still wins, because the report is
    # worst-first — but within one severity a reader wants a share's problems
    # together, and sorting only by id interleaves every share.
    found.sort(
        key=lambda item: (order.get(item.severity, len(order)), item.subject.lower(), item.id)
    )
    return found


# ---------------------------------------------------------------------------
# The two shared readers. Every option rule goes through them; nothing indexes
# a share's options directly.
# ---------------------------------------------------------------------------


def _stored(entry: dict[str, Any]) -> dict[str, str] | None:
    """The share's registry values, or ``None`` when they could not be read.

    ``None`` is the whole point. A share defined in the text smb.conf has no
    registry key at all, that file cannot be read over anything SAMFSCON
    speaks, and every option rule is therefore *unreadable* for that share
    rather than clean. Returning ``{}`` here would make every one of them pass
    in silence.
    """
    if not entry.get("config_readable"):
        return None
    options = entry.get("options")
    return options if isinstance(options, dict) else {}


def _flag(stored: dict[str, str], name: str) -> bool | None:
    """``yes`` / ``no`` as this key stores it, or ``None`` when it does not.

    ``None`` is not ``False``. The option may be set in ``[global]`` in the text
    smb.conf, which Samba applies to every share that does not override it — so
    "this key does not carry `guest ok`" says nothing about the server.

    A value that is neither is also ``None``: Samba's own parser would not
    honour it either, and a rule deciding which way it fell would be guessing.
    """
    raw = stored.get(name)
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in {"yes", "true", "1", "on"}:
        return True
    if value in {"no", "false", "0", "off"}:
        return False
    return None


# ---------------------------------------------------------------------------
# Management
# ---------------------------------------------------------------------------


def _management(
    capabilities: dict[str, Any] | None, registry: dict[str, Any] | None
) -> list[Finding]:
    if capabilities is None:
        return []

    found: list[Finding] = []
    notes = [note.get("code") for note in capabilities.get("notes") or [] if note.get("code")]

    # Never on None. A refused probe leaves registry_config as None, and a rule
    # written `if not registry_config` would send somebody to edit an smb.conf
    # that is already right.
    if capabilities.get("registry_config") is False:
        found.append(
            Finding(
                id="registry_config_absent",
                severity="medium",
                area="management",
                evidence={
                    "registry_config": False,
                    "notes": notes,
                    "fix": "include = registry",
                },
            )
        )

    if registry is not None and registry.get("served") is False:
        found.append(
            Finding(
                id="registry_shares_not_served",
                severity="high",
                area="management",
                evidence={
                    "registry_share_sections": registry.get("share_section_count", 0),
                    "live_matches": registry.get("live_matches", 0),
                    "sections": list(registry.get("share_sections") or []),
                    "global_section_excluded": True,
                    "fix": "registry shares = yes",
                },
            )
        )

    # Never on None either, and this one matters most. The privilege check
    # cannot follow nested group membership, so it answers None whenever the
    # right is held by somebody it could not match the session against — a
    # domain administrator inside BUILTIN\Administrators through Domain Admins
    # looks like a non-holder. False is set in one place only: the holder list
    # came back empty, and an empty list is an answer.
    #
    # So this finding is not "you lack the right". It is "nobody holds it".
    if capabilities.get("has_disk_operator") is False:
        found.append(
            Finding(
                id="disk_operator_unassigned",
                severity="medium",
                area="management",
                evidence={
                    "right": "SeDiskOperatorPrivilege",
                    "holders": [],
                    "grant_command": _grant_command(capabilities),
                },
            )
        )

    broad = _broad_holders(capabilities.get("disk_operator_sids") or [])
    if broad:
        names = capabilities.get("disk_operators") or []
        found.append(
            Finding(
                id="disk_operator_broadly_granted",
                severity="high",
                area="management",
                evidence={
                    "right": "SeDiskOperatorPrivilege",
                    "broad_holders": broad,
                    "broad_holder_names": list(names),
                    "holders_total": len(capabilities.get("disk_operator_sids") or []),
                    "convention": [*BROAD_TRUSTEES, "*-513", "*-514"],
                    "kind": "convention",
                },
            )
        )

    return found


def _broad_holders(sids: list[str]) -> list[str]:
    """The holders that mean "anyone who can sign in".

    Matched on SIDs, never on names: the same group is ``BUILTIN\\Users`` on one
    server and ``VORDEFINIERT\\Benutzer`` on the next, so a name check would
    miss it on a localised server and fire on any server where somebody called
    a group "Users".
    """
    found: list[str] = []
    for sid in sids:
        if sid in BROAD_TRUSTEES:
            found.append(sid)
            continue
        match = _DOMAIN_SID_RE.match(sid)
        if match and int(match.group(1)) in BROAD_RIDS:
            found.append(sid)
    return found


def _grant_command(capabilities: dict[str, Any]) -> str | None:
    """The command from the capability notes, if one is there.

    Lifted out of the note's params rather than composed here: the note already
    carries a command naming a group that exists on this server, and a second
    place assembling one is a second place to get the domain wrong.
    """
    for note in capabilities.get("notes") or []:
        params = note.get("params") or {}
        command = params.get("command")
        if command:
            return str(command)
    return None


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


def _transport(transport: dict[str, Any], server: dict[str, Any]) -> list[Finding]:
    found: list[Finding] = []

    if transport.get("identity_verified") is False:
        found.append(
            Finding(
                id="transport_peer_unverified",
                severity="low",
                area="transport",
                evidence={
                    "auth": transport.get("auth"),
                    "identity_verified": False,
                    "signed": transport.get("signed"),
                    "encrypted": transport.get("encrypted"),
                    "server_name": transport.get("server_name"),
                    # So a reader can see which they have: on a standalone
                    # server NTLM is the only thing on offer, which makes this
                    # a property of the deployment rather than a mistake. Hence
                    # low.
                    "mode": server.get("mode"),
                },
            )
        )

    # A fact row rather than a problem. `scope` is the load-bearing key: both
    # of these describe SAMFSCON's end of the connection — signing is required
    # client-side and encryption is a container setting — so without it the row
    # reads as "the server requires signing" and hands a server with
    # `server signing = auto` a clean bill it has not earned.
    found.append(
        Finding(
            id="transport_this_session",
            severity="info",
            area="transport",
            evidence={
                "scope": "this_connection",
                "auth": transport.get("auth"),
                "signed": transport.get("signed"),
                "encrypted": transport.get("encrypted"),
                "identity_verified": transport.get("identity_verified"),
                "server_name": transport.get("server_name"),
            },
        )
    )
    return found


# ---------------------------------------------------------------------------
# Shares
# ---------------------------------------------------------------------------


def _shares(
    entries: list[dict[str, Any]],
    registry: dict[str, Any] | None,
    *,
    suppress_not_served: bool,
) -> list[Finding]:
    found: list[Finding] = []

    for entry in entries:
        name = str(entry.get("name") or "")
        stored = _stored(entry)
        if stored is None:
            # No option rule may speak for this share. unreadable_shares names
            # it instead, so the silence has a stated cause.
            continue
        found.extend(_share_options(name, stored))

    found.extend(_share_paths(entries))
    if not suppress_not_served:
        found.extend(_configured_not_served(entries, registry))
    return found


def _roots(roots: dict[str, bool | None]) -> list[Finding]:
    """Shares whose own directory refuses this account.

    The share exists, the registry key is right, and nothing can be put in it.
    That combination produces no other finding on this page — every rule above
    reads configuration, and this one is about the file system underneath it,
    which is the half a console managing shares over the network does not own.

    Only a decided ``False`` becomes a finding. ``None`` is the probe saying it
    could not ask, and a report that turned that into "you cannot write here"
    would be inventing the very kind of fault it exists to find.
    """
    found: list[Finding] = []
    for name in sorted(roots):
        if roots[name] is not True and roots[name] is not None:
            found.append(
                Finding(
                    id="share_root_not_writable",
                    severity="medium",
                    area="shares",
                    subject=name,
                    evidence={
                        # Named so the finding can be checked: this is what the
                        # server answered to an open for add-file and
                        # add-subdirectory, not something worked out from the
                        # entries naming this account.
                        "asked": "create a file or folder in the share root",
                        "answer": "refused",
                        "asked_of": "the server, by opening a handle",
                        "account_groups_included": True,
                    },
                )
            )
    return found


def _share_options(name: str, stored: dict[str, str]) -> list[Finding]:
    found: list[Finding] = []

    guest = _flag(stored, "guest ok")
    read_only = _flag(stored, "read only")

    if guest is True and read_only is False:
        found.append(
            Finding(
                id="share_guest_writable",
                severity="high",
                area="shares",
                subject=name,
                evidence={
                    "option": "guest ok",
                    "value": "yes",
                    "read_only": stored.get("read only"),
                    "observed_in": "share_registry_key",
                    "global_readable": False,
                },
            )
        )
    elif guest is True:
        # read only absent means nothing: Samba defaults it to yes, and a
        # global can flip it. So this falls back to the milder finding rather
        # than inferring writable.
        found.append(
            Finding(
                id="share_guest_ok",
                severity="medium",
                area="shares",
                subject=name,
                evidence={
                    "option": "guest ok",
                    "value": "yes",
                    "read_only": stored.get("read only"),
                    "observed_in": "share_registry_key",
                    "global_readable": False,
                },
            )
        )

    if _flag(stored, "wide links") is True:
        found.append(
            Finding(
                id="share_wide_links",
                severity="high",
                area="shares",
                subject=name,
                evidence={
                    "wide_links": stored.get("wide links"),
                    "follow_symlinks": stored.get("follow symlinks"),
                    # The null is the point. Samba silently disables wide links
                    # while unix extensions is on, and that option is global
                    # only — so the finding names what it read and what it
                    # could not.
                    "unix_extensions": None,
                    "unix_extensions_note": "global_only",
                },
            )
        )

    masks = _world_writable_masks(stored)
    if masks["options"]:
        found.append(
            Finding(
                id="share_create_mask_world_writable",
                severity="medium",
                area="shares",
                subject=name,
                evidence={
                    "options": masks["options"],
                    "world_write": WORLD_WRITE,
                    # A value that would not parse is listed rather than
                    # counted clean, but it does not on its own make a finding:
                    # "we could not read this mask" is not "this mask is open".
                    "unparsed": masks["unparsed"],
                },
            )
        )

    force_user = (stored.get("force user") or "").strip()
    if force_user:
        root = force_user.lower() in {"root", "0"}
        found.append(
            Finding(
                id="share_force_user_root" if root else "share_force_user",
                severity="high" if root else "low",
                area="shares",
                subject=name,
                evidence={"option": "force user", "value": force_user},
            )
        )

    unrecognised = _unrecognised_hosts(stored)
    if unrecognised:
        found.append(
            Finding(
                id="share_hosts_allow_unparsable",
                severity="medium",
                area="shares",
                subject=name,
                evidence={
                    "unrecognised": unrecognised,
                    "values": {
                        option: stored[option]
                        for option in ("hosts allow", "hosts deny")
                        if option in stored
                    },
                    # This is the rule most likely to be wrong about a legal
                    # value, so what it accepted is printed beside what it
                    # refused.
                    "recognised_forms": [
                        "address",
                        "cidr",
                        "netmask",
                        "prefix",
                        "hostname",
                        "@netgroup",
                        "ALL",
                        "LOCAL",
                        "EXCEPT",
                    ],
                },
            )
        )

    deny = (stored.get("hosts deny") or "").strip().upper()
    if deny and "hosts allow" not in stored and ("ALL" in deny or "0.0.0.0/0" in deny):
        found.append(
            Finding(
                id="share_hosts_deny_without_allow",
                severity="low",
                area="shares",
                subject=name,
                evidence={
                    "hosts_deny": stored.get("hosts deny"),
                    # Capped at low, and the null says why: a global
                    # `hosts allow` would make this correct, and that is the
                    # one file this console cannot read.
                    "hosts_allow": None,
                    "global_readable": False,
                },
            )
        )

    if name.endswith("$") and _flag(stored, "browseable") is True:
        found.append(
            Finding(
                id="share_hidden_name_browseable",
                severity="low",
                area="shares",
                subject=name,
                evidence={"name": name, "browseable": stored.get("browseable")},
            )
        )

    found.extend(_vfs_options_without_module(name, stored))
    return found


def _world_writable_masks(stored: dict[str, str]) -> dict[str, Any]:
    """Which mode options grant write to everybody, and which would not parse.

    A value that will not parse as octal is never counted clean. Anything this
    console wrote is canonical, because the option catalogue normalises it on
    the way in — but a value somebody typed into smb.conf by hand may not be.
    """
    offending: dict[str, str] = {}
    unparsed: list[str] = []

    for option in MASK_OPTIONS:
        raw = stored.get(option)
        if raw is None:
            continue
        try:
            mode = int(raw.strip(), 8)
        except ValueError:
            unparsed.append(option)
            continue
        if mode & WORLD_WRITE:
            offending[option] = raw.strip()

    return {"options": offending, "unparsed": unparsed}


def _vfs_options_without_module(name: str, stored: dict[str, str]) -> list[Finding]:
    """Options that need a VFS module the share does not load.

    Only when the key carries ``vfs objects`` itself. A share-level value
    *replaces* the global one rather than adding to it, so a share that sets it
    is decidable — and one carrying ``recycle:keeptree`` with no ``vfs objects``
    at all inherits the global, which this console cannot read.

    One finding per missing module rather than per option: five ``recycle:*``
    settings with no recycle module is one problem. Two missing modules on one
    share are two findings, which is right.
    """
    from samfscon.srv import shareconf

    if "vfs objects" not in stored:
        return []

    loaded = set(shareconf.vfs_modules(stored))
    missing: dict[str, list[str]] = {}

    for option in stored:
        spec = shareconf.BY_NAME.get(option)
        if spec is None or spec.requires_vfs is None:
            continue
        if spec.requires_vfs not in loaded:
            missing.setdefault(spec.requires_vfs, []).append(option)

    return [
        Finding(
            id="share_vfs_option_without_module",
            severity="medium",
            area="shares",
            subject=name,
            evidence={
                "requires": module,
                "options": sorted(options),
                "vfs_objects": stored.get("vfs objects"),
                "observed_in": "share_registry_key",
            },
        )
        for module, options in sorted(missing.items())
    ]


def _share_paths(entries: list[dict[str, Any]]) -> list[Finding]:
    """Overlapping, duplicated and sensitive paths.

    Cross-share and pure. Possible at all only because the share reader strips
    the drive letter srvsvc fabricates — comparing `C:/tank/a` against
    `/tank/a` would find nothing.

    Case-sensitive: the filesystem underneath is POSIX, and `/Tank` and `/tank`
    are two directories.
    """
    disks = [
        (str(entry.get("name") or ""), _normalise(entry.get("path")), entry)
        for entry in entries
        if entry.get("type") == "disk"
    ]
    known = [(name, path, entry) for name, path, entry in disks if path]
    unknown = len(disks) - len(known)

    found: list[Finding] = []

    by_path: dict[str, list[str]] = {}
    for name, path, _entry in known:
        by_path.setdefault(path, []).append(name)

    for name, path, entry in known:
        others = [other for other in by_path[path] if other != name]
        if others:
            found.append(
                Finding(
                    id="share_path_duplicate",
                    severity="medium",
                    area="shares",
                    subject=name,
                    evidence={
                        "path": path,
                        "others": sorted(others),
                        "this_read_only": _option(entry, "read only"),
                        # Never treated as non-overlapping: a share whose path
                        # srvsvc did not report is one this rule could not
                        # compare, and the count says how many.
                        "paths_unknown": unknown,
                    },
                )
            )

        for other_name, other_path, other_entry in known:
            if other_name == name or other_path == path:
                continue
            # On a component boundary, so /tank/projects contains
            # /tank/projects/2026 and not /tank/projects-old.
            if path.startswith(other_path.rstrip("/") + "/"):
                found.append(
                    Finding(
                        id="share_path_nested",
                        severity="medium",
                        area="shares",
                        subject=name,
                        evidence={
                            "path": path,
                            "within": other_name,
                            "other_path": other_path,
                            "this_read_only": _option(entry, "read only"),
                            "other_read_only": _option(other_entry, "read only"),
                            "paths_unknown": unknown,
                        },
                    )
                )

        matched = _sensitive(path)
        if matched is not None:
            where, severity = matched
            found.append(
                Finding(
                    id="share_path_sensitive",
                    severity=severity,
                    area="shares",
                    subject=name,
                    evidence={
                        "path": path,
                        "matched": where,
                        "convention": [list(item) for item in SENSITIVE_PATHS],
                        "kind": "convention",
                    },
                )
            )

    return found


def _configured_not_served(
    entries: list[dict[str, Any]], registry: dict[str, Any] | None
) -> list[Finding]:
    """Registry sections the server is not publishing, where it says why.

    The conjunction is deliberate. Absence from the live list has at least two
    other causes this console cannot tell apart: a stored section that is not a
    share at all, and smbd not having re-read the registry yet. ``available =
    no`` is the one cause that is both readable and sufficient.
    """
    if registry is None:
        return []

    live = {str(entry.get("name") or "").lower() for entry in entries}
    found: list[Finding] = []

    for section, options in sorted((registry.get("sections") or {}).items()):
        if section.lower() in live or section.lower() == "global":
            continue
        if _flag(options, "available") is not False:
            continue
        found.append(
            Finding(
                id="share_configured_not_served",
                severity="medium",
                area="shares",
                subject=section,
                evidence={
                    "available": options.get("available"),
                    "in_registry": True,
                    "in_live_list": False,
                    "registry_shares_served": registry.get("served"),
                },
            )
        )
    return found


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def _sessions(entries: list[dict[str, Any]]) -> list[Finding]:
    """Guest sessions, which are an observation rather than an inference.

    A guest session connected right now is proof that guest access works
    somewhere, whatever any configuration file says — so this fires even when
    the option sweep found nothing at all. A separate id from
    ``share_guest_ok`` because it is a different kind of fact, reached by a
    different route.
    """
    return [
        Finding(
            id="guest_session_present",
            severity="medium",
            area="sessions",
            subject=str(entry.get("client") or entry.get("user") or ""),
            evidence={
                "client": entry.get("client"),
                "user": entry.get("user"),
                "open_files": entry.get("open_files"),
                "connected_seconds": entry.get("connected_seconds"),
            },
        )
        for entry in entries
        if entry.get("guest") is True
    ]


# ---------------------------------------------------------------------------
# What the interface needs beside the findings
# ---------------------------------------------------------------------------


def unreadable_shares(entries: list[dict[str, Any]]) -> list[Unreadable]:
    """The shares whose configuration nobody could read.

    Derived from the same records the rules judged, so the list the interface
    shows and the silence in the findings have one cause between them.
    """
    return [
        Unreadable(
            area="shares",
            subject=str(entry.get("name") or ""),
            reason=str(entry.get("config_unreadable_reason") or "configuration_not_in_registry"),
        )
        for entry in entries
        if _stored(entry) is None
    ]


def coverage(entries: list[dict[str, Any]]) -> dict[str, int]:
    """How much of the server the findings actually speak for.

    The counters the view needs so the list cannot be misread by layout. Nine
    silent shares out of thirteen is not nine clean shares, and a report that
    does not say so is one that reads as a clean bill of health.
    """
    total = len(entries)
    readable = sum(1 for entry in entries if _stored(entry) is not None)
    return {
        "shares_total": total,
        "shares_with_readable_configuration": readable,
        "shares_without_readable_configuration": total - readable,
    }


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------


def _option(entry: dict[str, Any], name: str) -> str | None:
    stored = _stored(entry)
    return None if stored is None else stored.get(name)


def _normalise(path: Any) -> str:
    if not isinstance(path, str) or not path:
        return ""
    trimmed = path.rstrip("/")
    return trimmed or "/"


def _sensitive(path: str) -> tuple[str, str] | None:
    for where, severity in SENSITIVE_PATHS:
        if where == "/":
            if path == "/":
                return where, severity
            continue
        if path == where or path.startswith(where + "/"):
            return where, severity
    return None


_LABEL = r"[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?"
# A host name, or a domain suffix written with a leading dot.
_HOSTNAME_RE = re.compile(rf"^\.?{_LABEL}(\.{_LABEL})*\.?$")
_PREFIX_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){0,2}\.$")
_KEYWORDS = {"ALL", "LOCAL", "EXCEPT", "NONE"}


def _unrecognised_hosts(stored: dict[str, str]) -> dict[str, list[str]]:
    """Entries in hosts allow / hosts deny that match no form Samba accepts.

    Both options in one rule, because a typo in either is the same fault and
    two rows for one line is noise.
    """
    found: dict[str, list[str]] = {}
    for option in ("hosts allow", "hosts deny"):
        raw = stored.get(option)
        if raw is None:
            continue
        bad = [item for item in re.split(r"[,\s]+", raw.strip()) if item and not _host_entry(item)]
        if bad:
            found[option] = bad
    return found


def _host_entry(item: str) -> bool:
    if item.upper() in _KEYWORDS:
        return True
    if item.startswith("@"):
        return len(item) > 1
    if _PREFIX_RE.match(item):
        return True
    for parse in (ipaddress.ip_address, lambda value: ipaddress.ip_network(value, strict=False)):
        try:
            parse(item)
            return True
        except ValueError:
            continue
    return bool(_HOSTNAME_RE.match(item))
