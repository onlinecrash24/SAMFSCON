"""samfsconctl — diagnostics for the container.

Runs inside the running container
(``docker compose exec samfscon samfsconctl ...``) and answers the questions
that come up when SAMFSCON cannot reach a server, or reaches it and refuses to
do anything: what the server says it is, whether the account authenticates,
whether the server is set up for remote share management, and who holds the
privilege it wants.

It is deliberately read-only. Nothing here changes a server.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from typing import Any

from samfscon import __version__


def _settings() -> Any:
    from samfscon.config import get_settings

    return get_settings()


def cmd_config(args: argparse.Namespace) -> int:
    settings = _settings()
    data = settings.model_dump()
    # Nothing secret lives in the settings today; guard against that changing.
    for key in list(data):
        if "password" in key or "secret" in key:
            data[key] = "***"
    print(json.dumps(data, indent=2, default=str))
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    """What a server says about itself, without credentials.

    The same call the sign-in form makes. When the console reports that it
    cannot tell whether a server is a domain member, this shows why — the notes
    name the query that was refused.
    """
    from samfscon.core.errors import SamfsconError
    from samfscon.srv import discovery

    settings = _settings()
    host = args.host or settings.server_host
    if not host:
        print(
            "No server given and none configured (SAMFSCON_SERVER_HOST is empty).",
            file=sys.stderr,
        )
        return 1

    try:
        found = discovery.probe(discovery.normalise_host(host), settings)
    except SamfsconError as exc:
        return _report_failure(exc)

    print(json.dumps(found.describe(), indent=2, default=str))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Sign in and report what this account may actually do.

    The one command worth running when the console says "access denied" and
    nobody can agree why: it separates "the server is not set up for this" from
    "your account lacks the privilege", which are the same status code on the
    wire and entirely different problems.

    The password is read from the terminal, never from an argument — an
    argument would sit in the shell history and the process list.
    """
    from samfscon.auth import kerberos
    from samfscon.auth.session import SessionSecret, get_store
    from samfscon.core.errors import SamfsconError
    from samfscon.core.executor import get_registry
    from samfscon.srv import diagnostics, targets
    from samfscon.srv.connection import connect

    settings = _settings()
    password = getpass.getpass("Password: ")

    registry = get_registry()
    store = get_store()
    session_id = store.new_id()
    ccache = None

    try:
        target = targets.resolve_target(
            settings, server=args.host, mode=args.mode, realm=args.realm
        )
    except SamfsconError as exc:
        return _report_failure(exc)

    default_realm = target.realm if target.uses_kerberos else (target.netbios_name or "")
    principal = kerberos.parse_principal(args.user, default_realm or "")

    try:
        secret = None
        if target.uses_kerberos:
            ccache = kerberos.ccache_path_for(settings, session_id)
            kerberos.acquire_ticket(principal, password, ccache, settings, target)
            expires = kerberos.ticket_expiry(ccache) or kerberos.default_expiry()
        else:
            secret = SessionSecret(password)
            expires = kerberos.default_expiry()

        session = store.create(
            session_id=session_id,
            principal=principal,
            target=target,
            ccache=ccache,
            secret=secret,
            expires_hard_at=expires,
        )

        conn = connect(session, settings)
        try:
            report = diagnostics.whoami(conn)
        finally:
            conn.close()
    except SamfsconError as exc:
        return _report_failure(exc)
    finally:
        # Whatever happened, the ticket and the password go away with the
        # process rather than outliving it.
        store.drop(session_id, reason="cli")
        registry.drop(session_id)
        if ccache is not None:
            kerberos.destroy_ticket(ccache)

    print(json.dumps(report, indent=2, default=str))

    caps = report.get("capabilities", {})
    if caps.get("can_manage_shares") is False:
        print("\nShares cannot be managed with this account on this server.", file=sys.stderr)
        for note in caps.get("notes", []):
            print(f"  - {note}", file=sys.stderr)
        return 2
    if caps.get("can_manage_shares") is None:
        print("\nWhether shares can be managed could not be determined.", file=sys.stderr)
        for note in caps.get("notes", []):
            print(f"  - {note}", file=sys.stderr)
    return 0


def _report_failure(exc: Any) -> int:
    print(f"FAILED: {exc.message}", file=sys.stderr)
    if getattr(exc, "hint", None):
        print(f"  hint: {exc.hint}", file=sys.stderr)
    if getattr(exc, "detail", None):
        print(f"  detail: {exc.detail}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="samfsconctl",
        description="Read-only diagnostics for the SAMFSCON container.",
    )
    parser.add_argument("--version", action="version", version=f"SAMFSCON {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    config = sub.add_parser("config", help="show the effective configuration")
    config.set_defaults(func=cmd_config)

    probe = sub.add_parser("probe", help="ask a server what it is, without credentials")
    probe.add_argument("host", nargs="?", help="address; defaults to SAMFSCON_SERVER_HOST")
    probe.set_defaults(func=cmd_probe)

    check = sub.add_parser("check", help="sign in and report what the account may do")
    check.add_argument("--host", help="address; defaults to SAMFSCON_SERVER_HOST")
    check.add_argument("--user", required=True, help="user name, or user@REALM")
    check.add_argument("--realm", help="Kerberos realm, if it cannot be discovered")
    check.add_argument(
        "--mode",
        choices=("ad_member", "standalone"),
        help="force the mode instead of asking the server",
    )
    check.set_defaults(func=cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
