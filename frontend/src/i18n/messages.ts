/**
 * The DE/EN catalogue.
 *
 * German is the reference: it is complete by construction, because `MessageKey`
 * is derived from it and English is typed as the same set of keys. A missing
 * English string is a compile error rather than a German word in an English
 * interface.
 *
 * Error codes get two entries each — `error.<code>` and `error.<code>.hint`.
 * The server writes its hints in English, and a hint is the half that says what
 * to do about the problem; leaving it untranslated under a translated message
 * is the worse half to get wrong.
 */

export const de = {
  // -- the application -----------------------------------------------------
  'app.title': 'SAMFSCON',
  'app.subtitle': 'Samba FileServer Console',

  // -- navigation ----------------------------------------------------------
  'nav.logout': 'Abmelden',
  'nav.search': 'Suchen',
  'nav.server': 'Server',
  'nav.language': 'Sprache',

  'snapin.shares': 'Freigaben',
  'snapin.sessions': 'Sitzungen',
  'snapin.files': 'Ordner und Dateien',
  'snapin.accounts': 'Lokale Benutzer und Gruppen',
  'snapin.diagnostics': 'Diagnose',
  'snapin.config': 'Servereinstellungen',

  'snapin.shares.note': 'Freigaben anlegen, ändern und löschen.',
  'snapin.sessions.note': 'Wer ist verbunden, und welche Dateien sind offen.',
  'snapin.files.note': 'Verzeichnisse innerhalb einer Freigabe und ihre Rechte.',
  'snapin.accounts.note': 'Konten, die auf diesem Server selbst liegen.',
  'snapin.diagnostics.note': 'Was am Server auffällt und was dieses Konto darf.',
  'snapin.config.note': 'Globale Einstellungen des Servers.',
  'snapin.unavailable': 'Dieser Bereich ist noch nicht gebaut.',
  'snapin.accounts.domainMember':
    'Dieser Server ist Mitglied der Domäne {domain}. Seine Benutzer und Gruppen kommen aus der Domäne und werden dort verwaltet — auf einem Domänencontroller oder mit SAMADCON. Nur lokale Konten eines eigenständigen Servers werden hier gezeigt.',

  // -- sign-in -------------------------------------------------------------
  'login.title': 'Anmelden',
  'login.server': 'Fileserver',
  'login.serverPlaceholder': 'fs1.example.lan oder 192.168.1.50',
  'login.serverHelp':
    'Adresse oder Name. SAMFSCON fragt den Server, was er ist, und füllt den Rest aus.',
  'login.username': 'Benutzername',
  'login.usernamePlaceholder': 'Administrator',
  'login.password': 'Passwort',
  'login.submit': 'Anmelden',
  'login.signingIn': 'Anmeldung läuft …',
  'login.probe': 'Server prüfen',
  'login.probing': 'Server wird geprüft …',
  'login.profile': 'Vorkonfigurierter Server',
  'login.profileNone': 'Adresse eingeben',
  'login.recent': 'Zuletzt verwendet',
  'login.forget': 'Entfernen',
  'login.realm': 'Kerberos-Realm',
  'login.realmHelp': 'Nur nötig, wenn der Server ihn nicht selbst nennt.',

  'login.mode': 'Art des Servers',
  'login.mode.ad_member': 'Domänenmitglied (Kerberos)',
  'login.mode.standalone': 'Eigenständig (Benutzername und Passwort)',
  'login.mode.auto': 'Automatisch erkennen',
  'login.mode.detected': 'Erkannt: {mode}',
  'login.mode.undecided':
    'Der Server hat keine unauthentifizierte Anfrage beantwortet — meist „restrict anonymous“. Bitte die Art des Servers selbst wählen.',
  'login.mode.standaloneDisabled':
    'Eigenständige Server sind auf dieser Installation nicht freigegeben.',

  'login.standaloneWarning':
    'Ein eigenständiger Server kennt kein Kerberos. Das Passwort bleibt darum für die Dauer der Sitzung im Arbeitsspeicher von SAMFSCON — nie auf der Festplatte, nie im Protokoll, und beim Abmelden überschrieben.',

  'login.probeResult': 'Der Server meldet sich als {name}',
  'login.probeVersion': 'Samba {version}',
  'login.probeUnreachable': 'Der Server ist nicht erreichbar.',

  // -- the session bar -----------------------------------------------------
  'session.auth.kerberos': 'Kerberos',
  'session.auth.ntlm': 'NTLM',
  'session.signed': 'signiert',
  'session.encrypted': 'verschlüsselt',
  'session.identityVerified': 'Serveridentität geprüft',
  'session.identityUnverified': 'Serveridentität ungeprüft',
  'session.identityUnverified.why':
    'NTLM weist den Client gegenüber dem Server aus, nicht umgekehrt. Die Verbindung ist signiert, aber wer am anderen Ende sitzt, ist damit nicht bewiesen.',
  'session.holdsPassword': 'Passwort im Speicher',
  'session.holdsPassword.why':
    'Diese Sitzung läuft gegen einen eigenständigen Server ohne Kerberos. Das Passwort wird für jede Verbindung erneut gebraucht und liegt darum im Arbeitsspeicher, bis die Sitzung endet.',

  // -- capabilities --------------------------------------------------------
  'caps.title': 'Was dieses Konto hier darf',
  'caps.canManageShares': 'Freigaben verwalten',
  'caps.registryConfig': 'Registry-Konfiguration',
  'caps.diskOperator': 'SeDiskOperatorPrivilege',
  'caps.yes': 'ja',
  'caps.no': 'nein',
  'caps.unknown': 'nicht feststellbar',
  'caps.holders': 'Gehalten von: {names}',

  // -- generic -------------------------------------------------------------
  'action.cancel': 'Abbrechen',
  'action.save': 'Speichern',
  'action.close': 'Schließen',
  'action.retry': 'Erneut versuchen',
  'action.refresh': 'Aktualisieren',
  'action.properties': 'Eigenschaften',
  'action.delete': 'Löschen',
  'action.openFolder': 'Ordner öffnen',
  'action.dismiss': 'Ausblenden',

  'status.loading': 'Wird geladen …',
  'status.empty': 'Nichts vorhanden.',
  'status.saved': 'Gespeichert.',

  'type.share': 'Freigabe',
  'type.folder': 'Ordner',
  'type.file': 'Datei',
  'type.user': 'Benutzer',
  'type.group': 'Gruppe',
  'type.alias': 'Lokale Gruppe',
  'type.well_known_group': 'Systemgruppe',
  'type.computer': 'Computer',
  'type.domain': 'Domäne',
  'type.contact': 'Kontakt',
  'type.unknown': 'Unbekannt',
  'type.deleted': 'Gelöscht',
  'type.invalid': 'Ungültig',
  'type.container': 'Container',
  'type.server': 'Server',
  'type.session': 'Sitzung',
  'type.diagnostics': 'Diagnose',
  'type.permissions': 'Berechtigungen',

  'list.count_one': '{count} Eintrag',
  'list.count_other': '{count} Einträge',


  // -- shares --------------------------------------------------------------
  'share.new': 'Neue Freigabe',
  'share.create': 'Anlegen',
  'share.delete': 'Freigabe löschen',
  'share.created': 'Die Freigabe {name} wurde angelegt.',
  'share.deleteConfirm': 'Freigabe löschen',
  'share.deleteWarning':
    'Die Freigabe {name} wird nicht mehr veröffentlicht, und ihre Konfiguration wird entfernt.',
  'share.deleteKeepsFiles':
    'Das Verzeichnis und alles darin bleibt liegen — diese Konsole löscht keine Dateien:',
  'share.deleted': 'Die Freigabe {name} wurde gelöscht.',
  'share.selectOne': 'Eine Freigabe auswählen.',
  'share.name': 'Name',
  'share.name.hint': 'So heißt die Freigabe im Netz.',
  'share.path': 'Pfad auf dem Server',
  'share.path.hint':
    'Muss auf dem Server bereits existieren. SAMFSCON verwaltet ihn über das Netz und kann kein Verzeichnis außerhalb einer bestehenden Freigabe anlegen.',
  'share.comment': 'Kommentar',
  'share.readOnly': 'Nur lesen',
  'share.browseable': 'Beim Durchsuchen sichtbar',
  'share.guestOk': 'Zugriff ohne Passwort',
  'share.guestOk.hint': 'Fast nie das, was gemeint war.',
  'share.default': 'Standard',
  'share.default.why':
    'Diese Freigabe setzt die Option nicht; gezeigt wird die Vorgabe des Servers. Sobald Sie sie ändern, wird sie ausdrücklich gesetzt.',
  'share.connectedCount': '{count} verbunden',
  'share.connected.why': 'So viele Clients haben diese Freigabe gerade geöffnet.',
  'share.createdNotServed':
    'Die Freigabe {name} wurde geschrieben, der Server liefert sie aber noch nicht aus. Die Konfiguration ist vollständig — es fehlt eines von zweien: entweder hat smbd die Registry noch nicht neu gelesen („smbcontrol all reload-config“ auf dem Server), oder in der smb.conf fehlt „registry shares = yes“ im Abschnitt [global]. Der Reload ist schneller geprüft.',
  'share.currentUsers': 'Verbunden',
  'share.fromSmbConf': 'aus der smb.conf',
  'share.fromSmbConf.why':
    'Diese Freigabe steht in der Textdatei smb.conf des Servers. SAMFSCON bearbeitet die Registry-Konfiguration — das ist der Teil, der über das Netz erreichbar ist. Ändern lässt sich diese Freigabe nur auf dem Server selbst, oder nachdem sie mit „net conf import“ in die Registry übernommen wurde.',
  'share.needsModule':
    'Wirkt erst, wenn das VFS-Modul „{module}“ unter „vfs objects“ geladen ist.',
  'share.otherOptions': 'Weitere Optionen',
  'share.otherOptions.why':
    'Auf dem Server gesetzt, aber nicht im Katalog von SAMFSCON beschrieben. Wird angezeigt statt verschwiegen — und bleibt beim Speichern unangetastet.',
  'share.cannotWrite': 'Auf diesem Server können hier keine Freigaben geändert werden.',
  'share.group.basic': 'Allgemein',
  'share.group.access': 'Zugriff',
  'share.group.files': 'Dateien',
  'share.group.vfs': 'Module',
  'share.group.advanced': 'Erweitert',

  'caps.note.privilege_unconfirmed':
    'Ob Ihr Konto Freigaben ändern darf, lässt sich von hier nicht sicher sagen: SeDiskOperatorPrivilege halten {holders}, und ob Sie über eine verschachtelte Gruppe dazugehören, kann diese Prüfung nicht auflösen — das entscheidet der Server, wenn er gefragt wird. Probieren Sie die Änderung. Lehnt er ab, fehlt das Recht wirklich, und dieser Befehl auf dem Server vergibt es: {command}',
  'caps.note.no_disk_operators.command':
    'Auf diesem Server hält niemand SeDiskOperatorPrivilege — solange das so ist, kann hier niemand Freigaben ändern. Auf dem Server ausführen: {command}',
  'caps.note.registry_missing':
    'Der Server hat keine erreichbare Registry-Konfiguration — „include = registry“ und „registry shares = yes“ in seiner smb.conf ergänzen.',
  'caps.note.registry_unreadable':
    'Die Registry-Konfiguration ist vorhanden, dieses Konto darf sie aber nicht lesen.',
  'caps.note.registry_read_only':
    'Dieses Konto darf die Registry-Konfiguration lesen, aber nicht ändern.',
  'caps.note.registry_probe_failed': 'Die Registry-Konfiguration ließ sich nicht prüfen ({detail}).',
  'caps.note.privilege_list_unreadable': 'Die Privilegienliste ließ sich nicht lesen ({reason}).',
  'caps.note.sid_unknown':
    'Die SID des angemeldeten Kontos ist unbekannt, darum ließen sich seine Privilegien nicht prüfen.',
  'caps.note.disk_operators_are': 'SeDiskOperatorPrivilege halten: {names}.',
  'caps.note.no_disk_operators':
    'Auf diesem Server hält niemand SeDiskOperatorPrivilege — solange das so ist, kann hier niemand Freigaben ändern. Auf dem Server ausführen: {command}',
  'caps.noRegistryConfig':
    'Dieser Server ist nicht dafür eingerichtet, Freigaben über das Netz zu verwalten. In den Abschnitt [global] seiner smb.conf „include = registry“ und „registry shares = yes“ eintragen und Samba neu laden. Lesen funktioniert ohne das.',
  'caps.noDiskOperator':
    'Ihr Konto hat SeDiskOperatorPrivilege auf diesem Server nicht. Gehalten wird es von: {names}. Vergeben mit: net rpc rights grant <Gruppe> SeDiskOperatorPrivilege -U <Admin>',
  'caps.unknownWhy':
    'Ob hier Freigaben verwaltet werden können, ließ sich nicht feststellen — die Prüfung selbst wurde abgelehnt.',

  'error.option_not_editable': 'Diese Option wird über die Freigabe selbst gesetzt.',
  'error.invalid_option_value': 'Dieser Wert passt nicht zu der Option.',
  'error.share_not_editable':
    'Diese Freigabe steht in der smb.conf und kann hier nicht geändert werden.',
  'error.share_not_editable.hint':
    'SAMFSCON bearbeitet die Registry-Konfiguration. Eine in die smb.conf geschriebene Freigabe muss dort geändert werden — oder mit „net conf import“ in die Registry übernommen werden.',
  'error.administrative_share': 'Diese Freigabe gehört dem Server selbst.',
  'error.administrative_share.hint':
    'IPC$, ADMIN$ und print$ verwaltet Samba, nicht eine Konsole.',


  // -- sessions ------------------------------------------------------------
  'sessions.connected': 'Verbunden',
  'sessions.files': 'Offene Dateien',
  'sessions.nobody': 'Zurzeit ist niemand verbunden.',
  'sessions.noFiles': 'Zurzeit ist keine Datei offen.',
  'sessions.readAt': 'Gelesen um {when}',
  'sessions.filter': 'Nach Pfad oder Benutzer filtern',
  'sessions.user': 'Benutzer',
  'sessions.client': 'Rechner',
  'sessions.openFiles': 'Dateien',
  'sessions.connectedFor': 'Verbunden seit',
  'sessions.idleFor': 'Untätig seit',
  'sessions.path': 'Pfad',
  'sessions.access': 'Zugriff',
  'sessions.locks': 'Sperren',
  'sessions.guest': 'Gast',
  'sessions.access.read': 'lesen',
  'sessions.access.write': 'schreiben',
  'sessions.access.create': 'anlegen',
  'sessions.close': 'Schließen',
  'sessions.showFiles': 'Offene Dateien anzeigen',
  'sessions.closeConfirm': 'Datei schließen',
  'sessions.closeWarning':
    '{path} wird für {user} zwangsweise geschlossen. Nicht gespeicherte Änderungen gehen dabei verloren, und der Client wird nicht gefragt.',
  'sessions.closed': '{path} wurde geschlossen.',
  'error.file_not_open': 'Diese Datei ist nicht mehr offen.',
  'error.file_not_open.hint':
    'Jemand hat sie geschlossen, oder die Liste ist veraltet. Neu laden und noch einmal nachsehen.',


  // -- permissions ---------------------------------------------------------
  'perm.share.what':
    'Freigabeberechtigungen werden einmal geprüft, wenn ein Client die Freigabe öffnet, und begrenzen alles Weitere. Auf den meisten Samba-Servern steht hier „Jeder: Vollzugriff“, und die Dateiberechtigungen machen die eigentliche Arbeit.',
  'perm.file.what':
    'Dateiberechtigungen werden bei jedem Zugriff geprüft. Was tatsächlich erlaubt ist, ist die Schnittmenge aus diesen und den Freigabeberechtigungen.',
  'perm.raw': 'Sicherheitsdeskriptor (SDDL)',
  'perm.unixUser': 'Unix-Benutzer {id}',
  'perm.unixGroup': 'Unix-Gruppe {id}',
  'perm.derived': 'aus der SID',
  'perm.derived.why':
    'Dieser Name steht so in der Spezifikation — RID 500 ist in jeder Domäne der Administrator. Der Server hat ihn nicht bestätigt, das Konto muss also nicht mehr existieren.',
  'perm.owner': 'Besitzer',
  'perm.group': 'Gruppe',
  'perm.grantsNothing': 'gewährt nichts',
  'perm.grantsNothing.why':
    'Einträge, die nichts gewähren, sind kein Fehler: Samba baut die NT-ACL aus der POSIX-ACL, und ein POSIX-Eintrag ohne Rechtebits wird zu einem ACE mit leerer Zugriffsmaske. Er steht in der Liste, weil er im Deskriptor steht.',
  'perm.trustee': 'Konto',
  'perm.kind': 'Art',
  'perm.kind.allow': 'Erlauben',
  'perm.kind.deny': 'Verweigern',
  'perm.level': 'Berechtigung',
  'perm.appliesTo': 'Gilt für',
  'perm.appliesTo.this_only': 'nur dieses Objekt',
  'perm.appliesTo.this_and_children': 'dieses Objekt und alles darunter',
  'perm.appliesTo.children_only': 'nur alles darunter',
  'perm.appliesTo.folders': 'Ordner',
  'perm.appliesTo.files': 'Dateien',
  'perm.preset.full': 'Vollzugriff',
  'perm.preset.modify': 'Ändern',
  'perm.preset.read_execute': 'Lesen und Ausführen',
  'perm.preset.read': 'Lesen',
  'perm.preset.write': 'Schreiben',
  'perm.inherited': 'geerbt',
  'perm.inherited.why':
    'Dieser Eintrag kommt aus dem übergeordneten Verzeichnis. Ihn hier zu ändern würde die Vererbung aufbrechen — geändert wird er dort, wo er herkommt.',
  'perm.remove': 'Entfernen',
  'perm.add': 'Eintrag hinzufügen',
  'perm.protected': 'Vererbung vom übergeordneten Verzeichnis unterbrechen',
  'perm.protected.hint':
    'Danach gelten hier nur noch die Einträge, die hier stehen. Die geerbten verschwinden.',
  'perm.inspect': 'Tatsächliche Rechte anzeigen',
  'perm.effective': 'Tatsächliche Rechte für {trustee}',
  'perm.nothing': 'Keine.',
  'perm.limitedByShare':
    'Die Freigabeberechtigung begrenzt das: die Dateiberechtigung erlaubt mehr, als über diese Freigabe möglich ist.',
  'perm.directOnly':
    'Gezählt werden die Einträge, die dieses Konto ausdrücklich nennen — Gruppenmitgliedschaften sind darin nicht enthalten.',
  'perm.pick': 'Konto auswählen',
  'perm.pick.search': 'Name',
  'perm.pick.hint':
    'Aufgelöst vom Fileserver selbst — lokale Gruppen und Domänenkonten über denselben Aufruf.',
  'perm.pick.wellKnown': 'Standardkonten',
  'perm.unresolved': 'nicht auflösbar',
  'perm.right.read': 'Lesen',
  'perm.right.write': 'Schreiben',
  'perm.right.append': 'Anhängen',
  'perm.right.execute': 'Ausführen',
  'perm.right.delete': 'Löschen',
  'perm.right.delete_child': 'Untergeordnetes löschen',
  'perm.right.read_attributes': 'Attribute lesen',
  'perm.right.write_attributes': 'Attribute schreiben',
  'perm.right.read_permissions': 'Rechte lesen',
  'perm.right.change_permissions': 'Rechte ändern',
  'perm.right.take_ownership': 'Besitz übernehmen',
  'share.group.permissions': 'Freigaberechte',
  'share.group.filePermissions': 'Dateirechte',
  'nav.consoles': 'Konsolen',
  'tree.nothing': 'Hier ist noch nichts.',
  'nav.actions': 'Aktionen',
  'app.sourceTitle': 'Quelltext und Lizenz dieser Fassung',
  'menu.empty': 'Hier ist nichts zu tun.',
  'splitter.tree': 'Breite des Navigationsbereichs',
  'splitter.detail': 'Breite des Eigenschaftenbereichs',
  'splitter.hint': 'Ziehen zum Verstellen, Doppelklick setzt zurück',
  'window.minimise': 'Minimieren',
  'window.maximise': 'Maximieren',
  'window.resize': 'Größe ändern',
  'window.taskbar': 'Geöffnete Fenster',
  'window.gone': 'Das gibt es auf diesem Server nicht mehr.',
  'error.no_dacl': 'Der Sicherheitsdeskriptor hat keine Zugriffsliste.',
  'error.no_dacl.hint': 'Ein Deskriptor ohne sie gewährt niemandem etwas.',
  'error.invalid_sddl': 'Das ist kein gültiger Sicherheitsdeskriptor.',
  'error.sddl_domain_unknown':
    'Dieser Server sagt nicht, zu welcher Domäne diese Einträge gehören.',
  'error.sddl_domain_unknown.hint':
    'Kürzel wie DA oder DU sind in SDDL keine vollständigen SIDs, sondern eine Nummer relativ zu einer Domäne. Welche gemeint ist, war nicht zu erfahren — und geraten würde daraus ein gültiger SID, der zu niemandem gehört. Schreiben Sie den SID vollständig aus oder wählen Sie das Konto aus der Liste.',
  'error.unknown_preset': 'Unbekannte Berechtigungsstufe.',
  'error.sddl_unrenderable': 'Der Sicherheitsdeskriptor ließ sich nicht darstellen.',
  'error.sddl_unrenderable.hint':
    'Es gibt einen, und diese Konsole konnte ihn nicht lesen. Er wird nicht als unbeschränkt angezeigt, denn ein Speichern darauf würde ihn ersetzen. `net rpc share getsecurity <Freigabe>` auf dem Server gibt denselben Deskriptor in einer vergleichbaren Form aus.',
  'error.srvsvc_unsupported': 'Diese Samba-Version unterstützt den Aufruf nicht.',
  'error.path_escapes_share': 'Ein Pfad darf seine Freigabe nicht verlassen.',
  'error.missing_path': 'Es wurde kein Name angegeben.',


  // -- local accounts ------------------------------------------------------
  'files.selectOne': 'Einen Ordner im Baum auswählen.',
  'files.created': 'Der Ordner {name} wurde angelegt.',
  'files.newFolder': 'Neuer Ordner',
  'files.newFolderIn': 'Wird angelegt in',
  'files.create': 'Anlegen',
  'files.open': 'Öffnen',
  'files.name': 'Name',
  'files.size': 'Größe',
  'files.modified': 'Geändert',
  'files.attributes': 'Attribute',
  'files.readOnly': 'schreibgeschützt',
  'files.hidden': 'versteckt',
  'files.system': 'System',
  'files.empty': 'Dieser Ordner ist leer.',
  'files.noFolders': 'Keine Unterordner.',
  'files.unreadable': 'Nicht lesbar mit diesem Konto.',
  'files.truncated':
    'Es werden nicht alle Einträge gezeigt — der Server bricht lange Auflistungen ab. Steigen Sie in einen Unterordner ab, um den Rest zu sehen.',
  'files.inheritsPermissions':
    'Der neue Ordner erbt die Rechte des übergeordneten, wie jedes über SMB angelegte Verzeichnis. Ändern lassen sie sich danach in seinen Eigenschaften.',
  'files.nameForbidden': 'Diese Zeichen sind in einem Namen nicht erlaubt: \ / : * ? " < > |',
  'share.root': 'Wurzel von {name}',
  'snapin.diagnostics.heading': 'Was an diesem Server auffällt',
  'findings.none': 'Nichts von dem, wonach diese Konsole sieht, ist aufgefallen.',
  'findings.severity.high': 'hoch',
  'findings.severity.medium': 'mittel',
  'findings.severity.low': 'gering',
  'findings.severity.info': 'Hinweis',
  'findings.area.management': 'Verwaltung',
  'findings.area.transport': 'Verbindung',
  'findings.area.shares': 'Freigaben',
  'findings.area.sessions': 'Sitzungen',
  'findings.generatedAt': 'Gelesen am {when}',
  'findings.evidence': 'Grundlage',
  'findings.unreadableHeading': 'Was nicht geprüft werden konnte',
  'findings.todo': 'Zu tun:',
  'findings.unreadable.capabilities_unreadable.do':
    'Mit einem Konto anmelden, das diesen Server verwalten darf — die Prüfung selbst wurde abgelehnt, es ist also nichts einzustellen.',
  'findings.unreadable.privilege_unconfirmed.do':
    'Nichts. Die Änderung probieren — lehnt der Server ab, fehlt das Recht wirklich, und dann vergibt es auf dem Server: net rpc rights grant \'<Gruppe>\' SeDiskOperatorPrivilege -U <Admin>',
  'findings.unreadable.registry_state_unknown.do':
    'Auf dem Server nachsehen, ob die Registry-Konfiguration eingebunden ist: testparm -s | grep -i registry',
  'findings.unreadable.server_facts_unreadable.do':
    'Nichts Dringendes: diese Angaben sind Beiwerk, und alles andere hier funktioniert ohne sie. Ein Konto mit weitergehenden Rechten auf dem Server bekäme sie.',
  'findings.unreadable.shares_unreadable.do':
    'Die Liste kommt über srvsvc und braucht Verwaltungsrechte auf dem Server. Wird sie abgelehnt, hat dieses Konto sie nicht.',
  'findings.unreadable.registry_unreadable.do':
    'Zugriff auf HKLM\\Software\\Samba\\smbconf prüfen. Lesen darf ihn jedes Konto, das den Server verwalten darf; ohne ihn bleibt diese Konsole auf das beschränkt, was srvsvc meldet.',
  'findings.unreadable.configuration_not_in_registry.do':
    'Diese Freigabe steht in der Text-smb.conf, die SAMFSCON nicht liest. Sichtbar und änderbar wird sie erst, wenn sie in der Registry steht — das ist ein Eingriff in die Konfiguration des Servers (net conf import, dazu include = registry in der smb.conf) und nichts, was nebenbei passieren sollte.',
  'findings.unreadable.sessions_unreadable.do':
    'Auch diese Liste kommt über srvsvc und braucht Verwaltungsrechte auf dem Server.',
  'findings.unreadableWhy':
    'Der Bericht unten sagt zu diesen Punkten nichts — nicht, weil dort nichts wäre, sondern weil es sich von hier aus nicht lesen ließ. Bei jedem steht, was zu tun wäre.',
  'findings.coverage': '{readable} von {total} Freigaben mit lesbarer Konfiguration.',
  'findings.coverage.rest':
    'Die übrigen {count} stehen in der Text-smb.conf, die diese Konsole nicht liest — zu ihren Optionen sagt dieser Bericht nichts.',
  'findings.coverage.notProbed':
    'Ob sich die Freigaben öffnen lassen und wie ihre Dateirechte zu den Freigaberechten stehen, wurde nicht geprüft. Das heißt nicht, dass dort nichts ist.',
  'findings.unreadable.capabilities_unreadable': 'Was dieses Konto darf, war nicht zu ermitteln.',
  'findings.unreadable.privilege_unconfirmed':
    'Ob dieses Konto SeDiskOperatorPrivilege hält, war nicht zu bestätigen — verschachtelte Gruppenmitgliedschaft ist von hier nicht auflösbar.',
  'findings.unreadable.registry_state_unknown':
    'Der Zustand der Registry-Konfiguration war nicht zu ermitteln.',
  'findings.unreadable.server_facts_unreadable': 'Die erweiterten Serverangaben wurden verweigert.',
  'findings.unreadable.shares_unreadable': 'Die Freigabenliste war nicht lesbar.',
  'findings.unreadable.registry_unreadable': 'Die Registry-Konfiguration war nicht lesbar.',
  'findings.unreadable.configuration_not_in_registry':
    'Diese Freigabe steht in der Text-smb.conf; ihre Optionen sind von hier nicht lesbar.',
  'findings.unreadable.sessions_unreadable': 'Die Sitzungsliste war nicht lesbar.',
  'findings.registry_config_absent':
    'Der Server liest seine Registry-Konfiguration nicht',
  'findings.registry_config_absent.why':
    'Ohne `include = registry` in der [global]-Sektion der smb.conf ignoriert Samba alles unter HKLM\\\\Software\\\\Samba\\\\smbconf — und das ist der einzige Ort, den diese Konsole beschreiben kann. Freigaben lassen sich dann lesen, aber nicht anlegen oder ändern.',
  'findings.registry_shares_not_served':
    'In der Registry stehen Freigaben, die der Server nicht veröffentlicht',
  'findings.registry_shares_not_served.why':
    'Die Konfiguration ist da und wird nicht gelesen. Meist fehlt `registry shares = yes` in der [global]-Sektion; manchmal hat smbd die Registry nur noch nicht neu eingelesen — `smbcontrol all reload-config` entscheidet, welches von beidem es ist.',
  'findings.disk_operator_unassigned':
    'Niemand auf diesem Server hält SeDiskOperatorPrivilege',
  'findings.disk_operator_unassigned.why':
    'Das Recht steuert, wer Freigaben und Freigabeberechtigungen über das Netz ändern darf. Die Liste der Inhaber kam leer zurück — nicht „wir konnten nicht nachsehen“, sondern „es hält es niemand“. Solange das so ist, kann keine Anmeldung hier etwas an Freigaben ändern.',
  'findings.disk_operator_broadly_granted':
    'SeDiskOperatorPrivilege ist sehr breit vergeben',
  'findings.disk_operator_broadly_granted.why':
    'Unter den Inhabern ist eine Gruppe, die praktisch jeden angemeldeten Benutzer umfasst. Damit darf jeder, der sich anmelden kann, Freigaben anlegen, ändern und ihre Berechtigungen setzen. Die zugrunde gelegte Liste steht in den Belegen — wer sie für zu streng hält, kann ihr widersprechen.',
  'findings.transport_peer_unverified':
    'Die Identität des Servers ist nicht geprüft',
  'findings.transport_peer_unverified.why':
    'Kerberos beweist, mit wem gesprochen wird: ein Ticket für cifs/<host> kann nur dieser Host entschlüsseln. NTLM beweist nur den Client gegenüber dem Server, nicht umgekehrt. Auf einem eigenständigen Server ist das die einzige Möglichkeit und darum eher eine Eigenschaft der Umgebung als ein Fehler.',
  'findings.transport_this_session':
    'Diese Verbindung',
  'findings.transport_this_session.why':
    'Wie *diese* Sitzung geschützt ist — nicht, was der Server von anderen verlangt. Signierung erzwingt SAMFSCON clientseitig, und die Verschlüsselung ist eine Einstellung des Containers. Was der Server selbst fordert, steht hier nicht.',
  'findings.share_guest_ok':
    'Diese Freigabe erlaubt Gastzugriff',
  'findings.share_guest_ok.why':
    '`guest ok = yes` lässt Zugriff ohne Anmeldung zu, abgebildet auf das Gastkonto. Ob dabei geschrieben werden darf, steht in dieser Freigabe nicht — es kann global gesetzt sein, und diese Datei liest die Konsole nicht.',
  'findings.share_guest_writable':
    'Diese Freigabe erlaubt Gästen zu schreiben',
  'findings.share_guest_writable.why':
    '`guest ok = yes` zusammen mit `read only = no`, beides in dieser Freigabe. Wer das Netz erreicht, kann ohne Anmeldung Dateien anlegen, ändern und löschen.',
  'findings.share_wide_links':
    'Diese Freigabe folgt Symlinks aus der Freigabe hinaus',
  'findings.share_wide_links.why':
    '`wide links = yes` erlaubt Symlinks, die aus dem Freigabeverzeichnis herausführen — ein Client kann damit Dateien erreichen, die nie freigegeben wurden. Samba schaltet das stillschweigend ab, solange `unix extensions = yes` gilt; diese Option ist global und darum von hier nicht lesbar. Erst beides zusammen entscheidet die Wirkung.',
  'findings.share_create_mask_world_writable':
    'Neue Dateien werden für alle beschreibbar angelegt',
  'findings.share_create_mask_world_writable.why':
    'Die Maske lässt das Schreibrecht für „andere“ stehen. Auf dem Dateisystem darf dann jeder lokale Benutzer schreiben, unabhängig davon, was die Freigabe- und Datei-ACLs sagen.',
  'findings.share_force_user':
    'Alle Zugriffe laufen unter einem festen Konto',
  'findings.share_force_user.why':
    '`force user` schreibt jeden Zugriff auf dieses Konto um. Datei-Berechtigungen unterscheiden danach nicht mehr, wer etwas getan hat — im Dateisystem sieht jede Änderung gleich aus.',
  'findings.share_force_user_root':
    'Alle Zugriffe laufen als root',
  'findings.share_force_user_root.why':
    '`force user = root` gibt jedem, der die Freigabe öffnen darf, die Rechte des Systemkontos auf allem darunter. Datei-ACLs greifen dann nicht mehr, und im Dateisystem ist nicht mehr erkennbar, wer etwas getan hat.',
  'findings.share_hosts_allow_unparsable':
    'In hosts allow oder hosts deny steht ein Eintrag, den Samba nicht deuten kann',
  'findings.share_hosts_allow_unparsable.why':
    'Ein Tippfehler in dieser Zeile fällt nicht auf: Samba verwirft den Eintrag stillschweigend, und die Zugriffsbeschränkung, die er darstellen sollte, existiert einfach nicht. Welche Formen erkannt wurden, steht in den Belegen.',
  'findings.share_hosts_deny_without_allow':
    'hosts deny sperrt alles, und hosts allow steht nicht daneben',
  'findings.share_hosts_deny_without_allow.why':
    'In dieser Freigabe steht keine Ausnahme. Wenn eine global gesetzt ist, ist alles in Ordnung — diese Datei liest die Konsole nicht, und deshalb steht das hier als Hinweis und nicht als Befund.',
  'findings.share_hidden_name_browseable':
    'Ein Name auf $ deutet auf versteckt, die Freigabe ist es aber nicht',
  'findings.share_hidden_name_browseable.why':
    'Namen mit $ am Ende werden üblicherweise nicht angezeigt. `browseable = yes` hebt das auf, sodass die Freigabe in der Netzwerkumgebung erscheint — was so vermutlich nicht gemeint war. Verstecken ist ohnehin keine Zugriffsbeschränkung.',
  'findings.share_vfs_option_without_module':
    'Optionen sind gesetzt, deren VFS-Modul nicht geladen ist',
  'findings.share_vfs_option_without_module.why':
    'Diese Einstellungen laufen nie: das Modul, das sie auswertet, steht nicht in `vfs objects` dieser Freigabe. Ein so konfigurierter Papierkorb sieht eingerichtet aus und fängt nichts auf.',
  'findings.share_path_nested':
    'Diese Freigabe liegt innerhalb einer anderen',
  'findings.share_path_nested.why':
    'Zwei Freigaben auf verschachtelten Pfaden haben eigene Berechtigungen auf denselben Dateien. Wer über die äußere hereinkommt, unterliegt den Regeln der inneren nicht — das ist der häufigste Weg, eine Beschränkung versehentlich zu umgehen.',
  'findings.share_path_duplicate':
    'Mehrere Freigaben zeigen auf dasselbe Verzeichnis',
  'findings.share_path_duplicate.why':
    'Jede bringt ihre eigenen Freigaberechte mit. Die großzügigste entscheidet, was möglich ist, und keine der Einstellungen sieht für sich genommen falsch aus.',
  'findings.share_path_sensitive':
    'Diese Freigabe veröffentlicht ein Systemverzeichnis',
  'findings.share_path_sensitive.why':
    'Der Pfad liegt in einem Bereich, der zum Betriebssystem gehört. Selbst lesend gibt das Konfiguration und Zugangsdaten heraus; schreibend ist es ein Weg, den Server zu übernehmen. Die zugrunde gelegte Liste steht in den Belegen.',
  'findings.share_configured_not_served':
    'Diese Freigabe ist konfiguriert und abgeschaltet',
  'findings.share_configured_not_served.why':
    'In der Registry steht `available = no`. Die Konfiguration ist vollständig, der Server veröffentlicht sie aber nicht — was gewollt sein kann und öfter ein Rest von etwas ist, das jemand einmal abgeschaltet hat.',
  'findings.guest_session_present':
    'Gerade ist eine Gastsitzung verbunden',
  'findings.guest_session_present.why':
    'Das ist keine Ableitung aus einer Datei, sondern eine Beobachtung: Gastzugriff funktioniert auf diesem Server, gleich was irgendwo konfiguriert ist.',
  'accounts.users': 'Benutzer',
  'accounts.groups': 'Gruppen',
  'accounts.new': 'Neues Konto',
  'accounts.create': 'Anlegen',
  'accounts.name': 'Name',
  'accounts.fullName': 'Vollständiger Name',
  'accounts.description': 'Beschreibung',
  'accounts.password': 'Passwort',
  'accounts.repeat': 'Passwort wiederholen',
  'accounts.mismatch': 'Die beiden Eingaben stimmen nicht überein.',
  'accounts.state': 'Zustand',
  'accounts.isEnabled': 'aktiv',
  'accounts.isDisabled': 'deaktiviert',
  'accounts.isLocked': 'gesperrt',
  'accounts.neverExpires': 'Passwort läuft nie ab',
  'accounts.createDisabled': 'Deaktiviert anlegen',
  'accounts.enable': 'Aktivieren',
  'accounts.disable': 'Deaktivieren',
  'accounts.delete': 'Löschen',
  'accounts.setPassword': 'Passwort setzen',
  'accounts.setPasswordFor': 'Passwort für {name} setzen',
  'accounts.protected': 'Dieses Konto gehört dem Server selbst.',
  'accounts.memberCount': '{count} Mitglieder',
  'accounts.members': 'Mitglieder',
  'accounts.noMembers': 'Diese Gruppe hat keine Mitglieder.',
  'accounts.membersReadOnly':
    'Die Mitgliedschaft wird hier gezeigt und noch nicht bearbeitet.',
  'accounts.created': 'Das Konto {name} wurde angelegt.',
  'accounts.deleted': 'Das Konto {name} wurde gelöscht.',
  'accounts.enabled': 'Das Konto {name} ist jetzt aktiv.',
  'accounts.disabled': 'Das Konto {name} ist jetzt deaktiviert.',
  'accounts.passwordSet': 'Das Passwort für {name} wurde gesetzt.',
  'accounts.deleteWarning':
    'Das Konto {name} wird vom Server entfernt. Seine Dateien bleiben liegen, aber die Rechte, die auf seine SID lauten, zeigen danach ins Leere.',
  'error.not_standalone': 'Dieser Server ist Domänenmitglied; seine Konten kommen aus der Domäne.',
  'error.not_standalone.hint':
    'Domänenbenutzer und -gruppen werden auf einem Domänencontroller verwaltet — mit SAMADCON oder mit den Windows-Werkzeugen.',
  'error.protected_account': 'Dieses Konto gehört dem Server selbst.',
  'error.protected_account.hint':
    'Stattdessen deaktivieren, wenn es nicht benutzbar sein soll.',
  'error.password_too_long': 'Das Passwort ist für dieses Protokoll zu lang.',
  'error.no_session_key':
    'Die Verbindung liefert keinen Sitzungsschlüssel, ein Passwort lässt sich damit nicht verschlüsseln.',
  'error.password_encryption_failed': 'Das Passwort ließ sich nicht für die Übertragung verschlüsseln.',
  'error.samr_password_unsupported': 'Diese Samba-Version unterstützt das Setzen des Passworts nicht.',

  // -- server settings ------------------------------------------------------
  'config.group.server': 'Server',
  'config.group.protocol': 'Protokoll',
  'config.group.access': 'Zugriff',
  'config.group.files': 'Dateien',
  'config.group.printing': 'Drucken',
  'config.group.winbind': 'Winbind',
  'config.group.advanced': 'Erweitert',

  'config.registryOnly':
    'Diese Seite zeigt und ändert nur, was in der Registry-Konfiguration steht. Die Text-smb.conf liest SAMFSCON nicht: ein leeres Feld heißt „hier nicht gesetzt“ und nicht „nicht gesetzt“.',
  'config.notApplied':
    'Gespeicherte Änderungen gelten erst, wenn Samba seine Konfiguration neu liest. SAMFSCON kann das weder auslösen noch etwas neu starten.',
  'config.notApplied.faster':
    'Auf dem Server geht das am schnellsten mit: smbcontrol all reload-config',
  'config.notApplied.restart':
    'Optionen mit „Neustart nötig“ wirken auch danach erst, wenn der genannte Dienst neu gestartet wurde.',
  'config.filesTabNote':
    'Diese Optionen sind die Vorgabe für alle Freigaben. Eine Freigabe, die dieselbe Option selbst setzt, gewinnt.',

  'config.sectionAbsent':
    'Dieser Server hat keinen global-Abschnitt in seiner Registry-Konfiguration.',
  'config.sectionUnknown':
    'Ob dieser Server einen global-Abschnitt in der Registry hat, ließ sich nicht feststellen. Das ist nicht dasselbe wie „er hat keinen“.',
  'config.createSection': 'Abschnitt anlegen',
  'config.createSection.explain':
    'Ihn anzulegen ändert nichts, solange die smb.conf des Servers nicht „include = registry“ enthält, und zwar vor den Zeilen, die dieselben Optionen setzen. Diese Datei kann SAMFSCON nicht lesen und das also nicht nachsehen.',
  'config.createSection.confirm': 'Trotzdem anlegen',

  'config.inForce.confirmed':
    'Der Server meldet, was hier gespeichert ist: die Registry-Konfiguration wird gelesen.',
  'config.inForce.contradicted':
    'Der Server meldet etwas anderes, als hier gespeichert ist. Vermutlich fehlt „include = registry“ in der Text-smb.conf, oder eine Zeile dort überschreibt sie.',
  'config.inForce.unknown.not_stored':
    'Ob die Registry-Konfiguration überhaupt gelesen wird, ist offen: es ist nichts gespeichert, womit sich das vergleichen ließe.',
  'config.inForce.unknown.variable_expansion':
    'Ob die Registry-Konfiguration gelesen wird, ist offen: der gespeicherte Wert enthält eine Variable, und der Server meldet sie aufgelöst.',
  'config.inForce.unknown.indistinguishable_from_default':
    'Ob die Registry-Konfiguration gelesen wird, ist offen: gespeicherter und gemeldeter Wert sind beide Sambas Vorgabe, und Übereinstimmung beweist dann nichts.',
  'config.inForce.unknown.live_unreadable':
    'Ob die Registry-Konfiguration gelesen wird, ist offen: der Server hat die Abfrage abgelehnt.',

  'config.verify.applied_confirmed': 'Gespeichert, und der Server meldet den neuen Wert bereits.',
  'config.verify.not_yet_visible':
    'Gespeichert. Der Server meldet weiter „{live}“ statt „{stored}“: entweder hat er seine Konfiguration noch nicht neu gelesen, oder die Text-smb.conf setzt dieselbe Option. Welches von beiden, kann diese Konsole nicht unterscheiden.',
  'config.verify.not_comparable':
    'Gespeichert. Ob es wirkt, ließ sich von hier aus nicht nachprüfen.',

  'config.notSetHere': 'hier nicht gesetzt',
  'config.bool.yes': 'ja',
  'config.bool.no': 'nein',
  'config.notSetHere.why':
    'Steht nicht in der Registry-Konfiguration. Ob die Text-smb.conf etwas setzt, sieht diese Konsole nicht.',
  'config.defaultIs': 'Ohne Eintrag gilt Sambas Vorgabe: {value}',
  'config.defaultNote.compiled_in':
    'Ohne Eintrag gilt die einkompilierte Vorgabe; welche das ist, meldet keine RPC-Schnittstelle.',
  'config.defaultNote.from_hostname': 'Ohne Eintrag leitet Samba den Wert aus dem Hostnamen ab.',
  'config.unlistedValue': 'gespeichert, steht nicht in der Auswahl',

  'config.effect.connection': 'gilt für neue Verbindungen',
  'config.effect.reload': 'gilt nach dem Neulesen der Konfiguration',
  'config.effect.restart': 'Neustart nötig',
  'config.effect.daemons': 'betrifft {names}',
  'config.readOnly': 'nur lesbar',
  'config.risky': 'riskant',

  'config.readOnly.machine_account_identity':
    'Dieser Name ist die Identität des Maschinenkontos. Er wird beim Domänenbeitritt gesetzt; ihn hier zu ändern bräche die Vertrauensstellung.',
  'config.readOnly.join_has_no_rpc':
    'Der Sicherheitsmodus wird beim Domänenbeitritt gesetzt. Dafür gibt es keine RPC-Schnittstelle: das geht auf dem Server selbst, mit net ads join.',
  'config.readOnly.member_workgroup_is_the_join':
    'Auf einem Domänenmitglied ist das die Domäne, der der Server beigetreten ist. Eine Änderung hier bräche den Beitritt.',
  'config.readOnly.bound_at_startup':
    'Samba wertet das beim Start aus. Ein hier geschriebener Wert würde bis zu einem Neustart, den diese Konsole nicht auslösen kann, etwas anderes anzeigen als gilt.',
  'config.readOnly.hides_configuration':
    'Das lenkt die Konfiguration in Dateien um, die diese Konsole nicht lesen kann. Sie zeigte dann weiter, was hier steht, während der Server etwas anderes täte.',
  'config.readOnly.invalidates_stored_names':
    'Alle bereits gespeicherten Namen sind mit dem jetzigen Trennzeichen geschrieben. Es zu ändern macht sie ungültig.',
  'config.readOnly.no_value_improves_on_the_default':
    'Sambas Vorgabe ist seit Jahren besser als jede Handeinstellung. Die Option steht hier, weil sie auf alten Servern gesetzt ist, nicht weil sie gesetzt gehört.',
  'config.readOnly.idmap_remaps_existing_files':
    'Die idmap-Bereiche bestimmen, welche Unix-Kennung zu welchem Domänenkonto gehört. Sie zu verschieben ordnet vorhandene Dateien anderen Konten zu.',

  'config.risk.lockout_hosts':
    'Diese Liste entscheidet, wer den Server erreicht. Der Server sieht diese Konsole unter {address}; fehlt diese Adresse, ist die nächste Verbindung von hier weg.',
  'config.risk.lockout_dialect_floor':
    'Verlangt der Server einen höheren Dialekt, als ein Client kann, verbindet dieser Client nicht mehr. SAMFSCON spricht mindestens {floor}.',
  'config.risk.lockout_dialect_ceiling':
    'Liegt die Obergrenze unter {floor}, erreicht diese Konsole den Server nicht mehr — und damit auch diese Einstellung nicht.',
  'config.risk.lockout_signing':
    'Verlangt der Server eine Signierung, die ein Client nicht leistet, verbindet dieser Client nicht mehr. Diese Konsole eingeschlossen.',
  'config.risk.availability_encryption':
    'Verschlüsselung zur Pflicht zu machen sperrt jeden Client aus, der sie nicht kann — auch Geräte wie Scanner und Drucker.',
  'config.risk.wide_links_disabled_by_unix_extensions':
    'Sind die Unix-Erweiterungen an, schaltet Samba „wide links“ für alle Freigaben ab. Eine Freigabe zeigt dann nicht mehr, was sie vorher zeigte, ohne dass an ihr etwas geändert wurde.',
  'config.risk.exposure_wide_links':
    'Symbolische Verweise dürfen dann aus der Freigabe herausführen. Wer die Freigabe erreicht, erreicht damit alles, worauf ein Verweis darin zeigt.',
  'config.risk.quiet_guest_substitution':
    'Fehlgeschlagene Anmeldungen werden dann still zum Gastkonto. Zugriffe erscheinen danach unter einem anderen Konto, als angemeldet wurde.',
  'config.risk.printing_management_off':
    'Windows-Clients können danach keine Druckertreiber und Warteschlangen mehr verwalten.',
  'config.risk.identity_meaning_changes':
    'Namen ohne Domänenteil meinen danach die eigene Domäne. Bereits vergebene Berechtigungen behalten ihre Schreibweise: dieselbe Zeichenkette meint dann etwas anderes.',
  'config.risk.disconnects_this_console':
    'Der Server trennt untätige Verbindungen nach dieser Zeit. Das betrifft auch die Verbindung, über die diese Konsole arbeitet.',
  'config.risk.exposure_usershares':
    'Damit dürfen auch Konten ohne Verwaltungsrechte Freigaben anlegen. Diese Konsole zeigt sie, verwalten kann sie sie nicht.',
  'config.risk.registry_shares_toggle':
    'Ausgeschaltet bedient der Server die Freigaben aus der Registry nicht mehr. Sie bleiben gespeichert und verschwinden vom Netz, und diese Konsole verwaltete danach etwas, das niemand sieht.',
  'config.risk.standalone_domain_rename':
    'Damit wandert der Arbeitsgruppen- bzw. Domänenname. Auf einem eigenständigen Server ist das eine Umbenennung; Clients finden ihn danach unter dem alten Namen nicht mehr.',

  'config.live.heading': 'Was der Server gerade meldet',
  'config.live.stored': 'hier gespeichert',
  'config.live.inForce': 'in Kraft',
  'config.live.source.srvsvc': 'was der Server meldet',
  'config.live.source.session_workgroup': 'womit diese Sitzung geöffnet wurde',
  'config.live.source.session_mode': 'wie sich diese Sitzung angemeldet hat',
  'config.live.source.observed': 'beobachtet, nicht abgefragt',
  'config.live.unreadable': 'Der Server hat diese Abfrage abgelehnt.',

  'config.idmap': 'idmap-Zuordnung',
  'config.idmap.empty':
    'Hier ist nichts in der Registry gespeichert. Der übliche Ort für idmap config ist die Text-smb.conf; leer heißt hier also „nichts in der Registry“ und nicht „kein idmap eingerichtet“.',
  'config.notApplicable': 'Für diese Art Server ohne Bedeutung',
  'config.notApplicable.why':
    'Gespeichert und angezeigt, auf einem Server dieser Art aber wirkungslos. Wegzulassen machte die Anzeige der übrigen Optionen zur Halbwahrheit.',
  'config.otherOptions': 'Weitere gespeicherte Optionen',
  'config.otherOptions.why':
    'Diese Optionen kennt SAMFSCON nicht. Sie stehen in der Registry dieses Servers und bleiben von hier aus unverändert.',

  'config.printing.noPrinterShares': 'Dieser Server veröffentlicht keine Druckerfreigaben.',
  'config.printing.unknown':
    'Ob dieser Server Druckerfreigaben veröffentlicht, ließ sich nicht feststellen: die Freigabeliste war nicht lesbar.',

  'config.revert': 'Verwerfen',
  'config.revert.why':
    'Setzt das Formular auf die zuletzt gelesenen Werte zurück. Das geht, solange diese Seite offen ist und die Verbindung steht; Gespeichertes rückgängig machen kann diese Konsole nicht.',
  'config.confirmTitle': 'Änderung bestätigen',
  'config.confirmIntro': 'Diese Änderungen können den Zugang zu diesem Server verändern:',
  'config.confirmProceed': 'Trotzdem speichern',
  'config.unwritable': 'Dieses Konto darf die Einstellungen dieses Servers nicht ändern.',

  'caps.note.registry_sections_unreadable':
    'Die Liste der Registry-Abschnitte ließ sich nicht lesen.',
  'caps.note.global_section_unreadable':
    'Der global-Abschnitt ließ sich nicht lesen.',
  'caps.note.live_value_unreadable':
    'Der Server hat die Abfrage für {option} abgelehnt.',
  'caps.note.own_address_ambiguous':
    'Diese Konsole hat mehrere Verbindungen zum Server. Welche Adresse hosts allow träfe, ist damit nicht eindeutig.',
  'caps.note.own_address_unknown':
    'Unter welcher Adresse der Server diese Konsole sieht, ließ sich nicht feststellen.',
  'caps.note.printer_shares_unknown':
    'Die Freigabeliste war nicht lesbar; ob es Druckerfreigaben gibt, bleibt offen.',
  'caps.note.capabilities_unreadable':
    'Was dieses Konto auf diesem Server darf, ließ sich nicht feststellen.',

  'error.global_section_absent':
    'Dieser Server hat keinen global-Abschnitt in seiner Registry-Konfiguration.',
  'error.global_section_absent.hint':
    'Er lässt sich anlegen. Das ändert aber nichts, solange die smb.conf des Servers nicht „include = registry“ vor den Zeilen enthält, die dieselben Optionen setzen.',
  'error.global_section_unknown':
    'Ob dieser Server einen global-Abschnitt in der Registry führt, ist unbekannt.',
  'error.global_section_unknown.hint':
    'Die Abschnittsliste war nicht lesbar, deshalb wurde nichts geschrieben. Das ist nicht dasselbe wie „es gibt keinen“.',
  'error.confirmation_required':
    'Diese Änderung betrifft eine Option, die bestätigt werden muss.',
  'error.dialect_below_console_floor':
    'Mit dieser Obergrenze käme diese Konsole nicht mehr an den Server.',
  'error.dialect_below_console_floor.hint':
    'SAMFSCON verhandelt nicht herunter. Zurückstellen ließe sich das danach nur mit einer Sitzung auf dem Server selbst.',
  'error.dialect_window_empty':
    'Mindest- und Höchstdialekt lassen zusammen keinen einzigen Dialekt übrig.',
  'error.hosts_allow_excludes_console':
    'Diese Liste enthält die Adresse nicht, unter der der Server diese Konsole sieht.',
  'error.hosts_allow_excludes_console.hint':
    'Nachgesehen, nicht vermutet: keine der Angaben trifft zu. Die Adresse ergänzen — es ist die des SAMFSCON-Containers, nicht die des Arbeitsplatzes.',
  'error.hosts_allow_undecidable':
    'Ob diese Liste diese Konsole weiter zulässt, ließ sich nicht entscheiden.',
  'error.hosts_allow_undecidable.hint':
    'Nicht dasselbe wie ausgeschlossen: es wurde nicht geprüft, nicht durchgefallen. Bestätigen speichert die Liste trotzdem.',
  'error.hosts_deny_includes_console':
    'Diese Liste nennt die Adresse, unter der der Server diese Konsole sieht, und keine Zulassungsliste holt sie zurück.',
  'error.hosts_deny_undecidable':
    'Ob diese Liste diese Konsole aussperrt, ließ sich nicht entscheiden.',
  'error.option_not_applicable':
    'Diese Option hat auf einem Server dieser Art keine Wirkung.',
  'error.unknown_option':
    'Diese Option kennt SAMFSCON nicht.',

  'config.undecided.title': 'Nicht nachprüfbar',
  'config.undecided.intro':
    'Diese Prüfung ließ sich nicht durchführen. Sie ist nicht fehlgeschlagen — sie konnte nicht laufen, und das ist etwas anderes.',
  'config.undecided.entries': 'Nicht auflösbar: {entries}',
  'config.undecided.accept': 'Ohne diese Prüfung speichern',
  'error.own_address_unknown':
    'Unter welcher Adresse der Server diese Konsole sieht, ließ sich nicht feststellen.',
  'error.own_address_unknown.hint':
    'Ohne diese Adresse lässt sich zu keiner Rechnerliste sagen, ob sie diese Konsole weiter zulässt. Das ist keine Aussage über die Liste: an ihr ändert nichts etwas daran. Bestätigen speichert sie ungeprüft.',

  // -- errors --------------------------------------------------------------
  'error.kerberos_needs_a_name': 'Kerberos braucht den Namen des Servers, bekannt ist nur seine Adresse.',
  'error.kerberos_needs_a_name.hint':
    'Den Namen des Servers statt seiner Adresse eintragen — oder SAMFSCON ihn lernen lassen: er kommt aus einer unauthentifizierten Policy-Abfrage, die dieser Server abgelehnt hat. Welcher Name auch benutzt wird, der Container muss ihn auflösen können; notfalls über extra_hosts.',
  'error.hint': 'Hinweis',
  'error.details': 'Technische Einzelheiten',
  'error.network_error': 'Der Server ist nicht erreichbar.',
  'error.network_error.hint': 'Läuft der Container noch, und ist das Netz in Ordnung?',
  'error.unexpected_response': 'Unerwartete Antwort vom Server.',
  'error.internal_error': 'Ein unerwarteter Fehler ist aufgetreten.',
  'error.internal_error.hint': 'Einzelheiten stehen im Container-Protokoll.',
  'error.validation_failed': 'Die Eingabe ist unvollständig oder ungültig.',
  'error.csrf_failed': 'Die Anfrage hatte kein gültiges Sicherheitstoken.',
  'error.csrf_failed.hint': 'Seite neu laden und noch einmal versuchen.',

  'error.not_authenticated': 'Nicht angemeldet.',
  'error.session_expired': 'Die Sitzung ist abgelaufen.',
  'error.session_expired.hint': 'Bitte erneut anmelden.',
  'error.secret_cleared': 'Die Anmeldedaten dieser Sitzung wurden verworfen.',
  'error.secret_cleared.hint': 'Bitte erneut anmelden.',
  'error.authentication_failed': 'Die Anmeldung ist fehlgeschlagen.',
  'error.invalid_credentials': 'Falscher Benutzername oder falsches Passwort.',
  'error.user_not_found': 'Dieses Konto gibt es auf dem Server nicht.',
  'error.account_not_found': 'Dieses Konto gibt es auf dem Server nicht.',
  'error.kerberos_principal_unknown': 'Dieses Konto gibt es in diesem Realm nicht.',
  'error.kerberos_principal_unknown.hint':
    'Als benutzer@REALM anmelden und die Schreibweise des Realms prüfen.',
  'error.directory_create_denied': 'Der Server hat das Anlegen dieses Ordners abgelehnt.',
  'error.directory_create_denied.hint':
    'Einen Ordner anzulegen ist ein gewöhnlicher Dateizugriff: das Konto braucht Schreibrechte auf dem Ordner, in dem er entstehen soll — dessen Berechtigungen prüfen. SeDiskOperatorPrivilege hilft hier nicht, dieses Recht gilt für das Verwalten von Freigaben.',
  'error.account_disabled': 'Das Konto ist deaktiviert.',
  'error.account_expired': 'Das Konto ist abgelaufen.',
  'error.account_locked_out': 'Das Konto ist gesperrt.',
  'error.password_expired': 'Das Passwort ist abgelaufen.',
  'error.password_must_change': 'Das Passwort muss zuerst geändert werden.',
  'error.login_throttled': 'Zu viele fehlgeschlagene Anmeldeversuche.',
  'error.login_throttled.hint':
    'SAMFSCON hält weitere Versuche zurück, damit das Konto nicht gesperrt wird.',
  'error.clock_skew': 'Die Uhren von SAMFSCON und dem Domänencontroller weichen zu stark ab.',
  'error.clock_skew.hint': 'Kerberos toleriert etwa fünf Minuten — die Uhr des Containers per NTP stellen.',
  'error.missing_username': 'Der Benutzername fehlt.',
  'error.invalid_username': 'Der Benutzername enthält unzulässige Zeichen.',
  'error.missing_password': 'Das Passwort fehlt.',
  'error.no_ticket': 'Es wurde kein Kerberos-Ticket ausgestellt.',
  'error.no_ticket.hint':
    'Realm-Schreibweise, Uhrzeitunterschied zum KDC und Existenz des Kontos prüfen.',
  'error.kdc_unreachable': 'Es war kein Key Distribution Center erreichbar.',
  'error.kdc_unreachable.hint': 'SAMFSCON_KDC_HOSTS, die SRV-Einträge und Port 88 prüfen.',
  'error.spn_not_found': 'Der Fileserver hat in diesem Realm keinen Dienstprincipal.',
  'error.spn_not_found.hint':
    'Kerberos stellt Tickets für cifs/<Hostname> aus. Den Namen des Servers verwenden statt einer Adresse, und prüfen, ob er noch der Domäne beigetreten ist.',
  'error.kerberos_unavailable': 'Es konnte kein Kerberos-Ticket beschafft werden.',
  'error.ccache_unsupported': 'Das Kerberos-Ticket konnte nicht an die Verbindung gehängt werden.',

  'error.missing_server': 'Es wurde kein Server angegeben.',
  'error.invalid_server': 'Die Serveradresse ist unbrauchbar.',
  'error.no_target': 'Es wurde kein Server angegeben, und diese Installation hat keinen Standard.',
  'error.no_target.hint': 'Die Adresse eines Fileservers eingeben.',
  'error.custom_servers_disabled': 'Diese Installation erlaubt nur die vorkonfigurierten Server.',
  'error.unknown_server_profile': 'Diesen vorkonfigurierten Server gibt es nicht.',
  'error.incomplete_server_profile': 'Der vorkonfigurierte Server nennt keinen Host.',
  'error.invalid_mode': 'Unbekannte Art von Server.',
  'error.mode_undecided': 'SAMFSCON konnte nicht erkennen, ob dieser Server Domänenmitglied ist.',
  'error.mode_undecided.hint':
    'Der Server hat keine unauthentifizierte Anfrage beantwortet — meist „restrict anonymous“. Bitte im Anmeldeformular „Domänenmitglied“ oder „Eigenständig“ wählen.',
  'error.missing_realm': 'Für diesen Server ist kein Kerberos-Realm bekannt.',
  'error.missing_realm.hint': 'Den Realm eintragen oder sich als benutzer@REALM anmelden.',
  'error.no_realm': 'Der Fileserver hat keinen Kerberos-Realm genannt.',
  'error.standalone_disabled': 'Eigenständige Server sind auf dieser Installation nicht freigegeben.',
  'error.standalone_disabled.hint':
    'Eine solche Sitzung müsste das Passwort im Speicher halten; SAMFSCON_ALLOW_STANDALONE=0 lehnt diesen Handel ab.',
  'error.no_credentials': 'Diese Sitzung hat keine Anmeldedaten für den Server.',

  'error.server_unreachable': 'Der Fileserver ist nicht erreichbar.',
  'error.server_unreachable.hint':
    'Prüfen, ob Port 445 offen ist und der Server SMB3 spricht — SMB1 verhandelt SAMFSCON nicht.',
  'error.server_unavailable': 'Der Fileserver ist nicht verfügbar.',
  'error.server_name_unknown': 'Der Fileserver ist nicht erreichbar.',
  'error.server_name_unknown.hint':
    'Es war nur die Adresse bekannt, und Kerberos stellt Tickets für cifs/<Hostname> aus — für eine nackte Adresse gibt es keinen Principal. Prüfen, ob der Container den Namen des Servers auflösen und ihn auf Port 445 erreichen kann.',
  'error.server_timeout': 'Der Fileserver hat nicht rechtzeitig geantwortet.',
  'error.timeout': 'Der Vorgang wurde nicht rechtzeitig fertig.',
  'error.server_error': 'Der Fileserver hat einen Fehler gemeldet.',
  'error.samba_missing': 'Die Samba-Bindings im Container sind unvollständig.',
  'error.smb_binding_unsupported': 'Die SMB-Verbindung konnte nicht geöffnet werden.',
  'error.smb_dialect_mismatch': 'Der Aufruf ist über den ausgehandelten SMB-Dialekt nicht verfügbar.',
  'error.lsa_unsupported': 'Die LSA-Bindings dieser Samba-Version haben eine unerwartete Signatur.',
  'error.winreg_unsupported': 'Diese Samba-Version unterstützt den Registry-Aufruf nicht.',
  'error.unsupported_info_level': 'Der Server unterstützt diese Informationsstufe nicht.',
  'error.unsupported_info_level.hint':
    'Die Samba-Version auf dem Server ist vermutlich älter, als SAMFSCON erwartet.',
  'error.not_supported': 'Der Server unterstützt diesen Vorgang nicht.',

  'error.insufficient_access': 'Dieser Vorgang wurde für Ihr Konto abgelehnt.',
  'error.insufficient_access.hint':
    'Der Server sagt nicht, welches Recht fehlt, und welches es ist, hängt davon ab, was versucht wurde: bei Dateien und Ordnern Schreibrechte auf dem übergeordneten Verzeichnis, bei Freigaben SeDiskOperatorPrivilege, bei der Konfiguration Schreibzugriff auf die Registry.',
  'error.missing_disk_operator': 'Ihr Konto darf die Freigaben dieses Servers nicht verwalten.',
  'error.missing_disk_operator.hint':
    'Der Server prüft dafür SeDiskOperatorPrivilege. Vergeben mit: net rpc rights grant \'<Gruppe>\' SeDiskOperatorPrivilege -U <Admin>',
  'error.not_configured': 'Der Server ist dafür nicht eingerichtet.',
  'error.registry_shares_disabled': 'Dieser Server liefert keine Registry-Freigaben aus.',
  'error.registry_shares_disabled.hint':
    'Die Konfiguration der Freigabe steht bereits in der Registry — Samba ignoriert sie nur. „registry shares = yes“ in den Abschnitt [global] der smb.conf des Servers eintragen und Samba neu laden; danach gilt sie, ohne dass etwas neu eingegeben werden muss.',
  'caps.note.registry_shares_disabled':
    'In der Registry dieses Servers stehen Freigaben, die er nicht ausliefert — es fehlt „registry shares = yes“ im Abschnitt [global] seiner smb.conf. Ohne das ignoriert Samba alles, was diese Konsole schreibt.',
  'error.registry_not_writable': 'Ihr Konto darf die Konfiguration dieses Servers nicht ändern.',
  'error.registry_not_writable.hint':
    'Freigaben werden in die Registry-Konfiguration unter HKLM\Software\Samba\smbconf geschrieben; dieses Konto darf sie lesen, aber nicht ändern.',
  'error.registry_config_missing':
    'Dieser Server ist nicht dafür eingerichtet, Freigaben über das Netz zu verwalten.',
  'error.registry_config_missing.hint':
    'In den Abschnitt [global] der smb.conf des Servers „include = registry“ und „registry shares = yes“ eintragen und Samba neu laden. Lesen funktioniert ohne das; nur Änderungen brauchen es.',

  'error.not_found': 'Nicht gefunden.',
  'error.share_not_found': 'Diese Freigabe gibt es auf dem Server nicht.',
  'error.share_exists': 'Eine Freigabe mit diesem Namen gibt es bereits.',
  'error.share_path_missing': 'Das Verzeichnis, das die Freigabe zeigen soll, gibt es nicht.',
  'error.share_path_missing.hint':
    'SAMFSCON verwaltet den Server über das Netz und kann kein Verzeichnis außerhalb einer bestehenden Freigabe anlegen. Bitte zuerst auf dem Server anlegen.',
  'error.share_path_redirected': 'Der Pfad ist bereits umgeleitet und kann nicht freigegeben werden.',
  'error.path_not_found': 'Diesen Pfad gibt es auf dem Server nicht.',
  'error.already_exists': 'Das gibt es bereits.',
  'error.already_member': 'Das Konto ist bereits Mitglied dieser Gruppe.',
  'error.not_a_member': 'Das Konto ist nicht Mitglied dieser Gruppe.',
  'error.not_empty': 'Das Verzeichnis ist nicht leer.',
  'error.file_in_use': 'Die Datei ist gerade in Benutzung.',
  'error.file_in_use.hint': 'Jemand hat sie offen. Die Sitzungsansicht zeigt, wer.',
  'error.session_not_found': 'Diese Sitzung gibt es nicht mehr.',
  'error.session_not_found.hint': 'Sie wurde vermutlich zwischen Auflistung und Anfrage beendet.',
  'error.sid_not_resolved': 'Der Name konnte keinem Konto zugeordnet werden.',
  'error.sid_not_resolved.hint':
    'Genau so schreiben, wie das Konto auf dem Server heißt, oder als DOMÄNE\\Name für ein Domänenkonto.',
  'error.invalid_sid': 'Das ist keine gültige Sicherheitskennung.',
  'error.share_add_rejected': 'Der Server hat das Anlegen dieser Freigabe abgelehnt.',
  'error.share_add_rejected.hint':
    'Der Name hat die Prüfung von SAMFSCON bestanden — der Server beanstandet also die Anfrage, nicht den Namen; vermutlich kam er leer bei ihm an. Das ist ein Fehler in SAMFSCON, nicht in Ihrer Eingabe. Einzelheiten stehen im Container-Protokoll.',
  'error.invalid_name': 'Der Name ist für diesen Server nicht zulässig.',
  'error.invalid_parameter': 'Der Server hat einen Parameter der Anfrage abgelehnt.',
  'error.invalid_request': 'Die Anfrage ist ungültig.',
  'error.constraint_violation': 'Der Wert verletzt eine Vorgabe des Servers.',
  'error.password_policy_violation': 'Das Passwort entspricht nicht den Vorgaben des Servers.',
  'error.password_policy_violation.hint':
    'Länge, Komplexität, Mindestalter und Passworthistorie prüfen.',
  'error.too_many_sessions': 'Zu viele gleichzeitige Sitzungen.',
  'error.session_closed': 'Die Sitzung wurde geschlossen.',
  'error.unknown_pipe': 'Unbekannte RPC-Schnittstelle.',
} as const

