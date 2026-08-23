/**
 * Local users and groups.
 *
 * Only reachable on a standalone server. On a domain member the snap-in stays
 * disabled with an explanation, because a member server's local SAM is almost
 * always empty and entirely beside the point — its users come from the domain.
 * Showing an empty list would be technically accurate and completely
 * misleading.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { api } from '../../api/endpoints'
import type { LocalAccount, LocalGroup } from '../../api/types'
import { Badge, ErrorMessage, Icon, Modal, Spinner } from '../../components/primitives'
import { useI18n } from '../../i18n'
import { NewAccountDialog } from './NewAccountDialog'
import { PasswordDialog } from './PasswordDialog'

export function AccountsView({
  section,
  onChanged,
  onOpen,
  onContext,
}: {
  /** Which half of the console the tree is pointing at. */
  section: 'users' | 'groups'
  onChanged: (message: string) => void
  onOpen: (of: 'user' | 'group', name: string) => void
  onContext: (
    of: 'user' | 'group',
    row: LocalAccount | LocalGroup,
    at: { x: number; y: number },
  ) => void
}) {
  const { t } = useI18n()
  const queryClient = useQueryClient()

  const [creating, setCreating] = useState(false)
  const [password, setPassword] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<LocalAccount | null>(null)

  const users = useQuery({ queryKey: ['localUsers'], queryFn: () => api.localUsers() })
  const groups = useQuery({ queryKey: ['localGroups'], queryFn: () => api.localGroups() })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['localUsers'] })
    void queryClient.invalidateQueries({ queryKey: ['localGroups'] })
  }

  const toggle = useMutation({
    mutationFn: (account: LocalAccount) =>
      api.updateLocalUser(account.name, { disabled: !account.disabled }),
    onSuccess: (_result, account) => {
      refresh()
      onChanged(
        account.disabled
          ? t('accounts.enabled', { name: account.name })
          : t('accounts.disabled', { name: account.name }),
      )
    },
  })

  const remove = useMutation({
    mutationFn: (name: string) => api.deleteLocalUser(name),
    onSuccess: (_result, name) => {
      setDeleting(null)
      refresh()
      onChanged(t('accounts.deleted', { name }))
    },
  })

  return (
    <div className="accounts">
      <div className="pane__header">
        <span className="muted small">{t('snapin.accounts.note')}</span>
        <div className="pane__actions">
          <button type="button" className="button" onClick={() => setCreating(true)}>
            + {t('accounts.new')}
          </button>
        </div>
      </div>

      <ErrorMessage error={users.error} />
      <ErrorMessage error={toggle.error} onDismiss={() => toggle.reset()} />
      <ErrorMessage error={remove.error} onDismiss={() => remove.reset()} />

      {section === 'users' && (
      <section className="detail__section">
        <h3>{t('accounts.users')}</h3>
        {users.isLoading && <Spinner label={t('status.loading')} />}
        <table className="table">
          <thead>
            <tr>
              <th>{t('accounts.name')}</th>
              <th>{t('accounts.fullName')}</th>
              <th>{t('accounts.state')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(users.data?.entries ?? []).map((account) => (
              <tr
                key={account.rid}
                onDoubleClick={() => onOpen('user', account.name)}
                onContextMenu={(event) => {
                  event.preventDefault()
                  onContext('user', account, { x: event.clientX, y: event.clientY })
                }}
              >
                <td>
                  <Icon type="user" /> {account.name}
                </td>
                <td>{account.full_name ?? '—'}</td>
                <td>
                  {account.disabled && <Badge tone="warn">{t('accounts.isDisabled')}</Badge>}
                  {account.locked_out && <Badge tone="danger">{t('accounts.isLocked')}</Badge>}
                  {account.password_never_expires && (
                    <Badge tone="muted">{t('accounts.neverExpires')}</Badge>
                  )}
                  {!account.disabled && !account.locked_out && (
                    <Badge tone="ok">{t('accounts.isEnabled')}</Badge>
                  )}
                </td>
                <td>
                  <button
                    type="button"
                    className="link"
                    onClick={() => setPassword(account.name)}
                  >
                    {t('accounts.setPassword')}
                  </button>
                  <button
                    type="button"
                    className="link"
                    disabled={toggle.isPending}
                    onClick={() => toggle.mutate(account)}
                  >
                    {account.disabled ? t('accounts.enable') : t('accounts.disable')}
                  </button>
                  {/* The server's own accounts are not offered for deletion:
                      removing the built-in administrator is how somebody locks
                      themselves out of the server they are managing. */}
                  <button
                    type="button"
                    className="link link--danger"
                    disabled={account.protected}
                    title={account.protected ? t('accounts.protected') : undefined}
                    onClick={() => setDeleting(account)}
                  >
                    {t('accounts.delete')}
                  </button>
                </td>
              </tr>
            ))}
            {users.data?.entries.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  {t('status.empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      )}

      {section === 'groups' && (
      <section className="detail__section">
        <h3>{t('accounts.groups')}</h3>
        {groups.isLoading && <Spinner label={t('status.loading')} />}
        <ul className="list">
          {(groups.data?.entries ?? []).map((group: LocalGroup) => (
            <li key={group.rid}>
              <button
                type="button"
                className="list__item"
                onDoubleClick={() => onOpen('group', group.name)}
                onClick={() => onOpen('group', group.name)}
                onContextMenu={(event) => {
                  event.preventDefault()
                  onContext('group', group, { x: event.clientX, y: event.clientY })
                }}
              >
                <Icon type="group" />
                <span className="list__name">{group.name}</span>
                {group.description && (
                  <span className="list__meta muted small">{group.description}</span>
                )}
                <Badge tone="muted">
                  {t('accounts.memberCount', { count: group.members.length })}
                </Badge>
              </button>
            </li>
          ))}
          {groups.data?.entries.length === 0 && (
            <li className="list__empty muted">{t('status.empty')}</li>
          )}
        </ul>
      </section>
      )}

      {creating && (
        <NewAccountDialog
          onClose={() => setCreating(false)}
          onDone={(name) => {
            setCreating(false)
            refresh()
            onChanged(t('accounts.created', { name }))
          }}
        />
      )}

      {password && (
        <PasswordDialog
          name={password}
          onClose={() => setPassword(null)}
          onDone={(name) => {
            setPassword(null)
            onChanged(t('accounts.passwordSet', { name }))
          }}
        />
      )}

      {deleting && (
        <Modal
          title={t('accounts.delete')}
          onClose={() => setDeleting(null)}
          footer={
            <>
              <button type="button" className="button" onClick={() => setDeleting(null)}>
                {t('action.cancel')}
              </button>
              <button
                type="button"
                className="button button--danger"
                disabled={remove.isPending}
                onClick={() => remove.mutate(deleting.name)}
              >
                {remove.isPending ? t('status.loading') : t('accounts.delete')}
              </button>
            </>
          }
        >
          <p>{t('accounts.deleteWarning', { name: deleting.name })}</p>
        </Modal>
      )}
    </div>
  )
}
