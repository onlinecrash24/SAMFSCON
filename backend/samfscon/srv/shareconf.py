"""The share options srvsvc does not know about.

srvsvc carries a share's name, path, comment and a couple of counters. Almost
everything that makes a Samba share what it is — read-only, browseable, who may
connect, the recycle bin, shadow copies, auditing, the masks new files get — is
an smb.conf option, and there is no RPC interface for smb.conf. There is one for
the registry, and Samba can read its configuration from there; that is what
:mod:`samfscon.srv.registry` writes and what this module describes.

**A curated catalogue, not the whole manual.** smb.conf has several hundred
per-share options and a console that offered a free-text field for all of them
would be a worse `vi`. What is here is what a file server actually gets
configured with, each with a type the interface can render as a control and a
sentence saying what it does. Anything outside the catalogue can still be read
and shown — a server configured by hand is not wrong — it just cannot be
invented in a form.

Validation happens here rather than at the server, for one reason: Samba
accepts a nonsense value for many options and simply behaves oddly afterwards.
``create mask = 999`` is not an error to the parser and is not what anyone
meant. Refusing it here, with the reason, is the only place that refusal can be
useful.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from samfscon.core.errors import InvalidRequest

# What kind of control the interface should draw, and how the value is checked.
TYPE_BOOL = "bool"
TYPE_TEXT = "text"
TYPE_LIST = "list"
TYPE_MODE = "mode"  # an octal permission mask
TYPE_INT = "int"
TYPE_CHOICE = "choice"

# Where the option belongs in the interface. The groups are the tabs.
GROUP_BASIC = "basic"
GROUP_ACCESS = "access"
GROUP_FILES = "files"
GROUP_VFS = "vfs"
GROUP_ADVANCED = "advanced"

_MODE_RE = re.compile(r"^0?[0-7]{3,4}$")
_YES = {"yes", "true", "1", "on"}
_NO = {"no", "false", "0", "off"}


@dataclass(frozen=True)
class Option:
    """One smb.conf option, as the interface should present it."""

    name: str
    type: str
    group: str
    # What Samba does when the option is absent. Shown as the placeholder, so
    # an empty field reads as "the server's default" rather than as "empty".
    default: str | None = None
    choices: tuple[str, ...] = ()
    # One sentence. Long enough to say what it does, short enough to sit under
    # a form field without becoming a manual page.
    doc: str = ""
    doc_de: str = ""
    # Options that only mean anything when a VFS module is loaded. The
    # interface greys them out until it is, rather than letting somebody
    # configure a recycle bin that is not running.
    requires_vfs: str | None = None


CATALOGUE: tuple[Option, ...] = (
    # -- the first tab -------------------------------------------------------
    Option(
        name="read only",
        type=TYPE_BOOL,
        group=GROUP_BASIC,
        default="yes",
        doc="Whether the share refuses every write, whatever the file permissions say.",
        doc_de="Ob die Freigabe jeden Schreibzugriff ablehnt, unabhängig von den Dateirechten.",
    ),
    Option(
        name="browseable",
        type=TYPE_BOOL,
        group=GROUP_BASIC,
        default="yes",
        doc="Whether the share appears in network browsing. Hiding it is not access control.",
        doc_de=(
            "Ob die Freigabe beim Durchsuchen des Netzes erscheint. "
            "Verstecken ist keine Zugriffskontrolle."
        ),
    ),
    Option(
        name="guest ok",
        type=TYPE_BOOL,
        group=GROUP_BASIC,
        default="no",
        doc="Whether connecting without a password is allowed. Rarely what anyone wants.",
        doc_de=(
            "Ob eine Verbindung ohne Passwort erlaubt ist. Fast nie das, was gemeint war."
        ),
    ),
    Option(
        name="available",
        type=TYPE_BOOL,
        group=GROUP_BASIC,
        default="yes",
        doc="Set to no to switch the share off without deleting its configuration.",
        doc_de=(
            "Auf „nein“ setzen, um die Freigabe abzuschalten, ohne ihre Konfiguration "
            "zu löschen."
        ),
    ),
    # -- who may connect -----------------------------------------------------
    Option(
        name="valid users",
        type=TYPE_LIST,
        group=GROUP_ACCESS,
        doc=(
            "Only these accounts and groups may connect at all. A group is written "
            "with a leading @. Empty means everyone the file permissions allow."
        ),
        doc_de=(
            "Nur diese Konten und Gruppen dürfen sich überhaupt verbinden. Eine Gruppe "
            "wird mit führendem @ geschrieben. Leer heißt: alle, die die Dateirechte "
            "zulassen."
        ),
    ),
    Option(
        name="invalid users",
        type=TYPE_LIST,
        group=GROUP_ACCESS,
        doc="These accounts are refused even when everything else would allow them.",
        doc_de=(
            "Diese Konten werden abgewiesen, auch wenn alles andere sie zulassen würde."
        ),
    ),
    Option(
        name="write list",
        type=TYPE_LIST,
        group=GROUP_ACCESS,
        doc="Accounts that may write even on a read-only share.",
        doc_de="Konten, die auch auf einer nur lesbaren Freigabe schreiben dürfen.",
    ),
    Option(
        name="read list",
        type=TYPE_LIST,
        group=GROUP_ACCESS,
        doc="Accounts that may only read, even on a writable share.",
        doc_de="Konten, die nur lesen dürfen, auch auf einer beschreibbaren Freigabe.",
    ),
    Option(
        name="hosts allow",
        type=TYPE_LIST,
        group=GROUP_ACCESS,
        doc="Addresses or networks that may connect. Everything else is refused.",
        doc_de="Adressen oder Netze, die sich verbinden dürfen. Alles andere wird abgewiesen.",
    ),
    Option(
        name="hosts deny",
        type=TYPE_LIST,
        group=GROUP_ACCESS,
        doc="Addresses or networks that are refused. Checked after hosts allow.",
        doc_de="Adressen oder Netze, die abgewiesen werden. Wird nach „hosts allow“ geprüft.",
    ),
    Option(
        name="max connections",
        type=TYPE_INT,
        group=GROUP_ACCESS,
        default="0",
        doc="How many clients may be connected at once. 0 means no limit.",
        doc_de="Wie viele Clients gleichzeitig verbunden sein dürfen. 0 heißt: unbegrenzt.",
    ),
    # -- what files look like ------------------------------------------------
    Option(
        name="create mask",
        type=TYPE_MODE,
        group=GROUP_FILES,
        default="0744",
        doc="The most permissive Unix mode a new file may get.",
        doc_de="Die weitesten Unix-Rechte, die eine neue Datei bekommen darf.",
    ),
    Option(
        name="directory mask",
        type=TYPE_MODE,
        group=GROUP_FILES,
        default="0755",
        doc="The most permissive Unix mode a new directory may get.",
        doc_de="Die weitesten Unix-Rechte, die ein neues Verzeichnis bekommen darf.",
    ),
    Option(
        name="force create mode",
        type=TYPE_MODE,
        group=GROUP_FILES,
        default="0000",
        doc="Bits every new file gets, whatever the client asked for.",
        doc_de="Bits, die jede neue Datei bekommt, unabhängig vom Wunsch des Clients.",
    ),
    Option(
        name="force directory mode",
        type=TYPE_MODE,
        group=GROUP_FILES,
        default="0000",
        doc="Bits every new directory gets, whatever the client asked for.",
        doc_de="Bits, die jedes neue Verzeichnis bekommt, unabhängig vom Wunsch des Clients.",
    ),
    Option(
        name="force user",
        type=TYPE_TEXT,
        group=GROUP_FILES,
        doc=(
            "Every connection acts as this Unix account. Convenient and blunt: "
            "the file permissions then no longer tell people apart."
        ),
        doc_de=(
            "Jede Verbindung handelt als dieses Unix-Konto. Bequem und grob: die "
            "Dateirechte unterscheiden die Benutzer dann nicht mehr."
        ),
    ),
    Option(
        name="force group",
        type=TYPE_TEXT,
        group=GROUP_FILES,
        doc="Every connection acts with this Unix group as its primary one.",
        doc_de="Jede Verbindung handelt mit dieser Unix-Gruppe als primärer Gruppe.",
    ),
    Option(
        name="hide unreadable",
        type=TYPE_BOOL,
        group=GROUP_FILES,
        default="no",
        doc="Leave out of listings what the user may not read. Costs a stat per entry.",
        doc_de=(
            "Aus Auflistungen weglassen, was der Benutzer nicht lesen darf. "
            "Kostet einen stat-Aufruf pro Eintrag."
        ),
    ),
    Option(
        name="veto files",
        type=TYPE_TEXT,
        group=GROUP_FILES,
        doc=(
            "Patterns of files that do not exist as far as clients are concerned, "
            "separated by slashes: /.DS_Store/Thumbs.db/"
        ),
        doc_de=(
            "Muster für Dateien, die es für Clients nicht gibt, durch Schrägstriche "
            "getrennt: /.DS_Store/Thumbs.db/"
        ),
    ),
    Option(
        name="follow symlinks",
        type=TYPE_BOOL,
        group=GROUP_FILES,
        default="yes",
        doc="Whether symlinks are followed. Turning it off is a containment measure.",
        doc_de=(
            "Ob symbolischen Links gefolgt wird. Abschalten ist eine Eingrenzungsmaßnahme."
        ),
    ),
    # -- modules -------------------------------------------------------------
    Option(
        name="vfs objects",
        type=TYPE_LIST,
        group=GROUP_VFS,
        doc=(
            "Modules layered over the file system, in order. The order matters: "
            "each sees what the one before it passed on."
        ),
        doc_de=(
            "Module, die über das Dateisystem gelegt werden, in dieser Reihenfolge. "
            "Die Reihenfolge zählt: jedes sieht, was das vorige durchgereicht hat."
        ),
    ),
    Option(
        name="recycle:repository",
        type=TYPE_TEXT,
        group=GROUP_VFS,
        default=".recycle",
        requires_vfs="recycle",
        doc="Where deleted files go, relative to the share root.",
        doc_de="Wohin gelöschte Dateien wandern, relativ zur Wurzel der Freigabe.",
    ),
    Option(
        name="recycle:keeptree",
        type=TYPE_BOOL,
        group=GROUP_VFS,
        default="no",
        requires_vfs="recycle",
        doc="Keep the directory structure inside the recycle bin.",
        doc_de="Die Verzeichnisstruktur im Papierkorb erhalten.",
    ),
    Option(
        name="recycle:versions",
        type=TYPE_BOOL,
        group=GROUP_VFS,
        default="no",
        requires_vfs="recycle",
        doc="Keep several deleted versions of the same name instead of overwriting.",
        doc_de=(
            "Mehrere gelöschte Fassungen desselben Namens behalten, statt zu überschreiben."
        ),
    ),
    Option(
        name="recycle:exclude",
        type=TYPE_LIST,
        group=GROUP_VFS,
        requires_vfs="recycle",
        doc="Patterns that are deleted outright rather than moved to the bin.",
        doc_de="Muster, die sofort gelöscht statt in den Papierkorb verschoben werden.",
    ),
    Option(
        name="recycle:maxsize",
        type=TYPE_INT,
        group=GROUP_VFS,
        default="0",
        requires_vfs="recycle",
        doc="Files larger than this many bytes are deleted outright. 0 means no limit.",
        doc_de=(
            "Dateien über dieser Größe in Bytes werden sofort gelöscht. 0 heißt: keine Grenze."
        ),
    ),
    Option(
        name="shadow:snapdir",
        type=TYPE_TEXT,
        group=GROUP_VFS,
        default=".snapshots",
        requires_vfs="shadow_copy2",
        doc="Where the snapshots live, so Windows can offer 'Previous Versions'.",
        doc_de=(
            "Wo die Snapshots liegen, damit Windows „Vorgängerversionen“ anbieten kann."
        ),
    ),
    Option(
        name="shadow:format",
        type=TYPE_TEXT,
        group=GROUP_VFS,
        default="@GMT-%Y.%m.%d-%H.%M.%S",
        requires_vfs="shadow_copy2",
        doc="How a snapshot directory's name encodes its timestamp.",
        doc_de="Wie der Name eines Snapshot-Verzeichnisses seinen Zeitstempel kodiert.",
    ),
    Option(
        name="shadow:sort",
        type=TYPE_CHOICE,
        group=GROUP_VFS,
        choices=("asc", "desc"),
        default="desc",
        requires_vfs="shadow_copy2",
        doc="The order snapshots are offered in.",
        doc_de="Die Reihenfolge, in der Snapshots angeboten werden.",
    ),
    Option(
        name="full_audit:success",
        type=TYPE_LIST,
        group=GROUP_VFS,
        requires_vfs="full_audit",
        doc="Which successful operations are logged, e.g. open unlink rename rmdir.",
        doc_de=(
            "Welche erfolgreichen Vorgänge protokolliert werden, z. B. open unlink "
            "rename rmdir."
        ),
    ),
    Option(
        name="full_audit:failure",
        type=TYPE_LIST,
        group=GROUP_VFS,
        requires_vfs="full_audit",
        doc="Which failed operations are logged.",
        doc_de="Welche fehlgeschlagenen Vorgänge protokolliert werden.",
    ),
    Option(
        name="full_audit:facility",
        type=TYPE_TEXT,
        group=GROUP_VFS,
        default="USER",
        requires_vfs="full_audit",
        doc="The syslog facility the audit lines go to.",
        doc_de="Die syslog-Facility, in die die Protokollzeilen gehen.",
    ),
    Option(
        name="full_audit:priority",
        type=TYPE_TEXT,
        group=GROUP_VFS,
        default="NOTICE",
        requires_vfs="full_audit",
        doc="The syslog priority the audit lines go to.",
        doc_de="Die syslog-Priorität, mit der die Protokollzeilen geschrieben werden.",
    ),
    # -- the rest ------------------------------------------------------------
    Option(
        name="inherit acls",
        type=TYPE_BOOL,
        group=GROUP_ADVANCED,
        default="no",
        doc="New files and directories inherit the parent's ACL rather than the masks.",
        doc_de=(
            "Neue Dateien und Verzeichnisse erben die ACL des übergeordneten "
            "Verzeichnisses statt der Masken."
        ),
    ),
    Option(
        name="inherit permissions",
        type=TYPE_BOOL,
        group=GROUP_ADVANCED,
        default="no",
        doc="New entries inherit the parent's Unix mode instead of using the masks.",
        doc_de=(
            "Neue Einträge erben die Unix-Rechte des übergeordneten Verzeichnisses, "
            "statt die Masken zu benutzen."
        ),
    ),
    Option(
        name="inherit owner",
        type=TYPE_CHOICE,
        group=GROUP_ADVANCED,
        choices=("no", "windows and unix", "unix only"),
        default="no",
        doc="New entries take the parent directory's owner rather than the creator's.",
        doc_de=(
            "Neue Einträge übernehmen den Besitzer des übergeordneten Verzeichnisses "
            "statt den des Erzeugers."
        ),
    ),
    Option(
        name="access based share enum",
        type=TYPE_BOOL,
        group=GROUP_ADVANCED,
        default="no",
        doc="Hide the share from anyone who could not open it anyway.",
        doc_de="Die Freigabe vor allen verbergen, die sie ohnehin nicht öffnen könnten.",
    ),
    Option(
        name="store dos attributes",
        type=TYPE_BOOL,
        group=GROUP_ADVANCED,
        default="yes",
        doc="Keep the DOS attribute bits in an extended attribute rather than in the mode.",
        doc_de=(
            "Die DOS-Attributbits in einem erweiterten Attribut halten statt in den "
            "Unix-Rechten."
        ),
    ),
    Option(
        name="strict allocate",
        type=TYPE_BOOL,
        group=GROUP_ADVANCED,
        default="no",
        doc="Allocate the blocks for a file up front. Slower, but no sparse files.",
        doc_de=(
            "Die Blöcke einer Datei sofort belegen. Langsamer, dafür keine "
            "Sparse-Dateien."
        ),
    ),
)

BY_NAME: dict[str, Option] = {option.name: option for option in CATALOGUE}

# Options the interface gives their own field, on the first tab, because every
# console does. They are ordinary registry values like all the others — this
# set exists so the generic option list does not show them a second time, not
# because anything else writes them.
SHOWN_SEPARATELY = frozenset({"path", "comment"})

# Kept under its old name for the validator, which still refuses them as
# free-form options: they have a route through the interface already, and two
# routes to one value is two routes that can disagree.
SRVSVC_OWNED = SHOWN_SEPARATELY


@dataclass
class ShareOptions:
    """A share's stored options, split into what we know and what we do not."""

    known: dict[str, str] = field(default_factory=dict)
    # Options the server has that the catalogue does not describe. Shown
    # read-only rather than hidden: a share configured by hand is not wrong,
    # and hiding half its configuration would make this console a liar.
    extra: dict[str, str] = field(default_factory=dict)

    def describe(self) -> dict[str, Any]:
        return {"known": dict(self.known), "extra": dict(self.extra)}


