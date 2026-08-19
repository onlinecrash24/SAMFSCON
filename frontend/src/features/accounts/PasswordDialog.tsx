/**
 * Setting an existing account's password.
 *
 * Two fields rather than one, because there is no way to check afterwards: the
 * server stores a hash, and a typo becomes an account nobody can sign in to
 * until somebody notices and tries again.
 */

import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { api } from '../../api/endpoints'
import { ErrorMessage, Field, Modal } from '../../components/primitives'
import { useI18n } from '../../i18n'

export function PasswordDialog({
  name,
  onClose,
  onDone,
}: {
  name: string
  onClose: () => void
  onDone: (name: string) => void
}) {
  const { t } = useI18n()
  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')

  const set = useMutation({
    mutationFn: () => api.setLocalPassword(name, password),
    onSuccess: () => {
      setPassword('')
      setRepeat('')
      onDone(name)
    },
  })

  const mismatch = repeat.length > 0 && password !== repeat
  const canSubmit = password.length > 0 && !mismatch

  function submit(event: FormEvent) {
    event.preventDefault()
    if (canSubmit) set.mutate()
  }

  return (
    <Modal
      title={t('accounts.setPasswordFor', { name })}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="button" onClick={onClose}>
            {t('action.cancel')}
          </button>
          <button
            type="submit"
            form="set-password"
            className="button button--primary"
            disabled={!canSubmit || set.isPending}
          >
            {set.isPending ? t('status.loading') : t('action.save')}
          </button>
        </>
      }
    >
      <form id="set-password" onSubmit={submit}>
        <Field label={t('accounts.password')}>
          <input
            type="password"
            value={password}
            autoFocus
            autoComplete="new-password"
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>

        <Field label={t('accounts.repeat')} hint={mismatch ? t('accounts.mismatch') : undefined}>
          <input
            type="password"
            value={repeat}
            autoComplete="new-password"
            onChange={(event) => setRepeat(event.target.value)}
          />
        </Field>

        <ErrorMessage error={set.error} onDismiss={() => set.reset()} />
      </form>
    </Modal>
  )
}
