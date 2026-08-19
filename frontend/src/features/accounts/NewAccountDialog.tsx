/**
 * Creating a local account.
 *
 * The password is required here rather than optional, and that is deliberate:
 * the server creates the account disabled and without one, and an account left
 * in that state is a half-made thing somebody has to remember to finish. Asking
 * for it up front means the account is complete when the dialog closes.
 */

import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { api } from '../../api/endpoints'
import { ErrorMessage, Field, Modal } from '../../components/primitives'
import { useI18n } from '../../i18n'

export function NewAccountDialog({
  onClose,
  onDone,
}: {
  onClose: () => void
  onDone: (name: string) => void
}) {
  const { t } = useI18n()
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const [fullName, setFullName] = useState('')
  const [description, setDescription] = useState('')
  const [disabled, setDisabled] = useState(false)
  const [neverExpires, setNeverExpires] = useState(false)

  const create = useMutation({
    mutationFn: () =>
      api.createLocalUser({
        name: name.trim(),
        password,
        full_name: fullName.trim() || null,
        description: description.trim() || null,
        disabled,
        password_never_expires: neverExpires,
      }),
    onSuccess: () => {
      // Whatever happens next, the fields do not keep it.
      setPassword('')
      setRepeat('')
      onDone(name.trim())
    },
  })

  const mismatch = repeat.length > 0 && password !== repeat
  const canSubmit = name.trim().length > 0 && password.length > 0 && !mismatch

  function submit(event: FormEvent) {
    event.preventDefault()
    if (canSubmit) create.mutate()
  }

  return (
    <Modal
      title={t('accounts.new')}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="button" onClick={onClose}>
            {t('action.cancel')}
          </button>
          <button
            type="submit"
            form="new-account"
            className="button button--primary"
            disabled={!canSubmit || create.isPending}
          >
            {create.isPending ? t('status.loading') : t('accounts.create')}
          </button>
        </>
      }
    >
      <form id="new-account" onSubmit={submit}>
        <Field label={t('accounts.name')}>
          <input
            type="text"
            value={name}
            autoFocus
            spellCheck={false}
            autoComplete="off"
            onChange={(event) => setName(event.target.value)}
          />
        </Field>

        <Field label={t('accounts.password')}>
          <input
            type="password"
            value={password}
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

        <Field label={t('accounts.fullName')}>
          <input
            type="text"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
          />
        </Field>

        <Field label={t('accounts.description')}>
          <input
            type="text"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </Field>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={disabled}
            onChange={(event) => setDisabled(event.target.checked)}
          />
          <span>{t('accounts.createDisabled')}</span>
        </label>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={neverExpires}
            onChange={(event) => setNeverExpires(event.target.checked)}
          />
          <span>{t('accounts.neverExpires')}</span>
        </label>

        <ErrorMessage error={create.error} onDismiss={() => create.reset()} />
      </form>
    </Modal>
  )
}
