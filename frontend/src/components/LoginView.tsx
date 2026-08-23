/**
 * Sign-in.
 *
 * Two things make this form different from an ordinary login box, and both come
 * from the same place: a Samba file server can be a domain member or standalone,
 * and only the first has Kerberos.
 *
 * 1. The form **asks the server** which it is, before anyone types a password.
 *    That is what lets an IP address work at all — Kerberos issues tickets for
 *    cifs/<hostname> and there is no such principal for a bare address.
 * 2. When the server will not say, the form asks the administrator rather than
 *    guessing. Guessing standalone against a domain member would hold a
 *    password in memory that Kerberos made unnecessary; guessing the other way
 *    would wait for a ticket no KDC will issue.
 *
 * The standalone trade is stated on this screen, next to the choice that makes
 * it — not buried in a README nobody reads at half past five.
 */

import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { api } from '../api/endpoints'
import type { AppInfo, ServerListing, ServerMode, ServerProbe } from '../api/types'
import { useI18n } from '../i18n'
import { forgetServer, listRecentServers, type RecentServer } from '../state/recentServers'
import { useSession } from '../state/session'
import { LogoLockup } from './Logo'
import { SourceNote } from './SourceNote'
import { Badge, Banner, ErrorMessage, Field, Spinner } from './primitives'

/** Value of the server selector. Anything else is a profile id. */
const CUSTOM = '__custom__'
const DEFAULT = '__default__'

