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
  // Created, and its directory refuses this account. Held here rather than
  // handed straight back, so the sentence is read before it is dismissed.
  const [blocked, setBlocked] = useState(false)
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
    onSuccess: (result) => {
      // A share is a registry key; the directory it points at is not, and its
      // permissions were decided by whoever created it on the server. A share
      // nobody can put anything in is worth stopping on rather than mentioning
      // in a notice that scrolls away — so a confirmed `false` holds the
      // dialog open. `null` means the server could not be asked, which is not
      // the same thing and is not worth stopping anybody for.
      if (result.root_writable === false) {
        setBlocked(true)
        return
      }
      onDone(name.trim(), result.served !== false)
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate()
  }

  if (blocked) {
    return (
      <Modal
        title={t('share.created.title')}
        onClose={() => onDone(name.trim(), true)}
        footer={
          <button
            type="button"
            className="button button--primary"
            onClick={() => onDone(name.trim(), true)}
          >
            {t('action.close')}
          </button>
        }
      >
        <p>{t('share.created', { name: name.trim() })}</p>
        <div className="alert alert--warning">
          <div className="alert__body">
            <strong>{t('share.rootNotWritable')}</strong>
            <p className="alert__hint">{t('share.rootNotWritable.why')}</p>
          </div>
        </div>
      </Modal>
    )
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
