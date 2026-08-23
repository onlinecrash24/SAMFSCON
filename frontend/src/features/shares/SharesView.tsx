/**
 * The shares list, and the detail pane for one share.
 *
 * Two things this view insists on, both learned from what goes wrong on a real
 * server:
 *
 * 1. **It says up front whether writing is possible at all.** The capability
 *    report comes back with the list, so a server without registry
 *    configuration shows the shares and explains why the "new share" button is
 *    not there — rather than offering a button that always fails.
 * 2. **It distinguishes a share it can edit from one it cannot.** A share
 *    written into the server's text smb.conf is readable here and not
 *    changeable, and the row says so. Pretending otherwise would produce a form
 *    that saves without effect.
 */

import { useQuery } from '@tanstack/react-query'

import { api } from '../../api/endpoints'
import type { CapabilityNote, Share, ShareListing } from '../../api/types'
import type { MessageKey } from '../../i18n/messages'
import { anchorOf } from '../../components/ContextMenu'
import { Badge, Banner, ErrorMessage, Icon, Spinner } from '../../components/primitives'
import { useI18n } from '../../i18n'
import { NewShareDialog } from './NewShareDialog'

export function SharesView({
  selected,
  onSelect,
  onOpen,
  onContext,
  creating,
  onCreate,
  onCreated,
}: {
  selected: string | null
  onSelect: (name: string) => void
  /** Double-click, or Properties: opens a window. */
  onOpen: (name: string) => void
  onContext: (share: Share, at: { x: number; y: number }) => void
  creating: boolean
  onCreate: () => void
  onCreated: (name: string, served: boolean) => void
}) {
  const { t } = useI18n()

  const shares = useQuery<ShareListing>({
    queryKey: ['shares'],
    queryFn: () => api.shares(),
  })

  const capabilities = shares.data?.capabilities
  /**
   * Whether to offer the write at all.
   *
   * `null` means the check could not resolve it — nested group membership is
   * not something it can follow — and the server evaluates the whole token
   * anyway. So an unconfirmed answer lets the attempt through and lets the
   * server give the complete one. Only a confirmed `false` takes the button
   * away, which happens when nobody on the server holds the privilege at all.
   */
  const canWrite = capabilities?.can_manage_shares !== false

  return (
    <div className="shares">
      <div className="pane__header">
        <span className="muted small">{t('snapin.shares.note')}</span>
        <div className="pane__actions">
          <button
            type="button"
            className="button"
            disabled={!canWrite}
            title={canWrite ? undefined : t('share.cannotWrite')}
            onClick={onCreate}
          >
            + {t('share.new')}
          </button>
        </div>
      </div>

      {/* Why the button is disabled, in the words that name the fix.
          "Could not be determined" on its own is the least useful thing this
          banner can say, so the notes the capability check collected are shown
          with it — they name which query was refused. */}
      {capabilities && capabilities.can_manage_shares !== true && (
        <Banner
          message={
            // The notes carry the whole story now, including the command to
            // run. Prefixing them with a summary produced the same thing said
            // twice, which is what made the old banner unreadable.
            capabilities.notes.length > 0
              ? capabilities.notes.map((note) => noteText(t, note)).join(' ')
              : capabilities.registry_config === false
                ? t('caps.noRegistryConfig')
                : t('caps.unknownWhy')
          }
          tone={capabilities.can_manage_shares === false ? 'warning' : 'info'}
        />
      )}

      {shares.isLoading && <Spinner label={t('status.loading')} />}
      <ErrorMessage error={shares.error} />

      <ul className="list list--shares">
        {(shares.data?.entries ?? []).map((share) => (
          <ShareRow
            key={share.name}
            share={share}
            selected={share.name === selected}
            onSelect={() => onSelect(share.name)}
            onOpen={() => onOpen(share.name)}
            onContext={(at) => onContext(share, at)}
          />
        ))}
        {shares.data?.entries.length === 0 && (
          <li className="list__empty muted">{t('status.empty')}</li>
        )}
      </ul>

      {creating && <NewShareDialog onClose={onCreate} onDone={onCreated} />}
    </div>
  )
}

/**
 * A capability note, in the reader's language.
 *
 * An unknown code falls back to the code itself rather than to a blank: a note
 * the server added before this catalogue caught up should still say *something*
 * a person can search for.
 */
function noteText(
  t: (key: MessageKey, params?: Record<string, string | number>) => string,
  note: CapabilityNote,
): string {
  const key = `caps.note.${note.code}` as MessageKey
  const text = t(key, note.params)
  return text === key ? note.code : text
}

function ShareRow({
  share,
  selected,
  onSelect,
  onOpen,
  onContext,
}: {
  share: Share
  selected: boolean
  onSelect: () => void
  onOpen: () => void
  onContext: (at: { x: number; y: number }) => void
}) {
  const { t } = useI18n()

  return (
    <li>
      <button
        type="button"
        className={selected ? 'list__item list__item--selected' : 'list__item'}
        onClick={onSelect}
        onDoubleClick={onOpen}
        // Selects first, then opens the menu — which is what Windows does, and
        // it matters: a menu acting on a row that is not the highlighted one is
        // how the wrong share gets deleted.
        onContextMenu={(event) => {
          event.preventDefault()
          onSelect()
          onContext({ x: event.clientX, y: event.clientY })
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter') onOpen()
          else if (event.shiftKey && event.key === 'F10') {
            event.preventDefault()
            onSelect()
            onContext(anchorOf(event.currentTarget))
          }
        }}
      >
        <Icon type="share" />
        {/* Two lines. The column is 300px wide on a normal window, and a name,
            a path, a comment and two badges competing for one of them left
            every field truncated to uselessness. */}
        <span className="list__lines">
          <span className="list__line">
            <span className="list__name">{share.name}</span>
            {/* Not a warning — a fact about where this share is configured. */}
            {!share.editable && <Badge tone="muted">{t('share.fromSmbConf')}</Badge>}
            {/* How many clients have it open. As a bare number it read as
                an unexplained "1" beside the name — which is what it was
                asked about. */}
            {share.current_users ? (
              <Badge tone="ok">
                <span title={t('share.connected.why')}>
                  {t('share.connectedCount', { count: share.current_users })}
                </span>
              </Badge>
            ) : null}
          </span>
          <span className="list__meta mono">{share.path ?? '—'}</span>
          {share.comment && <span className="list__meta">{share.comment}</span>}
        </span>
      </button>
    </li>
  )
}
