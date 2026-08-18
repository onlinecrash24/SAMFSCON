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

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { api } from '../../api/endpoints'
import type { Share, ShareListing } from '../../api/types'
import { Badge, Banner, ErrorMessage, Icon, Spinner } from '../../components/primitives'
import { useI18n } from '../../i18n'
import { NewShareDialog } from './NewShareDialog'
import { ShareDetail } from './ShareDetail'

export function SharesView({ onChanged }: { onChanged: (message: string) => void }) {
  const { t } = useI18n()
  const queryClient = useQueryClient()

  const [selected, setSelected] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const shares = useQuery<ShareListing>({
    queryKey: ['shares'],
    queryFn: () => api.shares(),
  })

  const remove = useMutation({
    mutationFn: (name: string) => api.deleteShare(name),
    onSuccess: (_result, name) => {
      setSelected(null)
      void queryClient.invalidateQueries({ queryKey: ['shares'] })
      onChanged(t('share.deleted', { name }))
    },
  })

  const capabilities = shares.data?.capabilities
  const canWrite = capabilities?.can_manage_shares === true

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
            onClick={() => setCreating(true)}
          >
            + {t('share.new')}
          </button>
        </div>
      </div>

      {/* Why the button is disabled, in the words that name the fix. */}
      {capabilities && capabilities.can_manage_shares !== true && (
        <Banner
          message={
            capabilities.registry_config === false
              ? t('caps.noRegistryConfig')
              : capabilities.has_disk_operator === false
                ? t('caps.noDiskOperator', {
                    names: capabilities.disk_operators.join(', ') || '—',
                  })
                : t('caps.unknownWhy')
          }
          tone="warning"
        />
      )}

      {shares.isLoading && <Spinner label={t('status.loading')} />}
      <ErrorMessage error={shares.error} />
      <ErrorMessage error={remove.error} onDismiss={() => remove.reset()} />

      <div className="shares__split">
        <ul className="list list--shares">
          {(shares.data?.entries ?? []).map((share) => (
            <ShareRow
              key={share.name}
              share={share}
              selected={share.name === selected}
              onSelect={() => setSelected(share.name)}
            />
          ))}
          {shares.data?.entries.length === 0 && (
            <li className="list__empty muted">{t('status.empty')}</li>
          )}
        </ul>

        <div className="shares__detail">
          {selected ? (
            <ShareDetail
              name={selected}
              canWrite={canWrite}
              onChanged={onChanged}
              onDeleted={() => remove.mutate(selected)}
              deleting={remove.isPending}
            />
          ) : (
            <div className="placeholder">
              <Icon type="share" className="icon--large" />
              <p className="muted">{t('share.selectOne')}</p>
            </div>
          )}
        </div>
      </div>

      {creating && (
        <NewShareDialog
          onClose={() => setCreating(false)}
          onDone={(name) => {
            setCreating(false)
            setSelected(name)
            void queryClient.invalidateQueries({ queryKey: ['shares'] })
            onChanged(t('share.created', { name }))
          }}
        />
      )}
    </div>
  )
}

function ShareRow({
  share,
  selected,
  onSelect,
}: {
  share: Share
  selected: boolean
  onSelect: () => void
}) {
  const { t } = useI18n()

  return (
    <li>
      <button
        type="button"
        className={selected ? 'list__item list__item--selected' : 'list__item'}
        onClick={onSelect}
      >
        <Icon type="share" />
        <span className="list__name">{share.name}</span>
        <span className="list__meta mono muted small">{share.path ?? '—'}</span>
        {share.comment && <span className="list__meta muted small">{share.comment}</span>}
        {/* Not a warning — a fact about where this share is configured. */}
        {!share.editable && <Badge tone="muted">{t('share.fromSmbConf')}</Badge>}
        {share.current_users ? <Badge tone="ok">{share.current_users}</Badge> : null}
      </button>
    </li>
  )
}
