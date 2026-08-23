"""The rules, and the three-valued discipline they are built on.

Every rule here is pure, so all of this runs without a server and without the
Samba bindings. That is the point of the module's shape and it is why these
tests can be thorough.

What they are mostly about is `None`. Almost every input a rule reads has three
states — yes, no, and nobody could tell — and collapsing the third into the
second is the fault this project has fixed six times in other modules. Here it
would be worse than elsewhere: a diagnostics report is read as a verdict, so a
rule that treats "not in this registry key" as "not set on this server" hands
somebody a clean bill of health for a guest-writable share.

So for each rule with an unknown input there are two tests: one that it fires
on the value that was read, and one that it stays silent on the value that was
not. The second is the one that would rot.
"""

from __future__ import annotations

from typing import Any

import pytest

from samfscon.core import findings
from samfscon.core.findings import Finding, coverage, evaluate, unreadable_shares


def ids(found: list[Finding]) -> list[str]:
    return [item.id for item in found]


def one(found: list[Finding], finding_id: str) -> Finding:
    matches = [item for item in found if item.id == finding_id]
    assert len(matches) == 1, f"expected exactly one {finding_id}, got {ids(found)}"
    return matches[0]


def share(name: str = "projects", **over: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": name,
        "type": "disk",
        "path": f"/tank/{name}",
        "config_readable": True,
        "options": {},
    }
    entry.update(over)
    return entry


# ===========================================================================
# The contract of the module itself
# ===========================================================================


def test_nothing_at_all_produces_nothing() -> None:
    """A caller that could read nothing gets no findings, not a clean report."""
    assert evaluate() == []


def test_every_id_a_rule_can_emit_is_declared() -> None:
    """IDS is what the message catalogue and the interface check against.

    A rule emitting an id that is not in the tuple would render as a raw
    identifier in the interface, in both languages.
    """
    found = _everything()
    for item in found:
        assert item.id in findings.IDS, f"{item.id} is not declared in IDS"


def test_every_finding_names_a_known_severity_and_area() -> None:
    for item in _everything():
        assert item.severity in findings.SEVERITIES
        assert item.area in findings.AREAS


def test_worst_first_then_by_subject() -> None:
    """Severity wins, because the report is read top-down.

    Within a severity the subject groups, because a reader wants one share's
    problems together and sorting by id alone interleaves every share.
    """
    found = _everything()
    order = {name: index for index, name in enumerate(findings.SEVERITIES)}
    keys = [(order[item.severity], item.subject.lower(), item.id) for item in found]
    assert keys == sorted(keys)


def _everything() -> list[Finding]:
    return evaluate(
        capabilities={
            "registry_config": False,
            "has_disk_operator": False,
            "disk_operator_sids": ["S-1-5-32-545"],
            "disk_operators": ["BUILTIN\\Users"],
            "notes": [{"code": "no_disk_operator", "params": {"command": "net rpc rights grant"}}],
        },
        registry={"served": None, "sections": {}},
        transport={"auth": "ntlm", "identity_verified": False, "signed": True, "encrypted": False},
        server={"mode": "standalone"},
        shares=[
            share(options={"guest ok": "yes", "read only": "no", "wide links": "yes"}),
            share("etc", path="/etc"),
            share("inner", path="/tank/projects/2026"),
            share("hidden$", options={"browseable": "yes"}),
        ],
        sessions=[{"guest": True, "client": "10.0.0.42"}],
    )


# ===========================================================================
# Management — every one of these has a None that must not fire
# ===========================================================================


def test_registry_config_absent_fires_on_a_store_that_is_not_there() -> None:
    found = evaluate(capabilities={"registry_config": False, "notes": []})
    assert "registry_config_absent" in ids(found)


def test_registry_config_absent_is_silent_when_the_probe_was_refused() -> None:
    """None is not False.

    A refused probe leaves this None, and a rule written `if not ...` would
    send an administrator to add `include = registry` to an smb.conf that
    already has it.
    """
    found = evaluate(capabilities={"registry_config": None, "notes": []})
    assert "registry_config_absent" not in ids(found)


def test_registry_shares_not_served_fires_only_on_a_measured_false() -> None:
    served = evaluate(
        capabilities={},
        registry={
            "served": False,
            "share_sections": ["a"],
            "share_section_count": 1,
            "live_matches": 0,
            "sections": {},
        },
    )
    assert "registry_shares_not_served" in ids(served)

    # None means there was nothing to compare — a registry holding only the
    # global section proves nothing either way.
    unknown = evaluate(capabilities={}, registry={"served": None, "sections": {}})
    assert "registry_shares_not_served" not in ids(unknown)


