<p align="center">
  <img src="docs/brand/samfscon-banner-transparent.svg"
       alt="SAMFSCON — die Samba-Fileserver-Konsole" width="560">
</p>

<p align="center"><em><a href="README.md">English version</a></em></p>

Eine Verwaltungskonsole im Browser für Samba-**Fileserver** — eigenständige ebenso wie
Domänenmitglieder. Sie ersetzt die Windows-Computerverwaltung (Freigegebene Ordner, Sitzungen,
Offene Dateien, Lokale Benutzer und Gruppen) durch einen Docker-Container.

SAMFSCON ist das Gegenstück zu [SAMADCON](https://github.com/onlinecrash24/SAMADCON), das dasselbe
für einen Samba-AD-Domänencontroller tut. Gleiche Architektur, gleiches Sicherheitsmodell, gleicher
Containeraufbau — die andere Hälfte einer Samba-Landschaft.

Gesprochen werden ausschließlich Standardprotokolle: **SMB und DCE/RPC** — `srvsvc` für Freigaben,
Sitzungen und offene Dateien, `samr` für lokale Konten, `lsarpc` für Namen und SIDs, `winreg` für
die registry-basierte Konfiguration. Der Container muss nicht auf dem Fileserver laufen, auf ihm
wird nichts installiert, und keine Datei seines Dateisystems wird direkt angefasst.

> Status: in Entwicklung. Was gebaut ist, steht unter [Meilensteine](#meilensteine).

## Warum

Unter Linux gibt es nichts Vergleichbares. `net conf`, `smbstatus`, `smbcacls`, `pdbedit` und
`net rpc share` sind fünf Kommandozeilenwerkzeuge, die zusammen die Arbeit abdecken, und die
Windows-Konsole, die es an einer Stelle tut, braucht einen domänengebundenen Windows-Client.

## Sicherheitsmodell

Jeder Administrator meldet sich mit **dem eigenen Konto** an, und jede Operation läuft mit den
Rechten dieses Kontos:

- Das Werkzeug selbst braucht **kein** privilegiertes Dienstkonto.
- Die Rechteprüfung des Servers greift genau so, wie sie für diese Person an jedem anderen Client
  greifen würde. Ein Verzeichnis, das sie nicht lesen darf, kann auch diese Konsole nicht auflisten.
- Jeder Schreibvorgang landet im lokalen Audit-Log: wer, was, welche Freigabe, welche Option von
  welchem auf welchen Wert.

Wie die Anmeldedaten gehalten werden, hängt davon ab, was der Server ist — und der Unterschied wird
ausdrücklich benannt, weil er ein echter Handel ist:

| | Domänenmitglied | Eigenständig |
|---|---|---|
| Authentisierung | Kerberos | NTLMSSP |
| Das Passwort | einmal für das Ticket benutzt, danach außer Reichweite | **für die Dauer der Sitzung im Speicher des Containers** |
| Wo es liegt | ein Kerberos-Ticket in einem sitzungseigenen Cache auf tmpfs | nur im Prozessspeicher — nie auf Platte, nie im Protokoll, nie in einer API-Antwort |
| Identität des Servers | konstruktionsbedingt bewiesen (ein Ticket für `cifs/<host>` kann nur dieser Host entschlüsseln) | **nicht bewiesen** — NTLM weist den Client gegenüber dem Server aus, nicht umgekehrt |

Ein eigenständiger Server hat kein KDC, also gibt es kein Ticket, von dem aus gearbeitet werden
könnte, und NTLMSSP braucht das Passwort bei jedem Verbindungsaufbau erneut. Die Sitzung behält es
darum — in einer Wrapper-Klasse, die sich nicht ausgeben, nicht serialisieren und nicht picklen
lässt und die beim Sitzungsende überschrieben wird. Das ist enger als „wir speichern es nicht“, und
etwas anderes zu behaupten wäre genau die Art von Sicherheitsversprechen, die dieses Projekt
vermeiden will.

Das Anmeldeformular sagt es in dem Moment, in dem die Wahl getroffen wird, die Sitzungsleiste
wiederholt es für die ganze Dauer der Sitzung, und `SAMFSCON_ALLOW_STANDALONE=0` lehnt den Handel
für Installationen, die ihn nicht wollen, von vornherein ab.

Beide Verbindungen sind **signiert und mindestens SMB3**. SMB1 wird nicht verhandelt.
`SAMFSCON_SMB_ENCRYPT=1` verlangt zusätzlich SMB3-Verschlüsselung, wo der Server sie anbietet.

## Was der Server braucht

Lesen funktioniert ohne jede Vorbereitung gegen jeden Samba-Fileserver: Freigaben, ihre Optionen,
Sitzungen, offene Dateien, Berechtigungen und lokale Konten.

**Ändern** einer Freigabe braucht eine einzige Sache, im Abschnitt `[global]` der `smb.conf` des
Servers:

```
    include = registry
    registry shares = yes
```

Beide Zeilen, und sie tun Verschiedenes. `include = registry` lässt Samba den Speicher lesen;
**`registry shares = yes` lässt es ausliefern, was darin steht** — ohne diese Zeile lässt sich eine
Freigabe einwandfrei schreiben und erscheint trotzdem nie. Der Speicher ist auf jedem Samba
öffenbar und für jeden Administrator beschreibbar, keines von beidem belegt also, dass diese Zeile
gesetzt ist. SAMFSCON prüft es daran, ob Registry-Abschnitte existieren, die der Server nicht
ausliefert, und sagt es dann.

Eine Freigabe ist ein Schlüssel unter `HKLM\Software\Samba\smbconf` mit einem `path`-Wert;
SAMFSCON schreibt ihn über `winreg`, und Samba lädt Registry-Freigaben bei Bedarf. Genau das tut
auch `net rpc conf addshare`.

**Nicht** `SeDiskOperatorPrivilege`, und **kein** `add share command` — was der Erwähnung wert ist,
weil der naheliegende Weg beides braucht. Sambas eigenes `NetShareAdd` lehnt mit
`WERR_ACCESS_DENIED` ab, solange die smb.conf kein `add share command` setzt, und zwar unabhängig
davon, welche Rechte der Aufrufer hat; Registry-Freigaben sind davon nicht ausgenommen. Dieser
Befehl existiert, um ein Skript laufen zu lassen, das die Text-smb.conf umschreibt — und das darf
eine Konsole einem Server nicht abverlangen. Also nimmt SAMFSCON den Registry-Weg, und die
Voraussetzung entfällt.

Für **Freigabeberechtigungen** wird das Recht weiterhin gebraucht. Die liegen in `share_info.tdb`,
haben keine Registry-Entsprechung und gehen über `srvsvc` Level 1501, das es prüft:

```bash
net rpc rights grant 'DOMÄNE\Domänen-Admins' SeDiskOperatorPrivilege -U administrator
```

SAMFSCON prüft beides und meldet es getrennt, weil es verschiedene Dinge freischaltet. Zum Lesen
braucht es nichts davon: Freigabenliste, Optionen, Berechtigungen und Sitzungen sind ohne jede
Vorbereitung da, und verweigert wird nur, was eine Voraussetzung wirklich braucht.

`samfsconctl check --user administrator` beantwortet dieselbe Frage von der Kommandozeile.

## Was außer Reichweite bleibt

Benannt statt umgangen. Einen Server über das Netz zu verwalten heißt, dass es diese Dinge nicht
gibt, und daran ändert keine Cleverness etwas:

- **Samba neu starten oder neu laden.** Registry-Änderungen greifen beim nächsten Konfigurations-
  Reload des Servers — binnen einer Minute, und für neue Verbindungen sofort.
- **Ein Verzeichnis außerhalb einer bestehenden Freigabe anlegen.** Der Pfad einer neuen Freigabe
  muss vorher existieren. Innerhalb einer Freigabe funktioniert das Anlegen eines Unterordners.
- **Quotas und POSIX-ACLs.** Für beides gibt es keine RPC-Schnittstelle.
- **Eine in die Text-`smb.conf` geschriebene Freigabe.** Sie wird aufgelistet, ihre Optionen werden
  gezeigt, und sie ist als nicht änderbar markiert — sie zu ändern hieße, eine Datei zu schreiben,
  die diese Konsole nicht erreicht. `net conf import` holt sie in die Registry, wenn sie änderbar
  sein soll.
- **Domänenkonten auf einem Mitgliedsserver.** Sie liegen in der Domäne; dafür ist SAMADCON da.

## Schnellstart

### Das veröffentlichte Image benutzen

```bash
docker pull ghcr.io/onlinecrash24/samfscon:latest
```

Eine vollständige `docker-compose.yml` dafür — in ein leeres Verzeichnis legen:

```yaml
services:
  samfscon:
    image: ghcr.io/onlinecrash24/samfscon:latest
    container_name: samfscon
    restart: unless-stopped

    environment:
      # Der Name, unter dem die Konsole erreicht wird. Er wird CN und SAN des
      # selbstsignierten Zertifikats und Ziel der HTTP-nach-HTTPS-Umleitung —
      # der eine Wert, den praktisch jede Installation ändern muss.
      SAMFSCON_PUBLIC_HOST: "samfscon.example.lan"
      # Muss den Port nennen, den der Host veröffentlicht, nicht den, auf dem
      # nginx lauscht.
      SAMFSCON_PUBLIC_HTTPS_PORT: "8444"

      # Beides optional: das Anmeldeformular fragt sonst nach einer Adresse und
      # holt sich den Rest vom Server selbst.
      SAMFSCON_SERVER_HOST: ""
      SAMFSCON_SERVER_MODE: "auto"

      SAMFSCON_LOG_LEVEL: "INFO"

    ports:
      - "8444:8443"
      - "8081:8080"

    volumes:
      # Ein echtes Zertifikat kommt hier als server.crt und server.key hinein.
      # Ohne eines erzeugt der Container beim ersten Start ein selbstsigniertes.
      - ./tls:/etc/samfscon/tls
      - samfscon-cache:/var/cache/samfscon
      - samfscon-data:/var/lib/samfscon
      # Die Audit-Spur sollte den Container überleben.
      - samfscon-logs:/var/log/samfscon

    # Kerberos-Credential-Caches liegen in /dev/shm und dürfen nie auf eine
    # Platte gelangen.
    shm_size: 64m
    tmpfs:
      # uid/gid sind nötig: ein tmpfs-Mount gehört standardmäßig root, und
      # nginx und supervisor laufen als uid 1000.
      - /run/samfscon:mode=0700,uid=1000,gid=1000,size=8m

    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL

volumes:
  samfscon-cache:
  samfscon-data:
  samfscon-logs:
```

Der Container läuft als uid 1000, und ein Bind-Mount gehört root — das Zertifikatsverzeichnis muss
also für ihn beschreibbar sein:

```bash
mkdir -p tls && sudo chown -R 1000:1000 tls
docker compose up -d
```

Die Ports sind **8444/8081** statt SAMADCONs 8443/8080, damit beide auf einem Host laufen können.

### Aus dem Quelltext bauen

```bash
git clone https://github.com/onlinecrash24/SAMFSCON.git
cd SAMFSCON
docker compose up -d --build
```

Eine `.env` wird nicht gebraucht — die ganze Konfiguration steht in `docker-compose.yml`.

Die Oberfläche läuft dann auf `https://<host>:8444`.

## Anmelden

Nicht die Domäne wird beim Containerstart festgelegt, sondern der **Server** bei der Anmeldung. Das
Formular bietet die freie Eingabe einer Adresse oder eines Namens, vorkonfigurierte Server aus
`SAMFSCON_SERVERS_FILE` (siehe [servers.example.json](docker/servers/servers.example.json)),
zuletzt benutzte Server, die nur im Browser stehen, und den Standard des Containers, falls einer
konfiguriert ist.

Zu einer Adresse fragt SAMFSCON den Server, was er ist: eine unauthentifizierte Abfrage der
LSA-Policy liefert den eigenen Namen des Servers, seine Kontendomäne und — bei einem
Domänenmitglied — den Kerberos-Realm. Dieser Schritt ist nötig, weil Kerberos Tickets für
`cifs/fs1.example.lan@EXAMPLE.LAN` ausstellt und eine nackte Adresse weder einen Principal noch
einen Realm ergibt.

**Ein Server, der nichts beantwortet, wird nicht geraten.** `restrict anonymous = 2` ist verbreitet;
das Formular fragt dann, um welche Art von Server es sich handelt, statt die Wahl zu treffen — mit
Begründung, damit die Antwort informiert ist. Auf „eigenständig“ zu raten hieße bei einem
Domänenmitglied, ein Passwort zu halten, das Kerberos überflüssig gemacht hat; andersherum zu raten
hieße, auf ein Ticket zu warten, das kein KDC ausstellen wird.

## Meilensteine

| # | Umfang | Status |
|---|---|---|
| 1a | Grundgerüst, beide Anmeldearten, Servererkennung, der Container | gebaut |
| 1b | Freigaben: anlegen, ändern, löschen, mit dem smb.conf-Optionskatalog | gebaut |
| 1c | Berechtigungen: Freigabe- und Dateiebene, mit der Berechnung der tatsächlichen Rechte | gebaut |
| 1d | Sitzungen und offene Dateien, inklusive Erzwingen des Schließens | gebaut |
| 1e | Lokale Benutzer und Gruppen auf einem eigenständigen Server (SAMR) | gebaut |
| 2 | Globale Servereinstellungen, Diagnoseansicht, Freigabevorlagen | geplant |

**Die Verifikation gegen einen laufenden Server hat begonnen und ist bisher nur bis zur Anmeldung
gekommen.** Gegen ein Samba-AD-Mitglied hat sie zwei Fehler gefunden, beide behoben:

- Eine abgelehnte anonyme Policy-Abfrage wurde als „dieser Server hat keinen Realm“ gelesen und
  entschied damit *eigenständig* für ein Domänenmitglied — die Konsole versuchte NTLM mit einem
  Domänenpasswort und meldete einen Anmeldefehler, der das falsche Problem benannte. Eine
  abgelehnte Abfrage entscheidet jetzt nichts, und das Formular fragt mitsamt Begründung.
- Der eigene Name des Servers wurde nur aus der `srvsvc`-Abfrage abgeleitet, die ein
  Domänenmitglied üblicherweise verweigert. Ohne ihn wurde Kerberos nach einem Ticket für eine
  nackte IP-Adresse gefragt, und die Verbindung scheiterte mit `NT_STATUS_INVALID_PARAMETER`. Der
  Name wird jetzt aus den beiden Angaben der LSA-Policy zusammengesetzt, mit einem Reverse-DNS-
  Lookup als letzter Möglichkeit — und eine Anmeldung, die gar nicht funktionieren kann, wird vor
  der Passwortabfrage abgelehnt statt danach.

Alles hinter der Anmeldung — Freigaben, Berechtigungen, Sitzungen, Konten — ist gegen einen echten
Server weiterhin unbewiesen. Die Unit-Suite (136 Tests) deckt ab, was ohne einen auskommt, und die
CI führt sie aus. Die Formen der RPC-Aufrufe sind gegen die Protokollspezifikationen geschrieben,
jede mit einem Helfer umgeben, der mehrere Signaturen durchprobiert, weil die Python-Bindings von
Samba diese Signaturen zwischen Versionen geändert haben. Dieser Helfer ist eine Abmilderung, kein
Ersatz für den Test: siehe [Verifikation](#verifikation).

### Freigaben

srvsvc trägt Name, Pfad, Kommentar und Zähler einer Freigabe. Alles andere, was eine Samba-Freigabe
ausmacht — `read only`, `valid users`, `create mask`, `vfs objects`, Papierkorb, Schattenkopien,
Auditing —, ist eine `smb.conf`-Option, und für `smb.conf` gibt es keine RPC-Schnittstelle. Für die
Registry gibt es eine, und genau die bearbeitet SAMFSCON: denselben Speicher, den auch `net conf`
benutzt. Eine hier geschriebene Freigabe ist eine, die `net conf list` anzeigt.

Der Optionskatalog ist kuratiert, nicht vollständig: `smb.conf` hat mehrere hundert Optionen pro
Freigabe, und eine Konsole mit einem Freitextfeld für alle wäre ein schlechteres `vi`. Darin steht,
womit Fileserver tatsächlich konfiguriert werden, jede mit einem Typ, den die Oberfläche als
Bedienelement zeichnet, und einem Satz dazu, was sie tut. **Optionen außerhalb des Katalogs werden
trotzdem gezeigt**, schreibgeschützt, und beim Speichern nicht angetastet — ein von Hand
konfigurierter Server ist nicht falsch, und die Hälfte seiner Konfiguration zu verschweigen würde
diese Konsole zur Lügnerin machen.

### Berechtigungen

Ein Editor, drei Orte: der Deskriptor der Freigabe (`srvsvc` Level 502), der Deskriptor des
Freigabe-Wurzelverzeichnisses (über SMB) und jedes Verzeichnis und jede Datei darunter. Es ist
dieselbe Struktur, also bekommt sie denselben Editor.

Zwei Dinge verschweigt er nicht:

**Geerbte Einträge werden gezeigt und sind nicht änderbar.** Sie gehören dem übergeordneten
Verzeichnis. Ein Editor, der sie an Ort und Stelle ändern ließe, würde die Vererbung aufbrechen,
aus der sie stammen — die Zeile sagt stattdessen, woher sie kommt, und beim Schreiben eines
Deskriptors werden geerbte Einträge nie als eigene zurückgeschrieben.

**Das tatsächliche Recht ist die Schnittmenge beider Ebenen.** SMB prüft die Freigabeberechtigung
einmal beim Öffnen der Freigabe und die Dateiberechtigung bei jedem Zugriff darin — keine der
beiden Zahlen beantwortet „darf Alice das schreiben“ für sich. Eine Freigabe, die Jeder Vollzugriff
gewährt, sagt nichts; eine Datei-ACL, die auf einer nur lesbaren Freigabe Schreiben gewährt, gewährt
nichts. Der Editor rechnet die Schnittmenge für ein ausgewähltes Konto aus und benennt den Fall,
der die Diskussionen erzeugt: die Datei-ACL erlaubt es, die Freigabe nicht.

Die Rechnung ist ehrlich über ihre Grenze: gezählt werden die Einträge, die dieses Konto nennen,
nicht die vollständige Token-Auswertung samt aller Gruppen, in denen es ist. Eine Zahl, die
*manchmal* die ganze Antwort ist, wäre schlechter als eine, die sagt, welche von beiden sie ist.

### Sitzungen und offene Dateien

`smbstatus` liest das aus den tdb-Dateien des Servers; srvsvc veröffentlicht dieselben Tatsachen
über das Netz. Wer verbunden ist, von welchem Rechner, seit wann, wie lange untätig — und welche
Dateien offen sind, mit ihren Sperren und dem, was das Handle darf.

Das erzwungene Schließen einer Datei ist der einzige destruktive Vorgang in dieser Hälfte der
Konsole: der Client, der sie hält, wird nicht gefragt und verliert Ungespeichertes. Es fragt vorher
nach, nennt in der Rückfrage, wen es trifft, und landet mit beidem im Audit-Log.

## Verifikation

**Unit-Tests** — kein Samba, kein Server, kein Netz. Das führt die CI aus:

```bash
cd backend && python -m pytest tests/unit -q
```

**Integrationstests** — gegen einen Wegwerf-Fileserver, nie gegen Produktion. Sie legen Freigaben
an und löschen sie wieder:

```bash
SAMFSCON_TARGET=test docker compose up -d --build
TEST_FS_HOST=fs1.example.lan TEST_ADMIN_PASSWORD=… \
  docker compose exec samfscon python -m pytest tests/integration -q
```

**Von außen** — der Teil, der es tatsächlich entscheidet. Eine Freigabe, die diese Konsole anlegt,
muss außerhalb dieser Konsole existieren:

| Was | Womit geprüft |
|---|---|
| Freigabe angelegt | `net conf list` auf dem Server; der Explorer öffnet `\\server\freigabe` |
| Freigabeberechtigungen | `net rpc share getsecurity <freigabe>` bzw. der Reiter „Freigabeberechtigungen“ |
| Dateiberechtigungen | `smbcacls //server/freigabe /` und der Reiter „Sicherheit“ im Explorer |
| VFS-Optionen | `net conf showshare <freigabe>`; vom Client eine Datei löschen und im Papierkorb nachsehen |
| Sitzungen und offene Dateien | `smbstatus` neben der Konsolenansicht, während ein Client eine Datei offen hält |
| Nichts läuft mit fremden Rechten | mit einem absichtlich unterprivilegierten Konto anmelden: SAMFSCON muss genau das verweigern, was diesem Konto ohnehin verwehrt ist |

**Oberfläche**: `npm run build` und `npm run typecheck` müssen sauber sein, und die Konsole wird auf
Deutsch und Englisch durchgeklickt — auch mit gezogenem Netzwerkkabel, für die Fehlerpfade.

## Lizenz

AGPL-3.0-or-later, wie SAMADCON.
