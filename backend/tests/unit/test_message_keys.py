"""Every code this module emits has a sentence in front of a reader.

The settings view builds most of its keys by interpolation —
``config.risk.${code}``, ``caps.note.${code}`` — and an interpolated key in
TypeScript needs a cast, which is the compiler being told to stop checking. A
code with no entry then renders as its own snake_case name, in English, in the
middle of a German sentence, and neither build says a word about it.

The codes are read from the catalogue and the keys from the file that has to
carry them, so nothing here can agree with itself. It lives on this side
because the codes do: whoever adds one runs these tests.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from samfscon.srv import globalconf as g

# Marked, and deselected when the suite runs inside the shipped image: that
# image carries the built bundle and no frontend source, so there would be
# nothing to read. CI runs these separately with the checkout mounted — see
# .github/workflows/docker.yml. Deselecting is not the same as skipping: a run
# that includes them and cannot find the file fails, loudly, below.
pytestmark = pytest.mark.repo

MESSAGES = Path(__file__).resolve().parents[3] / "frontend" / "src" / "i18n" / "messages.ts"


def catalogue() -> str:
    # Loudly, not skipped. Whether these tests run at all is decided by the
    # marker, in one place, by whoever chose the command; deciding it here from
    # a missing file would mean a run that was *meant* to check reported a pass
    # after checking nothing.
    assert MESSAGES.is_file(), f"{MESSAGES} is missing"
    return MESSAGES.read_text(encoding="utf-8")


def keys(language: str = "de") -> set[str]:
    """The keys of one catalogue.

    One at a time and never the union of both. A union answers "is this string
    written down anywhere", which is true of a key that exists only in German —
    and a German sentence in an English interface is exactly the fault this
    file is here to catch.
    """
    text = catalogue()
    boundary = text.index("export const en")
    half = text[:boundary] if language == "de" else text[boundary:]
    return set(re.findall(r"^  '([A-Za-z0-9._]+)':", half, re.MULTILINE))


def both() -> set[str]:
    """The keys that are in both, which is the only kind that can be rendered."""
    return keys("de") & keys("en")


def note_codes() -> set[str]:
    source = Path(g.__file__).read_text(encoding="utf-8")
    return set(re.findall(r'Note\("([a-z_]+)"', source))


def verification_codes() -> set[str]:
    source = Path(g.__file__).read_text(encoding="utf-8")
    return set(re.findall(r'"code": "([a-z_]+)"', source))


@pytest.mark.parametrize(
    ("prefix", "codes"),
    [
        ("config.risk.", g.RISK_CODES),
        ("config.readOnly.", g.READ_ONLY_REASONS),
        ("config.defaultNote.", g.DEFAULT_NOTES),
        ("config.group.", g.GROUPS),
        ("config.effect.", (g.EFFECT_CONNECTION, g.EFFECT_RELOAD, g.EFFECT_RESTART)),
    ],
)
def test_every_code_has_a_message_key(prefix: str, codes: tuple[str, ...]) -> None:
    present = both()
    assert codes, "an empty code list would make this pass and prove nothing"
    missing = [f"{prefix}{code}" for code in codes if f"{prefix}{code}" not in present]
    assert not missing, f"no message for: {', '.join(missing)}"


def test_every_note_this_module_writes_has_a_message_key() -> None:
    present = both()
    missing = [code for code in sorted(note_codes()) if f"caps.note.{code}" not in present]
    assert not missing, f"no message for: {', '.join(missing)}"


def test_each_verification_outcome_has_a_message_key() -> None:
    present = both()
    found = verification_codes()
    # Three, and the test says so: a fourth would be a code meaning "the write
    # failed", which this console cannot establish and must not claim.
    assert found == {"applied_confirmed", "not_yet_visible", "not_comparable"}
    missing = [code for code in sorted(found) if f"config.verify.{code}" not in present]
    assert not missing, f"no message for: {', '.join(missing)}"


def error_codes() -> set[str]:
    source = Path(g.__file__).read_text(encoding="utf-8")
    # `code=` and `code =` both, because the module raises some of these
    # through a helper that takes the code by keyword and one that assigns it.
    return set(re.findall(r'code\s*=\s*"([a-z_]+)"', source))


def test_every_refusal_this_module_raises_has_a_message() -> None:
    """Otherwise the reader gets the server's English sentence under a German
    heading — which is what `te()` falls back to, and it is a fallback rather
    than a translation."""
    present = both()
    found = error_codes()
    assert len(found) >= 10, "the extraction found almost nothing, which is not a pass"
    missing = [code for code in sorted(found) if f"error.{code}" not in present]
    assert not missing, f"no message for: {', '.join(missing)}"


def test_the_two_families_are_both_present_and_stay_apart() -> None:
    """What the split is for.

    A refusal the interface can offer a button for is 409 and names the token
    to send back; a refusal that is a value to fix is 400 and names none. Both
    kinds exist here, so neither classification can quietly swallow the other.
    """
    from samfscon.core.errors import Conflict, InvalidRequest

    source = Path(g.__file__).read_text(encoding="utf-8")
    assert "raise Conflict(" in source
    assert "raise InvalidRequest(" in source
    assert Conflict.status_code == 409
    assert InvalidRequest.status_code == 400

    # And the two acceptances are two tokens: one about a list, one about this
    # session. A single token would let either stand for the other.
    assert g.ADDRESS_UNKNOWN_CONFIRM not in g.UNDECIDABLE_CONFIRM_FOR.values()
    assert len(set(g.UNDECIDABLE_CONFIRM_FOR.values())) == len(g.UNDECIDABLE_CONFIRM_FOR)


def test_the_two_catalogues_hold_the_same_keys() -> None:
    """MessageKey derives from the German one, so this is what the type cannot see.

    The compiler requires English to have every German key. It cannot see a key
    English has and German does not — that one falls back to itself and renders
    as its own dotted name — and it says nothing about this file's shape, which
    is what every other test here reads.
    """
    german, english = keys("de"), keys("en")
    assert german, "the German half was not found, which is not a pass"
    assert sorted(german - english) == [], "missing from the English catalogue"
    assert sorted(english - german) == [], "missing from the German catalogue"