def test_disk_operator_unassigned_is_about_the_server_not_about_you() -> None:
    """False means the holder list came back empty. None means it could not
    be matched against this session, which happens whenever nested group
    membership is in the way — and telling the one person who can fix
    everything that they may not is the worst version of this mistake.
    """
    assert "disk_operator_unassigned" in ids(evaluate(capabilities={"has_disk_operator": False}))
    assert "disk_operator_unassigned" not in ids(evaluate(capabilities={"has_disk_operator": None}))


@pytest.mark.parametrize(
    "sid",
    [
        "S-1-1-0",  # Everyone
        "S-1-5-11",  # Authenticated Users
        "S-1-5-32-545",  # BUILTIN\Users
        "S-1-5-21-1-2-3-513",  # Domain Users
        "S-1-5-21-1-2-3-514",  # Domain Guests
    ],
)
def test_a_broad_holder_of_the_privilege_is_found_by_sid(sid: str) -> None:
    found = evaluate(capabilities={"disk_operator_sids": [sid], "disk_operators": []})
    assert "disk_operator_broadly_granted" in ids(found)


@pytest.mark.parametrize(
    "sid",
    [
        "S-1-5-32-544",  # BUILTIN\Administrators — the point of the privilege
        "S-1-5-21-1-2-3-512",  # Domain Admins
        "S-1-5-21-1-2-3-1104",  # somebody's account
    ],
)
def test_a_narrow_holder_is_not_a_finding(sid: str) -> None:
    found = evaluate(capabilities={"disk_operator_sids": [sid], "disk_operators": []})
    assert "disk_operator_broadly_granted" not in ids(found)


def test_broad_holders_are_matched_on_sids_and_never_on_names() -> None:
    """A name is localised; a SID is not.

    Matching on names would miss the finding on a German server, where the
    group is VORDEFINIERT\\Benutzer — and fire on any server where somebody
    called a group "Users".
    """
    found = evaluate(
        capabilities={"disk_operator_sids": ["S-1-5-21-1-2-3-1200"], "disk_operators": ["Users"]}
    )
    assert "disk_operator_broadly_granted" not in ids(found)


# ===========================================================================
# Transport
# ===========================================================================


def test_the_session_row_says_whose_connection_it_describes() -> None:
    """Without `scope` this row reads as a statement about the server.

    Signing is required by this client and encryption is a container setting;
    neither says what the server demands of anybody else.
    """
    found = evaluate(transport={"auth": "kerberos", "identity_verified": True, "signed": True})
    row = one(found, "transport_this_session")
    assert row.evidence["scope"] == "this_connection"
    assert row.severity == "info"


def test_an_unverified_peer_is_low_and_carries_the_mode() -> None:
    found = evaluate(
        transport={"auth": "ntlm", "identity_verified": False},
        server={"mode": "standalone"},
    )
    item = one(found, "transport_peer_unverified")
    # Low, because on a standalone server NTLM is the only thing on offer —
    # a property of the deployment rather than a mistake. The mode is in the
    # evidence so a reader can see which they have.
    assert item.severity == "low"
    assert item.evidence["mode"] == "standalone"


# ===========================================================================
# Shares — the option rules, and the silence that is not a pass
# ===========================================================================


def test_a_share_whose_configuration_is_unreadable_produces_no_option_finding() -> None:
    """The invariant, stated as a test.

    A share defined in the text smb.conf has no registry key. Every option
    rule is *unreadable* for it, not clean — and if this ever returned {} the
    whole rule set would pass in silence on exactly the shares nobody can see.
    """
    found = evaluate(shares=[share("textonly", config_readable=False)])
    assert [item.id for item in found if item.area == "shares" and item.subject == "textonly"] == []

    named = unreadable_shares([share("textonly", config_readable=False)])
    assert [item.subject for item in named] == ["textonly"]


def test_guest_ok_fires_on_the_value_and_not_on_its_absence() -> None:
    assert "share_guest_ok" in ids(evaluate(shares=[share(options={"guest ok": "yes"})]))
    # Absent means the global may set it, and this console cannot read that.
    assert "share_guest_ok" not in ids(evaluate(shares=[share(options={})]))
    assert "share_guest_ok" not in ids(evaluate(shares=[share(options={"guest ok": "no"})]))


