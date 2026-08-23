"""Going and getting what the rules judge.

:mod:`samfscon.core.findings` is pure on purpose; this is the half that makes
round trips. Keeping them apart is what lets every rule be tested without a
server — and having exactly one gatherer is what makes the screen and any report
describe **one reading** of the server rather than two moments that drifted.

**Every section is read in its own try, and a failure costs only that section.**
A permission gap on one call must not take the page down, and it must not
silently shrink the report either: what could not be read is named in
``unreadable``, beside the findings and never inside them.

**Nothing here is probed by connecting to it.** Whether each share can actually
be opened, whether its descriptor contradicts its file permissions, whether
inheritance reaches its children — all of that needs a tree connect per share,
which is a fresh session setup per share, and the calls for it are specified and
not built. So the report says nothing about connectivity, and *that is not the
same as saying nothing is wrong with it*. It is carried as a zero in
``coverage`` rather than as silence, because a reader counts what is on the
screen and a screen that lists no broken shares is read as a server with none.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from samfscon.core import findings
from samfscon.srv.connection import ServerConnection

logger = logging.getLogger(__name__)

AREAS = findings.AREAS


def collect(conn: ServerConnection) -> dict[str, Any]:
    """One reading of the server: the findings, and everything they rest on.

    The values travel with the findings rather than being fetched again by
    whoever wants to show them. A report assembled from a second set of reads
    would carry a timestamp that is true of none of it.
    """
    unreadable: list[findings.Unreadable] = []

    # 1. Free. Both are recorded at connect time and cannot fail here.
    server = conn.info.describe()
    transport = conn.transport.describe()

    capabilities = _capabilities(conn, unreadable)
    facts = _facts(conn, unreadable)
    shares, registry = _shares(conn, unreadable)
    sessions = _sessions(conn, unreadable)
    roots = _roots(conn, shares, unreadable)

    found = findings.evaluate(
        capabilities=capabilities,
        registry=registry,
        server=server,
        transport=transport,
        shares=shares,
        sessions=sessions,
        roots=roots,
    )

    if shares is not None:
        unreadable.extend(findings.unreadable_shares(shares))

    return {
        # UTC with the offset carried rather than assumed. A report read in
        # another timezone has to be able to say when it was taken.
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "findings": [item.describe() for item in found],
        "unreadable": [item.describe() for item in unreadable],
        "coverage": _coverage(shares, roots),
        # What the findings were decided from, so any of them can be checked.
        "server": server,
        "transport": transport,
        "capabilities": capabilities,
        "facts": facts,
        "registry": registry,
        "shares": shares or [],
        "sessions": sessions or [],
    }


def gather(conn: ServerConnection) -> list[dict[str, Any]]:
    """Just the findings, for a caller that wants nothing else."""
    return collect(conn)["findings"]


# ---------------------------------------------------------------------------
# The sections
# ---------------------------------------------------------------------------


def _capabilities(
    conn: ServerConnection, unreadable: list[findings.Unreadable]
) -> dict[str, Any] | None:
    from samfscon.srv import diagnostics

    try:
        described = diagnostics.capabilities(conn).describe()
    except Exception:
        logger.warning("the capability probe failed; the management rules are skipped")
        logger.debug("capabilities failed", exc_info=True)
        unreadable.append(findings.Unreadable("management", "", "capabilities_unreadable"))
        return None

    # Two states that come out of the data rather than out of a failure, and
    # both belong here. A rule that stayed silent on them would be indis-
    # tinguishable from one that looked and found nothing wrong.
    if described.get("has_disk_operator") is None:
        unreadable.append(findings.Unreadable("management", "", "privilege_unconfirmed"))
    if described.get("registry_config") is None:
        unreadable.append(findings.Unreadable("management", "", "registry_state_unknown"))

    return described


def _facts(conn: ServerConnection, unreadable: list[findings.Unreadable]) -> dict[str, Any] | None:
    from samfscon.srv import diagnostics

    try:
        return diagnostics.server_facts(conn)
    except Exception:
        # Level 102 needs more rights than 101, and this is the one function in
        # that module that raises. One permission gap costs this block.
        logger.debug("server facts refused", exc_info=True)
        unreadable.append(findings.Unreadable("management", "", "server_facts_unreadable"))
        return None


def _shares(
    conn: ServerConnection, unreadable: list[findings.Unreadable]
) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    """The share list merged with the registry, and what the registry says.

    Returns ``(None, None)`` when the share list itself could not be read —
    everything downstream of it is then skipped rather than guessed at.
    """
    from samfscon.srv import registry as registry_module
    from samfscon.srv import shareconf
    from samfscon.srv import shares as shares_module

    try:
        # Administrative shares are excluded: IPC$ and its siblings refuse the
        # per-share calls by design, and a sweep must not spend a round trip
        # finding that out.
        listed = shares_module.list_shares(conn)
    except Exception:
        logger.warning("the share list could not be read; every share rule is skipped")
        logger.debug("list_shares failed", exc_info=True)
        unreadable.append(findings.Unreadable("shares", "", "shares_unreadable"))
        return None, None

    stored: dict[str, dict[str, str]] | None
    try:
        stored = registry_module.read_all(conn)
    except Exception:
        logger.debug("the registry could not be swept", exc_info=True)
        # One row, not one per share. The cause is the same for all of them,
        # and thirteen identical lines would bury the findings.
        unreadable.append(findings.Unreadable("shares", "", "registry_unreadable"))
        stored = None

    by_name = {name.lower(): values for name, values in (stored or {}).items()}
    merged: list[dict[str, Any]] = []

    for share in listed:
        described = share.describe()
        key = share.name.lower()
        options = by_name.get(key)
        merged.append(
            {
                "name": described["name"],
                "type": described["type"],
                "path": described["path"],
                "comment": described["comment"],
                "editable": described["editable"],
                # Distinct from `editable`, which is False both when a share
                # has no key and when the whole registry was unreadable. The
                # rules need those apart: one is a fact about the share, the
                # other is a fact about this session.
                "config_readable": stored is not None and options is not None,
                "options": dict(options or {}),
                "vfs": shareconf.vfs_modules(options or {}),
            }
        )

    share_sections = sorted(
        name for name in (stored or {}) if name.lower() != registry_module.GLOBAL_SECTION
    )
    live = {share.name.lower() for share in listed}
    matches = sum(1 for name in share_sections if name.lower() in live)

    registry_state: dict[str, Any] | None = None
    if stored is not None:
        registry_state = {
            "readable": True,
            "sections": {
                name: values
                for name, values in stored.items()
                if name.lower() != registry_module.GLOBAL_SECTION
            },
            "share_sections": share_sections,
            "share_section_count": len(share_sections),
            "global_section_present": any(
                name.lower() == registry_module.GLOBAL_SECTION for name in stored
            ),
            "live_matches": matches,
            # None when there is nothing to compare. A registry holding only
            # the global section proves nothing either way, which is the thing
            # the share reader used to get wrong.
            "served": bool(matches) if share_sections else None,
        }

    return merged, registry_state


def _sessions(
    conn: ServerConnection, unreadable: list[findings.Unreadable]
) -> list[dict[str, Any]] | None:
    from samfscon.srv import sessions as sessions_module

    try:
        return [session.describe() for session in sessions_module.list_sessions(conn)]
    except Exception:
        logger.debug("the session list could not be read", exc_info=True)
        unreadable.append(findings.Unreadable("sessions", "", "sessions_unreadable"))
        return None


#: How many shares one report will open a handle on. A server with two hundred
#: shares would otherwise make two hundred SMB connections for one page. What
#: was left out is reported rather than quietly dropped — a coverage number
#: that silently stopped counting is the thing this whole block exists against.
MAX_ROOT_PROBES = 40


def _roots(
    conn: ServerConnection,
    shares: list[dict[str, Any]] | None,
    unreadable: list[findings.Unreadable],
) -> dict[str, bool | None] | None:
    """Whether this session may create anything in each share's root.

    Asked of the server, one open per share, because the arithmetic that could
    answer it locally cannot see group membership: on a share whose only entry
    is for Domain Admins it would tell a member of Domain Admins they have no
    access. A finding built on that would be wrong on exactly the shares that
    are set up properly.
    """
    from samfscon.srv import acl

    if shares is None:
        return None

    answers: dict[str, bool | None] = {}
    for entry in shares[:MAX_ROOT_PROBES]:
        name = str(entry.get("name") or "")
        if not name:
            continue
        try:
            answers[name] = acl.probe_access(conn, name, "", acl.PROBE_CREATE)
        except Exception:
            logger.debug("the root of %s could not be probed", name, exc_info=True)
            answers[name] = None

    dropped = max(0, len(shares) - MAX_ROOT_PROBES)
    if dropped:
        unreadable.append(findings.Unreadable("shares", "", "too_many_shares_to_probe"))
    return answers


def _coverage(
    shares: list[dict[str, Any]] | None, roots: dict[str, bool | None] | None
) -> dict[str, Any]:
    """How much of the server the findings speak for.

    ``shares_probed`` counts the ones whose root gave a decided answer — not
    the ones an open was attempted on. A share that could not be asked is not
    covered, and counting it would make the number say more than it knows.
    """
    counts = findings.coverage(shares or [])
    decided = [name for name, answer in (roots or {}).items() if answer is not None]
    counts.update(
        {
            "shares_probed": len(decided),
            "shares_with_permissions_read": 0,
            # True only when at least one share gave a decided answer.
            # Attempting and learning nothing is not examining: the flag is
            # what suppresses "nothing was probed" on the screen, and it must
            # not be suppressed by a round of questions that all went
            # unanswered.
            "connectivity_examined": bool(decided),
            # Still zero and still says why: nothing here reads a share's own
            # descriptor, so the report is silent about how file rights stand
            # against share rights — and silence on a screen reads as "fine".
            "permissions_examined": False,
        }
    )
    return counts
