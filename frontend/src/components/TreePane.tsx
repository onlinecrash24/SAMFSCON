/**
 * The navigation pane, which now belongs to whichever console is open.
 *
 * It used to hold the list of consoles — six buttons that never change, in the
 * column a tree is supposed to occupy. The consoles are a strip across the top
 * now, and this pane shows what the open console actually navigates.
 *
 * Which is not much, for most of them: a file server is a handful of lists, and
 * a list has nothing above it to draw a tree of. Those consoles declare
 * `panes.tree: false` and the shell never renders this at all. What is left is
 * the two that do have a hierarchy — local accounts, which divide into users
 * and groups, and the folder tree inside a share, which is not built yet.
 *
 * The server heading stays regardless. It is the one place that says which
 * machine is being changed, and on a screen with six consoles and several open
 * windows that is worth a permanent line rather than a memory.
 */

import type { ServerSummary } from '../api/types'
import type { SnapinId } from '../features/console/snapins'
import { useI18n } from '../i18n'
import type { MessageKey } from '../i18n/messages'
import { Icon } from './primitives'

/** A branch of whatever the open console navigates. */
export interface TreeBranch {
  id: string
  label: MessageKey
  icon: string
}

const BRANCHES: Partial<Record<SnapinId, TreeBranch[]>> = {
  accounts: [
    { id: 'users', label: 'accounts.users', icon: 'user' },
    { id: 'groups', label: 'accounts.groups', icon: 'group' },
  ],
}

/** What a console shows in the pane, or nothing. */
export function branchesFor(snapin: SnapinId): TreeBranch[] {
  return BRANCHES[snapin] ?? []
}

/** The branch a console opens on. */
export function firstBranch(snapin: SnapinId): string | null {
  return branchesFor(snapin)[0]?.id ?? null
}

export function TreePane({
  server,
  snapin,
  selected,
  onSelect,
}: {
  server: ServerSummary
  snapin: SnapinId
  selected: string | null
  onSelect: (id: string) => void
}) {
  const { t } = useI18n()
  const branches = branchesFor(snapin)

  return (
    <nav className="tree" aria-label={t('nav.server')}>
      <div className="tree__root">
        <Icon type="server" />
        <div className="tree__rootText">
          <strong>{server.name}</strong>
          <span className="muted small">
            {server.mode === 'ad_member' ? (server.realm ?? server.workgroup) : server.workgroup}
          </span>
        </div>
      </div>

      <ul className="tree__list">
        {branches.map((branch) => (
          <li key={branch.id}>
            <button
              type="button"
              className={
                selected === branch.id ? 'tree__item tree__item--active' : 'tree__item'
              }
              aria-current={selected === branch.id ? 'page' : undefined}
              onClick={() => onSelect(branch.id)}
            >
              <Icon type={branch.icon} />
              <span>{t(branch.label)}</span>
            </button>
          </li>
        ))}
        {branches.length === 0 && (
          // Reached only by a console that declares a tree and has nothing to
          // put in it yet — the folder tree, which arrives with its console.
          <li className="tree__empty muted small">{t('tree.nothing')}</li>
        )}
      </ul>
    </nav>
  )
}
