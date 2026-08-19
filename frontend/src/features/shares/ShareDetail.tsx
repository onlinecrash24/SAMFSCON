/**
 * One share, in tabs.
 *
 * The tabs follow the option catalogue's groups rather than a layout decided
 * here, so an option added to the catalogue appears in the interface without
 * anyone touching this file. What the catalogue does not describe still shows
 * up — read-only, under "advanced" — because a server configured by hand is not
 * wrong, and hiding half its configuration would make this console a liar.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'

import { api } from '../../api/endpoints'
import type { OptionSpec, Share } from '../../api/types'
import { Badge, ErrorMessage, Field, Spinner, TextRow } from '../../components/primitives'
import { useI18n } from '../../i18n'
import { PermissionEditor } from '../permissions/PermissionEditor'

const GROUPS = ['basic', 'permissions', 'filePermissions', 'access', 'files', 'vfs', 'advanced'] as const
type Group = (typeof GROUPS)[number]

export function ShareDetail({
  name,
  canWrite,
  onChanged,
  onDeleted,
  deleting,
}: {
  name: string
  canWrite: boolean
  onChanged: (message: string) => void
  onDeleted: () => void
  deleting: boolean
}) {
  const { t, language } = useI18n()
  const queryClient = useQueryClient()
  const [group, setGroup] = useState<Group>('basic')

  const share = useQuery<Share>({ queryKey: ['share', name], queryFn: () => api.share(name) })
  const catalogue = useQuery({
    queryKey: ['shareCatalogue', language],
    queryFn: () => api.shareCatalogue(language),
    staleTime: Infinity,
  })

  // What the form holds, seeded from the server and reset whenever a different
  // share is opened. Only the fields that actually differ are sent.
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [comment, setComment] = useState('')
  const [path, setPath] = useState('')

  useEffect(() => {
    if (!share.data) return
    setDraft({ ...share.data.options.known })
    setComment(share.data.comment ?? '')
    setPath(share.data.path ?? '')
  }, [share.data])

  const save = useMutation({
    mutationFn: () => {
      const stored = share.data?.options.known ?? {}
      const changed: Record<string, string | null> = {}
      for (const [key, value] of Object.entries(draft)) {
        // An empty field means "the server's default", which is a deletion
        // rather than an empty value — smb.conf honours an empty string.
        const next = value === '' ? null : value
        if ((stored[key] ?? null) !== next) changed[key] = next
      }
      return api.updateShare(name, {
        path: path !== share.data?.path ? path : undefined,
        comment: comment !== (share.data?.comment ?? '') ? comment : undefined,
        options: changed,
      })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['share', name] })
      void queryClient.invalidateQueries({ queryKey: ['shares'] })
      onChanged(t('status.saved'))
    },
  })

  const loaded = share.data
  const specs = catalogue.data?.options ?? []

  // Options that need a VFS module the share has not loaded are shown and
  // disabled: a recycle bin configured on a share without the module never
  // runs, and never says so.
  const loadedModules = useMemo(() => new Set(loaded?.vfs ?? []), [loaded])

  if (share.isLoading) return <Spinner label={t('status.loading')} />
  if (!loaded) return <ErrorMessage error={share.error} />

  const editable = loaded.editable && canWrite

  return (
    <div className="detail">
      <header className="detail__header">
        <h2>{loaded.name}</h2>
        <div className="detail__badges">
          {!loaded.editable && <Badge tone="warn">{t('share.fromSmbConf')}</Badge>}
        </div>
      </header>

      {!loaded.editable && <p className="muted small">{t('share.fromSmbConf.why')}</p>}

      <nav className="tabs">
        {GROUPS.map((entry) => (
          <button
            key={entry}
            type="button"
            className={group === entry ? 'tabs__tab tabs__tab--active' : 'tabs__tab'}
            onClick={() => setGroup(entry)}
          >
            {t(`share.group.${entry}`)}
          </button>
        ))}
      </nav>

      <ErrorMessage error={save.error} onDismiss={() => save.reset()} />

      {group === 'basic' && (
        <>
          <Field label={t('share.path')} hint={t('share.path.hint')}>
            <input
              type="text"
              value={path}
              disabled={!editable}
              spellCheck={false}
              onChange={(event) => setPath(event.target.value)}
            />
          </Field>
          <Field label={t('share.comment')}>
            <input
              type="text"
              value={comment}
              disabled={!editable}
              onChange={(event) => setComment(event.target.value)}
            />
          </Field>
          <TextRow label={t('share.currentUsers')} value={loaded.current_users ?? 0} />
        </>
      )}

      {group === 'permissions' && (
        <PermissionEditor
          share={loaded.name}
          level="share"
          canWrite={canWrite}
          onChanged={onChanged}
        />
      )}

      {group === 'filePermissions' && (
        <PermissionEditor
          share={loaded.name}
          path=""
          level="file"
          canWrite={canWrite}
          onChanged={onChanged}
        />
      )}

      {specs
        .filter((spec) => spec.group === group)
        .map((spec) => {
          const missing =
            spec.requires_vfs !== null && !loadedModules.has(spec.requires_vfs)
              ? spec.requires_vfs
              : null
          return (
            <OptionField
              key={spec.name}
              spec={spec}
              value={draft[spec.name] ?? ''}
              disabled={!editable || missing !== null}
              missingModule={missing}
              onChange={(value) => setDraft((current) => ({ ...current, [spec.name]: value }))}
            />
          )
        })}

      {group === 'advanced' && Object.keys(loaded.options.extra).length > 0 && (
        <section className="detail__section">
          <h3>{t('share.otherOptions')}</h3>
          <p className="muted small">{t('share.otherOptions.why')}</p>
          <dl className="kv">
            {Object.entries(loaded.options.extra).map(([key, value]) => (
              <div key={key}>
                <dt className="mono">{key}</dt>
                <dd className="mono">{value}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <footer className="detail__footer">
        <button
          type="button"
          className="button button--primary"
          disabled={!editable || save.isPending}
          onClick={() => save.mutate()}
        >
          {save.isPending ? t('status.loading') : t('action.save')}
        </button>
        <button
          type="button"
          className="button button--danger"
          disabled={!editable || deleting}
          onClick={onDeleted}
        >
          {t('share.delete')}
        </button>
      </footer>
    </div>
  )
}

function OptionField({
  spec,
  value,
  disabled,
  missingModule,
  onChange,
}: {
  spec: OptionSpec
  value: string
  disabled: boolean
  missingModule: string | null
  onChange: (value: string) => void
}) {
  const { t } = useI18n()
  const hint = missingModule ? t('share.needsModule', { module: missingModule }) : spec.doc

  if (spec.type === 'bool') {
    return (
      <label className="checkbox">
        <input
          type="checkbox"
          checked={value === 'yes'}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked ? 'yes' : 'no')}
        />
        <span>{spec.name}</span>
        <span className="field__hint">{hint}</span>
      </label>
    )
  }

  if (spec.type === 'choice') {
    return (
      <Field label={spec.name} hint={hint}>
        <select
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">{spec.default ?? ''}</option>
          {spec.choices.map((choice) => (
            <option key={choice} value={choice}>
              {choice}
            </option>
          ))}
        </select>
      </Field>
    )
  }

  return (
    <Field label={spec.name} hint={hint}>
      <input
        type="text"
        value={value}
        disabled={disabled}
        spellCheck={false}
        // The server's default as the placeholder, so an empty field reads as
        // "whatever Samba does" rather than as "nothing".
        placeholder={spec.default ?? ''}
        onChange={(event) => onChange(event.target.value)}
      />
    </Field>
  )
}