def test_a_guest_share_is_only_writable_when_the_key_says_so() -> None:
    writable = evaluate(shares=[share(options={"guest ok": "yes", "read only": "no"})])
    assert "share_guest_writable" in ids(writable)
    assert "share_guest_ok" not in ids(writable), "one share, one guest finding"

    # `read only` absent does not mean writable. Samba defaults it to yes, and
    # a global can flip it — so this falls back to the milder finding.
    unknown = evaluate(shares=[share(options={"guest ok": "yes"})])
    assert "share_guest_writable" not in ids(unknown)
    assert "share_guest_ok" in ids(unknown)


def test_a_value_that_is_neither_yes_nor_no_decides_nothing() -> None:
    """Samba's own parser would not honour it either."""
    found = evaluate(shares=[share(options={"guest ok": "maybe"})])
    assert "share_guest_ok" not in ids(found)


def test_wide_links_names_what_it_could_not_read() -> None:
    item = one(evaluate(shares=[share(options={"wide links": "yes"})]), "share_wide_links")
    # Samba silently disables wide links while unix extensions is on, and that
    # option is global-only. The null is the finding admitting it.
    assert item.evidence["unix_extensions"] is None
    assert item.evidence["unix_extensions_note"] == "global_only"


@pytest.mark.parametrize("mode", ["0777", "0666", "0002"])
def test_a_world_writable_mask_is_found(mode: str) -> None:
    found = evaluate(shares=[share(options={"create mask": mode})])
    assert "share_create_mask_world_writable" in ids(found)


@pytest.mark.parametrize("mode", ["0770", "0750", "0644"])
def test_a_mask_that_keeps_others_out_is_not_a_finding(mode: str) -> None:
    found = evaluate(shares=[share(options={"create mask": mode})])
    assert "share_create_mask_world_writable" not in ids(found)


def test_a_mask_that_will_not_parse_is_never_counted_clean() -> None:
    found = evaluate(shares=[share(options={"create mask": "rwxrwxrwx", "directory mask": "0777"})])
    item = one(found, "share_create_mask_world_writable")
    assert item.evidence["unparsed"] == ["create mask"]


def test_an_unparsable_mask_alone_is_not_a_finding() -> None:
    """ "We could not read this mask" is not "this mask is open"."""
    found = evaluate(shares=[share(options={"create mask": "rwxrwxrwx"})])
    assert "share_create_mask_world_writable" not in ids(found)


@pytest.mark.parametrize("value", ["root", "ROOT", "0"])
def test_force_user_root_is_its_own_finding(value: str) -> None:
    found = evaluate(shares=[share(options={"force user": value})])
    assert "share_force_user_root" in ids(found)
    assert "share_force_user" not in ids(found), "never both"


def test_force_user_anybody_else_is_the_milder_one() -> None:
    found = evaluate(shares=[share(options={"force user": "projects"})])
    assert ids([item for item in found if item.subject == "projects"]) == ["share_force_user"]


# ---------------------------------------------------------------------------
# hosts allow / hosts deny — the rule most likely to be wrong about a legal
# value, which is why what it accepts is tested as carefully as what it refuses
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "192.168.1.5",
        "192.168.1.0/24",
        "192.168.1.0/255.255.255.0",
        "192.168.1.",
        "192.168.",
        "127.",
        "2001:db8::1",
        "2001:db8::/32",
        "ALL",
        "LOCAL",
        "ALL EXCEPT 192.168.1.5",
        "@netgroup",
        "host.example.com",
        ".example.com",
        "192.168.1.0/24, 10.0.0.0/8",
    ],
)
def test_a_legal_host_entry_is_not_reported(value: str) -> None:
    found = evaluate(shares=[share(options={"hosts allow": value})])
    assert "share_hosts_allow_unparsable" not in ids(found), value


# Single tokens on purpose. Samba splits this value on whitespace and commas
# and so does the rule, so a phrase would be reported one word at a time.
@pytest.mark.parametrize("value", ["192.168.1.O/24", "host!", "10.0.0.0//8", "-leading-dash"])
def test_an_entry_matching_no_form_is_reported(value: str) -> None:
    found = evaluate(shares=[share(options={"hosts allow": value})])
    item = one(found, "share_hosts_allow_unparsable")
    assert item.evidence["unrecognised"]["hosts allow"] == [value]
    # What it accepted, beside what it refused, so a wrong refusal is arguable.
    assert "cidr" in item.evidence["recognised_forms"]