export function LoginView() {
  const { t, language, setLanguage } = useI18n()
  const { login } = useSession()

  const [info, setInfo] = useState<AppInfo | null>(null)
  const [servers, setServers] = useState<ServerListing | null>(null)
  const [recents, setRecents] = useState<RecentServer[]>([])

  const [choice, setChoice] = useState<string>(DEFAULT)
  const [host, setHost] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [realm, setRealm] = useState('')
  // Empty means "whatever the server said". Set only when the administrator
  // overrides the probe, or when the probe had nothing to say.
  const [mode, setMode] = useState<ServerMode | ''>('')

  const [probe, setProbe] = useState<ServerProbe | null>(null)
  const [probing, setProbing] = useState(false)
  const [probeError, setProbeError] = useState<unknown>(null)
  const [error, setError] = useState<unknown>(null)
  const [pending, setPending] = useState(false)

  useEffect(() => {
    api.info().then(setInfo).catch(() => setInfo(null))
    api
      .servers()
      .then((listing) => {
        setServers(listing)
        // Land on something usable: the configured default if there is one,
        // otherwise the first profile, otherwise free entry.
        if (listing.default) setChoice(DEFAULT)
        else if (listing.profiles.length > 0) setChoice(listing.profiles[0]!.id)
        else setChoice(CUSTOM)
      })
      .catch(() => setServers(null))
    setRecents(listRecentServers())
  }, [])

  const isCustom = choice === CUSTOM
  const profile = useMemo(
    () => servers?.profiles.find((item) => item.id === choice) ?? null,
    [servers, choice],
  )

  const allowStandalone = servers?.allow_standalone ?? info?.allow_standalone ?? true

  /** The server this sign-in will go to, whichever way it was chosen. */
  const currentHost = isCustom ? host.trim() : (profile?.host ?? servers?.default?.host ?? '')

  /**
   * Which mode this sign-in will actually use.
   *
   * The administrator's choice wins, then what the probe found, then what a
   * profile declared. Null means nobody has decided and the form has to ask.
   */
  const effectiveMode: ServerMode | null = useMemo(() => {
    if (mode) return mode
    if (probe?.decided) return probe.mode
    if (profile && profile.mode !== 'auto') return profile.mode
    if (choice === DEFAULT && servers?.default && servers.default.mode !== 'auto') {
      return servers.default.mode
    }
    return null
  }, [mode, probe, profile, choice, servers])

  async function runProbe(address: string) {
    const trimmed = address.trim()
    if (!trimmed) return
    setProbing(true)
    setProbeError(null)
    try {
      const result = await api.probe(trimmed, isCustom ? undefined : choice)
      setProbe(result)
      // A server that answered clears any override: what it said is better
      // than what somebody guessed a minute ago against a different address.
      if (result.decided) setMode('')
      if (result.realm) setRealm(result.realm)
    } catch (cause) {
      setProbe(null)
      setProbeError(cause)
    } finally {
      setProbing(false)
    }
  }

  // A configured or default server gets asked what it is, exactly as a typed
  // address does. Without this the form showed "detect automatically" with
  // nothing behind it and let the sign-in find out the hard way — which against
  // a domain member that answers no anonymous query meant an NTLM attempt with a
  // domain password, and a logon error that named the wrong problem.
  useEffect(() => {
    if (isCustom || !currentHost || probe || probing) return
    void runProbe(currentHost)
    // runProbe is stable enough for this: it closes over `choice`, which is in
    // the dependency list, and any other change resets `probe` to null first.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentHost, isCustom, choice])

  function selectServer(value: string) {
    setChoice(value)
    setProbe(null)
    setProbeError(null)
    setMode('')
    setRealm('')
  }

  function useRecent(entry: RecentServer) {
    setChoice(CUSTOM)
    setHost(entry.host)
    setProbe(null)
    setProbeError(null)
    // The remembered mode is why the entry is worth keeping: on a server that
    // answers nothing, this is the field the administrator would otherwise
    // have to fill in again every single time.
    setMode(entry.mode === 'auto' ? '' : entry.mode)
    setRealm(entry.realm ?? '')
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setPending(true)
    try {
      await login(username, password, {
        server: isCustom ? host.trim() : undefined,
        profileId: isCustom || choice === DEFAULT ? undefined : choice,
        mode: mode || undefined,
        realm: realm.trim() || undefined,
      })
    } catch (cause) {
      setError(cause)
    } finally {
      setPending(false)
      // Whatever happened, the field does not keep it.
      setPassword('')
    }
  }

  const canSubmit =
    username.trim().length > 0 &&
    password.length > 0 &&
    (!isCustom || host.trim().length > 0) &&
    !pending

  return (
    <div className="login">
      <form className="login__card" onSubmit={submit}>
        <LogoLockup className="login__logo" />

        {/* -- which server ------------------------------------------------ */}

        {servers && (servers.profiles.length > 0 || servers.default) && (
          <Field label={t('login.profile')}>
            <select value={choice} onChange={(event) => selectServer(event.target.value)}>
              {servers.default && (
                <option value={DEFAULT}>{servers.default.host}</option>
              )}
              {servers.profiles.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {entry.label}
                </option>
              ))}
              {servers.allow_custom_servers && (
                <option value={CUSTOM}>{t('login.profileNone')}</option>
              )}
            </select>
          </Field>
        )}

        {isCustom && (
          <Field label={t('login.server')} hint={t('login.serverHelp')}>
            <div className="login__row">
              <input
                type="text"
                value={host}
                autoComplete="off"
                spellCheck={false}
                placeholder={t('login.serverPlaceholder')}
                onChange={(event) => {
                  setHost(event.target.value)
                  setProbe(null)
                }}
                onBlur={(event) => void runProbe(event.target.value)}
              />
              <button
                type="button"
                className="button"
                disabled={probing || host.trim().length === 0}
                onClick={() => void runProbe(host)}
              >
                {probing ? t('login.probing') : t('login.probe')}
              </button>
            </div>
          </Field>
        )}

        {recents.length > 0 && isCustom && (
          <div className="login__recents">
            <span className="muted small">{t('login.recent')}</span>
            <ul>
              {recents.map((entry) => (
                <li key={entry.host}>
                  <button type="button" className="link" onClick={() => useRecent(entry)}>
                    {entry.label ? `${entry.label} (${entry.host})` : entry.host}
                  </button>
                  <button
                    type="button"
                    className="link link--quiet"
                    title={t('login.forget')}
                    onClick={() => {
                      forgetServer(entry.host)
                      setRecents(listRecentServers())
                    }}
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {probing && <Spinner label={t('login.probing')} />}
        <ErrorMessage error={probeError} onDismiss={() => setProbeError(null)} />

        {probe?.reachable && (
          <div className="login__probe">
            <span>{t('login.probeResult', { name: probe.server_fqdn ?? probe.netbios_name ?? probe.host })}</span>
            {probe.os_version && (
              <Badge tone="muted">{t('login.probeVersion', { version: probe.os_version })}</Badge>
            )}
          </div>
        )}

        {/* -- which kind of server ---------------------------------------- */}

        <Field label={t('login.mode')}>
          <select
            value={mode || (effectiveMode ?? '')}
            onChange={(event) => setMode(event.target.value as ServerMode | '')}
          >
            {!effectiveMode && <option value="">{t('login.mode.auto')}</option>}
            <option value="ad_member">{t('login.mode.ad_member')}</option>
            <option value="standalone" disabled={!allowStandalone}>
              {t('login.mode.standalone')}
              {allowStandalone ? '' : ` — ${t('login.mode.standaloneDisabled')}`}
            </option>
          </select>
        </Field>

        {probe && !probe.decided && (
          <Banner
            message={
              probe.notes.length > 0
                ? `${t('login.mode.undecided')} (${probe.notes.join('; ')})`
                : t('login.mode.undecided')
            }
            tone="warning"
          />
        )}

        {/* The trade, stated where the choice is made. */}
        {effectiveMode === 'standalone' && (
          <Banner message={t('login.standaloneWarning')} tone="warning" />
        )}

        {effectiveMode === 'ad_member' && !probe?.realm && (
          <Field label={t('login.realm')} hint={t('login.realmHelp')}>
            <input
              type="text"
              value={realm}
              autoComplete="off"
              spellCheck={false}
              placeholder="EXAMPLE.LAN"
              onChange={(event) => setRealm(event.target.value)}
            />
          </Field>
        )}

        {/* -- who -------------------------------------------------------- */}

        <Field label={t('login.username')}>
          <input
            type="text"
            value={username}
            autoComplete="username"
            spellCheck={false}
            placeholder={t('login.usernamePlaceholder')}
            onChange={(event) => setUsername(event.target.value)}
          />
        </Field>

        <Field label={t('login.password')}>
          <input
            type="password"
            value={password}
            autoComplete="current-password"
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>

        <ErrorMessage error={error} onDismiss={() => setError(null)} />

        <button type="submit" className="button button--primary" disabled={!canSubmit}>
          {pending ? t('login.signingIn') : t('login.submit')}
        </button>

        {/* The language, and what this build is. Both belong at the foot of
            the card rather than in a corner: the switch is a full word here,
            which "EN" in the top right was not — a two-letter code is only
            legible to somebody who already knows what it does.

            The minimum SMB dialect used to stand here. It said "SMB3" with
            nothing to say what that was about, which is a fact about the
            client's negotiation floor and not something anybody reads a
            sign-in card for. It is in the README, where it can carry its
            sentence.

            The licence and the source before anybody signs in, because AGPL
            §13 obliges a modified version offered over a network to offer its
            source to the people using it — and that includes the people
            standing at the door. */}
        <div className="login__footer">
          <button
            type="button"
            className="link"
            onClick={() => setLanguage(language === 'de' ? 'en' : 'de')}
          >
            {language === 'de' ? 'English' : 'Deutsch'}
          </button>
          <SourceNote version={info?.version} />
        </div>
      </form>
    </div>
  )
}

/** The host currently selected, exported for tests and for the session bar. */
export function describeChoice(
  choice: string,
  host: string,
  servers: ServerListing | null,
): string {
  if (choice === CUSTOM) return host
  if (choice === DEFAULT) return servers?.default?.host ?? ''
  return servers?.profiles.find((entry) => entry.id === choice)?.host ?? ''
}
