"""The server's global smb.conf options, as the interface should present them.

The sibling of :mod:`samfscon.srv.shareconf`, for the ``[global]`` section
rather than a share's. It edits ``registry.GLOBAL_SECTION``, which is the same
store ``net conf`` writes, and it is subject to the same one limitation that
shapes everything else in this project:

**What is not set here may well be set in the text smb.conf.** SAMFSCON reads
winreg, srvsvc and SMB, and no file. So an empty field means "not set *here*",
never "not set" — and Samba's own default is shown as reference text under the
field rather than as a placeholder *in* it, because a placeholder reads as the
value in force and this console cannot know what that is.

Worse, and the reason §``in_force`` exists at all: a server whose ``[global]``
lives entirely in its text file will accept every write made here and honour
none of them, unless ``include = registry`` sits in that file *before* the lines
setting the same options. That is the common case, it cannot be read, and a
console that stayed quiet about it would leave somebody certain they had changed
something.

**Three things a global option can be, and the catalogue says which.**

``SAFE`` is offered. ``RISKY`` is offered behind a confirmation that names the
specific way it bites — as a code rather than as prose, because one of the
warnings has to quote an address the backend supplies. ``READ_ONLY`` is shown
and never offered, each with its own reason: nine options refused with one
shared sentence would be nine puzzles.

Refusing is the default where a value could not be come back from. An option
this console does not offer is one somebody edits in smb.conf with a shell,
which is a worse interface and a safer one.

**And nothing here takes effect when it is saved.** SAMFSCON writes the
registry; it cannot make Samba re-read it and cannot restart anything, because
there is no RPC call for either. ``effect`` says which of the three kinds an
option is, and the view carries that as a badge rather than as a footnote.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Any

from samfscon.config import MODE_AD_MEMBER
from samfscon.core.errors import InvalidRequest
from samfscon.srv.shareconf import TYPE_BOOL, TYPE_CHOICE, TYPE_INT, TYPE_LIST, TYPE_TEXT

# The tabs.
GROUP_SERVER = "server"
GROUP_PROTOCOL = "protocol"
GROUP_ACCESS = "access"
GROUP_FILES = "files"
GROUP_PRINTING = "printing"
GROUP_WINBIND = "winbind"
GROUP_ADVANCED = "advanced"

GROUPS = (
    GROUP_SERVER,
    GROUP_PROTOCOL,
    GROUP_ACCESS,
    GROUP_FILES,
    GROUP_PRINTING,
    GROUP_WINBIND,
    GROUP_ADVANCED,
)

# Whether the interface may offer the option, and how loudly.
SAFE = "safe"
RISKY = "risky"
READ_ONLY = "read_only"

# When a change starts mattering. Three, because the difference is the whole
# reason the view carries three badges: this console writes the registry, can
# make nothing re-read it, and cannot restart anything at all.
EFFECT_CONNECTION = "connection"
EFFECT_RELOAD = "reload"
EFFECT_RESTART = "restart"

DAEMON_SMBD = "smbd"
DAEMON_NMBD = "nmbd"
DAEMON_WINBINDD = "winbindd"

# Risk codes rather than sentences, following diagnostics.Note: the interface
# is bilingual, and the `hosts allow` warning has to name an address the
# backend supplies, which prose in a static catalogue could not carry.
RISK_CODES = (
    "lockout_hosts",
    "lockout_dialect_floor",
    "lockout_dialect_ceiling",
    "lockout_signing",
    "availability_encryption",
    "wide_links_disabled_by_unix_extensions",
    "exposure_wide_links",
    "quiet_guest_substitution",
    "printing_management_off",
    "disconnects_this_console",
    "exposure_usershares",
    "registry_shares_toggle",
    "standalone_domain_rename",
    "identity_meaning_changes",
)

# Why an option is shown and not offered. One code per reason.
READ_ONLY_REASONS = (
    "machine_account_identity",
    "join_has_no_rpc",
    "member_workgroup_is_the_join",
    "bound_at_startup",
    "hides_configuration",
    "invalidates_stored_names",
    "no_value_improves_on_the_default",
    "idmap_remaps_existing_files",
)

# Why the catalogue cannot state a default. Two codes, because "Samba works it
# out from the host name" and "it is a build option and no RPC reports build
# options" send a reader to two different places.
DEFAULT_NOTES = ("compiled_in", "from_hostname")

# Families shown read-only and refused by prefix rather than by name, because
# the stored names are generated: `idmap config EXAMPLE : range`.
NOT_WRITABLE_PREFIXES: dict[str, str] = {
    "idmap config": "idmap_remaps_existing_files",
}

# The dialects, oldest first. The order is what makes a floor-above-ceiling
# comparison arithmetic rather than a table of special cases.
DIALECTS = ("NT1", "SMB2_02", "SMB2_10", "SMB3_00", "SMB3_02", "SMB3_11")

# Samba accepts family names as well, and which concrete dialect each maps to
# has moved between releases. Resolved to the *floor* reading, because
# `min protocol` means "the lowest I will accept" — and named here in one place
# with the uncertainty stated rather than assumed correct at four call sites.
DIALECT_ALIASES = {
    "SMB1": "NT1",
    "LANMAN2": "NT1",
    "SMB2": "SMB2_02",
    "SMB2_FF": "SMB2_10",
    "SMB3": "SMB3_00",
}


@dataclass(frozen=True)
class GlobalOption:
    """One global smb.conf option, as the interface should present it."""

    name: str
    type: str
    group: str
    # What Samba does when nothing sets the option. Deliberately not a
    # placeholder: a placeholder reads as the value in force, and this console
    # cannot know that. Rendered as reference text under the field — a
    # statement about Samba rather than about this server.
    default: str | None = None
    # Why there is no default to state.
    default_note: str | None = None
    choices: tuple[str, ...] = ()
    doc: str = ""
    doc_de: str = ""

    safety: str = SAFE
    # Set exactly when safety is RISKY. A code, not prose.
    risk: str | None = None
    # Set exactly when safety is READ_ONLY.
    read_only_reason: str | None = None
    # (mode, reason) pairs that make it read-only on one kind of server only.
    # `workgroup` is why this exists: risky on a standalone server, and on a
    # member it *is* the machine account's trust.
    read_only_in: tuple[tuple[str, str], ...] = ()
    # Only meaningful on one kind of server.
    mode_only: str | None = None

    effect: str = EFFECT_RELOAD
    # Which process must re-read it. A tuple, because `server string` needs
    # smbd for srvsvc and nmbd for browse announcements, and "the server will
    # re-read this" without saying which server is the half-answer that costs
    # an afternoon.
    daemons: tuple[str, ...] = (DAEMON_SMBD,)
    # The endpoint that reports the value actually in force, where one exists.
    live_source: str | None = None


_DIALECT_CHOICES = DIALECTS


CATALOGUE: tuple[GlobalOption, ...] = (
    # -- Server ------------------------------------------------------------
    GlobalOption(
        name="server string",
        type=TYPE_TEXT,
        group=GROUP_SERVER,
        default="Samba",
        effect=EFFECT_RELOAD,
        daemons=(DAEMON_SMBD, DAEMON_NMBD),
        live_source="srvsvc.comment",
        doc="What the server calls itself in browse lists and in a client's properties window.",
        doc_de=(
            "Wie der Server sich in Netzwerklisten und im Eigenschaftenfenster eines Clients nennt."
        ),
    ),
    GlobalOption(
        name="workgroup",
        type=TYPE_TEXT,
        group=GROUP_SERVER,
        default="WORKGROUP",
        safety=RISKY,
        risk="standalone_domain_rename",
        read_only_in=((MODE_AD_MEMBER, "member_workgroup_is_the_join"),),
        effect=EFFECT_RESTART,
        daemons=(DAEMON_NMBD,),
        live_source="session.workgroup",
        doc=(
            "The NetBIOS domain the server belongs to; on a domain member it has to stay exactly "
            "the joined domain's name."
        ),
        doc_de=(
            "Die NetBIOS-Domäne, zu der der Server gehört; auf einem Domänenmitglied muss sie "
            "genau der Name der beigetretenen Domäne bleiben."
        ),
    ),
    GlobalOption(
        name="netbios name",
        type=TYPE_TEXT,
        group=GROUP_SERVER,
        default_note="from_hostname",
        safety=READ_ONLY,
        read_only_reason="machine_account_identity",
        effect=EFFECT_RESTART,
        daemons=(DAEMON_SMBD, DAEMON_NMBD),
        live_source="srvsvc.server_name",
        doc=(
            "The name the server answers to. Shown here and changed on the server: a new name "
            "invalidates the machine account and every Kerberos name built from it."
        ),
        doc_de=(
            "Der Name, unter dem der Server antwortet. Wird hier angezeigt und am Server "
            "geändert: ein neuer Name entwertet das Computerkonto und jeden daraus gebildeten "
            "Kerberos-Namen."
        ),
    ),
    GlobalOption(
        name="security",
        type=TYPE_CHOICE,
        group=GROUP_SERVER,
        default="USER",
        choices=("AUTO", "USER", "DOMAIN", "ADS"),
        safety=READ_ONLY,
        read_only_reason="join_has_no_rpc",
        effect=EFFECT_RESTART,
        daemons=(DAEMON_SMBD, DAEMON_WINBINDD),
        live_source="session.mode",
        doc=(
            "How the server authenticates: with its own accounts or with a domain's. Shown, not "
            "edited — the other half of that change is a domain join, and there is no RPC call "
            "for one."
        ),
        doc_de=(
            "Wie der Server authentifiziert: mit eigenen Konten oder mit denen einer Domäne. Wird "
            "angezeigt, nicht bearbeitet — die andere Hälfte dieser Änderung ist ein "
            "Domänenbeitritt, und dafür gibt es keinen RPC-Aufruf."
        ),
    ),
    # -- Protocols ---------------------------------------------------------
    GlobalOption(
        name="server min protocol",
        type=TYPE_CHOICE,
        group=GROUP_PROTOCOL,
        default="SMB2_02",
        choices=_DIALECT_CHOICES,
        safety=RISKY,
        risk="lockout_dialect_floor",
        effect=EFFECT_CONNECTION,
        doc=(
            "The oldest SMB dialect the server accepts. Raising it refuses every client that "
            "cannot reach the new floor, with no message a user can act on."
        ),
        doc_de=(
            "Der älteste SMB-Dialekt, den der Server annimmt. Ein höherer Wert weist jeden "
            "Client ab, der die neue Untergrenze nicht erreicht — ohne Meldung, mit der ein "
            "Benutzer etwas anfangen kann."
        ),
    ),
    GlobalOption(
        name="server max protocol",
        type=TYPE_CHOICE,
        group=GROUP_PROTOCOL,
        default="SMB3_11",
        choices=_DIALECT_CHOICES,
        safety=RISKY,
        risk="lockout_dialect_ceiling",
        effect=EFFECT_CONNECTION,
        doc=(
            "The newest dialect the server offers. Below SMB3 this console cannot connect at "
            "all: it speaks SMB3 and nothing older."
        ),
        doc_de=(
            "Der neueste Dialekt, den der Server anbietet. Unterhalb von SMB3 kann sich diese "
            "Konsole überhaupt nicht mehr verbinden: sie spricht SMB3 und nichts Älteres."
        ),
    ),
    GlobalOption(
        name="client min protocol",
        type=TYPE_CHOICE,
        group=GROUP_PROTOCOL,
        default="SMB2_02",
        choices=_DIALECT_CHOICES,
        effect=EFFECT_CONNECTION,
        daemons=(DAEMON_SMBD, DAEMON_WINBINDD),
        doc=(
            "The oldest dialect the server uses when it is itself a client — towards a domain "
            "controller, or another file server."
        ),
        doc_de=(
            "Der älteste Dialekt, den der Server benutzt, wenn er selbst Client ist — gegenüber "
            "einem Domänencontroller oder einem anderen Dateiserver."
        ),
    ),
    GlobalOption(
        name="server signing",
        type=TYPE_CHOICE,
        group=GROUP_PROTOCOL,
        default="default",
        choices=("default", "auto", "mandatory", "disabled"),
        safety=RISKY,
        risk="lockout_signing",
        effect=EFFECT_CONNECTION,
        doc=(
            "Whether the server requires its traffic to be signed. `disabled` is the dangerous "
            "value, not `mandatory`: a client that requires signing then cannot connect, and "
            "this console is one."
        ),
        doc_de=(
            "Ob der Server verlangt, dass sein Verkehr signiert wird. Der gefährliche Wert ist "
            "„disabled“, nicht „mandatory“: ein Client, der Signierung verlangt, kommt dann gar "
            "nicht mehr durch — und diese Konsole ist so einer."
        ),
    ),
    GlobalOption(
        name="smb encrypt",
        type=TYPE_CHOICE,
        group=GROUP_PROTOCOL,
        default="default",
        choices=("default", "off", "desired", "required"),
        safety=RISKY,
        risk="availability_encryption",
        effect=EFFECT_CONNECTION,
        doc=(
            "Whether SMB3 encryption is offered, wanted, or insisted on. `required` refuses "
            "everything that cannot encrypt, which is everything below SMB3."
        ),
        doc_de=(
            "Ob SMB3-Verschlüsselung angeboten, gewünscht oder verlangt wird. „required“ weist "
            "alles ab, was nicht verschlüsseln kann — also alles unterhalb von SMB3."
        ),
    ),
    GlobalOption(
        name="unix extensions",
        type=TYPE_BOOL,
        group=GROUP_PROTOCOL,
        default="yes",
        safety=RISKY,
        risk="wide_links_disabled_by_unix_extensions",
        effect=EFFECT_CONNECTION,
        doc=(
            "POSIX semantics for Unix clients. While it is on, Samba ignores `wide links` "
            "everywhere, whatever the shares say."
        ),
        doc_de=(
            "POSIX-Semantik für Unix-Clients. Solange sie an ist, beachtet Samba „wide links“ "
            "nirgends, ganz gleich was die Freigaben sagen."
        ),
    ),
    # -- Access ------------------------------------------------------------
    GlobalOption(
        name="hosts allow",
        type=TYPE_LIST,
        group=GROUP_ACCESS,
        safety=RISKY,
        risk="lockout_hosts",
        effect=EFFECT_CONNECTION,
        doc=(
            "Addresses and networks that may reach this server at all. Empty means everyone; a "
            "filled list refuses everything it does not name, this console included."
        ),
        doc_de=(
            "Adressen und Netze, die diesen Server überhaupt erreichen dürfen. Leer heißt: alle; "
            "eine gefüllte Liste weist alles ab, was nicht darin steht — auch diese Konsole."
        ),
    ),
    GlobalOption(
        name="hosts deny",
        type=TYPE_LIST,
        group=GROUP_ACCESS,
        safety=RISKY,
        risk="lockout_hosts",
        effect=EFFECT_CONNECTION,
        doc=(
            "Addresses and networks that are refused. Checked after `hosts allow`, so an entry "
            "in both is allowed."
        ),
        doc_de=(
            "Adressen und Netze, die abgewiesen werden. Wird nach „hosts allow“ geprüft, ein "
            "Eintrag in beiden ist also erlaubt."
        ),
    ),
    GlobalOption(
        name="map to guest",
        type=TYPE_CHOICE,
        group=GROUP_ACCESS,
        default="Never",
        choices=("Never", "Bad User", "Bad Password", "Bad Uid"),
        safety=RISKY,
        risk="quiet_guest_substitution",
        effect=EFFECT_CONNECTION,
        doc=(
            "What becomes of a logon that fails. Anything but `Never` turns a refusal into a "
            "quiet guest session, and the user never learns which one they got."
        ),
        doc_de=(
            "Was aus einer fehlgeschlagenen Anmeldung wird. Alles außer „Never“ macht aus einer "
            "Abweisung eine stille Gastsitzung, und der Benutzer erfährt nie, welche von beiden "
            "er bekommen hat."
        ),
    ),
    GlobalOption(
        name="guest account",
        type=TYPE_TEXT,
        group=GROUP_ACCESS,
        default="nobody",
        doc=(
            "The Unix account a guest session runs as. SAMFSCON cannot check that it exists: no "
            "RPC call lists a server's Unix accounts."
        ),
        doc_de=(
            "Das Unix-Konto, unter dem eine Gastsitzung läuft. SAMFSCON kann nicht prüfen, ob es "
            "existiert: kein RPC-Aufruf listet die Unix-Konten eines Servers auf."
        ),
    ),
    GlobalOption(
        name="interfaces",
        type=TYPE_LIST,
        group=GROUP_ACCESS,
        safety=READ_ONLY,
        read_only_reason="bound_at_startup",
        effect=EFFECT_RESTART,
        daemons=(DAEMON_SMBD, DAEMON_NMBD),
        doc=(
            "Which addresses the server listens on. Shown, not edited: the sockets are bound at "
            "startup, so a mistake here does nothing until somebody restarts Samba — and then "
            "the server is unreachable and this console cannot revert it."
        ),
        doc_de=(
            "Auf welchen Adressen der Server lauscht. Wird angezeigt, nicht bearbeitet: die "
            "Sockets werden beim Start gebunden, ein Fehler wirkt also erst beim nächsten "
            "Neustart von Samba — und dann ist der Server nicht mehr erreichbar und diese "
            "Konsole kann nichts zurücknehmen."
        ),
    ),
    GlobalOption(
        name="bind interfaces only",
        type=TYPE_BOOL,
        group=GROUP_ACCESS,
        default="no",
        safety=READ_ONLY,
        read_only_reason="bound_at_startup",
        effect=EFFECT_RESTART,
        daemons=(DAEMON_SMBD, DAEMON_NMBD),
        doc=(
            "Whether the list above is a restriction or only a preference. Shown, not edited, "
            "for the same reason."
        ),
        doc_de=(
            "Ob die Liste darüber eine Einschränkung ist oder nur eine Bevorzugung. Wird aus "
            "demselben Grund angezeigt und nicht bearbeitet."
        ),
    ),
    # -- File behaviour ----------------------------------------------------
    GlobalOption(
        name="follow symlinks",
        type=TYPE_BOOL,
        group=GROUP_FILES,
        default="yes",
        effect=EFFECT_CONNECTION,
        doc="Whether symlinks are followed, for shares that do not decide for themselves.",
        doc_de=(
            "Ob symbolischen Links gefolgt wird — für Freigaben, die es nicht selbst entscheiden."
        ),
    ),
    GlobalOption(
        name="wide links",
        type=TYPE_BOOL,
        group=GROUP_FILES,
        default="no",
        safety=RISKY,
        risk="exposure_wide_links",
        effect=EFFECT_CONNECTION,
        doc=(
            "Whether a symlink may lead out of its own share. Anyone who can create one can then "
            "publish any directory on the server."
        ),
        doc_de=(
            "Ob ein symbolischer Link aus seiner Freigabe herausführen darf. Wer einen anlegen "
            "kann, veröffentlicht damit jedes Verzeichnis des Servers."
        ),
    ),
    GlobalOption(
        name="veto files",
        type=TYPE_TEXT,
        group=GROUP_FILES,
        effect=EFFECT_CONNECTION,
        doc=(
            "Patterns of files that do not exist as far as clients are concerned, separated by "
            "slashes: /.DS_Store/Thumbs.db/ — a vetoed file also cannot be deleted, so its "
            "directory stays undeletable."
        ),
        doc_de=(
            "Muster für Dateien, die es für Clients nicht gibt, durch Schrägstriche getrennt: "
            "/.DS_Store/Thumbs.db/ — eine solche Datei lässt sich auch nicht löschen, ihr "
            "Verzeichnis bleibt also unlöschbar."
        ),
    ),
    # -- Printing ----------------------------------------------------------
    GlobalOption(
        name="load printers",
        type=TYPE_BOOL,
        group=GROUP_PRINTING,
        default="yes",
        doc="Whether every printer the print system knows is published automatically.",
        doc_de="Ob jeder dem Drucksystem bekannte Drucker automatisch veröffentlicht wird.",
    ),
    GlobalOption(
        name="printing",
        type=TYPE_CHOICE,
        group=GROUP_PRINTING,
        default_note="compiled_in",
        choices=("bsd", "sysv", "plp", "lprng", "aix", "hpux", "qnx", "cups", "iprint"),
        doc=(
            "Which print system the server talks to. Choosing it also resets every print command "
            "that is not set explicitly. Samba's own default here is a build option, and no RPC "
            "call reports build options."
        ),
        doc_de=(
            "Mit welchem Drucksystem der Server spricht. Die Wahl setzt außerdem jeden nicht "
            "ausdrücklich gesetzten Druckbefehl zurück. Sambas eigener Standardwert ist hier "
            "eine Bauoption, und kein RPC-Aufruf meldet Bauoptionen."
        ),
    ),
    GlobalOption(
        name="disable spoolss",
        type=TYPE_BOOL,
        group=GROUP_PRINTING,
        default="no",
        safety=RISKY,
        risk="printing_management_off",
        effect=EFFECT_CONNECTION,
        doc=(
            "Turns off the print-management interface. Printing keeps working; installing a "
            "printer from the server stops."
        ),
        doc_de=(
            "Schaltet die Druckverwaltungsschnittstelle ab. Drucken funktioniert weiter, das "
            "Einrichten eines Druckers vom Server aus nicht mehr."
        ),
    ),
    # -- Domain (member servers only) --------------------------------------
    GlobalOption(
        name="winbind use default domain",
        type=TYPE_BOOL,
        group=GROUP_WINBIND,
        default="no",
        mode_only=MODE_AD_MEMBER,
        safety=RISKY,
        risk="identity_meaning_changes",
        daemons=(DAEMON_WINBINDD,),
        doc=(
            "Whether an unqualified name means a domain account. Turning it on changes who "
            "`Administrator` refers to, and with it who owns what in every permission list."
        ),
        doc_de=(
            "Ob ein Name ohne Domänenpräfix ein Domänenkonto meint. Eingeschaltet ändert sich, "
            "wen „Administrator“ bezeichnet — und damit, wem in jeder Rechteliste was gehört."
        ),
    ),
    GlobalOption(
        name="winbind enum users",
        type=TYPE_BOOL,
        group=GROUP_WINBIND,
        default="no",
        mode_only=MODE_AD_MEMBER,
        daemons=(DAEMON_WINBINDD,),
        # Not risky. It is a performance problem on a large domain, not a
        # lockout and not an exposure, and a confirmation dialog on it would
        # train people to click through the ones that matter.
        doc=(
            "Whether the whole domain appears in the server's user list. On a large domain this "
            "makes ordinary tools hang."
        ),
        doc_de=(
            "Ob die ganze Domäne in der Benutzerliste des Servers erscheint. In einer großen "
            "Domäne bleiben gewöhnliche Werkzeuge damit hängen."
        ),
    ),
    GlobalOption(
        name="winbind enum groups",
        type=TYPE_BOOL,
        group=GROUP_WINBIND,
        default="no",
        mode_only=MODE_AD_MEMBER,
        daemons=(DAEMON_WINBINDD,),
        doc="The same for groups, with the same cost.",
        doc_de="Dasselbe für Gruppen, mit denselben Kosten.",
    ),
    GlobalOption(
        name="template shell",
        type=TYPE_TEXT,
        group=GROUP_WINBIND,
        default="/bin/false",
        mode_only=MODE_AD_MEMBER,
        daemons=(DAEMON_WINBINDD,),
        doc="The login shell domain accounts get where none is stored for them.",
        doc_de="Die Anmelde-Shell, die Domänenkonten bekommen, wenn keine für sie hinterlegt ist.",
    ),
    GlobalOption(
        name="template homedir",
        type=TYPE_TEXT,
        group=GROUP_WINBIND,
        default="/home/%D/%U",
        mode_only=MODE_AD_MEMBER,
        daemons=(DAEMON_WINBINDD,),
        doc="The home directory path domain accounts get.",
        doc_de="Der Pfad des Heimatverzeichnisses, den Domänenkonten bekommen.",
    ),
    GlobalOption(
        name="winbind cache time",
        type=TYPE_INT,
        group=GROUP_WINBIND,
        default="300",
        mode_only=MODE_AD_MEMBER,
        daemons=(DAEMON_WINBINDD,),
        doc="How many seconds a looked-up name stays cached.",
        doc_de="Wie viele Sekunden ein nachgeschlagener Name im Zwischenspeicher bleibt.",
    ),
    GlobalOption(
        name="winbind separator",
        type=TYPE_TEXT,
        group=GROUP_WINBIND,
        default="\\",
        mode_only=MODE_AD_MEMBER,
        safety=READ_ONLY,
        read_only_reason="invalidates_stored_names",
        effect=EFFECT_RESTART,
        daemons=(DAEMON_WINBINDD,),
        doc=(
            "The character between domain and account name. Shown, not edited: changing it "
            "invalidates every stored name string and every ACL entry this console displays, and "
            "winbindd has to be restarted, which SAMFSCON cannot do."
        ),
        doc_de=(
            "Das Zeichen zwischen Domänen- und Kontoname. Wird angezeigt, nicht bearbeitet: eine "
            "Änderung entwertet jede gespeicherte Namenszeichenkette und jeden Rechteeintrag, den "
            "diese Konsole anzeigt, und winbindd muss neu gestartet werden — was SAMFSCON nicht "
            "kann."
        ),
    ),
    # -- Advanced ----------------------------------------------------------
    GlobalOption(
        name="log level",
        type=TYPE_TEXT,
        group=GROUP_ADVANCED,
        default="0",
        daemons=(DAEMON_SMBD, DAEMON_NMBD, DAEMON_WINBINDD),
        doc=(
            "How much the server logs, optionally per area: `1 auth:3`. From level 3 the log "
            "grows fast and the server gets measurably slower."
        ),
        doc_de=(
            "Wie ausführlich der Server protokolliert, wahlweise pro Bereich: „1 auth:3“. Ab "
            "Stufe 3 wächst das Protokoll schnell und der Server wird messbar langsamer."
        ),
    ),
    GlobalOption(
        name="max log size",
        type=TYPE_INT,
        group=GROUP_ADVANCED,
        default="5000",
        doc="At what size in KiB the log file is rotated. 0 means no limit.",
        doc_de=(
            "Ab welcher Größe in KiB die Protokolldatei umgebrochen wird. 0 heißt: keine Grenze."
        ),
    ),
    GlobalOption(
        name="deadtime",
        type=TYPE_INT,
        group=GROUP_ADVANCED,
        default="10080",
        safety=RISKY,
        risk="disconnects_this_console",
        doc=(
            "After how many idle minutes a session with no open files is disconnected. 0 means "
            "never. SAMFSCON's own connection idles while you read a permission list, so a low "
            "value disconnects this console repeatedly."
        ),
        doc_de=(
            "Nach wie vielen untätigen Minuten eine Sitzung ohne offene Dateien getrennt wird. 0 "
            "heißt: nie. Die Verbindung von SAMFSCON ist untätig, während Sie eine Rechteliste "
            "lesen — ein niedriger Wert trennt also immer wieder diese Konsole."
        ),
    ),
    GlobalOption(
        name="usershare max shares",
        type=TYPE_INT,
        group=GROUP_ADVANCED,
        default="0",
        safety=RISKY,
        risk="exposure_usershares",
        doc=(
            "How many shares ordinary users may publish themselves. 0 means none. Whether the "
            "server's usershare directory is set up for it cannot be read from here."
        ),
        doc_de=(
            "Wie viele Freigaben gewöhnliche Benutzer selbst veröffentlichen dürfen. 0 heißt: "
            "keine. Ob das Usershare-Verzeichnis des Servers dafür eingerichtet ist, lässt sich "
            "von hier aus nicht lesen."
        ),
    ),
    GlobalOption(
        name="registry shares",
        type=TYPE_BOOL,
        group=GROUP_ADVANCED,
        default="no",
        safety=RISKY,
        risk="registry_shares_toggle",
        live_source="observed.registry_shares_served",
        doc=(
            "Whether the server serves the shares held in the registry — the ones this console "
            "writes."
        ),
        doc_de=(
            "Ob der Server die Freigaben ausliefert, die in der Registry stehen — also die, die "
            "diese Konsole schreibt."
        ),
    ),
    GlobalOption(
        name="socket options",
        type=TYPE_TEXT,
        group=GROUP_ADVANCED,
        default="TCP_NODELAY",
        safety=READ_ONLY,
        read_only_reason="no_value_improves_on_the_default",
        effect=EFFECT_CONNECTION,
        doc=(
            "TCP options for every connection. Shown, not edited: by consensus and by the "
            "manual's own warning every non-default value is worse than the default, and a "
            "mistyped option name degrades every connection the server makes."
        ),
        doc_de=(
            "TCP-Optionen für jede Verbindung. Wird angezeigt, nicht bearbeitet: nach "
            "allgemeiner Auffassung und nach der Warnung im Handbuch selbst ist jeder "
            "abweichende Wert schlechter als der Standard, und ein Tippfehler im Optionsnamen "
            "verschlechtert jede Verbindung des Servers."
        ),
    ),
    GlobalOption(
        name="include",
        type=TYPE_TEXT,
        group=GROUP_ADVANCED,
        safety=READ_ONLY,
        read_only_reason="hides_configuration",
        doc=(
            "Which further configuration file is pulled in. Shown, not edited: `include = "
            "registry` written into the registry is circular and does nothing, and any other "
            "value pulls in a file this console cannot read — after which everything on this "
            "page may be overridden by content it has no way to see."
        ),
        doc_de=(
            "Welche weitere Konfigurationsdatei eingebunden wird. Wird angezeigt, nicht "
            "bearbeitet: „include = registry“ in die Registry geschrieben ist zirkulär und "
            "bewirkt nichts, und jeder andere Wert bindet eine Datei ein, die diese Konsole "
            "nicht lesen kann — danach kann alles auf dieser Seite von Inhalten überschrieben "
            "sein, die sie nicht sehen kann."
        ),
    ),
    GlobalOption(
        name="config backend",
        type=TYPE_CHOICE,
        group=GROUP_ADVANCED,
        default="file",
        choices=("file", "registry"),
        safety=READ_ONLY,
        read_only_reason="hides_configuration",
        effect=EFFECT_RESTART,
        doc=(
            "Where the server takes its configuration from. Shown, not edited: `registry` cuts "
            "the text file out entirely, which is unrecoverable if the registry is then damaged."
        ),
        doc_de=(
            "Woher der Server seine Konfiguration nimmt. Wird angezeigt, nicht bearbeitet: "
            "„registry“ schneidet die Textdatei ganz heraus — nicht wiederherstellbar, wenn die "
            "Registry danach beschädigt wird."
        ),
    ),
)

BY_NAME: dict[str, GlobalOption] = {option.name: option for option in CATALOGUE}


# ---------------------------------------------------------------------------
# Presenting the catalogue
# ---------------------------------------------------------------------------


def safety_for(option: GlobalOption, mode: str) -> tuple[str, str | None]:
    """How this option stands on *this* kind of server.

    ``workgroup`` is the reason this is a function rather than a field. On a
    standalone server it is a rename anybody may do; on a member it *is* the
    machine account's trust with the domain, and changing it breaks the join.
    One resolution point, so the interface and the write gate cannot disagree.
    """
    for restricted_mode, reason in option.read_only_in:
        if restricted_mode == mode:
            return READ_ONLY, reason
    return option.safety, option.read_only_reason


def describe_catalogue(mode: str, language: str = "en") -> list[dict[str, Any]]:
    """The catalogue as the interface needs it, for this kind of server.

    Resolved here rather than in the view: the route already knows the session's
    mode, so it costs nothing — and two readers of ``mode_only`` are two things
    that can drift.
    """
    described: list[dict[str, Any]] = []
    for option in CATALOGUE:
        if option.mode_only is not None and option.mode_only != mode:
            continue
        safety, reason = safety_for(option, mode)
        described.append(
            {
                "name": option.name,
                "type": option.type,
                "group": option.group,
                "default": option.default,
                "default_note": option.default_note,
                "choices": list(option.choices),
                "doc": option.doc_de if language.startswith("de") else option.doc,
                "safety": safety,
                "risk": option.risk if safety == RISKY else None,
                "read_only_reason": reason if safety == READ_ONLY else None,
                "effect": option.effect,
                "daemons": list(option.daemons),
                "live_source": option.live_source,
            }
        )
    return described


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_YES = {"yes", "true", "1", "on"}
_NO = {"no", "false", "0", "off"}


def validate(
    options: dict[str, str | None], *, mode: str, confirm: frozenset[str] = frozenset()
) -> dict[str, str | None]:
    """Check and normalise what the form sent, and refuse what cannot be undone.

    Three kinds of refusal, and they are different on purpose:

    * a value that cannot mean anything — the same treatment ``shareconf``
      gives it, naming the option and what was wrong with it;
    * an option this console does not offer, each with its own reason;
    * a value that would cut the connection needed to put it back. Those are
      refused outright where the arithmetic decides it, and gated behind an
      explicit confirmation where the consequence is severe but survivable.

    ``confirm`` carries the option names the caller has been shown a warning
    for and accepted. An option that is ``RISKY`` and not in it is refused with
    its risk code, so the interface can show the sentence that belongs to it.
    """
    checked: dict[str, str | None] = {}

    for raw_name, value in options.items():
        name = raw_name.strip().lower()

        for prefix, reason in NOT_WRITABLE_PREFIXES.items():
            if name.startswith(prefix):
                raise InvalidRequest(
                    f"{raw_name!r} is shown here and changed on the server.",
                    code="option_not_editable",
                    context={"option": raw_name, "reason": reason},
                )

        option = BY_NAME.get(name)
        if option is None:
            raise InvalidRequest(
                f"{raw_name!r} is not an option this console offers.",
                code="unknown_option",
                context={"option": raw_name},
            )

        if option.mode_only is not None and option.mode_only != mode:
            raise InvalidRequest(
                f"{option.name!r} means nothing on this kind of server.",
                code="option_not_applicable",
                context={"option": option.name, "mode": mode, "only_on": option.mode_only},
            )

        safety, reason = safety_for(option, mode)
        if safety == READ_ONLY:
            raise InvalidRequest(
                f"{option.name!r} is shown here and changed on the server.",
                code="option_not_editable",
                context={"option": option.name, "reason": reason},
            )

        # Clearing is always allowed: removing a value this console wrote can
        # only ever restore whatever the text smb.conf or Samba's default says,
        # which is the state the server was in before.
        if value is None:
            checked[option.name] = None
            continue

        if safety == RISKY and option.name not in confirm:
            raise InvalidRequest(
                f"{option.name!r} needs to be confirmed before it is changed.",
                code="confirmation_required",
                context={"option": option.name, "risk": option.risk},
            )

        checked[option.name] = _validate_one(option, value)

    _check_dialect_window(checked, options)
    return checked


def _validate_one(option: GlobalOption, value: str) -> str:
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
        # Matched without regard to case and stored in the catalogue's own
        # spelling. Samba accepts either, and `net conf list` then shows the
        # form the documentation uses rather than whatever was typed.
        for choice in option.choices:
            if choice.lower() == text.lower():
                return choice
        raise InvalidRequest(
            f"{option.name!r} takes one of: {', '.join(option.choices)}.",
            code="invalid_option_value",
            context={"option": option.name, "value": value, "allowed": list(option.choices)},
        )

    if option.type == TYPE_LIST:
        items = [item for item in re.split(r"[,\s]+", text) if item]
        return " ".join(items)

    return text


# ---------------------------------------------------------------------------
# The refusals that are pure arithmetic
# ---------------------------------------------------------------------------


def dialect_index(value: str) -> int | None:
    """Where a dialect sits in the ordering, aliases resolved.

    ``None`` for anything unrecognised, which the caller must treat as "cannot
    decide" rather than as "out of range".
    """
    name = value.strip().upper()
    name = DIALECT_ALIASES.get(name, name)
    try:
        return DIALECTS.index(name)
    except ValueError:
        return None


def _check_dialect_window(checked: dict[str, str | None], raw: dict[str, str | None]) -> None:
    """Refuse a floor above the ceiling.

    Not a warning. A server whose minimum is above its maximum accepts nothing
    from anyone, the person who typed it included, and no confirmation makes
    that recoverable from here.
    """
    low = checked.get("server min protocol")
    high = checked.get("server max protocol")
    if not isinstance(low, str) or not isinstance(high, str):
        return

    low_index = dialect_index(low)
    high_index = dialect_index(high)
    if low_index is None or high_index is None:
        return

    if low_index > high_index:
        raise InvalidRequest(
            "The lowest dialect is above the highest, so the server would accept nothing.",
            code="dialect_window_empty",
            context={
                "server min protocol": low,
                "server max protocol": high,
                # Both spellings, because an alias resolving differently than
                # somebody expected is exactly the thing worth seeing.
                "resolved_min": DIALECTS[low_index],
                "resolved_max": DIALECTS[high_index],
                "submitted": {
                    name: raw.get(name) for name in ("server min protocol", "server max protocol")
                },
            },
        )


def check_console_floor(value: str, console_min: str) -> None:
    """Refuse a maximum this console could not connect through.

    Arithmetic, and not overridable. SAMFSCON negotiates SMB3 and nothing
    older, and it does not negotiate down — so a server whose ceiling falls
    below that floor cannot be reached again by the thing that would put it
    back. Recovery would need a shell on the server, which is the need this
    console exists to remove.
    """
    ceiling = dialect_index(value)
    floor = dialect_index(console_min)
    if ceiling is None or floor is None:
        return

    if ceiling < floor:
        raise InvalidRequest(
            "This console could not reconnect to a server with that maximum dialect.",
            code="dialect_below_console_floor",
            context={
                "server max protocol": value,
                "resolved": DIALECTS[ceiling],
                # Verbatim beside the resolved constant, so an alias that maps
                # differently than expected is visible rather than silent.
                "console_min_protocol": console_min,
                "console_resolved": DIALECTS[floor],
            },
        )


# ---------------------------------------------------------------------------
# hosts allow / hosts deny, as far as it can be decided
# ---------------------------------------------------------------------------


_LABEL = r"[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?"
# A host name, or a domain suffix written with a leading dot.
_NAME_RE = re.compile(rf"\.?{_LABEL}(\.{_LABEL})*\.?")


@dataclass(frozen=True)
class HostEntry:
    """One entry in a hosts list, and what it can decide."""

    text: str
    kind: str


def parse_host_entry(text: str) -> HostEntry:
    item = text.strip()
    upper = item.upper()

    if upper in {"ALL"}:
        return HostEntry(item, "all")
    if upper in {"LOCAL"}:
        return HostEntry(item, "local")
    if upper in {"EXCEPT"}:
        return HostEntry(item, "except")
    if item.startswith("@"):
        return HostEntry(item, "netgroup")
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){0,2}\.", item):
        return HostEntry(item, "prefix")

    try:
        ipaddress.ip_address(item)
        return HostEntry(item, "address")
    except ValueError:
        pass
    try:
        ipaddress.ip_network(item, strict=False)
        return HostEntry(item, "network")
    except ValueError:
        pass

    if _NAME_RE.fullmatch(item):
        return HostEntry(item, "name")
    return HostEntry(item, "unparsable")


def covers(entry: HostEntry, address: str) -> bool | None:
    """Whether this entry matches an address.

    ``None`` where it cannot be decided rather than a guess in either
    direction: a host name the server may or may not resolve to us, ``LOCAL``,
    and a netgroup whose membership is not readable from here.
    """
    if entry.kind == "all":
        return True
    if entry.kind in {"local", "name", "netgroup", "except", "unparsable"}:
        return None

    try:
        target = ipaddress.ip_address(address)
    except ValueError:
        return None

    if entry.kind == "address":
        return ipaddress.ip_address(entry.text) == target
    if entry.kind == "network":
        return target in ipaddress.ip_network(entry.text, strict=False)
    if entry.kind == "prefix":
        return address.startswith(entry.text)
    return None


def hosts_verdict(value: str, address: str | None) -> dict[str, Any]:
    """Whether a hosts list decidably covers an address.

    Three answers, and the difference between the last two is the whole design:

    * ``covered`` — an entry matches. Safe.
    * ``excluded`` — every entry was decidable and none matched. We checked,
      and it locks the console out.
    * ``undecidable`` — at least one entry could not be decided, or there is no
      address to check against. We could *not* check, which is a different
      fact, and treating it as the one above would be reporting
      could-not-determine as is-so.
    """
    entries = [parse_host_entry(item) for item in re.split(r"[,\s]+", value.strip()) if item]
    if not entries:
        # An empty list restricts nothing.
        return {"verdict": "covered", "entries": [], "undecidable": []}

    if address is None:
        return {
            "verdict": "undecidable",
            "entries": [entry.text for entry in entries],
            "undecidable": [entry.text for entry in entries],
            "reason": "own_address_unknown",
        }

    # An EXCEPT anywhere makes the whole list undecidable, and the check has to
    # come before the coverage loop rather than inside it. `ALL EXCEPT 10.0.0.5`
    # matched entry by entry answers "covered" on the first token — for an
    # address Samba would refuse. Saying "safe" about a list that locks the
    # console out is the one wrong answer here that cannot be recovered from,
    # and working out what an EXCEPT modifies is not something to guess at.
    if any(entry.kind == "except" for entry in entries):
        return {
            "verdict": "undecidable",
            "entries": [entry.text for entry in entries],
            "undecidable": [entry.text for entry in entries],
            "reason": "except_clause",
        }

    undecidable: list[str] = []
    for entry in entries:
        decided = covers(entry, address)
        if decided is True:
            return {"verdict": "covered", "entries": [e.text for e in entries], "undecidable": []}
        if decided is None:
            undecidable.append(entry.text)

    if undecidable:
        return {
            "verdict": "undecidable",
            "entries": [entry.text for entry in entries],
            "undecidable": undecidable,
            "reason": "entries_not_decidable",
        }

    return {
        "verdict": "excluded",
        "entries": [entry.text for entry in entries],
        "undecidable": [],
    }


__all__ = [
    "BY_NAME",
    "CATALOGUE",
    "GROUPS",
    "GlobalOption",
    "HostEntry",
    "check_console_floor",
    "covers",
    "describe_catalogue",
    "dialect_index",
    "hosts_verdict",
    "parse_host_entry",
    "safety_for",
    "validate",
]
