/**
 * The permission editor, used at both levels.
 *
 * One component for share permissions and file permissions, because they are
 * one structure. What differs is which endpoint it reads and writes, and that
 * is a prop.
 *
 * Two things it refuses to hide, both because hiding them is how people end up
 * arguing with a screenshot:
 *
 * - **Inherited entries are shown and not editable.** They belong to the parent
 *   directory. Editing one in place would silently break the inheritance it
 *   came from, so the row says where it came from instead.
 * - **The effective right is the intersection of both levels.** A file ACL
 *   granting write on a read-only share grants nothing. The editor computes it
 *   for a selected trustee rather than leaving two numbers side by side for
 *   somebody to combine in their head.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { api } from '../../api/endpoints'
import type {
  Ace,
  PermissionLevel,
  ResolvedTrustee,
  SecurityDescriptor,
  Trustee,
} from '../../api/types'
import type { MessageKey } from '../../i18n/messages'
import { Badge, ErrorMessage, Spinner } from '../../components/primitives'
import { useI18n } from '../../i18n'
import { TrusteePicker } from './TrusteePicker'

const PRESETS = ['full', 'modify', 'read_execute', 'read', 'write'] as const

export function PermissionEditor({
  share,
  path,
  level,
  canWrite,
  onChanged,
}: {
  share: string
  path?: string
  level: PermissionLevel
  canWrite: boolean
  onChanged: (message: string) => void
}) {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const key = ['permissions', level, share, path ?? '']

  const descriptor = useQuery<SecurityDescriptor>({
    queryKey: key,
    queryFn: () =>
      level === 'share' ? api.sharePermissions(share) : api.pathPermissions(share, path ?? ''),
  })

  const [aces, setAces] = useState<Ace[]>([])
  const [protectedDacl, setProtectedDacl] = useState(false)
  const [adding, setAdding] = useState(false)
  const [inspect, setInspect] = useState<string | null>(null)

  useEffect(() => {
    if (!descriptor.data) return
    setAces(descriptor.data.aces)
    setProtectedDacl(descriptor.data.protected)
  }, [descriptor.data])

  const save = useMutation({
    mutationFn: () => {
      const sddl = buildSddl(descriptor.data, aces, protectedDacl)
      return level === 'share'
        ? api.setSharePermissions(share, sddl)
        : api.setPathPermissions(share, path ?? '', sddl, protectedDacl)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: key })
      onChanged(t('status.saved'))
    },
  })

  // Only asked for when a trustee is selected: it costs two server round trips,
  // and it answers a question nobody has until they point at a row.
  const effective = useQuery({
    queryKey: ['effective', share, path ?? '', inspect],
    queryFn: () => api.effectiveAccess(share, inspect!, path ?? ''),
    enabled: inspect !== null,
  })

  if (descriptor.isLoading) return <Spinner label={t('status.loading')} />
  if (!descriptor.data) return <ErrorMessage error={descriptor.error} />

  const editable = canWrite

  return (
    <div className="permissions">
      <p className="muted small">
        {level === 'share' ? t('perm.share.what') : t('perm.file.what')}
      </p>

      {/* Who the descriptor belongs to. `Creator Owner` resolves through the
          owner, so an editor that hides it is hiding half of what one of its
          own rows means. */}
      {(descriptor.data.owner || descriptor.data.group) && (
        <p className="muted small">
          {t('perm.owner')}:{' '}
          <span className="mono">
            {trusteeLabel(t, descriptor.data.owner ?? '—', descriptor.data.trustees[descriptor.data.owner ?? ''])}
          </span>
          {' · '}
          {t('perm.group')}:{' '}
          <span className="mono">
            {trusteeLabel(t, descriptor.data.group ?? '—', descriptor.data.trustees[descriptor.data.group ?? ''])}
          </span>
        </p>
      )}

      {/* Entries that grant nothing are not a fault and not rare: Samba builds
          an NT ACL out of a POSIX one, and a POSIX entry with no permission
          bits becomes an ACE with an empty access mask. Said once above the
          table rather than on every row that has one. */}
      {descriptor.data.aces.some((ace) => ace.understood && ace.mask === 0) && (
        <p className="muted small">{t('perm.grantsNothing.why')}</p>
      )}

      <ErrorMessage error={save.error} onDismiss={() => save.reset()} />

      <table className="table">
        <thead>
          <tr>
            <th>{t('perm.trustee')}</th>
            <th>{t('perm.kind')}</th>
            <th>{t('perm.level')}</th>
            <th>{t('perm.appliesTo')}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {aces.map((ace, index) => (
            <tr key={`${ace.trustee}-${ace.kind}-${index}`} className={ace.inherited ? 'row--muted' : undefined}>
              <td>
                <button
                  type="button"
                  className="link"
                  onClick={() => setInspect(ace.trustee)}
                  title={t('perm.inspect')}
                >
                  {trusteeLabel(t, ace.trustee, descriptor.data.trustees[ace.trustee])}
                </button>
                {/* The SID under the name. An ACE naming an account that has
                    since been deleted resolves to nothing, and then the SID is
                    the only thing left to search for. */}
                <span className="perm__sid mono muted small">{ace.trustee}</span>
              </td>
              <td>
                <Badge tone={ace.kind === 'deny' ? 'danger' : 'ok'}>
                  {t(`perm.kind.${ace.kind}`)}
                </Badge>
              </td>
              <td>
                <select
                  value={ace.preset ?? ''}
                  // An entry whose rights this parser could not read is not one
                  // to offer a replacement for: picking a level would rewrite it
                  // from a mask we have already admitted is incomplete.
                  disabled={!editable || ace.inherited || !ace.understood}
                  onChange={(event) =>
                    setAces((current) =>
                      current.map((entry, position) =>
                        position === index
                          ? { ...entry, preset: event.target.value, mask: 0 }
                          : entry,
                      ),
                    )
                  }
                >
                  {/* A mask that sits on no named rung keeps its exact value,
                      shown as hexadecimal rather than rounded to the nearest
                      preset — rounding it would change the permission. An
                      entry the parser could not fully read shows the text the
                      descriptor actually carried: a confident 0x00000000 in a
                      permissions dialog is a lie about who may do what. */}
                  {ace.preset === null && (
                    <option value="">
                      {!ace.understood
                        ? ace.raw_rights
                        : ace.mask === 0
                          ? t('perm.grantsNothing')
                          : `0x${ace.mask.toString(16).padStart(8, '0')}`}
                    </option>
                  )}
                  {PRESETS.map((preset) => (
                    <option key={preset} value={preset}>
                      {t(`perm.preset.${preset}`)}
                    </option>
                  ))}
                </select>
              </td>
              <td className="muted small">{t(`perm.appliesTo.${ace.applies_to}`)}</td>
              <td>
                {ace.inherited ? (
                  <span className="muted small" title={t('perm.inherited.why')}>
                    {t('perm.inherited')}
                  </span>
                ) : (
                  <button
                    type="button"
                    className="link link--danger"
                    disabled={!editable}
                    onClick={() =>
                      setAces((current) => current.filter((_, position) => position !== index))
                    }
                  >
                    {t('perm.remove')}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {inspect && (
        <section className="detail__section">
          <h3>{t('perm.effective', { trustee: inspect })}</h3>
          {effective.isLoading && <Spinner />}
          {effective.data && (
            <>
              <p>
                {effective.data.rights.length > 0
                  ? effective.data.rights.map((right) => rightLabel(t, right)).join(', ')
                  : t('perm.nothing')}
              </p>
              {/* The case that produces the argument. */}
              {effective.data.limited_by_share && (
                <p className="muted small">{t('perm.limitedByShare')}</p>
              )}
              <p className="muted small">{t('perm.directOnly')}</p>
            </>
          )}
          <button type="button" className="link" onClick={() => setInspect(null)}>
            {t('action.close')}
          </button>
        </section>
      )}

      {/* The descriptor as smbcacls prints it. Collapsed, because nobody wants
          it until a row shows something they did not expect — and then it is
          the only thing that answers why. */}
      <details className="perm__raw">
        <summary>{t('perm.raw')}</summary>
        <code>{descriptor.data.sddl}</code>
      </details>

      {level === 'file' && (
        <label className="checkbox">
          <input
            type="checkbox"
            checked={protectedDacl}
            disabled={!editable}
            onChange={(event) => setProtectedDacl(event.target.checked)}
          />
          <span>{t('perm.protected')}</span>
          <span className="field__hint">{t('perm.protected.hint')}</span>
        </label>
      )}

      <footer className="detail__footer">
        <button
          type="button"
          className="button"
          disabled={!editable}
          onClick={() => setAdding(true)}
        >
          + {t('perm.add')}
        </button>
        <button
          type="button"
          className="button button--primary"
          disabled={!editable || save.isPending}
          onClick={() => save.mutate()}
        >
          {save.isPending ? t('status.loading') : t('action.save')}
        </button>
      </footer>

      {adding && (
        <TrusteePicker
          onClose={() => setAdding(false)}
          onPick={(trustee: Trustee) => {
            setAdding(false)
            if (!trustee.sid) return
            // The new row's trustee is its SID, and the name for it is not in
            // the descriptor's map until the next fetch. Seeding it keeps the
            // row from appearing as a bare SID for a second.
            if (descriptor.data) {
              descriptor.data.trustees[trustee.sid] = {
                sid: trustee.sid,
                name: trustee.name,
                domain: trustee.domain,
                type: trustee.type,
              }
            }
            setAces((current) => [
              ...current,
              {
                trustee: trustee.sid!,
                kind: 'allow',
                mask: 0,
                flags: 3, // object + container inherit: what a new entry means
                inherited: false,
                preset: 'read_execute',
                rights: [],
                applies_to: 'this_and_children',
                // A row typed here was never parsed from a descriptor, so
                // there is nothing it could have failed to understand.
                raw_rights: '',
                understood: true,
              },
            ])
          }}
        />
      )}
    </div>
  )
}

/**
 * Render the edited entries back to SDDL.
 *
 * Done here rather than on the server because the server's job is to apply a
 * descriptor, not to reconstruct one from a UI's notion of rows. Inherited
 * entries are left out: they belong to the parent and the server re-applies
 * them, and writing them back as explicit entries is how an inheritance chain
 * turns into frozen copies that stop tracking their parent.
 */
function buildSddl(
  original: SecurityDescriptor | undefined,
  aces: Ace[],
  protectedDacl: boolean,
): string {
  const parts: string[] = []
  if (original?.owner) parts.push(`O:${original.owner}`)
  if (original?.group) parts.push(`G:${original.group}`)

  let dacl = 'D:'
  if (protectedDacl) dacl += 'P'
  for (const ace of aces) {
    if (ace.inherited) continue
    const letter = ace.kind === 'deny' ? 'D' : 'A'
    const rights = ace.preset ? PRESET_LETTERS[ace.preset] : `0x${ace.mask.toString(16).padStart(8, '0')}`
    dacl += `(${letter};${flagLetters(ace.flags)};${rights};;;${ace.trustee})`
  }
  parts.push(dacl)
  return parts.join('')
}

/**
 * The SDDL right strings for the five named levels.
 *
 * Kept in step with `samfscon.srv.acl.PRESETS` — the server re-parses whatever
 * arrives, so a disagreement here shows up as a permission that is not the one
 * that was chosen rather than as an error.
 */
const PRESET_LETTERS: Record<string, string> = {
  full: 'FA',
  modify: '0x001301bf',
  read_execute: '0x001200a9',
  read: 'FR',
  write: 'FW',
}

/**
 * A trustee, as a person would name it.
 *
 * Falls back through everything it knows before giving up: the resolved name,
 * then a Unix uid or gid named for what it is, then the alias, then the raw
 * string. The last of those is what the whole column used to show.
 */
function trusteeLabel(
  t: (key: MessageKey, params?: Record<string, string | number>) => string,
  trustee: string,
  resolved: ResolvedTrustee | undefined,
): string {
  if (resolved?.name) {
    return resolved.domain ? `${resolved.domain}\\${resolved.name}` : resolved.name
  }
  if (resolved?.unix) {
    const key =
      resolved.unix.kind === 'unix_user' ? 'perm.unixUser' : 'perm.unixGroup'
    return t(key, { id: resolved.unix.id })
  }
  if (resolved?.alias) return resolved.alias
  return trustee
}

/**
 * A right's label, falling back to its own name.
 *
 * The server names rights as free-form strings, so a right added there before
 * a translation exists must render as itself rather than as a missing key —
 * or worse, fail to compile the day somebody adds one.
 */
function rightLabel(t: (key: MessageKey) => string, right: string): string {
  const key = `perm.right.${right}` as MessageKey
  const label = t(key)
  return label === key ? right : label
}

function flagLetters(flags: number): string {
  let out = ''
  if (flags & 0x01) out += 'OI'
  if (flags & 0x02) out += 'CI'
  if (flags & 0x04) out += 'NP'
  if (flags & 0x08) out += 'IO'
  // 0x10 (inherited) is never written: it is the server's statement about
  // where an entry came from, not ours to claim.
  return out
}
