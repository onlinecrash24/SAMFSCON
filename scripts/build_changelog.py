"""The changelog is not written here. It is read out of the tags.

The release note belongs to the release, and ``git tag -a`` already holds one.
Writing it there rather than into a file means it is fixed at the moment it is
true — including the part a hand-maintained changelog quietly loses, which is
the paragraph naming what was *not* verified. A file gets tidied; an annotated
tag does not.

So there is one source and it stays the tag. This regenerates the file from it;
it does not merge, and it does not preserve edits. Anything typed straight into
``CHANGELOG.md`` is gone on the next run, which is the intended behaviour: two
places holding the same text is how they start to disagree.

English only, because the annotations are. A stale translation of a release
note is worse than a link to one that is current.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "CHANGELOG.md"

HEADER = """# Changelog

Generated from the annotated git tags by `scripts/build_changelog.py` — the
tag is the source, this file is a copy of it. Do not edit it by hand; the next
release overwrites it.

Each entry is the release note as it was written at the time, unedited. Where
one says something was not verified, that sentence is part of the record and
stays.

Images for every version are on GHCR: `ghcr.io/onlinecrash24/samfscon:0.2.0`
pins one exactly, `:0.2` follows the minor series, `:latest` the newest
release.
"""


def git(*args: str) -> str:
    """One git call, decoded, with the trailing newline removed."""
    out = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=True, text=True,
        encoding="utf-8",
    )
    return out.stdout.rstrip("\n")


def released_tags() -> list[tuple[str, str]]:
    """Every ``v*`` tag, newest first, as (tag, date).

    Version sort rather than date sort: two releases on one afternoon get the
    same date, and 0.2.10 has to land above 0.2.9 rather than between 0.2.0
    and 0.2.2.
    """
    lines = git(
        "for-each-ref", "refs/tags/v*",
        "--sort=-version:refname",
        "--format=%(refname:short)\t%(objecttype)\t%(creatordate:short)",
    ).splitlines()

    tags = []
    for line in lines:
        tag, kind, date = line.split("\t")
        if kind != "tag":
            # A lightweight tag has no message at all, so there is nothing to
            # put under the heading. Refusing beats emitting an empty section.
            sys.exit(f"{tag} is a lightweight tag and carries no release note.")
        tags.append((tag, date))
    return tags


def section(tag: str, date: str) -> str:
    """One tag's note, under a heading built from the tag rather than the text."""
    subject = git("for-each-ref", f"refs/tags/{tag}", "--format=%(contents:subject)")
    body = git("for-each-ref", f"refs/tags/{tag}", "--format=%(contents:body)")

    version = tag.lstrip("v")
    lines = [f"## {version} — {date}", ""]

    # The subject is "SAMFSCON 0.2.0" on all of them, which the heading already
    # says. If one ever isn't, it is carried into the body rather than dropped:
    # losing a line silently is the one thing this must not do.
    if not re.fullmatch(rf"SAMFSCON\s+{re.escape(version)}", subject.strip()):
        lines.append(subject.strip())
        lines.append("")

    lines.append(body.strip())
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tags = released_tags()
    if not tags:
        sys.exit("No v* tags found — nothing to build a changelog from.")

    parts = [HEADER] + [section(tag, date) for tag, date in tags]

    # LF, always. .gitattributes normalises on commit anyway, and writing what
    # git stores keeps a second run byte-identical instead of producing a diff
    # made entirely of line endings.
    text = "\n---\n\n".join(parts)
    OUT.write_text(text, encoding="utf-8", newline="\n")

    newest, oldest = tags[0][0], tags[-1][0]
    print(f"CHANGELOG.md: {len(tags)} releases, {oldest} to {newest}, {len(text)} characters")


if __name__ == "__main__":
    main()
