/**
 * A local user or group, in a window of its own.
 *
 * The list already shows a name, a state and three buttons. What it cannot show
 * is a group's membership: `LocalGroup.members` is a list of SIDs, which in a
 * table of forty-character strings is worse than nothing. This is the first
 * place they are resolved into names.
 *
 * It holds an identity and fetches by it, like every window. So an account
 * renamed or removed from under this one says so on the next read instead of
 * showing what used to be true.
 */

import { useQuery } from '@tanstack/react-query'

import { api } from '../../api/endpoints'
import type { LocalAccount, LocalGroup, Trustee } from '../../api/types'
import { Badge, Icon, Spinner, TextRow } from '../../components/primitives'
import { useI18n } from '../../i18n'

export function AccountWindow({
  of,
  name,
  onAction,
}: {
  of: 'user' | 'group'
  name: string
  /** Handed back to the shell, which owns the dialogs and the mutations. */
  onAction: (id: string) => void
}) {
  return of === 'user' ? (
    <UserSheet name={name} onAction={onAction} />
  ) : (
    <GroupSheet name={name} />
  )
}

function Missing() {
  const { t } = useI18n()
  return <p className="muted">{t('window.gone')}</p>
}

function UserSheet({ name, onAction }: { name: string; onAction: (id: string) => void }) {
  const { t } = useI18n()
  const users = useQuery({ queryKey: ['localUsers'], queryFn: () => api.localUsers() })

  if (users.isLoading) return <Spinner label={t('status.loading')} />

  const account = users.data?.entries.find((entry: LocalAccount) => entry.name === name)
  if (!account) return <Missing />

  return (
    <div className="sheet-window">
      <div className="sheet-window__panel">
        <div className="detail__header">
          <Icon type="user" className="icon--large" />
          <div>
            <h2>{account.name}</h2>
            <span className="muted small">{t('accounts.users')}</span>
          </div>
        </div>

        <div className="detail__badges">
          {account.disabled ? (
            <Badge tone="warn">{t('accounts.isDisabled')}</Badge>
          ) : (
            <Badge tone="ok">{t('accounts.isEnabled')}</Badge>
          )}
          {account.locked_out && <Badge tone="danger">{t('accounts.isLocked')}</Badge>}
          {account.password_never_expires && (
            <Badge tone="muted">{t('accounts.neverExpires')}</Badge>
          )}
          {account.protected && <Badge tone="muted">{t('accounts.protected')}</Badge>}
        </div>

        <section className="detail__section">
          <TextRow label={t('accounts.fullName')} value={account.full_name} />
          <TextRow label={t('accounts.description')} value={account.description} />
          <TextRow label="RID" value={String(account.rid)} />
          {/* The SID is what every permission entry on this server actually
              names. Shown so it can be compared with one. */}
          <TextRow label="SID" value={account.sid && <span className="mono">{account.sid}</span>} />
        </section>
      </div>

      <footer className="sheet-window__footer">
        <button type="button" className="button" onClick={() => onAction('account.password')}>
          {t('accounts.setPassword')}
        </button>
        <button
          type="button"
          className="button"
          onClick={() => onAction(account.disabled ? 'account.enable' : 'account.disable')}
        >
          {account.disabled ? t('accounts.enable') : t('accounts.disable')}
        </button>
        <button
          type="button"
          className="button button--danger"
          disabled={account.protected}
          title={account.protected ? t('accounts.protected') : undefined}
          onClick={() => onAction('account.delete')}
        >
          {t('accounts.delete')}
        </button>
      </footer>
    </div>
  )
}

function GroupSheet({ name }: { name: string }) {
  const { t } = useI18n()
  const groups = useQuery({ queryKey: ['localGroups'], queryFn: () => api.localGroups() })
  const group = groups.data?.entries.find((entry: LocalGroup) => entry.name === name)

  // Resolved only once there is something to resolve, and only for this group.
  // A local group can hold domain accounts, so these are not all local SIDs.
  const members = useQuery({
    queryKey: ['trustees', group?.members ?? []],
    queryFn: () => api.lookupSids(group?.members ?? []),
    enabled: (group?.members.length ?? 0) > 0,
  })

  if (groups.isLoading) return <Spinner label={t('status.loading')} />
  if (!group) return <Missing />

  return (
    <div className="sheet-window">
      <div className="sheet-window__panel">
        <div className="detail__header">
          <Icon type="group" className="icon--large" />
          <div>
            <h2>{group.name}</h2>
            <span className="muted small">{t('accounts.groups')}</span>
          </div>
        </div>

        <section className="detail__section">
          <TextRow label={t('accounts.description')} value={group.description} />
          <TextRow label="RID" value={String(group.rid)} />
          <TextRow label="SID" value={group.sid && <span className="mono">{group.sid}</span>} />
        </section>

        <section className="detail__section">
          <h3>{t('accounts.members')}</h3>
          {group.members.length === 0 && <p className="muted">{t('accounts.noMembers')}</p>}
          {members.isLoading && <Spinner label={t('status.loading')} />}
          <ul className="list">
            {(members.data?.entries ?? []).map((trustee: Trustee) => (
              <li key={trustee.sid} className="list__item list__item--static">
                <Icon type={trustee.type} />
                <span className="list__lines">
                  <span className="list__line">
                    <span className="list__name">{trustee.name ?? trustee.sid}</span>
                    {trustee.domain && <span className="muted small">{trustee.domain}</span>}
                  </span>
                  {/* Kept beside the name rather than instead of it: a name
                      that could not be resolved has to be distinguishable from
                      one that could, and the SID is the only thing that is
                      certainly true. */}
                  <span className="list__meta mono">{trustee.sid}</span>
                </span>
              </li>
            ))}
          </ul>
          {/* Editable through api.setGroupMembers, which nothing calls yet.
              Said here rather than left as a menu entry that does nothing. */}
          <p className="muted small">{t('accounts.membersReadOnly')}</p>
        </section>
      </div>
    </div>
  )
}
