/**
 * What is inside the folder the tree is pointing at.
 *
 * Read-only, plus one creation, and that is the whole product decision:
 * SAMFSCON is a permissions console rather than a file manager. What it needs
 * from a share's contents is somewhere to point the ACL editor; adding upload,
 * download and delete would be a second application with a second set of ways
 * to lose somebody's data. `mkdir` is the exception because creating a folder
 * is what one does *while* setting permissions on a new project directory.
 *
 * The three attribute badges are not decoration. Each explains behaviour that
 * gets blamed on permissions: a read-only file refuses a write the ACL allows,
 * a hidden one is missing from Explorer, and a system one is both and looks
 * like neither.
 */

import { useQuery } from '@tanstack/react-query'

import { api } from '../../api/endpoints'
import type { DirectoryEntry, DirectoryListing } from '../../api/types'
import { anchorOf } from '../../components/ContextMenu'
import { Badge, Banner, ErrorMessage, Icon, Spinner, useDateFormat } from '../../components/primitives'
import { useI18n } from '../../i18n'
import { displayPath, type FileLocation } from './location'

export function FilesView({
  location,
  onOpen,
  onProperties,
  onContext,
  onCreate,
}: {
  location: FileLocation | null
  /** A folder: walk into it. */
  onOpen: (path: string) => void
  /** Anything: open its permissions in a window. */
  onProperties: (entry: DirectoryEntry) => void
  onContext: (entry: DirectoryEntry | null, at: { x: number; y: number }) => void
  onCreate: () => void
}) {
  const { t } = useI18n()
  const format = useDateFormat()

  const listing = useQuery<DirectoryListing>({
    queryKey: ['directory', location?.share, location?.path],
    queryFn: () => api.listDirectory(location!.share, location!.path),
    enabled: location !== null,
  })

  if (!location) {
    return (
      <div className="placeholder">
        <Icon type="folder" className="icon--large" />
        <p className="muted">{t('files.selectOne')}</p>
      </div>
    )
  }

  const entries = listing.data?.entries ?? []

  return (
    <div className="files">
      <div className="pane__header">
        <span className="mono small">{displayPath(location)}</span>
        <div className="pane__actions">
          <button type="button" className="button" onClick={onCreate}>
            + {t('files.newFolder')}
          </button>
        </div>
      </div>

      {/* The server stops at a fixed number of entries. Saying so is the
          difference between a short list and a wrong one. */}
      {listing.data?.truncated && <Banner message={t('files.truncated')} tone="warning" />}

      {listing.isLoading && <Spinner label={t('status.loading')} />}
      <ErrorMessage error={listing.error} />

      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              <th>{t('files.name')}</th>
              <th>{t('files.size')}</th>
              <th>{t('files.modified')}</th>
              <th>{t('files.attributes')}</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr
                key={entry.path}
                onDoubleClick={() =>
                  entry.is_directory ? onOpen(entry.path) : onProperties(entry)
                }
                onContextMenu={(event) => {
                  event.preventDefault()
                  onContext(entry, { x: event.clientX, y: event.clientY })
                }}
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    entry.is_directory ? onOpen(entry.path) : onProperties(entry)
                  } else if (event.shiftKey && event.key === 'F10') {
                    event.preventDefault()
                    onContext(entry, anchorOf(event.currentTarget))
                  }
                }}
              >
                <td>
                  <Icon type={entry.is_directory ? 'folder' : 'file'} /> {entry.name}
                </td>
                {/* A directory has no size worth printing: what SMB reports for
                    one is the size of the directory entry, not of what is in
                    it, and a number that looks like an answer is worse than a
                    dash. */}
                <td className="mono">{entry.is_directory ? '—' : bytes(entry.size)}</td>
                <td>{format(entry.modified as string | null)}</td>
                <td>
                  {entry.read_only && <Badge tone="muted">{t('files.readOnly')}</Badge>}
                  {entry.hidden && <Badge tone="muted">{t('files.hidden')}</Badge>}
                  {entry.system && <Badge tone="muted">{t('files.system')}</Badge>}
                </td>
              </tr>
            ))}
            {listing.isSuccess && entries.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  {t('files.empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/**
 * A size somebody can read at a glance.
 *
 * Binary units, because that is what a file system reports and what Windows
 * shows beside the same file. Naming them KiB rather than KB is the honest
 * spelling of 1024 and avoids the argument entirely.
 */
function bytes(size: number): string {
  if (!Number.isFinite(size) || size < 0) return '—'
  if (size < 1024) return `${size} B`

  const units = ['KiB', 'MiB', 'GiB', 'TiB']
  let value = size / 1024
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value < 10 ? value.toFixed(1) : Math.round(value)} ${units[unit]}`
}
