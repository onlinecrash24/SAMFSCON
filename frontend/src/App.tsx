import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from './api/endpoints'
import type {
  DirectoryEntry,
  LocalAccount,
  LocalGroup,
  OpenFile,
  ServerSession,
  SessionInfo,
  Share,
} from './api/types'
import { useContextMenu } from './components/ContextMenu'
import { LoginView } from './components/LoginView'
import { LogoMark } from './components/Logo'
import { Badge, Icon, Spinner } from './components/primitives'
import { SourceNote } from './components/SourceNote'
import { Splitter } from './components/Splitter'
import { TreePane, firstBranch } from './components/TreePane'
import { Taskbar, WindowLayer, useWindowCounts } from './components/WindowLayer'
import { AccountWindow } from './features/accounts/AccountWindow'
import { AccountsView } from './features/accounts/AccountsView'
import { ConsoleTabs } from './features/console/ConsoleTabs'
import {
  fileMenu,
  localGroupMenu,
  localUserMenu,
  openFileMenu,
  sessionMenu,
  shareMenu,
  type ActionId,
} from './features/console/menuActions'
import { SNAPINS, panesFor, snapinById, type SnapinId } from './features/console/snapins'
import { ServerSettingsView } from './features/config/ServerSettingsView'
import { DiagnosticsView } from './features/diagnostics/DiagnosticsView'
import { FilesView } from './features/files/FilesView'
import { FolderWindow } from './features/files/FolderWindow'
import { NewFolderDialog } from './features/files/NewFolderDialog'
import { childOf, decodeLocation, encodeLocation, type FileLocation } from './features/files/location'
import { SessionsView } from './features/sessions/SessionsView'
import { DeleteShareDialog } from './features/shares/DeleteShareDialog'
import { ShareDetail, type ShareGroup } from './features/shares/ShareDetail'
import { SharesView } from './features/shares/SharesView'
import { ShareWindow } from './features/shares/ShareWindow'
import { useI18n } from './i18n'
import { readConsoleLocation, writeConsoleLocation } from './state/consoleLocation'
import { clampWidth, readPaneWidths, writePaneWidths, type Boundary } from './state/paneWidths'
import { useSession } from './state/session'
import { WindowProvider, useWindows } from './state/windows'

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

  // The provider sits above the console rather than inside it, so signing out
  // unmounts every open window without anything having to remember to close
  // them.
  return session ? (
    <WindowProvider>
      <Console session={session} />
    </WindowProvider>
  ) : (
    <LoginView />
  )
}

/**
 * The console: a strip of consoles over three panes.
 *
 * What lives here rather than in a view, and why:
 *
 * - **Which console is open, and what is selected in it.** Both survive a
 *   refresh, which means one place has to own them.
 * - **The dialogs.** A confirmation opened from a list, from a property sheet
 *   in the detail pane, and from the same sheet in a window has to be one
 *   dialog, or the three drift apart.
 * - **runAction.** The menus say what a row *offers*; what an offer does is
 *   decided here, beside the dialogs and the mutations it needs.
 */
