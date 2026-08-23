/**
 * Who is connected, and what they have open.
 *
 * The view exists for one question, and the layout is built around it: "who has
 * this file open, because I cannot save it." So the open files are the lower
 * half and searchable, the sessions are the upper half for context, and the
 * only action is the one that answers the question — closing the handle.
 *
 * That action is destructive in a way nothing else in this console is: the
 * person holding the file is not asked and loses unsaved work. It therefore
 * confirms first, names who will be affected in the confirmation, and lands in
 * the audit log with both.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { api } from '../../api/endpoints'
import type { OpenFile, ServerSession } from '../../api/types'
import { Badge, ErrorMessage, Icon, Modal, Spinner } from '../../components/primitives'
import { useI18n } from '../../i18n'

export function SessionsView({
  onChanged,
  onContext,
}: {
  onChanged: (message: string) => void
  /** Two tables, so the row says which of them it came from. */
  onContext: (
    kind: 'session' | 'file',
    row: ServerSession | OpenFile,
    at: { x: number; y: number },
  ) => void
}) {
  const { t, tn } = useI18n()
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState('')
  const [closing, setClosing] = useState<OpenFile | null>(null)

  // Refetched on an interval: this is the one view whose whole point is that
  // it is current. Everything else in the console is configuration, which does
  // not change while you look at it.
  const sessions = useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.sessions(),
    refetchInterval: 10_000,
  })
  const files = useQuery({
    queryKey: ['openFiles'],
    queryFn: () => api.openFiles(),
    refetchInterval: 10_000,
  })

  const close = useMutation({
    mutationFn: (fileId: number) => api.closeFile(fileId),
    onSuccess: (result) => {
      setClosing(null)
      void queryClient.invalidateQueries({ queryKey: ['openFiles'] })
      void queryClient.invalidateQueries({ queryKey: ['sessions'] })
      onChanged(t('sessions.closed', { path: result.file?.path ?? String(result.file_id) }))
    },
  })

  const needle = filter.trim().toLowerCase()
  const shown = (files.data?.entries ?? []).filter(
    (file) =>
      !needle ||
      (file.path ?? '').toLowerCase().includes(needle) ||
      (file.user ?? '').toLowerCase().includes(needle),
  )

  return (
    <div className="sessions">
      <div className="pane__header">
        <span className="muted small">{t('snapin.sessions.note')}</span>
        <input
          type="search"
          value={filter}
          placeholder={t('sessions.filter')}
          onChange={(event) => setFilter(event.target.value)}
        />
      </div>

      <ErrorMessage error={sessions.error} />
      <ErrorMessage error={files.error} />
      <ErrorMessage error={close.error} onDismiss={() => close.reset()} />

      <section className="detail__section">
        <h3>
          {t('sessions.connected')}{' '}
          <span className="muted small">
            {tn('list.count', sessions.data?.entries.length ?? 0)}
          </span>
        </h3>
        {sessions.isLoading && <Spinner label={t('status.loading')} />}
        <table className="table">
          <thead>
            <tr>
              <th>{t('sessions.user')}</th>
              <th>{t('sessions.client')}</th>
              <th>{t('sessions.openFiles')}</th>
              <th>{t('sessions.connectedFor')}</th>
              <th>{t('sessions.idleFor')}</th>
            </tr>
          </thead>
          <tbody>
            {(sessions.data?.entries ?? []).map((entry, index) => (
              <SessionRow
                key={`${entry.client}-${entry.user}-${index}`}
                session={entry}
                onContext={(at) => onContext('session', entry, at)}
              />
            ))}
            {sessions.data?.entries.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  {t('sessions.nobody')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="detail__section">
        <h3>
          {t('sessions.files')}{' '}
          <span className="muted small">{tn('list.count', shown.length)}</span>
        </h3>
        {files.isLoading && <Spinner label={t('status.loading')} />}
        <table className="table">
          <thead>
            <tr>
              <th>{t('sessions.path')}</th>
              <th>{t('sessions.user')}</th>
              <th>{t('sessions.access')}</th>
              <th>{t('sessions.locks')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {shown.map((file) => (
              <tr
                key={file.id ?? file.path}
                onContextMenu={(event) => {
                  event.preventDefault()
                  onContext('file', file, { x: event.clientX, y: event.clientY })
                }}
              >
                <td className="mono">{file.path ?? '—'}</td>
                <td>{file.user ?? '—'}</td>
                <td>
                  {file.permissions.map((permission) => (
                    <Badge key={permission} tone={permission === 'write' ? 'warn' : 'muted'}>
                      {t(`sessions.access.${permission}`)}
                    </Badge>
                  ))}
                </td>
                <td>{file.locks ?? 0}</td>
                <td>
                  <button
                    type="button"
                    className="link link--danger"
                    disabled={file.id === null}
                    onClick={() => setClosing(file)}
                  >
                    {t('sessions.close')}
                  </button>
                </td>
              </tr>
            ))}
            {shown.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  {needle ? t('status.empty') : t('sessions.noFiles')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      {closing && (
        <Modal
          title={t('sessions.close')}
          onClose={() => setClosing(null)}
          footer={
            <>
              <button type="button" className="button" onClick={() => setClosing(null)}>
                {t('action.cancel')}
              </button>
              <button
                type="button"
                className="button button--danger"
                disabled={close.isPending}
                onClick={() => closing.id !== null && close.mutate(closing.id)}
              >
                {close.isPending ? t('status.loading') : t('sessions.closeConfirm')}
              </button>
            </>
          }
        >
          {/* Who loses what, in the sentence that asks. */}
          <p>
            {t('sessions.closeWarning', {
              path: closing.path ?? '—',
              user: closing.user ?? '—',
            })}
          </p>
        </Modal>
      )}
    </div>
  )
}

function SessionRow({
  session,
  onContext,
}: {
  session: ServerSession
  onContext: (at: { x: number; y: number }) => void
}) {
  const { t } = useI18n()
  return (
    <tr
      onContextMenu={(event) => {
        event.preventDefault()
        onContext({ x: event.clientX, y: event.clientY })
      }}
    >
      <td>
        <Icon type="user" /> {session.user ?? '—'}
        {session.guest && <Badge tone="warn">{t('sessions.guest')}</Badge>}
      </td>
      <td className="mono">{session.client ?? '—'}</td>
      <td>{session.open_files ?? 0}</td>
      <td>{formatDuration(session.connected_seconds)}</td>
      <td>{formatDuration(session.idle_seconds)}</td>
    </tr>
  )
}

/**
 * srvsvc reports durations in seconds, and the number people actually want is
 * "about how long". Rendered without a library: three units, no pluralisation
 * rules beyond what German and English share.
 */
function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds < 0) return '—'
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ${minutes % 60}m`
  return `${Math.floor(hours / 24)}d ${hours % 24}h`
}