def test_a_phrase_is_judged_one_entry_at_a_time() -> None:
    """Samba splits on whitespace, so a value is a list and not a sentence.

    Only the entries that match nothing are named; the words beside them that
    happen to be legal host names are not the rule's business.
    """
    found = evaluate(shares=[share(options={"hosts allow": "192.168.1.5 bad!! 10.0.0.0/8"})])
    item = one(found, "share_hosts_allow_unparsable")
    assert item.evidence["unrecognised"]["hosts allow"] == ["bad!!"]


def test_both_host_options_are_one_finding() -> None:
    found = evaluate(shares=[share(options={"hosts allow": "bad!!", "hosts deny": "worse!!"})])
    item = one(found, "share_hosts_allow_unparsable")
    assert set(item.evidence["unrecognised"]) == {"hosts allow", "hosts deny"}


def test_deny_all_without_an_allow_is_capped_at_low() -> None:
    item = one(
        evaluate(shares=[share(options={"hosts deny": "ALL"})]),
        "share_hosts_deny_without_allow",
    )
    # Low, and the null says why: a global `hosts allow` would make this
    # correct, and that is the one file this console cannot read.
    assert item.severity == "low"
    assert item.evidence["hosts_allow"] is None
    assert item.evidence["global_readable"] is False


def test_deny_all_with_an_allow_beside_it_is_not_a_finding() -> None:
    found = evaluate(shares=[share(options={"hosts deny": "ALL", "hosts allow": "192.168.1.0/24"})])
    assert "share_hosts_deny_without_allow" not in ids(found)


# ---------------------------------------------------------------------------
# Hidden names, and VFS options with no module
# ---------------------------------------------------------------------------


def test_a_dollar_share_that_is_browseable_is_not_hidden() -> None:
    found = evaluate(shares=[share("backup$", options={"browseable": "yes"})])
    assert "share_hidden_name_browseable" in ids(found)


def test_a_dollar_share_says_nothing_when_browseable_is_absent() -> None:
    found = evaluate(shares=[share("backup$", options={})])
    assert "share_hidden_name_browseable" not in ids(found)


def test_a_recycle_option_without_the_module_is_found() -> None:
    found = evaluate(
        shares=[
            share(
                options={
                    "vfs objects": "acl_xattr",
                    "recycle:keeptree": "yes",
                    "recycle:repository": ".bin",
                }
            )
        ]
    )
    item = one(found, "share_vfs_option_without_module")
    # One finding per missing module, not per option: five recycle settings
    # with no recycle module is one problem.
    assert item.evidence["requires"] == "recycle"
    assert item.evidence["options"] == ["recycle:keeptree", "recycle:repository"]


def test_a_recycle_option_with_the_module_is_fine() -> None:
    found = evaluate(
        shares=[share(options={"vfs objects": "recycle acl_xattr", "recycle:keeptree": "yes"})]
    )
    assert "share_vfs_option_without_module" not in ids(found)


def test_a_share_that_does_not_set_vfs_objects_is_not_judged() -> None:
    """A share-level value replaces the global one rather than adding to it.

    So a share that sets it is decidable, and one that does not inherits a
    global this console cannot read.
    """
    found = evaluate(shares=[share(options={"recycle:keeptree": "yes"})])
    assert "share_vfs_option_without_module" not in ids(found)


# ---------------------------------------------------------------------------
# Paths — cross-share, and pure
# ---------------------------------------------------------------------------


def test_a_share_inside_another_is_found_on_a_component_boundary() -> None:
    found = evaluate(
        shares=[share("outer", path="/tank/projects"), share("inner", path="/tank/projects/2026")]
    )
    item = one(found, "share_path_nested")
    assert item.subject == "inner"
    assert item.evidence["within"] == "outer"


def test_a_path_that_merely_starts_the_same_is_not_nested() -> None:
    found = evaluate(
        shares=[share("a", path="/tank/projects"), share("b", path="/tank/projects-old")]
    )
    assert "share_path_nested" not in ids(found)


