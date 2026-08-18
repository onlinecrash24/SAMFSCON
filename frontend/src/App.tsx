import { useEffect, useState } from 'react'

import type { SessionInfo } from './api/types'
import { LoginView } from './components/LoginView'
import { LogoMark } from './components/Logo'
import { Badge, Icon, Spinner } from './components/primitives'
import { SNAPINS, DEFAULT_SNAPIN, type SnapinId } from './features/console/snapins'
import { SessionsView } from './features/sessions/SessionsView'
import { SharesView } from './features/shares/SharesView'
import { useI18n } from './i18n'
import { TreePane } from './components/TreePane'
import { useSession } from './state/session'

export function App() {
  const { session, loading } = useSession()
  const { t } = useI18n()

  if (loading) {
    return (
      <div className="boot">
        <Spinner label={t('status.loading')} />
      </div>
    )
  }

  return session ? <Console session={session} /> : <LoginView />
}

function Console({ session }: { session: SessionInfo }) {
  const { t, language, setLanguage } = useI18n()
  const { logout } = useSession()
  const [snapin, setSnapin] = useState<SnapinId>(DEFAULT_SNAPIN)
  const [notice, setNotice] = useState<string | null>(null)

  // Transient success messages should not linger.
  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(null), 4000)
    return () => window.clearTimeout(timer)
  }, [notice])

  return (
    <div className="console">
      <header className="topbar">
        <div className="topbar__brand">
          <LogoMark size={26} />
          <strong>{t('app.title')}</strong>
          <span>{session.server.name}</span>
        </div>

        <ConnectionBadges session={session} />

        <div className="topbar__actions">
          <button
            type="button"
            className="link"
            onClick={() => setLanguage(language === 'de' ? 'en' : 'de')}
          >
            {language === 'de' ? 'EN' : 'DE'}
          </button>
          <span className="topbar__user" title={session.principal}>
            {session.username}
          </span>
          <button type="button" className="button" onClick={() => void logout()}>
            {t('nav.logout')}
          </button>
        </div>
      </header>

      {notice && <div className="alert alert--success">{notice}</div>}

      <div className="console__panes">
        <div className="pane pane--tree">
          <TreePane server={session.server} active={snapin} onSelect={setSnapin} />
        </div>

        <div className="pane pane--list">
          {snapin === 'shares' ? (
            <SharesView onChanged={setNotice} />
          ) : snapin === 'sessions' ? (
            <SessionsView onChanged={setNotice} />
          ) : (
            <SnapinPlaceholder id={snapin} session={session} />
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * How this session is protected, in the one place it stays visible.
 *
 * Not decoration. The two modes differ in what they prove and in what they
 * cost, and neither difference should have to be remembered:
 *
 * - Kerberos proves the server's identity; NTLM proves only ours to it, so a
 *   standalone session is signed but its peer is unverified.
 * - A standalone session holds the password in the server process for as long
 *   as it lasts. That is stated at sign-in and repeated here, because a warning
 *   shown once at half past five is a warning nobody acts on.
 */
function ConnectionBadges({ session }: { session: SessionInfo }) {
  const { t } = useI18n()
  const { connection, holds_password: holdsPassword } = session

  return (
    <div className="topbar__state">
      <Badge tone={connection.identity_verified ? 'ok' : 'warn'}>
        {t(`session.auth.${connection.auth}`)}
      </Badge>
      <span
        className="muted small"
        title={
          connection.identity_verified ? undefined : t('session.identityUnverified.why')
        }
      >
        {connection.identity_verified
          ? t('session.identityVerified')
          : t('session.identityUnverified')}
        {connection.encrypted ? ` · ${t('session.encrypted')}` : ` · ${t('session.signed')}`}
      </span>
      {holdsPassword && (
        <Badge tone="warn">
          <span title={t('session.holdsPassword.why')}>{t('session.holdsPassword')}</span>
        </Badge>
      )}
    </div>
  )
}

/** Stands in for a snap-in that is planned but not built yet. */
function SnapinPlaceholder({ id, session }: { id: SnapinId; session: SessionInfo }) {
  const { t } = useI18n()
  const snapin = SNAPINS.find((entry) => entry.id === id)
  if (!snapin) return null

  const notApplicable = snapin.standaloneOnly === true && session.server.mode !== 'standalone'

  return (
    <div className="placeholder">
      <Icon type={snapin.icon} className="icon--large" />
      <h2>{t(snapin.label)}</h2>
      {notApplicable ? (
        <p className="muted">
          {t('snapin.accounts.domainMember', {
            domain: session.server.realm ?? session.server.workgroup ?? '',
          })}
        </p>
      ) : (
        <>
          {snapin.note && <p className="muted">{t(snapin.note)}</p>}
          {!snapin.available && <p className="muted small">{t('snapin.unavailable')}</p>}
        </>
      )}
    </div>
  )
}
