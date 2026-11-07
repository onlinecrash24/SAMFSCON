"""The nginx add_header inheritance trap, asserted rather than remembered.

nginx inherits `add_header` from an enclosing block only if the inner block
declares none. Two locations set a Cache-Control of their own, and that one
directive dropped CSP, HSTS and X-Frame-Options from the HTML page — while the
API, which sets none, kept all of them. `nginx -t` in CI cannot see this: the
configuration is valid, it just says less than it appears to.

Reads the template from the repository, so it is a `repo` test — the shipped
image holds the rendered file, not the template, and CI mounts the checkout.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.repo

DOCKER = Path(__file__).resolve().parents[3] / "docker"
TEMPLATE = DOCKER / "nginx.conf.template"
SNIPPET = DOCKER / "security-headers.conf"
INCLUDE = "security-headers.conf;"


def blocks(text: str) -> list[tuple[str, str]]:
    """(header, body) for every `server` and `location` block, braces matched."""
    found: list[tuple[str, str]] = []
    for match in re.finditer(r"(?m)^\s*(server|location[^{\n]*?)\s*\{", text):
        depth, start = 1, match.end()
        index = start
        while depth and index < len(text):
            depth += {"{": 1, "}": -1}.get(text[index], 0)
            index += 1
        found.append((match.group(1).strip(), text[start : index - 1]))
    return found


def own_lines(body: str) -> str:
    """The block's own directives, with nested blocks cut out."""
    out, depth = [], 0
    for char in body:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif depth == 0:
            out.append(char)
    return "".join(out)


def test_the_files_are_there() -> None:
    assert TEMPLATE.is_file(), f"{TEMPLATE} is missing"
    assert SNIPPET.is_file(), f"{SNIPPET} is missing"


def test_every_block_with_its_own_add_header_includes_the_security_headers() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    checked = 0
    for header, body in blocks(text):
        own = own_lines(body)
        if "add_header" in own:
            checked += 1
            assert INCLUDE in own, (
                f"`{header}` sets an add_header of its own and so inherits none — "
                "it must include security-headers.conf itself"
            )
    assert checked >= 2, "the two static locations were not found, which is not a pass"


def test_the_server_block_carries_them_for_the_locations_that_inherit() -> None:
    """/api/ sets no add_header and inherits — from here."""
    text = TEMPLATE.read_text(encoding="utf-8")
    servers = [own_lines(body) for header, body in blocks(text) if header == "server"]
    assert any(INCLUDE in server and "ssl_certificate" in server for server in servers)


def test_no_security_header_is_set_outside_the_snippet() -> None:
    """One file, so the three places cannot drift apart."""
    text = TEMPLATE.read_text(encoding="utf-8")
    for name in ("Content-Security-Policy", "Strict-Transport-Security", "X-Frame-Options"):
        assert name not in text, f"{name} is set in the template as well as in the snippet"
    snippet = SNIPPET.read_text(encoding="utf-8")
    for name in ("Content-Security-Policy", "Strict-Transport-Security", "X-Frame-Options",
                 "X-Content-Type-Options", "Referrer-Policy"):
        assert name in snippet