def test_two_shares_on_one_path_each_name_the_other() -> None:
    found = evaluate(shares=[share("a", path="/tank/x"), share("b", path="/tank/x")])
    duplicates = [item for item in found if item.id == "share_path_duplicate"]
    # One per share, so both rows appear in a subject-sorted report.
    assert sorted(item.subject for item in duplicates) == ["a", "b"]


def test_paths_are_compared_case_sensitively() -> None:
    """The filesystem underneath is POSIX. /Tank and /tank are two directories."""
    found = evaluate(shares=[share("a", path="/tank/x"), share("b", path="/Tank/x")])
    assert "share_path_duplicate" not in ids(found)


def test_a_share_with_no_path_is_counted_rather_than_assumed_safe() -> None:
    found = evaluate(
        shares=[share("a", path="/tank/x"), share("b", path="/tank/x"), share("c", path=None)]
    )
    item = next(entry for entry in found if entry.id == "share_path_duplicate")
    assert item.evidence["paths_unknown"] == 1


@pytest.mark.parametrize(
    ("path", "severity"),
    [("/", "high"), ("/etc", "high"), ("/etc/samba", "high"), ("/usr", "medium")],
)
def test_a_sensitive_path_carries_its_severity_and_the_whole_convention(
    path: str, severity: str
) -> None:
    item = one(evaluate(shares=[share("s", path=path)]), "share_path_sensitive")
    assert item.severity == severity
    # A convention, so a reader can disagree with the list rather than with
    # the finding.
    assert item.evidence["kind"] == "convention"
    assert ["/etc", "high"] in item.evidence["convention"]


@pytest.mark.parametrize("path", ["/etcetera", "/tank", "/rootfs", "/var"])
def test_a_path_that_only_looks_sensitive_is_not(path: str) -> None:
    found = evaluate(shares=[share("s", path=path)])
    assert "share_path_sensitive" not in ids(found)


# ---------------------------------------------------------------------------
# Configured and not served
# ---------------------------------------------------------------------------


def test_a_section_disabled_in_the_registry_is_reported() -> None:
    found = evaluate(
        capabilities={},
        registry={"served": True, "sections": {"archive": {"available": "no"}}},
        shares=[share("projects")],
    )
    assert "share_configured_not_served" in ids(found)


def test_a_section_merely_missing_from_the_live_list_is_not() -> None:
    """Absence alone has causes this console cannot tell apart.

    A stored section that is not a share, and smbd not having re-read the
    registry yet, look identical from here. `available = no` is the one cause
    that is both readable and sufficient.
    """
    found = evaluate(
        capabilities={},
        registry={"served": True, "sections": {"archive": {"path": "/tank/archive"}}},
        shares=[share("projects")],
    )
    assert "share_configured_not_served" not in ids(found)


def test_one_cause_gives_one_finding() -> None:
    """If the server ignores its whole registry, every section is missing.

    Reporting each of them as well as the cause is how a report loses its
    reader.
    """
    found = evaluate(
        capabilities={},
        registry={
            "served": False,
            "share_sections": ["archive"],
            "share_section_count": 1,
            "live_matches": 0,
            "sections": {"archive": {"available": "no"}},
        },
        shares=[share("projects")],
    )
    assert "registry_shares_not_served" in ids(found)
    assert "share_configured_not_served" not in ids(found)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def test_a_guest_session_is_an_observation_not_an_inference() -> None:
    """It fires even when the configuration sweep found nothing.

    A guest connected right now is proof guest access works somewhere,
    whatever any file says.
    """
    found = evaluate(
        shares=[share(options={})],
        sessions=[{"guest": True, "client": "10.0.0.42", "user": "nobody", "open_files": 3}],
    )
    item = one(found, "guest_session_present")
    assert item.subject == "10.0.0.42"
    assert item.evidence["user"] == "nobody"


def test_an_ordinary_session_is_not_a_finding() -> None:
    found = evaluate(sessions=[{"guest": False, "client": "10.0.0.42"}])
    assert found == []


# ---------------------------------------------------------------------------
# Coverage — the numbers that stop the list being misread
# ---------------------------------------------------------------------------


def test_coverage_counts_the_shares_nobody_could_read() -> None:
    """Nine silent shares out of thirteen is not nine clean shares."""
    counts = coverage(
        [
            share("a"),
            share("b"),
            share("c", config_readable=False),
            share("d", config_readable=False),
        ]
    )
    assert counts == {
        "shares_total": 4,
        "shares_with_readable_configuration": 2,
        "shares_without_readable_configuration": 2,
    }
