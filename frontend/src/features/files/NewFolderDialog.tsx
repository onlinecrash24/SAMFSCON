/**
 * Creating one directory inside a share.
 *
 * The only write this console makes to a server's file system, and it earns
 * its place: creating a subfolder is what one does *while* setting permissions
 * on a new project directory, and it is the one such write these protocols can
 * perform — precisely because it happens inside a share that already exists.
 *
 * It inherits the parent's permissions, as any directory created over SMB
 * does. Said here, because "why does the new folder have the old folder's
 * rights" is otherwise a question somebody asks after the fact.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { api } from '../../api/endpoints'
import { ErrorMessage, Field, Modal } from '../../components/primitives'
import { useI18n } from '../../i18n'
import { childOf, displayPath, type FileLocation } from './location'

// The characters SMB refuses in a name. Checked here so the refusal names the
// character, rather than arriving as a status code that names nothing.
const FORBIDDEN = /[\\/:*?"<>|]/

export function NewFolderDialog({
  location,
  onClose,
  onDone,
}: {
  location: FileLocation
  onClose: () => void
  onDone: (name: string) => void
}) {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const [name, setName] = useState('')

  const trimmed = name.trim()
  const invalid = trimmed !== '' && FORBIDDEN.test(trimmed)

  const create = useMutation({
    mutationFn: () => api.createDirectory(location.share, childOf(location, trimmed)),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['directory', location.share] })
      onDone(trimmed)
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!trimmed || invalid) return
    create.mutate()
  }

  return (
    <Modal
      title={t('files.newFolder')}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="button" onClick={onClose}>
            {t('action.cancel')}
          </button>
          <button
            type="submit"
            form="new-folder"
            className="button button--primary"
            disabled={create.isPending || !trimmed || invalid}
          >
            {create.isPending ? t('status.loading') : t('files.create')}
          </button>
        </>
      }
    >
      <form id="new-folder" onSubmit={submit}>
        <p className="muted small">
          {t('files.newFolderIn')} <span className="mono">{displayPath(location)}</span>
        </p>

        <Field label={t('files.name')} hint={t('files.inheritsPermissions')}>
          <input
            type="text"
            value={name}
            autoFocus
            spellCheck={false}
            onChange={(event) => setName(event.target.value)}
          />
        </Field>

        {invalid && <p className="muted small">{t('files.nameForbidden')}</p>}

        <ErrorMessage error={create.error} onDismiss={() => create.reset()} />
      </form>
    </Modal>
  )
}
