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

MESSAGES = Path(__file__).resolve().parents[3] / "frontend" / "src" / "i18n" / "messages.ts"


def catalogue() -> str:
    # Loudly, not skipped: this repository holds both halves, and "the front
    # end was not there to check against" is not a reason to report a pass.
    assert MESSAGES.is_file(), f"{MESSAGES} is missing"
    return MESSAGES.read_text(encoding="utf-8")


def keys() -> set[str]:
    return set(re.findall(r"^  '([A-Za-z0-9._]+)':", catalogue(), re.MULTILINE))


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
    present = keys()
    assert codes, "an empty code list would make this pass and prove nothing"
    missing = [f"{prefix}{code}" for code in codes if f"{prefix}{code}" not in present]
    assert not missing, f"no message for: {', '.join(missing)}"


def test_every_note_this_module_writes_has_a_message_key() -> None:
    present = keys()
    missing = [code for code in sorted(note_codes()) if f"caps.note.{code}" not in present]
    assert not missing, f"no message for: {', '.join(missing)}"


def test_each_verification_outcome_has_a_message_key() -> None:
    present = keys()
    found = verification_codes()
    # Three, and the test says so: a fourth would be a code meaning "the write
    # failed", which this console cannot establish and must not claim.
    assert found == {"applied_confirmed", "not_yet_visible", "not_comparable"}
    missing = [code for code in sorted(found) if f"config.verify.{code}" not in present]
    assert not missing, f"no message for: {', '.join(missing)}"


def test_the_english_catalogue_carries_the_same_settings_keys() -> None:
    """MessageKey derives from the German one, so this is what the type cannot see.

    A key present twice is one German and one English string; a key present
    once is a German sentence rendered in an English interface.
    """
    text = catalogue()
    once = [
        key
        for key in sorted(keys())
        if key.startswith(("config.", "caps.note."))
        and len(re.findall(rf"^  '{re.escape(key)}':", text, re.MULTILINE)) != 2
    ]
    assert not once, f"not in both catalogues: {', '.join(once)}"
