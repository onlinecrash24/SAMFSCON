/**
 * The shares, and the folders inside them.
 *
 * A share is a root; everything under it is fetched a level at a time, when a
 * branch is opened and not before. A share can hold a hundred thousand
 * directories, and the console has no reason to know about any of them until
 * somebody points at one.
 *
 * Only directories appear here. Files are in the list beside it, which is the
 * arrangement every file manager uses and the reason the tree stays legible on
 * a share where the files outnumber the folders fifty to one.
 *
 * A branch that cannot be read is not a branch that is empty. The listing is
 * refused for a directory the signed-in account may not read — which is
 * correct, and is exactly the case somebody is looking at this console to
 * understand — so it says so on the row rather than drawing nothing.
 */

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { api } from '../../api/endpoints'
import type { DirectoryEntry, DirectoryListing, ShareListing } from '../../api/types'
import { Chevron, Icon } from '../../components/primitives'
import { useI18n } from '../../i18n'
import { childOf, decodeLocation, encodeLocation } from './location'

export function FolderTree({
  selected,
  onSelect,
  onContext,
}: {
  /** An encoded location, or null before anything has been chosen. */
  selected: string | null
  onSelect: (encoded: string) => void
  onContext: (share: string, path: string, at: { x: number; y: number }) => void
}) {
  const { t } = useI18n()
  const shares = useQuery<ShareListing>({ queryKey: ['shares'], queryFn: () => api.shares() })
  const here = decodeLocation(selected)

  const entries = shares.data?.entries ?? []
  if (entries.length === 0) {
    return <p className="tree__empty muted small">{t('status.empty')}</p>
  }

  return (
    <ul className="tree__list">
      {entries.map((share) => (
        <Branch
          key={share.name}
          share={share.name}
          path=""
          label={share.name}
          icon="share"
          depth={0}
          // A share is open when it is the one selected, or holds it.
          openByDefault={here?.share === share.name}
          selected={selected}
          onSelect={onSelect}
          onContext={onContext}
        />
      ))}
    </ul>
  )
}

function Branch({
  share,
  path,
  label,
  icon,
  depth,
  openByDefault,
  selected,
  onSelect,
  onContext,
}: {
  share: string
  path: string
  label: string
  icon: string
  depth: number
  openByDefault: boolean
  selected: string | null
  onSelect: (encoded: string) => void
  onContext: (share: string, path: string, at: { x: number; y: number }) => void
}) {
  const { t } = useI18n()
  const [open, setOpen] = useState(openByDefault)
  const encoded = encodeLocation(share, path)
  const isSelected = selected === encoded

  // Nothing is asked for until the branch is opened, and then it is asked for
  // once — the same listing the pane beside it is showing, under the same key,
  // so opening a folder that is already displayed costs no request at all.
  const listing = useQuery<DirectoryListing>({
    queryKey: ['directory', share, path],
    queryFn: () => api.listDirectory(share, path),
    enabled: open,
  })

  const folders = (listing.data?.entries ?? []).filter((entry) => entry.is_directory)

  return (
    <li>
      <button
        type="button"
        className={isSelected ? 'tree__item tree__item--active' : 'tree__item'}
        style={{ paddingLeft: depth * 14 + 6 }}
        aria-current={isSelected ? 'page' : undefined}
        aria-expanded={open}
        onClick={() => {
          setOpen(true)
          onSelect(encoded)
        }}
        onContextMenu={(event) => {
          event.preventDefault()
          onSelect(encoded)
          onContext(share, path, { x: event.clientX, y: event.clientY })
        }}
      >
        <span
          className="tree__twisty"
          // The expander is not a second button: a nested one inside a button
          // is invalid, and a span with a stopped click does the same job.
          onClick={(event) => {
            event.stopPropagation()
            setOpen((value) => !value)
          }}
        >
          <Chevron open={open} />
        </span>
        <Icon type={icon} />
        <span>{label}</span>
      </button>

      {open && (
        <ul className="tree__list">
          {listing.isLoading && (
            <li className="tree__empty muted small" style={{ paddingLeft: (depth + 1) * 14 + 6 }}>
              {t('status.loading')}
            </li>
          )}
          {/* Refused, not empty. Which of the two it is decides whether
              somebody goes looking for a permissions problem. */}
          {listing.isError && (
            <li className="tree__empty muted small" style={{ paddingLeft: (depth + 1) * 14 + 6 }}>
              {t('files.unreadable')}
            </li>
          )}
          {folders.map((folder: DirectoryEntry) => (
            <Branch
              key={folder.path}
              share={share}
              path={childOf({ share, path }, folder.name)}
              label={folder.name}
              icon="folder"
              depth={depth + 1}
              openByDefault={false}
              selected={selected}
              onSelect={onSelect}
              onContext={onContext}
            />
          ))}
          {listing.isSuccess && folders.length === 0 && (
            <li className="tree__empty muted small" style={{ paddingLeft: (depth + 1) * 14 + 6 }}>
              {t('files.noFolders')}
            </li>
          )}
        </ul>
      )}
    </li>
  )
}
