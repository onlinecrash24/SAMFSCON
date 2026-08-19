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
  'error.no_dacl': 'Der Sicherheitsdeskriptor hat keine Zugriffsliste.',
  'error.no_dacl.hint': 'Ein Deskriptor ohne sie gewährt niemandem etwas.',
  'error.invalid_sddl': 'Das ist kein gültiger Sicherheitsdeskriptor.',
  'error.unknown_preset': 'Unbekannte Berechtigungsstufe.',
  'error.sddl_unrenderable': 'Der Sicherheitsdeskriptor ließ sich nicht darstellen.',
  'error.srvsvc_unsupported': 'Diese Samba-Version unterstützt den Aufruf nicht.',
  'error.path_escapes_share': 'Ein Pfad darf seine Freigabe nicht verlassen.',
  'error.missing_path': 'Es wurde kein Name angegeben.',


  // -- local accounts ------------------------------------------------------
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
    'Zum Verwalten von Freigaben braucht das Konto SeDiskOperatorPrivilege auf dem Fileserver: net rpc rights grant \'<Gruppe>\' SeDiskOperatorPrivilege -U <Admin>',
  'error.missing_disk_operator': 'Ihr Konto darf die Freigaben dieses Servers nicht verwalten.',
  'error.missing_disk_operator.hint':
    'Der Server prüft dafür SeDiskOperatorPrivilege. Vergeben mit: net rpc rights grant \'<Gruppe>\' SeDiskOperatorPrivilege -U <Admin>',
  'error.not_configured': 'Der Server ist dafür nicht eingerichtet.',
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
  'error.no_dacl': 'The security descriptor has no access list.',
  'error.no_dacl.hint': 'A descriptor without one grants nothing to anybody.',
  'error.invalid_sddl': 'This is not a valid security descriptor.',
  'error.unknown_preset': 'Unknown permission level.',
  'error.sddl_unrenderable': 'The security descriptor could not be rendered.',
  'error.srvsvc_unsupported': 'This Samba build does not support the call.',
  'error.path_escapes_share': 'A path may not step outside its share.',
  'error.missing_path': 'No name was given.',


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
    'Managing shares needs SeDiskOperatorPrivilege on the file server: net rpc rights grant \'<group>\' SeDiskOperatorPrivilege -U <admin>',
  'error.missing_disk_operator': 'Your account may not manage this server’s shares.',
  'error.missing_disk_operator.hint':
    'The server checks SeDiskOperatorPrivilege for this. Grant it with: net rpc rights grant \'<group>\' SeDiskOperatorPrivilege -U <admin>',
  'error.not_configured': 'The server is not set up for this.',
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
