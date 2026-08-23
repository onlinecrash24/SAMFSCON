<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"
            srcset="docs/brand/samfscon-lockup-transparent-dark.svg">
    <img src="docs/brand/samfscon-lockup-transparent-light.svg"
         alt="SAMFSCON — the Samba FileServer console" width="420">
  </picture>
</p>

<p align="center"><em><a href="README.de.md">Deutsche Fassung</a></em></p>

A browser-based management console for Samba **file servers** — standalone as well as domain
members. It replaces the Windows Computer Management console (Shared Folders, Sessions, Open
Files, Local Users and Groups) with a Docker container.

SAMFSCON is the companion to [SAMADCON](https://github.com/onlinecrash24/SAMADCON), which does the
same for a Samba AD domain controller. Same architecture, same security model, same container
shape — the other half of a Samba estate.

It speaks nothing but standard protocols: **SMB and DCE/RPC** — `srvsvc` for shares, sessions and
open files, `samr` for local accounts, `lsarpc` for names and SIDs, `winreg` for the
registry-backed configuration. The container does not have to run on the file server, nothing is
installed on it, and no file of its file system is touched directly.

> Released as **0.2.x**: what is listed under [Milestones](#milestones) is built, and the
> interface is still changing. Each release's notes are in the
> [changelog](CHANGELOG.md).

## Why

There is no equivalent under Linux. `net conf`, `smbstatus`, `smbcacls`, `pdbedit` and
`net rpc share` are five command-line tools that between them cover the job, and the Windows
console that does it in one place needs a domain-joined Windows client.

## Security model

Every administrator signs in with **their own account**, and every operation runs with that
account's rights:

- The tool itself needs **no** privileged service account.
- The server's own permission checks apply exactly as they would to that person at any other
  client. A directory they may not read is one this console cannot list either.
- Every write lands in the local audit log: who, what, which share, which option changed from what
  to what.

How the credentials are held depends on what the server is, and the difference is stated plainly
because it is a real trade:

| | Domain member | Standalone |
|---|---|---|
| Authentication | Kerberos | NTLMSSP |
| The password | used once, for the ticket, then out of scope | **held in the container's memory for the lifetime of the session** |
| Where it lives | a Kerberos ticket in a session-private cache on tmpfs | process memory only — never on disk, never in the log, never in an API response |
| Server identity | proved by construction (a ticket for `cifs/<host>` is only decryptable by that host) | **not proved** — NTLM authenticates the client to the server, not the other way round |

A standalone server has no KDC, so there is no ticket to run off and NTLMSSP needs the password at
every connection setup. The session therefore keeps it, in one wrapper class that cannot be
printed, serialised or pickled, and that is overwritten when the session ends. This is narrower
than "we do not store it", and saying otherwise would be the kind of security claim this project
is written to avoid.

The sign-in form says so at the moment the choice is made, the session bar repeats it for as long
as the session lasts, and `SAMFSCON_ALLOW_STANDALONE=0` refuses the trade outright for
installations that do not want it.

Both connections are **signed and SMB3 or better**. SMB1 is not negotiated. `SAMFSCON_SMB_ENCRYPT=1`
additionally requires SMB3 encryption, where the server offers it.

## What the server needs

Reading works against any Samba file server with no preparation at all: shares, their options,
sessions, open files, permissions and local accounts.

**Changing** a share needs one thing, in the `[global]` section of the server's `smb.conf`:

```
    include = registry
    registry shares = yes
```

Both lines, and they do different things. `include = registry` makes Samba read the store;
`registry shares = yes` makes it serve what is in there. The store is openable on every Samba and
writable for any administrator, so neither of those is evidence that the second line is set —
SAMFSCON checks by looking for registry sections the server is not serving.

**A share that does not appear straight away has two possible causes**, and they look identical
from outside: `registry shares = yes` is missing so Samba never looks, or smbd has not re-read the
registry yet — it does so on its own schedule, and `smbcontrol all reload-config` settles that in a
second. SAMFSCON reports the share as written and names both, rather than picking one and sending
you to change a setting that was already right.

A share is a key under `HKLM\Software\Samba\smbconf` with a `path` value, SAMFSCON writes it over
`winreg`, and Samba loads registry shares on demand. It is the same thing `net rpc conf addshare`
does.

**Not** `SeDiskOperatorPrivilege`, and not an `add share command` — which is worth saying because
the obvious route needs both. `srvsvc`'s own `NetShareAdd` refuses with `WERR_ACCESS_DENIED` unless
smb.conf sets an `add share command`, and it refuses that way no matter what privileges the caller
holds; registry shares get no exemption. That command exists to run a script that rewrites the text
smb.conf, which is not a thing this console has any business asking a server to do. So it takes the
registry route instead, and the prerequisite disappears.

The privilege is still needed for **share permissions**. Those live in `share_info.tdb`, have no
registry equivalent, and go through `srvsvc` level 1501, which does check it:

```bash
net rpc rights grant 'DOMAIN\Domain Admins' SeDiskOperatorPrivilege -U administrator
```

SAMFSCON checks both and reports them separately, because they gate different things. Reading needs
neither: the share list, the options, the permissions and the sessions are all there without any of
it, and only the writes that need a prerequisite are refused.

`samfsconctl check --user administrator` answers the same question from a shell.

## What is out of reach

Named rather than worked around. Managing a server over the network means these are not available,
and no amount of cleverness changes that:

- **Restarting or reloading Samba.** Registry changes take effect on the server's next
  configuration reload — within a minute, and immediately for new connections.
- **Creating a directory outside an existing share.** A new share's path has to exist beforehand.
  Inside a share, creating a subfolder works.
- **Quotas and POSIX ACLs.** Neither has an RPC interface.
- **A share written into the text `smb.conf`.** It is listed, its options are shown, and it is
  marked as not editable — because editing it would mean writing a file this console cannot reach.
  `net conf import` moves it into the registry if you want it editable.
- **Domain accounts on a member server.** They live in the domain; SAMADCON manages those.

## Quick start

### Running the published image

```bash
docker pull ghcr.io/onlinecrash24/samfscon:latest
```

A complete `docker-compose.yml` for that image — put it in an empty directory:

```yaml
services:
  samfscon:
    image: ghcr.io/onlinecrash24/samfscon:latest
    container_name: samfscon
    restart: unless-stopped

    environment:
      # The name the console is reached under. It becomes the CN and the SAN of
      # the self-signed certificate and the target of the HTTP-to-HTTPS
      # redirect — the one value practically every installation must change.
      SAMFSCON_PUBLIC_HOST: "samfscon.example.lan"
      # Must name the port the host publishes, not the one nginx listens on.
      SAMFSCON_PUBLIC_HTTPS_PORT: "8444"

      # All optional: the sign-in form asks for a server address and works the
      # rest out from the server itself.
      SAMFSCON_SERVER_HOST: ""
      SAMFSCON_SERVER_MODE: "auto"

      SAMFSCON_LOG_LEVEL: "INFO"

      # Which hops in front of this container may be believed when they say who
      # the caller is. Leave it empty when nothing is; then the audit log
      # records the address that actually connected. Never 0.0.0.0/0.
      SAMFSCON_TRUSTED_PROXIES: ""

    ports:
      # Loopback unless you say otherwise. Without an address Docker publishes
      # on every interface the host has, and this is a sign-in form that issues
      # Kerberos tickets. Set SAMFSCON_BIND to the address it should listen on
      # — 0.0.0.0 means every interface — or put a reverse proxy in front and
      # name it above.
      - "${SAMFSCON_BIND:-127.0.0.1}:8444:8443"
      - "${SAMFSCON_BIND:-127.0.0.1}:8081:8080"

    volumes:
      # A real certificate goes here as server.crt and server.key. Without one
      # the container generates a self-signed certificate on first start.
      - ./tls:/etc/samfscon/tls
      - samfscon-cache:/var/cache/samfscon
      - samfscon-data:/var/lib/samfscon
      # The audit trail should outlive the container.
      - samfscon-logs:/var/log/samfscon

    # Kerberos credential caches live in /dev/shm and must never hit a disk.
    shm_size: 64m
    tmpfs:
      # uid/gid are required: a tmpfs mount belongs to root by default, and
      # nginx and supervisor run as uid 1000.
      - /run/samfscon:mode=0700,uid=1000,gid=1000,size=8m

    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL

volumes:
  samfscon-cache:
  samfscon-data:
  samfscon-logs:
```

The container runs as uid 1000 and a bind mount belongs to root, so the certificate directory has
to be writable for it:

```bash
mkdir -p tls && sudo chown -R 1000:1000 tls
docker compose up -d
```

The ports are **8444/8081** rather than SAMADCON's 8443/8080, so both can run on one host.

### Building from source

```bash
git clone https://github.com/onlinecrash24/SAMFSCON.git
cd SAMFSCON
docker compose up -d --build
```

No `.env` is needed — the whole configuration lives in `docker-compose.yml`.

The interface then runs on `https://<host>:8444`.

## Signing in

The domain is not chosen when the container starts; the **server** is chosen at sign-in. The form
offers free entry of an address or host name, pre-configured servers from `SAMFSCON_SERVERS_FILE`
(see [servers.example.json](docker/servers/servers.example.json)), recently used servers kept in
the browser only, and the container's default if one is configured.

Given an address, SAMFSCON asks the server what it is: an unauthenticated LSA policy query returns
the server's own name, its account domain and — for a domain member — the Kerberos realm. That
step is necessary because Kerberos issues tickets for `cifs/fs1.example.lan@EXAMPLE.LAN`, and a
bare address yields neither a principal nor a realm.

**A server that answers nothing is not guessed at.** `restrict anonymous = 2` is common, and the
form then asks which kind of server it is rather than choosing for you — with the reason, so that
choice is informed. Guessing standalone against a domain member would hold a password that
Kerberos made unnecessary; guessing the other way would wait for a ticket no KDC will issue.

## Milestones

| # | Scope | Status |
|---|---|---|
| 1a | Foundation, both authentication modes, server discovery, the container | built |
| 1b | Shares: create, change, delete, with the smb.conf option catalogue | built |
| 1c | Permissions: share-level and file-level, with the effective-access calculation | built |
| 1d | Sessions and open files, including force-closing one | built |
| 1e | Local users and groups on a standalone server (SAMR) | built |
| 2a | Global server settings, with the option catalogue and the lockout guards | built |
| 2b | The diagnostics view: what stands out, and what nobody could look at | built |
| 2c | Share templates | planned |

**Verification against a live server is under way, and it has reached sign-in, the share list and
the share write path.** Against a Samba AD member it has found a fault in each. The two at sign-in:

- A refused anonymous policy query was read as "this server has no realm", which decided
  *standalone* for a domain member — so the console tried NTLM with a domain password and reported
  a logon failure that named the wrong problem. A refused query now decides nothing, and the form
  asks with the reason attached.
- The server's own name was only ever derived from the `srvsvc` probe, which a domain member
  commonly refuses. Without it Kerberos was asked for a ticket for a bare IP address and the
  connection failed with `NT_STATUS_INVALID_PARAMETER`. The name is now composed from the LSA
  policy's own two facts, with a reverse DNS lookup as the last resort, and a sign-in that could
  not possibly work is refused before the password is asked for rather than after.

Reading and writing shares has since been exercised the same way, and cost more than the sign-in
did. `NetShareAdd` turned out to require an `add share command` in `smb.conf` unconditionally, with
no exemption for registry shares, so creating one had to be rewritten to go through `winreg` — which
then needed four separate corrections to the registry call shapes before a share appeared in
`net conf list`. Trustee names were being rendered as raw SIDs because every LSA lookup was passing
an argument the wire format derives. And a share's path was shown as `C:	ank\share`, because
srvsvc has to answer with a Windows path and Samba fabricates a drive letter for one.

**What remains unproven against a real server is permissions, sessions and accounts** — the write
paths in particular. The unit suite (258 backend tests and 73 in the front end) covers what does not
need a server, and the CI runs both. The RPC call shapes are written against the protocol
specifications with a tolerant-signature helper around each, because the Samba python bindings have
changed those signatures between releases. Every fault listed above was found by a real server
regardless, which is the point: that helper is a mitigation, not a substitute for the test. See
[Verifying it](#verifying-it).

### Shares

srvsvc carries a share's name, path, comment and counters. Everything else that makes a Samba
share what it is — `read only`, `valid users`, `create mask`, `vfs objects`, the recycle bin,
shadow copies, auditing — is an `smb.conf` option, and there is no RPC interface for `smb.conf`.
There is one for the registry, so that is what SAMFSCON edits: the same store `net conf` uses, so
a share written here is one `net conf list` shows.

The option catalogue is curated rather than complete: `smb.conf` has several hundred per-share
options, and a console offering a free-text field for all of them would be a worse `vi`. What is
in it is what file servers actually get configured with, each with a type the interface renders as
a control and a sentence saying what it does. **Options outside the catalogue are still shown**,
read-only, and left untouched when saving — a server configured by hand is not wrong, and hiding
half its configuration would make this console a liar.

### Permissions

One editor, three places: the share descriptor (`srvsvc` level 502), the share root's descriptor
(over SMB), and any directory or file below it. They are the same structure, so they get the same
editor.

Two things it will not hide:

**Inherited entries are shown and not editable.** They belong to the parent directory. An editor
that let you change one in place would silently break the inheritance it came from — so the row
says where it came from instead, and writing a descriptor never writes the inherited entries back
as explicit ones.

**The effective right is the intersection of both levels.** SMB checks the share permission once
when the share is opened and the file permission on every operation within it, so neither number
answers "may Alice write this" on its own. A share granting Everyone full control tells you
nothing; a file ACL granting write on a read-only share grants nothing. The editor computes the
intersection for a selected account and names the case that causes the arguments — the file ACL
permits it and the share does not.

The calculation is honest about its limit: it counts the entries naming that account, not the full
token evaluation including every group it is in. A number that is *sometimes* the whole answer
would be worse than one that says which it is.

### Folders and files

The tree lists the shares and, under each, the directories inside it — fetched a level at a time
when a branch is opened, because a share can hold a hundred thousand of them and the console has no
reason to know about any until somebody points at one. Files appear in the list beside the tree,
not in it; a share where files outnumber folders fifty to one is the ordinary case.

**Read-only, plus creating a directory.** That is a decision rather than a gap. This is a
permissions console: what it needs from a share's contents is somewhere to point the ACL editor,
and adding upload, download and delete would be a second product with a second set of ways to lose
data. Creating a folder is the exception because it is what one does *while* setting permissions on
a new project directory, and it is the one write to a server's file system these protocols can
perform — precisely because it happens inside a share that already exists. It inherits its parent's
permissions, as any directory created over SMB does, and the dialog says so.

A directory the signed-in account may not read is listed as unreadable rather than as empty. The
refusal is correct — the console runs as that account and can see no more than it can — and telling
the two apart is usually the whole reason somebody opened this view.

Each entry carries its read-only, hidden and system attributes, because each explains behaviour
that gets blamed on the ACL: a read-only file refuses a write the permissions allow, a hidden one
is missing from Explorer, and a system one is both.

### Sessions and open files

`smbstatus` reads these from the server's tdb files; srvsvc publishes the same facts over the
network. Who is connected, from which machine, how long, how long idle — and which files are open,
with their locks and what the handle may do.

Force-closing a file is the one destructive operation in this half of the console: the client
holding it is not asked and loses unsaved work. It confirms first, names who will be affected in
the confirmation, and lands in the audit log with both.

## Verifying it

**Unit tests** — no Samba, no server, no network. This is what CI runs:

```bash
cd backend && python -m pytest tests/unit -q
```

**Integration tests** — against a throwaway file server, never production. They create and delete
shares:

```bash
SAMFSCON_TARGET=test docker compose up -d --build
TEST_FS_HOST=fs1.example.lan TEST_ADMIN_PASSWORD=… \
  docker compose exec samfscon python -m pytest tests/integration -q
```

**From outside** — the part that actually settles it. A share this console creates has to exist
outside this console:

| What | Checked with |
|---|---|
| Share created | `net conf list` on the server; Explorer opens `\\server\share` |
| Share permissions | `net rpc share getsecurity <share>`, or Windows' "Share Permissions" tab |
| File permissions | `smbcacls //server/share /` and Explorer's "Security" tab |
| VFS options | `net conf showshare <share>`; delete a file from a client and look in the recycle bin |
| Sessions and open files | `smbstatus` beside the console view, while a client holds a file open |
| Nothing runs with borrowed rights | sign in with a deliberately unprivileged account: SAMFSCON must refuse exactly what that account is refused anyway |

**Front end**: `npm run build` and `npm run typecheck` must be clean, and the console gets clicked
through in both German and English — including with the network unplugged, for the error paths.

## Licence

AGPL-3.0-or-later, the same as SAMADCON. See [LICENSE](LICENSE).

The console names its licence and links to this repository — top right when
signed in, and in the footer of the sign-in card. That is not decoration.
Section 13 obliges anyone who modifies SAMFSCON and offers it to others over a
network to offer them its source; a console that never says what it is or where
it came from makes that promise impossible to keep and impossible to notice
being broken. **If you fork it, point the link at your fork rather than removing
it** — one string, `SOURCE_URL` in `frontend/src/components/SourceNote.tsx`.

Two licences travel with it. The Samba python bindings are GPL-3.0-or-later and
are used, not redistributed — they come from the distribution's own packages.
The Phosphor icons are MIT and *are* redistributed, compiled into the bundle as
path data, so their notice is reproduced in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). Both are compatible with
AGPLv3.

## Releasing

The version is written in **one** place, `backend/samfscon/__init__.py`.
`pyproject.toml` declares `dynamic = ["version"]` and reads the attribute from
there, so those two cannot disagree. Everything that names a version to anybody
— `/api/v1/health`, `/api/v1/info`, the sign-in card, `samfsconctl --version`,
the OpenAPI description — reads it through that module.

`frontend/package.json` has to carry one too, because npm requires the field.
Nothing reads it at runtime, which is exactly why it drifts, so it is checked
rather than remembered:

```bash
python scripts/check_versions.py
```

The lint job runs it on every push, and on a tag build compares against the tag
as well. That last part catches what no single-source arrangement can: a tag
pushed without the version having been raised at all. It exists because it
happened to SAMADCON — v0.5.2 shipped announcing itself as 0.5.1, and a reader
found it rather than the project.

The release note lives in the annotated tag, and [CHANGELOG.md](CHANGELOG.md) is
generated from it. Tag first, then generate, then commit the result:

```bash
git tag -a v0.2.0
python scripts/build_changelog.py
git commit -m "Read the changelog out of the tag" CHANGELOG.md
```

Nothing is edited in `CHANGELOG.md` by hand; the next run overwrites it. Two
places holding the same text is how they start to disagree — and a tag, unlike
a file, does not get tidied later.
