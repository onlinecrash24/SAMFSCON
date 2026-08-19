<p align="center">
  <img src="docs/brand/samfscon-banner-transparent.svg"
       alt="SAMFSCON — the Samba FileServer console" width="560">
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

> Status: under development. What is built is listed under [Milestones](#milestones).

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

**Changing** a share needs two things on the server, and they are the same two the Windows
Computer Management console needs against Samba. In the `[global]` section of its `smb.conf`:

```
    include = registry
    registry shares = yes
```

and the right that `srvsvc` checks before it will touch a share:

```bash
net rpc rights grant 'DOMAIN\Domain Admins' SeDiskOperatorPrivilege -U administrator
```

SAMFSCON **detects both** and says which one is missing, with the command that fixes it. It does
not fail obscurely: the share list, the permissions and the sessions are all there, and only the
writes that need the preparation are refused. Both are the same `WERR_ACCESS_DENIED` on the wire,
which is exactly why the console checks them separately — the advice for one sends you entirely
the wrong way for the other.

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

    ports:
      - "8444:8443"
      - "8081:8080"

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
| 2 | Global server settings, the diagnostics view, share templates | planned |

**Verification against a live server has started, and the sign-in path is the only part it has
reached.** Against a Samba AD member it found two faults, both since fixed:

- A refused anonymous policy query was read as "this server has no realm", which decided
  *standalone* for a domain member — so the console tried NTLM with a domain password and reported
  a logon failure that named the wrong problem. A refused query now decides nothing, and the form
  asks with the reason attached.
- The server's own name was only ever derived from the `srvsvc` probe, which a domain member
  commonly refuses. Without it Kerberos was asked for a ticket for a bare IP address and the
  connection failed with `NT_STATUS_INVALID_PARAMETER`. The name is now composed from the LSA
  policy's own two facts, with a reverse DNS lookup as the last resort, and a sign-in that could
  not possibly work is refused before the password is asked for rather than after.

Everything past the sign-in — shares, permissions, sessions, accounts — is still unproven against a
real server. The unit suite (136 tests) covers what does not need one, and the CI runs it. The RPC
call shapes are written against the protocol specifications with a tolerant-signature helper around
each, because the Samba python bindings have changed those signatures between releases. That helper
is a mitigation, not a substitute for the test: see [Verifying it](#verifying-it).

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

AGPL-3.0-or-later, the same as SAMADCON.
