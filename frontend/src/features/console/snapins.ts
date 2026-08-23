/**
 * The consoles SAMFSCON offers, as a strip across the top.
 *
 * The ones that are not built yet are listed on purpose. An administrator
 * coming from the Windows Computer Management console looks for "Shared
 * Folders" and "Sessions"; finding them in the strip with a note saying what
 * is not there yet is far less confusing than finding nothing and wondering
 * whether they are hidden somewhere.
 *
 * `standaloneOnly` is the other reason an entry can be inactive, and it is not
 * a gap to be filled later: a domain member's accounts live in the domain, and
 * a console that offered to edit them here would be offering something it
 * cannot do.
 */

import type { MessageKey } from '../../i18n/messages'

export type SnapinId =
  | 'shares'
  | 'sessions'
  | 'files'
  | 'accounts'
  | 'diagnostics'
  | 'config'

/** Which of the three panes a console has anything to put in. */
export interface Panes {
  tree: boolean
  detail: boolean
}

export interface Snapin {
  id: SnapinId
  label: MessageKey
  /** Icon type from the shared icon set. */
  icon: string
  available: boolean
  /** Shown under the heading, whether the snap-in is built or not. */
  note?: MessageKey
  /** Only meaningful on a server that owns its own accounts. */
  standaloneOnly?: boolean
  /**
   * What this console does with the three-pane layout.
   *
   * Declared rather than inferred, because the alternative was one boolean
   * meaning "is this the main console?" — which cannot express that half of
   * these have no tree at all and were being handed an empty column two
   * hundred pixels wide.
   *
   * It says what the console *will* want. Whether anything exists to put
   * there is `available`, and panesFor answers with the two together.
   */
  panes: Panes
}

export const SNAPINS: Snapin[] = [
  {
    id: 'shares',
    label: 'snapin.shares',
    icon: 'share',
    available: true,
    note: 'snapin.shares.note',
    // A flat list of shares; nothing above them to draw a tree of. The detail
    // pane is the share's property sheet.
    panes: { tree: false, detail: true },
  },
  {
    id: 'sessions',
    label: 'snapin.sessions',
    icon: 'session',
    available: true,
    note: 'snapin.sessions.note',
    // Two tables, one under the other. Both are wide and neither has anything
    // to select into a third pane.
    panes: { tree: false, detail: false },
  },
  {
    id: 'files',
    label: 'snapin.files',
    icon: 'folder',
    available: false,
    note: 'snapin.files.note',
    // Share, then the folders inside it, loaded a level at a time. The
    // properties of a folder open in a window rather than a pane, because
    // comparing two of them is the whole reason anybody opens them.
    panes: { tree: true, detail: false },
  },
  {
    id: 'accounts',
    label: 'snapin.accounts',
    icon: 'user',
    available: true,
    note: 'snapin.accounts.note',
    // Users and Groups — two words, which is why this console's tree wants a
    // narrow column and the files console's wants a wide one.
    panes: { tree: true, detail: false },
    standaloneOnly: true,
  },
  {
    id: 'diagnostics',
    label: 'snapin.diagnostics',
    icon: 'diagnostics',
    available: false,
    note: 'snapin.diagnostics.note',
    // A list of findings, full width.
    panes: { tree: false, detail: false },
  },
  {
    id: 'config',
    label: 'snapin.config',
    icon: 'container',
    available: false,
    note: 'snapin.config.note',
    // One form.
    panes: { tree: false, detail: false },
  },
]

export const DEFAULT_SNAPIN: SnapinId = 'shares'

/**
 * Which panes to draw for a console.
 *
 * A console that is not built yet fills nothing, whatever it declares — its
 * placeholder is one paragraph and would look lost beside an empty tree. The
 * declaration is still worth having: it says what the console will want, so
 * the layout does not have to be re-decided on the day it is written.
 */
export function panesFor(id: SnapinId): Panes {
  const snapin = SNAPINS.find((entry) => entry.id === id)
  if (!snapin?.available) return { tree: false, detail: false }
  return snapin.panes
}

export function snapinById(id: SnapinId): Snapin | undefined {
  return SNAPINS.find((entry) => entry.id === id)
}
