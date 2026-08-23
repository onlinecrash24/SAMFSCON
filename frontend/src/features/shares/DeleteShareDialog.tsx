/**
 * Asking before removing a share.
 *
 * There was no confirmation at all: the button in the property sheet fired the
 * DELETE straight away. That was survivable while deleting meant finding the
 * share, opening it and reaching the footer — three deliberate steps. On a
 * right-click menu it is one, next to the item above it.
 *
 * What it says is what the deletion actually does, which is less than people
 * expect and worth stating plainly: the share stops being published and its
 * configuration is removed. The directory and everything in it stay exactly
 * where they are — this console has no way to delete files on a server and
 * would not do it here if it had.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query'

import { api } from '../../api/endpoints'
import { ErrorMessage, Modal } from '../../components/primitives'
import { useI18n } from '../../i18n'

export function DeleteShareDialog({
  name,
  path,
  onClose,
  onDone,
}: {
  name: string
  path: string | null
  onClose: () => void
  onDone: (name: string) => void
}) {
  const { t } = useI18n()
  const queryClient = useQueryClient()

  const remove = useMutation({
    mutationFn: () => api.deleteShare(name),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['shares'] })
      onDone(name)
    },
  })

  return (
    <Modal
      title={t('share.deleteConfirm')}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="button" onClick={onClose}>
            {t('action.cancel')}
          </button>
          <button
            type="button"
            className="button button--danger"
            disabled={remove.isPending}
            onClick={() => remove.mutate()}
          >
            {remove.isPending ? t('status.loading') : t('share.delete')}
          </button>
        </>
      }
    >
      <p>{t('share.deleteWarning', { name })}</p>
      {path && (
        <p className="muted small">
          {t('share.deleteKeepsFiles')} <span className="mono">{path}</span>
        </p>
      )}
      <ErrorMessage error={remove.error} onDismiss={() => remove.reset()} />
    </Modal>
  )
}
