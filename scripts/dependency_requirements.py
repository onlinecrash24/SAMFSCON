"""The dependency list, in the two shapes an audit needs.

Auditing the *installed* packages answers only half the question. A floor
written too low — `>=` some version with a known hole — never shows up there,
because `>=` resolves to the newest release and a fresh build is therefore
never exposed. It shows up on the machine that installed months ago and
resolved differently, and on anyone who pins from these constraints.

SAMADCON had exactly one such floor, found by a reader rather than by a tool,
which is what made it worth a check instead of a fix.

So this prints the same dependencies two ways, and CI audits both:

``--declared`` (the default)
    The constraints as written. Audited, this answers "is what a build gets
    today safe?" — the question that matters to whoever pulls the image.

``--floors``
    Every ``>=`` pinned to ``==``. Audited, this answers "do the constraints
    permit anything vulnerable?" — the question the reader was really asking,
    and the one nothing else in this repository asks.

Running both found two more floors than the report did, and then something
worse: at their floors the dependencies could not be installed together at
all. Nobody had ever resolved that combination.

Reads pyproject.toml directly rather than importing samfscon, because the lint
job has no samba bindings.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "backend" / "pyproject.toml"


def dependencies() -> list[str]:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["dependencies"]


def at_floors(requirement: str) -> str:
    """``fastapi>=0.141.1`` becomes ``fastapi==0.141.1``.

    Only ``>=`` is rewritten. A dependency written any other way is passed
    through untouched rather than guessed at — a wrong pin here would audit
    something the project never declared.
    """
    return requirement.replace(">=", "==", 1) if ">=" in requirement else requirement


def main(argv: list[str]) -> int:
    floors = "--floors" in argv
    for requirement in dependencies():
        print(at_floors(requirement) if floors else requirement)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
