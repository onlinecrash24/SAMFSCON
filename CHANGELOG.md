# Changelog

Generated from the annotated git tags by `scripts/build_changelog.py` — the
tag is the source, this file is a copy of it. Do not edit it by hand; the next
release overwrites it.

Each entry is the release note as it was written at the time, unedited. Where
one says something was not verified, that sentence is part of the record and
stays.

Images for every version are on GHCR: `ghcr.io/onlinecrash24/samfscon:0.2.0`
pins one exactly, `:0.2` follows the minor series, `:latest` the newest
release.

---

## 0.2.0 — 2026-08-23

The first release, and the one that makes this console feel like its sibling
again. SAMFSCON was forked from SAMADCON in August and inherited its shell;
ninety commits later that shell had been rebuilt there and not here. This
brings it across, and brings the release machinery with it.

**The console has a strip across the top.** Six consoles that used to be six
buttons in the left column, occupying the space a tree belongs in. The column
now shows what the open console navigates — for four of them, nothing, so it is
kept out of the grid rather than drawn empty. The boundaries between panes can
be dragged, and each console remembers its own widths.

**More than one thing can be open at once.** A share's property sheet opens in
a window with a title bar, a taskbar entry and a count on its console tab.
Comparing two shares' permissions was previously a matter of clicking back and
forth and remembering. A local group opens the same way, and it is the first
place a group's members are resolved from SIDs into names.

**Right-click works, and never offers what cannot be done.** No disconnect on a
session and no unlock on an account, because no endpoint performs either; no
delete on a share defined in the server's text smb.conf, because the server
would refuse it. The offer is a pure function with its own tests.

Deleting a share asks first. It never did, which was survivable while it meant
opening the share and reaching the footer; on a menu it is one click from the
row above it.

**Three faults inherited at the fork, all found by tools added here.**

The Kerberos ticket's expiry was read out of klist and stamped UTC, on the
assumption that the container runs in UTC — true as shipped and of nothing
else. With the offset running forwards the session outlived the ticket, so
calls failed partway through somebody's work rather than at the sign-in screen.
TZ is pinned now.

Sixteen advisories sat under the declared dependency floors, none of which an
audit of installed packages could have seen: `>=` resolves to the newest
release, so a fresh build was never exposed and a machine that installed months
ago was. python-multipart went entirely — declared from the first commit and
never used, since nothing here takes an upload.

The ports published on every interface the host has. They bind to loopback
now unless SAMFSCON_BIND says otherwise. **This changes an existing
installation**: a container reached from another machine stops answering until
that variable is set or a reverse proxy is put in front — which it can now be
told about, so the audit log records the caller rather than the proxy.

**What was not verified.** The interface changes were checked by measurement,
not by looking: pane geometry, the four grid shapes at two widths, the stacking
order and the parsed rule list, all read out of a browser that could not
produce a screenshot. Nobody has yet clicked through the new shell against a
running server. Milestone 1's write paths for share and file permissions remain
unexercised outside their unit tests, as they were in 0.1.0.

One defect this release found in itself is worth recording, because it is the
reason for the check that found it: a missing closing brace in the tab-strip
stylesheet made every later rule parse as a descendant of one selector,
including the window layer's. The build was green. Text search in the bundle
was green. Only reading the browser's own cssRules showed it.
