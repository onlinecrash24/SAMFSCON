/**
 * The consoles SAMFSCON offers, as MMC presents them: each snap-in is a root of
 * the navigation tree rather than a separate page.
 *
 * The ones that are not built yet are listed on purpose. An administrator
 * coming from the Windows Computer Management console looks for "Shared
 * Folders" and "Sessions" in this tree; finding them greyed out with a note is
 * far less confusing than finding nothing and wondering whether they are hidden
 * somewhere.
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
}

export const SNAPINS: Snapin[] = [
  {
    id: 'shares',
    label: 'snapin.shares',
    icon: 'share',
    available: true,
    note: 'snapin.shares.note',
  },
  {
    id: 'sessions',
    label: 'snapin.sessions',
    icon: 'session',
    available: true,
    note: 'snapin.sessions.note',
  },
  {
    id: 'files',
    label: 'snapin.files',
    icon: 'folder',
    available: false,
    note: 'snapin.files.note',
  },
  {
    id: 'accounts',
    label: 'snapin.accounts',
    icon: 'user',
    available: true,
    note: 'snapin.accounts.note',
    standaloneOnly: true,
  },
  {
    id: 'diagnostics',
    label: 'snapin.diagnostics',
    icon: 'diagnostics',
    available: false,
    note: 'snapin.diagnostics.note',
  },
  {
    id: 'config',
    label: 'snapin.config',
    icon: 'container',
    available: false,
    note: 'snapin.config.note',
  },
]

export const DEFAULT_SNAPIN: SnapinId = 'shares'