def split(stored: dict[str, str]) -> ShareOptions:
    """Sort what the registry holds into catalogued and uncatalogued."""
    result = ShareOptions()
    for name, value in stored.items():
        if name in BY_NAME:
            result.known[name] = value
        elif name in SRVSVC_OWNED:
            continue  # srvsvc reports these; showing them twice invites disagreement
        else:
            result.extra[name] = value
    return result


def describe_catalogue(language: str = "en") -> list[dict[str, Any]]:
    """The catalogue, for the interface to build its forms from."""
    return [
        {
            "name": option.name,
            "type": option.type,
            "group": option.group,
            "default": option.default,
            "choices": list(option.choices),
            "doc": option.doc_de if language == "de" and option.doc_de else option.doc,
            "requires_vfs": option.requires_vfs,
        }
        for option in CATALOGUE
    ]


def validate(options: dict[str, str | None]) -> dict[str, str | None]:
    """Check and normalise what a form sent.

    Returns the values as Samba should store them. Raises on the first one that
    cannot mean anything — with the option's name and what was wrong with it,
    because "invalid request" against a form of thirty fields is not an error
    message, it is a puzzle.

    Values for options outside the catalogue pass through unchanged. Refusing
    them would make this console unable to preserve a configuration it did not
    write, which is worse than not validating them.
    """
    checked: dict[str, str | None] = {}

    for raw_name, value in options.items():
        name = raw_name.strip().lower().replace("_", " ")
        if not name:
            continue
        if name in SRVSVC_OWNED:
            raise InvalidRequest(
                f"{name!r} is set through the share itself, not through its options.",
                code="option_not_editable",
                context={"option": name},
            )

        if value is None:
            checked[name] = None  # a deletion needs no checking
            continue

        option = BY_NAME.get(name)
        if option is None:
            checked[name] = value.strip()
            continue

        checked[name] = _validate_one(option, value)

    return checked