function Console({ session }: { session: SessionInfo }) {
  const { t, language, setLanguage } = useI18n()
  const { logout } = useSession()
  const queryClient = useQueryClient()
  const windows = useWindows()
  const windowCounts = useWindowCounts()
  const menu = useContextMenu()

  // Lazy initialisers: both read storage, and doing that on every render would
  // be reading a string a person can edit several times a second.
  const [location, setLocation] = useState(readConsoleLocation)
  const [widths, setWidths] = useState(readPaneWidths)
  const [notice, setNotice] = useState<string | null>(null)

  // What this build is, for the licence line. It cannot change while the page
  // is open, so it is asked for once and never again.
  const info = useQuery({ queryKey: ['info'], queryFn: () => api.info(), staleTime: Infinity })
  const [creating, setCreating] = useState(false)
  const [deletingShare, setDeletingShare] = useState<Share | null>(null)
  const [creatingFolder, setCreatingFolder] = useState<FileLocation | null>(null)

  const snapin = location.snapin
  const selected = location.selected
  // One field holds the selection for every console; for this one it packs a
  // share and a path. See features/files/location.ts.
  const here = snapin === 'files' ? decodeLocation(selected) : null

  useEffect(() => writeConsoleLocation(location), [location])

  // Transient success messages should not linger.
  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(null), 4000)
    return () => window.clearTimeout(timer)
  }, [notice])

  const go = useCallback((id: SnapinId) => {
    setLocation({ snapin: id, selected: firstBranch(id), search: '' })
  }, [])

  const select = useCallback((value: string | null) => {
    setLocation((current) => ({ ...current, selected: value }))
  }, [])

  const standalone = session.server.mode === 'standalone'
  const panes = panesFor(snapin)
  const shape = panes.tree && panes.detail ? 'full' : panes.detail ? 'detail' : panes.tree ? 'tree' : 'list'

  const shares = queryClient.getQueryData<{ entries: Share[]; capabilities?: { can_manage_shares?: boolean | null } }>(['shares'])
  const canWriteShares = shares?.capabilities?.can_manage_shares !== false
  const filesAvailable = snapinById('files')?.available === true

  const setWidth = useCallback(
    (boundary: Boundary, px: number | null) => {
      setWidths((current) => {
        const mine = { ...(current[snapin] ?? {}) }
        if (px === null) delete mine[boundary]
        else mine[boundary] = clampWidth(boundary, px)
        const next = { ...current, [snapin]: mine }
        writePaneWidths(next)
        return next
      })
    },
    [snapin],
  )

  const paneStyle = useMemo(() => {
    const mine = widths[snapin] ?? {}
    const style: Record<string, string> = {}
    if (mine.tree !== undefined) style['--tree-w'] = `${mine.tree}px`
    if (mine.detail !== undefined) style['--detail-w'] = `${mine.detail}px`
    return style as React.CSSProperties
  }, [widths, snapin])

  // -------------------------------------------------------------------------
  // Doing what a menu offered
  // -------------------------------------------------------------------------

  const openShare = useCallback(
    (name: string, group?: ShareGroup) => {
      windows.open({ snapin: 'shares', target: { kind: 'share', name }, title: name })
      if (group) setShareTab(group)
    },
    [windows],
  )
  // Which tab a freshly opened share window starts on. Held beside the window
  // rather than inside it, because the window is identified by the share and
  // opening the same one again from "Permissions…" has to move the tab of the
  // sheet that already exists.
  const [shareTab, setShareTab] = useState<ShareGroup | undefined>(undefined)

  const openFolder = useCallback(
    (share: string, path: string) => {
      windows.open({
        snapin: 'files',
        target: { kind: 'folder', share, path },
        // The last segment, because a title bar has room for a name and not
        // for a path. The path is in the sheet's own heading.
        title: path ? (path.split('/').pop() ?? path) : share,
      })
    },
    [windows],
  )

  const runAction = useCallback(
    (id: ActionId, subject: unknown) => {
      switch (id) {
        case 'refresh':
          void queryClient.invalidateQueries()
          return
        case 'share.new':
          setCreating(true)
          return
        case 'share.properties':
          openShare((subject as Share).name)
          return
        case 'share.permissions':
          openShare((subject as Share).name, 'permissions')
          return
        case 'share.open':
          go('files')
          return
        case 'share.delete':
          setDeletingShare(subject as Share)
          return
        case 'session.files':
          go('sessions')
          return
        case 'account.properties':
          windows.open({
            snapin: 'accounts',
            target: { kind: 'account', of: 'user', name: (subject as LocalAccount).name },
            title: (subject as LocalAccount).name,
          })
          return
        case 'folder.new':
          if (here) setCreatingFolder(here)
          return
        case 'folder.open':
          if (here) select(encodeLocation(here.share, (subject as DirectoryEntry).path))
          return
        case 'folder.properties':
          if (here) openFolder(here.share, (subject as DirectoryEntry).path)
          return
        case 'group.properties':
          windows.open({
            snapin: 'accounts',
            target: { kind: 'account', of: 'group', name: (subject as LocalGroup).name },
            title: (subject as LocalGroup).name,
          })
          return
        default:
          // The remaining account actions live in AccountsView, which owns the
          // dialogs and mutations for them. Reaching them from a menu is the
          // next thing to wire, and doing nothing is better than doing
          // something else.
          return
      }
    },
    [queryClient, openShare, openFolder, windows, go, select, here],
  )

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
          <SourceNote version={info.data?.version} />
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

      <ConsoleTabs active={snapin} onSelect={go} windowCounts={windowCounts} />

      {notice && <div className="alert alert--success">{notice}</div>}

      <div className={`console__panes console__panes--${shape}`} style={paneStyle}>
        {/* Always rendered, hidden by the shape rules. Unmounting it would
            throw away whatever the tree had unfolded. */}
        <div className="pane pane--tree">
          <TreePane
            server={session.server}
            snapin={snapin}
            selected={selected}
            onSelect={select}
            onFolderContext={(share, path, at) =>
              menu.open(at, fileMenu(null), (id) => {
                if (id === 'folder.properties') openFolder(share, path)
                else if (id === 'folder.new') setCreatingFolder({ share, path })
                else runAction(id as ActionId, null)
              })
            }
          />
        </div>
        <Splitter boundary="tree" onCommit={(px) => setWidth('tree', px)} />

        <div className="pane pane--list">
          {snapin === 'shares' ? (
            <SharesView
              selected={selected}
              onSelect={select}
              onOpen={(name) => openShare(name)}
              onContext={(share, at) =>
                menu.open(at, shareMenu(share, { canWrite: canWriteShares, filesAvailable }), (id) =>
                  runAction(id as ActionId, share),
                )
              }
              creating={creating}
              onCreate={() => setCreating((value) => !value)}
              onCreated={(name, served) => {
                setCreating(false)
                select(name)
                void queryClient.invalidateQueries({ queryKey: ['shares'] })
                // Written either way. Whether the server has re-read its
                // configuration is a different fact, and worth saying rather
                // than leaving somebody to wonder where their share went.
                setNotice(
                  served ? t('share.created', { name }) : t('share.createdNotServed', { name }),
                )
              }}
            />
          ) : snapin === 'sessions' ? (
            <SessionsView
              onChanged={setNotice}
              onContext={(kind, row, at) =>
                kind === 'session'
                  ? menu.open(at, sessionMenu(row as ServerSession), (id) =>
                      runAction(id as ActionId, row),
                    )
                  : menu.open(at, openFileMenu(row as OpenFile), (id) =>
                      runAction(id as ActionId, row),
                    )
              }
            />
          ) : snapin === 'files' ? (
            <FilesView
              location={here}
              onOpen={(path) => here && select(encodeLocation(here.share, path))}
              onProperties={(entry) => here && openFolder(here.share, entry.path)}
              onCreate={() => here && setCreatingFolder(here)}
              onContext={(entry, at) =>
                menu.open(at, fileMenu(entry), (id) => runAction(id as ActionId, entry))
              }
            />
          ) : snapin === 'diagnostics' ? (
            <DiagnosticsView />
          ) : snapin === 'config' ? (
            <ServerSettingsView onChanged={setNotice} />
          ) : snapin === 'accounts' && standalone ? (
            <AccountsView
              section={selected === 'groups' ? 'groups' : 'users'}
              onChanged={setNotice}
              onOpen={(of, name) =>
                windows.open({ snapin: 'accounts', target: { kind: 'account', of, name }, title: name })
              }
              onContext={(of, row, at) =>
                menu.open(
                  at,
                  of === 'user'
                    ? localUserMenu(row as LocalAccount, { canWrite: true })
                    : localGroupMenu(row as LocalGroup),
                  (id) => runAction(id as ActionId, row),
                )
              }
            />
          ) : (
            <SnapinPlaceholder id={snapin} session={session} />
          )}
        </div>

        <Splitter boundary="detail" onCommit={(px) => setWidth('detail', px)} />

        <div className="pane pane--detail">
          {snapin === 'shares' && selected ? (
            <ShareDetail
              name={selected}
              canWrite={canWriteShares}
              onChanged={setNotice}
              onDelete={() => {
                const share = shares?.entries.find((entry) => entry.name === selected)
                if (share) setDeletingShare(share)
              }}
            />
          ) : (
            <div className="placeholder">
              <Icon type="share" className="icon--large" />
              <p className="muted">{t('share.selectOne')}</p>
            </div>
          )}
        </div>
      </div>

      {deletingShare && (
        <DeleteShareDialog
          name={deletingShare.name}
          path={deletingShare.path}
          onClose={() => setDeletingShare(null)}
          onDone={(name) => {
            setDeletingShare(null)
            if (selected === name) select(null)
            // The window showing it would otherwise sit there reporting that
            // the share is gone, which is true and not useful.
            const open = windows.windows.find((w) => w.title === name && w.snapin === 'shares')
            if (open) windows.close(open.id)
            setNotice(t('share.deleted', { name }))
          }}
        />
      )}

      {creatingFolder && (
        <NewFolderDialog
          location={creatingFolder}
          onClose={() => setCreatingFolder(null)}
          onDone={(name) => {
            const parent = creatingFolder
            setCreatingFolder(null)
            setNotice(t('files.created', { name }))
            // Step into it: the reason for creating one here is to set its
            // permissions, and that is the next thing anybody does.
            select(encodeLocation(parent.share, childOf(parent, name)))
          }}
        />
      )}

      {menu.menu}

      {/* An ordinary flex child, not a fixed strip: the panes are flex:1, so a
          row at the end takes its height and they shrink. Nothing is covered
          and there is no z-index to reason about. */}
      <Taskbar activeSnapin={snapin} />

      <WindowLayer
        activeSnapin={snapin}
        render={(window) =>
          window.target.kind === 'share' ? (
            <ShareWindow
              name={window.target.name}
              canWrite={canWriteShares}
              initialGroup={shareTab}
              onChanged={setNotice}
              onDelete={() => {
                const share = shares?.entries.find((entry) => entry.name === window.title)
                if (share) setDeletingShare(share)
              }}
            />
          ) : window.target.kind === 'account' ? (
            <AccountWindow
              of={window.target.of}
              name={window.target.name}
              onAction={(id) => runAction(id as ActionId, { name: window.title })}
            />
          ) : (
            <FolderWindow
              share={window.target.share}
              path={window.target.path}
              canWrite={canWriteShares}
              onChanged={setNotice}
            />
          )
        }
      />
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
        title={connection.identity_verified ? undefined : t('session.identityUnverified.why')}
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
