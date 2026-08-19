/**
 * Creating a share.
 *
 * Only the fields every console asks for. Everything else is edited afterwards
 * on the share's own tabs, because a creation form carrying thirty options is a
 * form people fill in wrongly once and never revisit.
 *
 * The path field carries the one limit of managing a server over the network:
 * the directory has to exist already. SAMFSCON speaks SMB and RPC, and neither
 * can create a directory outside a share it can already reach. Said here rather
 * than left to a WERR_NERR_UNKNOWNDEVDIR nobody can read.
 */

import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { api } from '../../api/endpoints'
import { ErrorMessage, Field, Modal } from '../../components/primitives'
import { useI18n } from '../../i18n'

export function NewShareDialog({
  onClose,
  onDone,
}: {
  onClose: () => void
  onDone: (name: string, served: boolean) => void
}) {
  const { t } = useI18n()
  const [name, setName] = useState('')
  const [path, setPath] = useState('')
  const [comment, setComment] = useState('')
  const [readOnly, setReadOnly] = useState(false)
  const [browseable, setBrowseable] = useState(true)
  const [guestOk, setGuestOk] = useState(false)

  const create = useMutation({
    mutationFn: () =>
      api.createShare({
        name: name.trim(),
        path: path.trim(),
        comment: comment.trim() || null,
        read_only: readOnly,
        browseable,
        guest_ok: guestOk,
        options: {},
      }),
    onSuccess: (result) => onDone(name.trim(), result.served !== false),
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate()
  }

  return (
    <Modal
      title={t('share.new')}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="button" onClick={onClose}>
            {t('action.cancel')}
          </button>
          <button
            type="submit"
            form="new-share"
            className="button button--primary"
            disabled={create.isPending || !name.trim() || !path.trim()}
          >
            {create.isPending ? t('status.loading') : t('share.create')}
          </button>
        </>
      }
    >
      <form id="new-share" onSubmit={submit}>
        <Field label={t('share.name')} hint={t('share.name.hint')}>
          <input
            type="text"
            value={name}
            autoFocus
            spellCheck={false}
            onChange={(event) => setName(event.target.value)}
          />
        </Field>

        <Field label={t('share.path')} hint={t('share.path.hint')}>
          <input
            type="text"
            value={path}
            spellCheck={false}
            placeholder="/srv/shares/projects"
            onChange={(event) => setPath(event.target.value)}
          />
        </Field>

        <Field label={t('share.comment')}>
          <input
            type="text"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
          />
        </Field>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={readOnly}
            onChange={(event) => setReadOnly(event.target.checked)}
          />
          <span>{t('share.readOnly')}</span>
        </label>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={browseable}
            onChange={(event) => setBrowseable(event.target.checked)}
          />
          <span>{t('share.browseable')}</span>
        </label>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={guestOk}
            onChange={(event) => setGuestOk(event.target.checked)}
          />
          <span>{t('share.guestOk')}</span>
          <span className="field__hint">{t('share.guestOk.hint')}</span>
        </label>

        <ErrorMessage error={create.error} onDismiss={() => create.reset()} />
      </form>
    </Modal>
  )
}