def _validate_one(option: Option, value: str) -> str:
    text = value.strip()

    if option.type == TYPE_BOOL:
        lowered = text.lower()
        if lowered in _YES:
            return "yes"
        if lowered in _NO:
            return "no"
        raise InvalidRequest(
            f"{option.name!r} takes yes or no.",
            code="invalid_option_value",
            context={"option": option.name, "value": value},
        )

    if option.type == TYPE_MODE:
        if not _MODE_RE.match(text):
            raise InvalidRequest(
                f"{option.name!r} takes an octal permission mask such as 0750.",
                code="invalid_option_value",
                context={"option": option.name, "value": value},
            )
        # Normalised to four digits, the way smb.conf writes them, so a value
        # that came back from the server compares equal to the one sent.
        return text.zfill(4) if not text.startswith("0") else text.rjust(4, "0")

    if option.type == TYPE_INT:
        try:
            number = int(text)
        except ValueError as exc:
            raise InvalidRequest(
                f"{option.name!r} takes a number.",
                code="invalid_option_value",
                context={"option": option.name, "value": value},
            ) from exc
        if number < 0:
            raise InvalidRequest(
                f"{option.name!r} cannot be negative.",
                code="invalid_option_value",
                context={"option": option.name, "value": value},
            )
        return str(number)

    if option.type == TYPE_CHOICE:
        lowered = text.lower()
        if lowered not in option.choices:
            raise InvalidRequest(
                f"{option.name!r} takes one of: {', '.join(option.choices)}.",
                code="invalid_option_value",
                context={"option": option.name, "value": value, "allowed": list(option.choices)},
            )
        return lowered

    if option.type == TYPE_LIST:
        # Samba separates these with spaces, and accepts commas. Normalised to
        # spaces so a value written here reads the same as one `net conf` shows.
        items = [item for item in re.split(r"[,\s]+", text) if item]
        return " ".join(items)

    return text


def vfs_modules(options: dict[str, str]) -> list[str]:
    """The VFS modules a share has loaded, in order.

    Used by the interface to grey out the options that depend on one. A recycle
    bin configured on a share without the module is not an error anyone gets
    told about — it simply never runs.
    """
    raw = options.get("vfs objects", "")
    return [item for item in re.split(r"[,\s]+", raw) if item]