export type MessageKey = keyof typeof de
export type Language = 'de' | 'en'

export const en: Record<MessageKey, string> = {
  'app.title': 'SAMFSCON',
  'app.subtitle': 'Samba FileServer Console',

  'nav.logout': 'Sign out',
  'nav.search': 'Search',
  'nav.server': 'Server',
  'nav.language': 'Language',

  'snapin.shares': 'Shares',
  'snapin.sessions': 'Sessions',
  'snapin.files': 'Folders and files',
  'snapin.accounts': 'Local users and groups',
  'snapin.diagnostics': 'Diagnostics',
  'snapin.config': 'Server settings',

  'snapin.shares.note': 'Create, change and remove shares.',
  'snapin.sessions.note': 'Who is connected, and which files are open.',
  'snapin.files.note': 'Directories inside a share, and their permissions.',
  'snapin.accounts.note': 'Accounts that live on this server itself.',
  'snapin.diagnostics.note': 'What stands out on the server, and what this account may do.',
  'snapin.config.note': 'The server’s global settings.',
  'snapin.unavailable': 'This part is not built yet.',
  'snapin.accounts.domainMember':
    'This server is a member of the {domain} domain. Its users and groups come from the domain and are managed there — on a domain controller, or with SAMADCON. Only a standalone server’s local accounts appear here.',

  'login.title': 'Sign in',
  'login.server': 'File server',
  'login.serverPlaceholder': 'fs1.example.lan or 192.168.1.50',
  'login.serverHelp':
    'Address or name. SAMFSCON asks the server what it is and fills in the rest.',
  'login.username': 'User name',
  'login.usernamePlaceholder': 'Administrator',
  'login.password': 'Password',
  'login.submit': 'Sign in',
  'login.signingIn': 'Signing in …',
  'login.probe': 'Check the server',
  'login.probing': 'Checking the server …',
  'login.profile': 'Configured server',
  'login.profileNone': 'Type an address',
  'login.recent': 'Recently used',
  'login.forget': 'Remove',
  'login.realm': 'Kerberos realm',
  'login.realmHelp': 'Only needed when the server will not name it itself.',

  'login.mode': 'Kind of server',
  'login.mode.ad_member': 'Domain member (Kerberos)',
  'login.mode.standalone': 'Standalone (user name and password)',
  'login.mode.auto': 'Detect automatically',
  'login.mode.detected': 'Detected: {mode}',
  'login.mode.undecided':
    'The server answered no unauthenticated query — usually ‘restrict anonymous’. Please choose the kind of server yourself.',
  'login.mode.standaloneDisabled': 'Standalone servers are not enabled on this installation.',

  'login.standaloneWarning':
    'A standalone server has no Kerberos. The password therefore stays in SAMFSCON’s memory for the lifetime of the session — never on disk, never in the log, and overwritten when you sign out.',

  'login.probeResult': 'The server reports itself as {name}',
  'login.probeVersion': 'Samba {version}',
  'login.probeUnreachable': 'The server cannot be reached.',

  'session.auth.kerberos': 'Kerberos',
  'session.auth.ntlm': 'NTLM',
  'session.signed': 'signed',
  'session.encrypted': 'encrypted',
  'session.identityVerified': 'Server identity verified',
  'session.identityUnverified': 'Server identity unverified',
  'session.identityUnverified.why':
    'NTLM proves the client to the server, not the other way round. The connection is signed, but who is at the other end is not thereby proven.',
  'session.holdsPassword': 'Password in memory',
  'session.holdsPassword.why':
    'This session runs against a standalone server without Kerberos. The password is needed again for every connection and therefore stays in memory until the session ends.',

  'caps.title': 'What this account may do here',
  'caps.canManageShares': 'Manage shares',
  'caps.registryConfig': 'Registry configuration',
  'caps.diskOperator': 'SeDiskOperatorPrivilege',
  'caps.yes': 'yes',
  'caps.no': 'no',
  'caps.unknown': 'could not be determined',
  'caps.holders': 'Held by: {names}',

  'action.cancel': 'Cancel',
  'action.save': 'Save',
  'action.close': 'Close',
  'action.retry': 'Try again',
  'action.refresh': 'Refresh',
  'action.properties': 'Properties',
  'action.delete': 'Delete',
  'action.openFolder': 'Open the folder',
  'action.dismiss': 'Dismiss',

  'status.loading': 'Loading …',
  'status.empty': 'Nothing here.',
  'status.saved': 'Saved.',

  'type.share': 'Share',
  'type.folder': 'Folder',
  'type.file': 'File',
  'type.user': 'User',
  'type.group': 'Group',
  'type.alias': 'Local group',
  'type.well_known_group': 'System group',
  'type.computer': 'Computer',
  'type.domain': 'Domain',
  'type.contact': 'Contact',
  'type.unknown': 'Unknown',
  'type.deleted': 'Deleted',
  'type.invalid': 'Invalid',
  'type.container': 'Container',
  'type.server': 'Server',
  'type.session': 'Session',
  'type.diagnostics': 'Diagnostics',
  'type.permissions': 'Permissions',

  'list.count_one': '{count} entry',
  'list.count_other': '{count} entries',


  'share.new': 'New share',
  'share.create': 'Create',
  'share.delete': 'Delete share',
  'share.created': 'The share {name} was created.',
  'share.deleteConfirm': 'Delete the share',
  'share.deleteWarning':
    'The share {name} stops being published and its configuration is removed.',
  'share.deleteKeepsFiles':
    'The directory and everything in it stays where it is — this console deletes no files:',
  'share.deleted': 'The share {name} was deleted.',
  'share.selectOne': 'Select a share.',
  'share.name': 'Name',
  'share.name.hint': 'What the share is called on the network.',
  'share.path': 'Path on the server',
  'share.path.hint':
    'Must already exist on the server. SAMFSCON manages it over the network and cannot create a directory outside an existing share.',
  'share.comment': 'Comment',
  'share.readOnly': 'Read only',
  'share.browseable': 'Visible when browsing',
  'share.guestOk': 'Access without a password',
  'share.guestOk.hint': 'Rarely what anyone wants.',
  'share.default': 'default',
  'share.default.why':
    'This share does not set the option; the server’s default is shown. Changing it sets it explicitly.',
  'share.connectedCount': '{count} connected',
  'share.connected.why': 'How many clients have this share open right now.',
  'share.createdNotServed':
    'The share {name} was written, but the server is not serving it yet. The configuration is complete — one of two things is missing: either smbd has not re-read the registry (‘smbcontrol all reload-config’ on the server), or smb.conf is missing ‘registry shares = yes’ in its [global] section. The reload is quicker to check.',
  'share.currentUsers': 'Connected',
  'share.fromSmbConf': 'from smb.conf',
  'share.fromSmbConf.why':
    'This share is written into the server\u2019s text smb.conf. SAMFSCON edits the registry configuration \u2014 the part that is reachable over the network. Changing this share means editing it on the server, or moving it into the registry with \u2018net conf import\u2019.',
  'share.needsModule':
    'Takes effect only once the VFS module \u2018{module}\u2019 is loaded under \u2018vfs objects\u2019.',
  'share.otherOptions': 'Other options',
  'share.otherOptions.why':
    'Set on the server but not described in SAMFSCON\u2019s catalogue. Shown rather than hidden \u2014 and left untouched when saving.',
  'share.cannotWrite': 'Shares cannot be changed here on this server.',
  'share.group.basic': 'General',
  'share.group.access': 'Access',
  'share.group.files': 'Files',
  'share.group.vfs': 'Modules',
  'share.group.advanced': 'Advanced',

  'caps.note.privilege_unconfirmed':
    'Whether your account may change shares cannot be said from here: SeDiskOperatorPrivilege is held by {holders}, and whether you belong through a nested group is something this check cannot resolve — the server decides that when it is asked. Try the change. If it refuses, the right really is missing, and this command on the server grants it: {command}',
  'caps.note.no_disk_operators.command':
    'Nobody on this server holds SeDiskOperatorPrivilege — while that is so, nobody can change shares here. Run on the server: {command}',
  'caps.note.registry_missing':
    'The server has no reachable registry configuration — add ‘include = registry’ and ‘registry shares = yes’ to its smb.conf.',
  'caps.note.registry_unreadable':
    'The registry configuration exists but this account may not read it.',
  'caps.note.registry_read_only':
    'This account may read the registry configuration but not change it.',
  'caps.note.registry_probe_failed': 'The registry configuration could not be probed ({detail}).',
  'caps.note.privilege_list_unreadable': 'The privilege list could not be read ({reason}).',
  'caps.note.sid_unknown':
    'The signed-in account’s SID is unknown, so its privileges could not be checked.',
  'caps.note.disk_operators_are': 'SeDiskOperatorPrivilege is held by: {names}.',
  'caps.note.no_disk_operators':
    'Nobody on this server holds SeDiskOperatorPrivilege — while that is so, nobody can change shares here. Run on the server: {command}',
  'caps.noRegistryConfig':
    'This server is not set up for managing shares over the network. Add \u2018include = registry\u2019 and \u2018registry shares = yes\u2019 to the [global] section of its smb.conf and reload Samba. Reading works without it.',
  'caps.noDiskOperator':
    'Your account does not hold SeDiskOperatorPrivilege on this server. It is held by: {names}. Grant it with: net rpc rights grant <group> SeDiskOperatorPrivilege -U <admin>',
  'caps.unknownWhy':
    'Whether shares can be managed here could not be determined \u2014 the check itself was refused.',

  'error.option_not_editable': 'This option is set through the share itself.',
  'error.invalid_option_value': 'That value does not fit the option.',
  'error.share_not_editable': 'This share is defined in smb.conf and cannot be changed here.',
  'error.share_not_editable.hint':
    'SAMFSCON edits the registry configuration. A share written into smb.conf has to be changed there \u2014 or moved into the registry with \u2018net conf import\u2019.',
  'error.administrative_share': 'This share belongs to the server itself.',
  'error.administrative_share.hint':
    'IPC$, ADMIN$ and print$ are managed by Samba, not by a console.',


  'sessions.connected': 'Connected',
  'sessions.files': 'Open files',
  'sessions.nobody': 'Nobody is connected right now.',
  'sessions.noFiles': 'No file is open right now.',
  'sessions.readAt': 'Read at {when}',
  'sessions.filter': 'Filter by path or user',
  'sessions.user': 'User',
  'sessions.client': 'Machine',
  'sessions.openFiles': 'Files',
  'sessions.connectedFor': 'Connected for',
  'sessions.idleFor': 'Idle for',
  'sessions.path': 'Path',
  'sessions.access': 'Access',
  'sessions.locks': 'Locks',
  'sessions.guest': 'Guest',
  'sessions.access.read': 'read',
  'sessions.access.write': 'write',
  'sessions.access.create': 'create',
  'sessions.close': 'Close',
  'sessions.showFiles': 'Show open files',
  'sessions.closeConfirm': 'Close the file',
  'sessions.closeWarning':
    '{path} will be force-closed for {user}. Unsaved changes are lost, and the client is not asked.',
  'sessions.closed': '{path} was closed.',
  'error.file_not_open': 'That file is no longer open.',
  'error.file_not_open.hint':
    'Somebody closed it, or the listing is out of date. Refresh and look again.',


  'perm.share.what':
    'Share permissions are checked once, when a client opens the share, and bound everything that follows. On most Samba servers this says Everyone: Full Control, and the file permissions do the real work.',
  'perm.file.what':
    'File permissions are checked on every access. What is actually permitted is the intersection of these and the share permissions.',
  'perm.raw': 'Security descriptor (SDDL)',
  'perm.unixUser': 'Unix user {id}',
  'perm.unixGroup': 'Unix group {id}',
  'perm.derived': 'from the SID',
  'perm.derived.why':
    'This name comes from the specification — RID 500 is Administrator in every domain. The server did not confirm it, so the account need not still exist.',
  'perm.owner': 'Owner',
  'perm.group': 'Group',
  'perm.grantsNothing': 'grants nothing',
  'perm.grantsNothing.why':
    'Entries that grant nothing are not a fault: Samba builds the NT ACL out of the POSIX one, and a POSIX entry with no permission bits becomes an ACE with an empty access mask. It is listed because it is in the descriptor.',
  'perm.trustee': 'Account',
  'perm.kind': 'Type',
  'perm.kind.allow': 'Allow',
  'perm.kind.deny': 'Deny',
  'perm.level': 'Permission',
  'perm.appliesTo': 'Applies to',
  'perm.appliesTo.this_only': 'this object only',
  'perm.appliesTo.this_and_children': 'this object and everything below',
  'perm.appliesTo.children_only': 'everything below only',
  'perm.appliesTo.folders': 'folders',
  'perm.appliesTo.files': 'files',
  'perm.preset.full': 'Full control',
  'perm.preset.modify': 'Modify',
  'perm.preset.read_execute': 'Read and execute',
  'perm.preset.read': 'Read',
  'perm.preset.write': 'Write',
  'perm.inherited': 'inherited',
  'perm.inherited.why':
    'This entry comes from the parent directory. Changing it here would break the inheritance it came from — it is changed where it originates.',
  'perm.remove': 'Remove',
  'perm.add': 'Add an entry',
  'perm.protected': 'Stop inheriting from the parent directory',
  'perm.protected.hint':
    'After this, only the entries listed here apply. The inherited ones disappear.',
  'perm.inspect': 'Show the effective rights',
  'perm.effective': 'Effective rights for {trustee}',
  'perm.nothing': 'None.',
  'perm.limitedByShare':
    'The share permission bounds this: the file permission allows more than this share does.',
  'perm.directOnly':
    'Counted from the entries naming this account explicitly — group memberships are not included.',
  'perm.pick': 'Choose an account',
  'perm.pick.search': 'Name',
  'perm.pick.hint':
    'Resolved by the file server itself — local groups and domain accounts through one call.',
  'perm.pick.wellKnown': 'Standard accounts',
  'perm.unresolved': 'not resolved',
  'perm.right.read': 'Read',
  'perm.right.write': 'Write',
  'perm.right.append': 'Append',
  'perm.right.execute': 'Execute',
  'perm.right.delete': 'Delete',
  'perm.right.delete_child': 'Delete child',
  'perm.right.read_attributes': 'Read attributes',
  'perm.right.write_attributes': 'Write attributes',
  'perm.right.read_permissions': 'Read permissions',
  'perm.right.change_permissions': 'Change permissions',
  'perm.right.take_ownership': 'Take ownership',
  'share.group.permissions': 'Share permissions',
  'share.group.filePermissions': 'File permissions',
  'nav.consoles': 'Consoles',
  'tree.nothing': 'Nothing here yet.',
  'nav.actions': 'Actions',
  'app.sourceTitle': 'Source and licence of this build',
  'menu.empty': 'Nothing can be done here.',
  'splitter.tree': 'Width of the navigation pane',
  'splitter.detail': 'Width of the properties pane',
  'splitter.hint': 'Drag to resize, double-click to reset',
  'window.minimise': 'Minimise',
  'window.maximise': 'Maximise',
  'window.resize': 'Resize',
  'window.taskbar': 'Open windows',
  'window.gone': 'This no longer exists on the server.',
  'error.no_dacl': 'The security descriptor has no access list.',
  'error.no_dacl.hint': 'A descriptor without one grants nothing to anybody.',
  'error.invalid_sddl': 'This is not a valid security descriptor.',
  'error.sddl_domain_unknown':
    'This server does not say which domain these entries belong to.',
  'error.sddl_domain_unknown.hint':
    'Aliases like DA or DU are not whole SIDs in SDDL — they are a number relative to a domain. Which domain could not be learned, and a guess would produce a valid SID belonging to nobody. Write the SID out in full, or pick the account from the list.',
  'error.unknown_preset': 'Unknown permission level.',
  'error.sddl_unrenderable': 'The security descriptor could not be rendered.',
  'error.sddl_unrenderable.hint':
    'There is one and this console could not read it. It is not shown as unrestricted, because saving on top of that would replace it. `net rpc share getsecurity <share>` on the server prints the same descriptor in a form that can be compared.',
  'error.srvsvc_unsupported': 'This Samba build does not support the call.',
  'error.path_escapes_share': 'A path may not step outside its share.',
  'error.missing_path': 'No name was given.',


  'files.selectOne': 'Select a folder in the tree.',
  'files.created': 'The folder {name} was created.',
  'files.newFolder': 'New folder',
  'files.newFolderIn': 'Will be created in',
  'files.create': 'Create',
  'files.open': 'Open',
  'files.name': 'Name',
  'files.size': 'Size',
  'files.modified': 'Modified',
  'files.attributes': 'Attributes',
  'files.readOnly': 'read-only',
  'files.hidden': 'hidden',
  'files.system': 'system',
  'files.empty': 'This folder is empty.',
  'files.noFolders': 'No subfolders.',
  'files.unreadable': 'Not readable with this account.',
  'files.truncated':
    'Not every entry is shown — the server stops a long listing. Step into a subfolder to see the rest.',
  'files.inheritsPermissions':
    'The new folder inherits the parent’s permissions, as any directory created over SMB does. They can be changed afterwards in its properties.',
  'files.nameForbidden': 'These characters are not allowed in a name: \ / : * ? " < > |',
  'share.root': 'Root of {name}',
  'snapin.diagnostics.heading': 'What stands out on this server',
  'findings.none': 'Nothing this console looks for stood out.',
  'findings.severity.high': 'high',
  'findings.severity.medium': 'medium',
  'findings.severity.low': 'low',
  'findings.severity.info': 'note',
  'findings.area.management': 'Management',
  'findings.area.transport': 'Connection',
  'findings.area.shares': 'Shares',
  'findings.area.sessions': 'Sessions',
  'findings.generatedAt': 'Read at {when}',
  'findings.evidence': 'Decided from',
  'findings.unreadableHeading': 'What could not be checked',
  'findings.todo': 'To do:',
  'findings.unreadable.capabilities_unreadable.do':
    'Sign in with an account that may administer this server: the check itself was refused, so there is nothing to configure.',
  'findings.unreadable.privilege_unconfirmed.do':
    'Nothing. Try the change: if the server refuses, the right really is missing, and this grants it on the server: net rpc rights grant \'<group>\' SeDiskOperatorPrivilege -U <admin>',
  'findings.unreadable.registry_state_unknown.do':
    'Check on the server whether the registry configuration is included: testparm -s | grep -i registry',
  'findings.unreadable.server_facts_unreadable.do':
    'Nothing urgent: these details are incidental and everything else here works without them. An account with wider rights on the server would get them.',
  'findings.unreadable.shares_unreadable.do':
    'The list comes over srvsvc and needs administrative rights on the server. If it is refused, this account does not have them.',
  'findings.unreadable.registry_unreadable.do':
    'Check access to HKLM\\Software\\Samba\\smbconf. Any account that may administer the server may read it; without it this console is limited to what srvsvc reports.',
  'findings.unreadable.configuration_not_in_registry.do':
    'This share lives in the text smb.conf, which SAMFSCON does not read. It becomes visible and editable only once it is in the registry — which means changing how the server is configured (net conf import, plus include = registry in smb.conf) and is not something to do in passing.',
  'findings.unreadable.sessions_unreadable.do':
    'This list also comes over srvsvc and needs administrative rights on the server.',
  'findings.unreadableWhy':
    'The report below says nothing about these — not because there is nothing there, but because it could not be read from here. Each one says what to do about it.',
  'findings.coverage': '{readable} of {total} shares have readable configuration.',
  'findings.coverage.rest':
    'The other {count} are in the text smb.conf, which this console does not read — this report says nothing about their options.',
  'findings.coverage.notProbed':
    'Whether the shares can be opened, and how their file permissions stand against their share permissions, was not examined. That is not the same as there being nothing there.',
  'findings.unreadable.capabilities_unreadable':
    'What this account may do could not be determined.',
  'findings.unreadable.privilege_unconfirmed':
    'Whether this account holds SeDiskOperatorPrivilege could not be confirmed — nested group membership is not resolvable from here.',
  'findings.unreadable.registry_state_unknown':
    'The state of the registry configuration could not be determined.',
  'findings.unreadable.server_facts_unreadable': 'The extended server details were refused.',
  'findings.unreadable.shares_unreadable': 'The share list could not be read.',
  'findings.unreadable.registry_unreadable': 'The registry configuration could not be read.',
  'findings.unreadable.configuration_not_in_registry':
    'This share is in the text smb.conf; its options are not readable from here.',
  'findings.unreadable.sessions_unreadable': 'The session list could not be read.',
  'findings.registry_config_absent':
    'The server does not read its registry configuration',
  'findings.registry_config_absent.why':
    'Without `include = registry` in the [global] section of smb.conf, Samba ignores everything under HKLM\\\\Software\\\\Samba\\\\smbconf — which is the only place this console can write. Shares can then be read here and not created or changed.',
  'findings.registry_shares_not_served':
    'The registry holds shares the server does not publish',
  'findings.registry_shares_not_served.why':
    'The configuration is there and is not being read. Usually `registry shares = yes` is missing from the [global] section; sometimes smbd has simply not re-read the registry yet, and `smbcontrol all reload-config` decides which of the two it is.',
  'findings.disk_operator_unassigned':
    'Nobody on this server holds SeDiskOperatorPrivilege',
  'findings.disk_operator_unassigned.why':
    'The right governs who may change shares and share permissions over the network. The holder list came back empty — not “we could not look” but “nobody holds it”. Until somebody does, no sign-in here can change a share.',
  'findings.disk_operator_broadly_granted':
    'SeDiskOperatorPrivilege is granted very broadly',
  'findings.disk_operator_broadly_granted.why':
    'One of the holders is a group covering practically everyone who can sign in, so anyone able to authenticate may create shares, change them and set their permissions. The list this rests on is in the evidence: anybody who thinks it too strict can disagree with it.',
  'findings.transport_peer_unverified':
    'The server’s identity is not verified',
  'findings.transport_peer_unverified.why':
    'Kerberos proves who is being talked to: a ticket for cifs/<host> is decryptable only by that host. NTLM proves the client to the server and nothing the other way. On a standalone server it is the only thing on offer, which makes this a property of the deployment rather than a mistake.',
  'findings.transport_this_session':
    'This connection',
  'findings.transport_this_session.why':
    'How *this* session is protected — not what the server demands of anybody else. Signing is required by SAMFSCON at the client end and encryption is a container setting. What the server itself requires is not stated here.',
  'findings.share_guest_ok':
    'This share allows guest access',
  'findings.share_guest_ok.why':
    '`guest ok = yes` permits access without signing in, mapped to the guest account. Whether writing is allowed with it is not stated in this share — it can be set globally, and this console reads no file.',
  'findings.share_guest_writable':
    'Guests may write to this share',
  'findings.share_guest_writable.why':
    '`guest ok = yes` together with `read only = no`, both in this share. Anyone who can reach the network can create, change and delete files without signing in.',
  'findings.share_wide_links':
    'This share follows symlinks out of itself',
  'findings.share_wide_links.why':
    '`wide links = yes` permits symlinks leading outside the share directory, so a client can reach files that were never shared. Samba silently disables it while `unix extensions = yes` is in force, and that option is global and unreadable from here. Only the two together decide the effect.',
  'findings.share_create_mask_world_writable':
    'New files are created writable by everybody',
  'findings.share_create_mask_world_writable.why':
    'The mask leaves the write bit set for “others”. Every local user on the server may then write to them, whatever the share and file ACLs say.',
  'findings.share_force_user':
    'Every access runs as one fixed account',
  'findings.share_force_user.why':
    '`force user` rewrites every access to that account. File permissions no longer distinguish who did what — in the filesystem every change looks the same.',
  'findings.share_force_user_root':
    'Every access runs as root',
  'findings.share_force_user_root.why':
    '`force user = root` gives anyone who may open the share the system account’s rights over everything beneath it. File ACLs stop applying, and the filesystem no longer records who did what.',
  'findings.share_hosts_allow_unparsable':
    'hosts allow or hosts deny carries an entry Samba cannot read',
  'findings.share_hosts_allow_unparsable.why':
    'A typo in this line does not announce itself: Samba discards the entry silently, and the restriction it was meant to express simply does not exist. Which forms were recognised is in the evidence.',
  'findings.share_hosts_deny_without_allow':
    'hosts deny blocks everything and no hosts allow sits beside it',
  'findings.share_hosts_deny_without_allow.why':
    'There is no exception in this share. If one is set globally then all is well — this console reads no file, which is why this is a note rather than a finding.',
  'findings.share_hidden_name_browseable':
    'A name ending in $ suggests hidden, and this share is not',
  'findings.share_hidden_name_browseable.why':
    'Names ending in $ are conventionally not listed. `browseable = yes` overrides that, so the share appears in network browsing — which is probably not what was meant. Hiding was never access control anyway.',
  'findings.share_vfs_option_without_module':
    'Options are set whose VFS module is not loaded',
  'findings.share_vfs_option_without_module.why':
    'These settings never run: the module that reads them is not in this share’s `vfs objects`. A recycle bin configured this way looks set up and catches nothing.',
  'findings.share_path_nested':
    'This share sits inside another',
  'findings.share_path_nested.why':
    'Two shares on nested paths carry separate permissions over the same files. Somebody entering through the outer one is not subject to the inner one’s rules, which is the commonest way a restriction gets bypassed by accident.',
  'findings.share_path_duplicate':
    'Several shares point at one directory',
  'findings.share_path_duplicate.why':
    'Each brings its own share permissions. The most generous decides what is possible, and none of the settings looks wrong on its own.',
  'findings.share_path_sensitive':
    'This share publishes a system directory',
  'findings.share_path_sensitive.why':
    'The path is inside an area that belongs to the operating system. Read-only it hands out configuration and credentials; writable it is a route to owning the server. The list this rests on is in the evidence.',
  'findings.share_configured_not_served':
    'This share is configured and switched off',
  'findings.share_configured_not_served.why':
    'The registry carries `available = no`. The configuration is complete and the server does not publish it — which can be deliberate, and is more often a remnant of something somebody turned off once.',
  'findings.guest_session_present':
    'A guest session is connected right now',
  'findings.guest_session_present.why':
    'Not an inference from a file but an observation: guest access works on this server, whatever is configured anywhere.',
  'accounts.users': 'Users',
  'accounts.groups': 'Groups',
  'accounts.new': 'New account',
  'accounts.create': 'Create',
  'accounts.name': 'Name',
  'accounts.fullName': 'Full name',
  'accounts.description': 'Description',
  'accounts.password': 'Password',
  'accounts.repeat': 'Repeat the password',
  'accounts.mismatch': 'The two entries do not match.',
  'accounts.state': 'State',
  'accounts.isEnabled': 'enabled',
  'accounts.isDisabled': 'disabled',
  'accounts.isLocked': 'locked out',
  'accounts.neverExpires': 'Password never expires',
  'accounts.createDisabled': 'Create it disabled',
  'accounts.enable': 'Enable',
  'accounts.disable': 'Disable',
  'accounts.delete': 'Delete',
  'accounts.setPassword': 'Set the password',
  'accounts.setPasswordFor': 'Set the password for {name}',
  'accounts.protected': 'This account belongs to the server itself.',
  'accounts.memberCount': '{count} members',
  'accounts.members': 'Members',
  'accounts.noMembers': 'This group has no members.',
  'accounts.membersReadOnly': 'Membership is shown here and not yet edited.',
  'accounts.created': 'The account {name} was created.',
  'accounts.deleted': 'The account {name} was deleted.',
  'accounts.enabled': 'The account {name} is now enabled.',
  'accounts.disabled': 'The account {name} is now disabled.',
  'accounts.passwordSet': 'The password for {name} was set.',
  'accounts.deleteWarning':
    'The account {name} will be removed from the server. Its files stay where they are, but permissions naming its SID will point at nothing afterwards.',
  'error.not_standalone': 'This server is a domain member; its accounts come from the domain.',
  'error.not_standalone.hint':
    'Domain users and groups are managed on a domain controller \u2014 with SAMADCON, or with the Windows tools.',
  'error.protected_account': 'This account belongs to the server itself.',
  'error.protected_account.hint': 'Disable it instead if it should not be usable.',
  'error.password_too_long': 'The password is too long for this protocol.',
  'error.no_session_key':
    'The connection exposes no session key, so a password cannot be encrypted.',
  'error.password_encryption_failed': 'The password could not be encrypted for transport.',
  'error.samr_password_unsupported': 'This Samba build does not support setting the password.',

  'config.group.server': 'Server',
  'config.group.protocol': 'Protocol',
  'config.group.access': 'Access',
  'config.group.files': 'Files',
  'config.group.printing': 'Printing',
  'config.group.winbind': 'Winbind',
  'config.group.advanced': 'Advanced',

  'config.registryOnly':
    'This page shows and changes only what is in the registry configuration. SAMFSCON does not read the text smb.conf: an empty field means ’not set here’, not ’not set’.',
  'config.notApplied':
    'Saved changes take effect only once Samba re-reads its configuration. SAMFSCON can neither trigger that nor restart anything.',
  'config.notApplied.faster': 'On the server the quickest route is: smbcontrol all reload-config',
  'config.notApplied.restart':
    'Options marked ’restart required’ need the named daemon restarted even after that.',
  'config.filesTabNote':
    'These are the defaults for every share. A share that sets the same option itself wins.',

  'config.sectionAbsent': 'This server has no global section in its registry configuration.',
  'config.sectionUnknown':
    'Whether this server keeps a global section in its registry could not be established. That is not the same as it having none.',
  'config.createSection': 'Create the section',
  'config.createSection.explain':
    'Creating it changes nothing unless the server’s smb.conf has ’include = registry’, and has it before the lines that set the same options. SAMFSCON cannot read that file, so it cannot check.',
  'config.createSection.confirm': 'Create it anyway',

  'config.inForce.confirmed':
    'The server reports what is stored here: the registry configuration is being read.',
  'config.inForce.contradicted':
    'The server reports something other than what is stored here. Most likely ’include = registry’ is missing from the text smb.conf, or a line there overrides it.',
  'config.inForce.unknown.not_stored':
    'Whether the registry configuration is read at all is open: nothing is stored that could be compared against it.',
  'config.inForce.unknown.variable_expansion':
    'Whether the registry configuration is read is open: the stored value contains a variable and the server reports it expanded.',
  'config.inForce.unknown.indistinguishable_from_default':
    'Whether the registry configuration is read is open: the stored and the reported value are both Samba’s default, and agreement then proves nothing.',
  'config.inForce.unknown.live_unreadable':
    'Whether the registry configuration is read is open: the server refused the query.',

  'config.verify.applied_confirmed': 'Saved, and the server already reports the new value.',
  'config.verify.not_yet_visible':
    'Saved. The server still reports ’{live}’ rather than ’{stored}’: either it has not re-read its configuration, or the text smb.conf sets the same option. This console cannot tell the two apart.',
  'config.verify.not_comparable': 'Saved. Whether it took effect could not be checked from here.',

  'config.notSetHere': 'not set here',
  'config.bool.yes': 'yes',
  'config.bool.no': 'no',
  'config.notSetHere.why':
    'Not in the registry configuration. Whether the text smb.conf sets it is something this console cannot see.',
  'config.defaultIs': 'With nothing set, Samba’s default applies: {value}',
  'config.defaultNote.compiled_in':
    'With nothing set the compiled-in default applies, and no RPC interface reports what that is.',
  'config.defaultNote.from_hostname':
    'With nothing set Samba derives the value from the host name.',
  'config.unlistedValue': 'stored, and not among the choices',

  'config.effect.connection': 'applies to new connections',
  'config.effect.reload': 'applies once the configuration is re-read',
  'config.effect.restart': 'restart required',
  'config.effect.daemons': 'affects {names}',
  'config.readOnly': 'read-only',
  'config.risky': 'risky',

  'config.readOnly.machine_account_identity':
    'This name is the machine account’s identity. It is set when the server joins; changing it here would break the trust.',
  'config.readOnly.join_has_no_rpc':
    'The security mode is set when the server joins a domain. There is no RPC interface for it; that happens on the server itself, with net ads join.',
  'config.readOnly.member_workgroup_is_the_join':
    'On a domain member this is the domain the server joined. Changing it here would break the join.',
  'config.readOnly.bound_at_startup':
    'Samba evaluates this at startup. A value written here would show something other than what applies until a restart this console cannot trigger.',
  'config.readOnly.hides_configuration':
    'This diverts the configuration into files this console cannot read. It would go on showing what is here while the server did something else.',
  'config.readOnly.invalidates_stored_names':
    'Every name already stored is written with the current separator. Changing it makes them invalid.',
  'config.readOnly.no_value_improves_on_the_default':
    'Samba’s default has beaten hand-tuning for years. The option is listed because old servers have it set, not because it should be.',
  'config.readOnly.idmap_remaps_existing_files':
    'The idmap ranges decide which Unix id belongs to which domain account. Moving them reassigns existing files to different accounts.',

  'config.risk.lockout_hosts':
    'This list decides who reaches the server. The server sees this console at {address}; leave that address out and the next connection from here is gone.',
  'config.risk.lockout_dialect_floor':
    'A server demanding a higher dialect than a client speaks locks that client out. SAMFSCON speaks {floor} at the lowest.',
  'config.risk.lockout_dialect_ceiling':
    'A ceiling below {floor} puts the server out of this console’s reach, and this setting with it.',
  'config.risk.lockout_signing':
    'A server demanding signing a client cannot do locks that client out. This console included.',
  'config.risk.availability_encryption':
    'Making encryption mandatory locks out every client that cannot do it, devices such as scanners and printers included.',
  'config.risk.wide_links_disabled_by_unix_extensions':
    'With the Unix extensions on, Samba turns ’wide links’ off for every share. A share then stops showing what it showed before, without anything about it having changed.',
  'config.risk.exposure_wide_links':
    'Symbolic links may then lead out of the share. Whoever reaches the share reaches everything a link inside it points at.',
  'config.risk.quiet_guest_substitution':
    'Failed logins then quietly become the guest account. Access shows up under an account other than the one that signed in.',
  'config.risk.printing_management_off':
    'Windows clients can then no longer manage printer drivers and queues.',
  'config.risk.identity_meaning_changes':
    'Names without a domain part then mean the server’s own domain. Permissions already granted keep their spelling, so the same string comes to mean something else.',
  'config.risk.disconnects_this_console':
    'The server drops idle connections after this long. That includes the connection this console works over.',
  'config.risk.exposure_usershares':
    'This lets accounts without administrative rights create shares. This console shows them and cannot manage them.',
  'config.risk.registry_shares_toggle':
    'Turned off, the server stops serving the shares kept in the registry. They stay stored and vanish from the network, and this console would go on managing something nobody can see.',
  'config.risk.standalone_domain_rename':
    'This moves the workgroup or domain name. On a standalone server it is a rename, and clients no longer find it under the old one.',

  'config.live.heading': 'What the server currently reports',
  'config.live.stored': 'stored here',
  'config.live.inForce': 'in force',
  'config.live.source.srvsvc': 'what the server reports',
  'config.live.source.session_workgroup': 'what this session was opened with',
  'config.live.source.session_mode': 'how this session authenticated',
  'config.live.source.observed': 'observed, not asked',
  'config.live.unreadable': 'The server refused this query.',

  'config.idmap': 'idmap ranges',
  'config.idmap.empty':
    'Nothing here is stored in the registry. The usual place for idmap config is the text smb.conf, so this being empty means ’nothing in the registry’, not ’no idmap configured’.',
  'config.notApplicable': 'Not applicable to this kind of server',
  'config.notApplicable.why':
    'Stored and shown, and without effect on a server of this kind. Leaving it out would make the display of the rest a half-truth.',
  'config.otherOptions': 'Other stored options',
  'config.otherOptions.why':
    'SAMFSCON does not know these options. They are in this server’s registry and nothing here changes them.',

  'config.printing.noPrinterShares': 'This server publishes no printer shares.',
  'config.printing.unknown':
    'Whether this server publishes printer shares could not be established: the share list was not readable.',

  'config.revert': 'Discard',
  'config.revert.why':
    'Puts the form back to the values last read. That works as long as this page stays open and the connection lasts; what is saved, this console cannot undo.',
  'config.confirmTitle': 'Confirm this change',
  'config.confirmIntro': 'These changes can alter access to this server:',
  'config.confirmProceed': 'Save anyway',
  'config.unwritable': 'This account may not change this server’s settings.',

  'caps.note.registry_sections_unreadable':
    'The list of registry sections could not be read.',
  'caps.note.global_section_unreadable':
    'The global section could not be read.',
  'caps.note.live_value_unreadable':
    'The server refused the query for {option}.',
  'caps.note.own_address_ambiguous':
    'This console has several connections to the server, so which address hosts allow would match is not decided.',
  'caps.note.own_address_unknown':
    'The address the server sees this console at could not be established.',
  'caps.note.printer_shares_unknown':
    'The share list was not readable, so whether there are printer shares is open.',
  'caps.note.capabilities_unreadable':
    'What this account may do on this server could not be established.',

  'error.global_section_absent':
    'This server keeps no global section in its registry configuration.',
  'error.global_section_absent.hint':
    'It can be created. That changes nothing unless the server’s smb.conf has ’include = registry’ before the lines setting the same options.',
  'error.global_section_unknown':
    'Whether this server keeps a global section in its registry is unknown.',
  'error.global_section_unknown.hint':
    'The section list could not be read, so nothing was written. That is not the same as there being none.',
  'error.confirmation_required':
    'This change touches an option that has to be confirmed.',
  'error.dialect_below_console_floor':
    'This console could not reconnect to a server with that maximum dialect.',
  'error.dialect_below_console_floor.hint':
    'SAMFSCON does not negotiate down. Putting it back would then need a shell on the server itself.',
  'error.dialect_window_empty':
    'The minimum and maximum dialect leave no dialect at all between them.',
  'error.hosts_allow_excludes_console':
    'This list does not include the address the server sees this console at.',
  'error.hosts_allow_excludes_console.hint':
    'Checked rather than assumed: none of the entries matches. Add the address, which is the SAMFSCON container’s and not the workstation’s.',
  'error.hosts_allow_undecidable':
    'Whether this list still admits this console could not be decided.',
  'error.hosts_allow_undecidable.hint':
    'Not the same as excluded: this was not checked, not failed. Confirming saves the list all the same.',
  'error.hosts_deny_includes_console':
    'This list names the address the server sees this console at, and no allow list brings it back.',
  'error.hosts_deny_undecidable':
    'Whether this list shuts this console out could not be decided.',
  'error.option_not_applicable':
    'This option has no effect on a server of this kind.',
  'error.unknown_option':
    'SAMFSCON does not know this option.',


  'config.undecided.title': 'Could not be checked',
  'config.undecided.intro':
    'This check could not be carried out. It did not fail; it could not run, and that is a different thing.',
  'config.undecided.entries': 'Could not be resolved: {entries}',
  'config.undecided.accept': 'Save without this check',
  'error.own_address_unknown':
    'The address the server sees this console at could not be established.',
  'error.own_address_unknown.hint':
    'Without that address, nothing can be said about any host list admitting this console. That is not a statement about the list — no wording of it changes this. Confirming saves it unchecked.',

  'error.kerberos_needs_a_name': 'Kerberos needs the server’s name, and only its address is known.',
  'error.kerberos_needs_a_name.hint':
    'Enter the server’s name instead of its address, or let SAMFSCON learn it: the name comes from an unauthenticated policy query that this server refused. Whichever name is used, the container has to be able to resolve it — add it to extra_hosts if DNS does not.',
  'error.hint': 'Hint',
  'error.details': 'Technical detail',
  'error.network_error': 'The server could not be reached.',
  'error.network_error.hint': 'Is the container still running, and is the network fine?',
  'error.unexpected_response': 'Unexpected response from the server.',
  'error.internal_error': 'An unexpected error occurred.',
  'error.internal_error.hint': 'The details are in the container log.',
  'error.validation_failed': 'The input is incomplete or invalid.',
  'error.csrf_failed': 'The request carried no valid security token.',
  'error.csrf_failed.hint': 'Reload the page and try again.',

  'error.not_authenticated': 'Not signed in.',
  'error.session_expired': 'The session has expired.',
  'error.session_expired.hint': 'Please sign in again.',
  'error.secret_cleared': 'This session’s credentials have been cleared.',
  'error.secret_cleared.hint': 'Please sign in again.',
  'error.authentication_failed': 'Authentication failed.',
  'error.invalid_credentials': 'Wrong user name or password.',
  'error.user_not_found': 'No such account on this server.',
  'error.account_not_found': 'No such account on this server.',
  'error.kerberos_principal_unknown': 'No such account in this realm.',
  'error.kerberos_principal_unknown.hint':
    'Sign in as user@REALM and check the spelling of the realm.',
  'error.directory_create_denied': 'The server refused to create this folder.',
  'error.directory_create_denied.hint':
    'Creating a folder is an ordinary file access: the account needs write permission on the folder it is created in — check that folder’s permissions. SeDiskOperatorPrivilege does not help here; that privilege governs managing shares.',
  'error.account_disabled': 'The account is disabled.',
  'error.account_expired': 'The account has expired.',
  'error.account_locked_out': 'The account is locked out.',
  'error.password_expired': 'The password has expired.',
  'error.password_must_change': 'The password must be changed first.',
  'error.login_throttled': 'Too many failed sign-in attempts.',
  'error.login_throttled.hint':
    'SAMFSCON pauses further attempts so the account is not locked out.',
  'error.clock_skew': 'The clocks of SAMFSCON and the domain controller differ too much.',
  'error.clock_skew.hint':
    'Kerberos tolerates about five minutes — synchronise the container’s clock via NTP.',
  'error.missing_username': 'The user name is missing.',
  'error.invalid_username': 'The user name contains invalid characters.',
  'error.missing_password': 'The password is missing.',
  'error.no_ticket': 'No Kerberos ticket was issued.',
  'error.no_ticket.hint':
    'Check the realm spelling, the clock difference to the KDC, and that the account exists.',
  'error.kdc_unreachable': 'No key distribution centre could be reached.',
  'error.kdc_unreachable.hint': 'Check SAMFSCON_KDC_HOSTS, the SRV records and port 88.',
  'error.spn_not_found': 'The file server has no service principal in this realm.',
  'error.spn_not_found.hint':
    'Kerberos issues tickets for cifs/<hostname>. Use the server’s own name rather than an address, and check that it is still joined.',
  'error.kerberos_unavailable': 'No Kerberos ticket could be obtained.',
  'error.ccache_unsupported': 'The Kerberos ticket could not be attached to the connection.',

  'error.missing_server': 'No server was given.',
  'error.invalid_server': 'The server address is unusable.',
  'error.no_target': 'No server was given and this installation has no default.',
  'error.no_target.hint': 'Enter the address of a file server.',
  'error.custom_servers_disabled': 'This installation only allows the configured servers.',
  'error.unknown_server_profile': 'The selected server profile does not exist.',
  'error.incomplete_server_profile': 'The server profile names no host.',
  'error.invalid_mode': 'Unknown kind of server.',
  'error.mode_undecided': 'SAMFSCON could not tell whether this server is a domain member.',
  'error.mode_undecided.hint':
    'The server answered no unauthenticated query — usually ‘restrict anonymous’. Choose ‘domain member’ or ‘standalone’ in the sign-in form.',
  'error.missing_realm': 'No Kerberos realm is known for this server.',
  'error.missing_realm.hint': 'Enter the realm, or sign in as user@REALM.',
  'error.no_realm': 'The file server named no Kerberos realm.',
  'error.standalone_disabled': 'Standalone servers are not enabled on this installation.',
  'error.standalone_disabled.hint':
    'Such a session would have to hold the password in memory; SAMFSCON_ALLOW_STANDALONE=0 declines that trade.',
  'error.no_credentials': 'This session carries no credentials for the server.',

  'error.server_unreachable': 'The file server cannot be reached.',
  'error.server_unreachable.hint':
    'Check that port 445 is open and that the server speaks SMB3 — SAMFSCON does not negotiate SMB1.',
  'error.server_unavailable': 'The file server is unavailable.',
  'error.server_name_unknown': 'The file server cannot be reached.',
  'error.server_name_unknown.hint':
    'Only the address was available, and Kerberos issues tickets for cifs/<hostname> — no such principal exists for a bare address. Check that the container can resolve the server’s name and reach it on port 445.',
  'error.server_timeout': 'The file server did not answer in time.',
  'error.timeout': 'The operation did not finish in time.',
  'error.server_error': 'The file server reported an error.',
  'error.samba_missing': 'The Samba bindings in the container are incomplete.',
  'error.smb_binding_unsupported': 'The SMB connection could not be opened.',
  'error.smb_dialect_mismatch': 'The call is not available over the negotiated SMB dialect.',
  'error.lsa_unsupported': 'This Samba build’s LSA bindings have an unexpected signature.',
  'error.winreg_unsupported': 'This Samba build does not support the registry call.',
  'error.unsupported_info_level': 'The server does not support this information level.',
  'error.unsupported_info_level.hint':
    'The Samba version on the server is probably older than SAMFSCON expects.',
  'error.not_supported': 'The server does not support this operation.',

  'error.insufficient_access': 'The server refused this operation for your account.',
  'error.insufficient_access.hint':
    'The server does not say which permission is missing, and which one it is depends on what was attempted: write access on the parent directory for a file or folder, SeDiskOperatorPrivilege for a share, write access to the registry for the configuration.',
  'error.missing_disk_operator': 'Your account may not manage this server’s shares.',
  'error.missing_disk_operator.hint':
    'The server checks SeDiskOperatorPrivilege for this. Grant it with: net rpc rights grant \'<group>\' SeDiskOperatorPrivilege -U <admin>',
  'error.not_configured': 'The server is not set up for this.',
  'error.registry_shares_disabled': 'This server does not serve registry shares.',
  'error.registry_shares_disabled.hint':
    'The share’s configuration is already in the registry — Samba is simply ignoring it. Add ‘registry shares = yes’ to the [global] section of the server’s smb.conf and reload Samba; it takes effect then, with nothing to enter again.',
  'caps.note.registry_shares_disabled':
    'This server’s registry holds shares it does not serve — ‘registry shares = yes’ is missing from the [global] section of its smb.conf. Without it Samba ignores everything this console writes.',
  'error.registry_not_writable': 'Your account may not change this server’s configuration.',
  'error.registry_not_writable.hint':
    'Shares are written into the registry configuration under HKLM\Software\Samba\smbconf, and this account may read it but not change it.',
  'error.registry_config_missing':
    'This server is not set up for managing shares over the network.',
  'error.registry_config_missing.hint':
    'Add ‘include = registry’ and ‘registry shares = yes’ to the [global] section of the server’s smb.conf and reload Samba. Reading works without it; only changes need it.',

  'error.not_found': 'Not found.',
  'error.share_not_found': 'The share does not exist on this server.',
  'error.share_exists': 'A share with this name already exists.',
  'error.share_path_missing': 'The directory the share should publish does not exist.',
  'error.share_path_missing.hint':
    'SAMFSCON manages the server over the network and cannot create a directory outside an existing share. Create it on the server first.',
  'error.share_path_redirected': 'The path is already redirected and cannot be shared.',
  'error.path_not_found': 'The path does not exist on the server.',
  'error.already_exists': 'That already exists.',
  'error.already_member': 'The account is already a member of this group.',
  'error.not_a_member': 'The account is not a member of this group.',
  'error.not_empty': 'The directory is not empty.',
  'error.file_in_use': 'The file is currently in use.',
  'error.file_in_use.hint': 'Someone has it open. The session view shows who.',
  'error.session_not_found': 'The session no longer exists.',
  'error.session_not_found.hint': 'It probably ended between the listing and this request.',
  'error.sid_not_resolved': 'The name could not be resolved to an account.',
  'error.sid_not_resolved.hint':
    'Spell it as it exists on the server, or as DOMAIN\\name for a domain account.',
  'error.invalid_sid': 'This is not a valid security identifier.',
  'error.share_add_rejected': 'The server rejected the request to create this share.',
  'error.share_add_rejected.hint':
    'The name passed SAMFSCON’s own check, so the server is objecting to the request rather than to the name — most likely it reached the server empty. This is a fault in SAMFSCON, not in what was typed. The container log has the detail.',
  'error.invalid_name': 'The name is not valid for this server.',
  'error.invalid_parameter': 'The server rejected a parameter of the request.',
  'error.invalid_request': 'The request is invalid.',
  'error.constraint_violation': 'The value violates a constraint of the server.',
  'error.password_policy_violation': 'The password does not satisfy the server’s policy.',
  'error.password_policy_violation.hint':
    'Check length, complexity, minimum age and password history.',
  'error.too_many_sessions': 'Too many concurrent sessions.',
  'error.session_closed': 'The session has been closed.',
  'error.unknown_pipe': 'Unknown RPC interface.',
}

export const catalogues: Record<Language, Record<MessageKey, string>> = { de, en }
