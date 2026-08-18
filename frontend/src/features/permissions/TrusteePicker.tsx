/**
 * Choosing who an entry applies to.
 *
 * Resolved by the **file server**, not by a domain controller. That is the
 * point: a member server resolves its own local groups and the domain's
 * accounts through one call, with the answer it would itself use when deciding
 * access. Asking a DC instead would give a different answer for exactly the
 * cases that matter — a local group, a well-known SID, an account from a
 * trusted domain the server cannot see.
 *
 * A name that resolves to nothing is shown as unresolved rather than dropped.
 * Somebody typing a name that does not exist should see that it does not exist,
 * not an empty list they read as a broken search box.
 */

import { useMutation, useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { api } from '../../api/endpoints'
import type { Trustee } from '../../api/types'
import { Badge, ErrorMessage, Field, Icon, Modal, Spinner } from '../../components/primitives'
import { useI18n } from '../../i18n'

export function TrusteePicker({
  onClose,
  onPick,
}: {
  onClose: () => void
  onPick: (trustee: Trustee) => void
}) {
  const { t } = useI18n()
  const [query, setQuery] = useState('')

  // The trustees most entries actually name, offered before anyone types.
  const wellKnown = useQuery({
    queryKey: ['wellKnownTrustees'],
    queryFn: () => api.wellKnownTrustees(),
    staleTime: 5 * 60_000,
  })

  const search = useMutation({
    mutationFn: (names: string[]) => api.lookupNames(names),
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    const name = query.trim()
    if (name) search.mutate([name])
  }

  const found = search.data?.entries ?? []

  return (
    <Modal title={t('perm.pick')} onClose={onClose}>
      <form onSubmit={submit}>
        <Field label={t('perm.pick.search')} hint={t('perm.pick.hint')}>
          <div className="login__row">
            <input
              type="text"
              value={query}
              autoFocus
              spellCheck={false}
              placeholder="alice, EXAMPLE\staff"
              onChange={(event) => setQuery(event.target.value)}
            />
            <button type="submit" className="button" disabled={search.isPending}>
              {search.isPending ? t('status.loading') : t('nav.search')}
            </button>
          </div>
        </Field>
      </form>

      <ErrorMessage error={search.error} onDismiss={() => search.reset()} />

      {found.length > 0 && (
        <ul className="list">
          {found.map((entry) => (
            <TrusteeRow key={entry.sid ?? entry.name} trustee={entry} onPick={onPick} />
          ))}
        </ul>
      )}

      <h3>{t('perm.pick.wellKnown')}</h3>
      {wellKnown.isLoading && <Spinner />}
      <ul className="list">
        {(wellKnown.data?.entries ?? []).map((entry) => (
          <TrusteeRow key={entry.sid ?? entry.name} trustee={entry} onPick={onPick} />
        ))}
      </ul>
    </Modal>
  )
}

function TrusteeRow({
  trustee,
  onPick,
}: {
  trustee: Trustee
  onPick: (trustee: Trustee) => void
}) {
  const { t } = useI18n()
  const resolved = trustee.sid !== null

  return (
    <li>
      <button
        type="button"
        className="list__item"
        disabled={!resolved}
        onClick={() => onPick(trustee)}
      >
        <Icon type={trustee.type} />
        <span className="list__name">{trustee.name ?? trustee.sid}</span>
        {trustee.domain && <span className="list__meta muted small">{trustee.domain}</span>}
        <span className="list__meta mono muted small">{trustee.sid ?? '—'}</span>
        {resolved ? (
          <Badge tone="muted">{t(`type.${trustee.type}`)}</Badge>
        ) : (
          <Badge tone="warn">{t('perm.unresolved')}</Badge>
        )}
      </button>
    </li>
  )
}
