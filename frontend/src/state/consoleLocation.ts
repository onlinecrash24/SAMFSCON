/**
 * Where in the console this tab was, so that F5 returns to it.
 *
 * A console is not a page you re-enter from the front door. Refreshing drops
 * whoever pressed it back onto the share list with nothing selected, however
 * deep into a share's permissions they had been.
 *
 * sessionStorage rather than the URL. A hash would also survive F5 and would
 * make positions shareable, which this does not — and it would put share names
 * into the address bar, the browser history and every screenshot. Nobody asked
 * for shareable links. sessionStorage is also per tab, so two tabs on two
 * different servers do not overwrite each other, which localStorage would.
 *
 * Everything read back is treated as untrusted. It is a string a person can
 * edit, and it survives a sign-out into a different session in the same tab —
 * the same browser can be pointed at another file server entirely. So a
 * remembered name is a *hint*: the console asks the server for it and shows
 * what comes back, including "there is no such share". It is never treated as
 * proof that the thing exists.
 */

import { SNAPINS, type SnapinId } from '../features/console/snapins'

const STORAGE_KEY = 'samfscon.console'

// The search box is free text and lands in a query key. A stored value is not
// worth more than a sane line of it.
const MAX_SEARCH = 256

// A share name is capped by the API at 80 characters and a path at 4096. What
// is stored here is only ever one of those two, and the cap exists so that a
// hand-edited entry cannot put a megabyte into a query key.
const MAX_SELECTED = 4096

export interface ConsoleLocation {
  snapin: SnapinId
  /**
   * What was selected in that console, in whatever way that console names
   * things — a share name, an account name, a path.
   *
   * Deliberately one field rather than one per console. It only ever means
   * something in the company of `snapin`, and storing the others would be
   * storing where somebody had been in consoles they are not returning to.
   */
  selected: string | null
  search: string
}

const FALLBACK: ConsoleLocation = { snapin: 'shares', selected: null, search: '' }

function knownSnapin(value: unknown): SnapinId | null {
  // Availability is checked, not just existence: a console switched off since
  // this tab was last open would land on a placeholder nobody navigated to.
  const found = SNAPINS.find((snapin) => snapin.id === value && snapin.available)
  return found ? found.id : null
}

function text(value: unknown, limit: number): string | null {
  if (typeof value !== 'string' || value.length === 0) return null
  return value.slice(0, limit)
}

export function readConsoleLocation(): ConsoleLocation {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return FALLBACK

    const stored: unknown = JSON.parse(raw)
    if (typeof stored !== 'object' || stored === null) return FALLBACK
    const value = stored as Record<string, unknown>

    const snapin = knownSnapin(value.snapin)
    if (snapin === null) return FALLBACK

    return {
      snapin,
      // Only alongside the console it belongs to. A share name restored into
      // the accounts console names nothing there.
      selected: text(value.selected, MAX_SELECTED),
      search: text(value.search, MAX_SEARCH) ?? '',
    }
  } catch {
    // Corrupt, or storage unavailable in a locked-down browser. Neither is a
    // reason to fail to open the console.
    return FALLBACK
  }
}

export function writeConsoleLocation(location: ConsoleLocation): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(location))
  } catch {
    // Private browsing, or a full quota. Remembering the position is a
    // convenience and must never be the thing that breaks.
  }
}

/**
 * Forget it.
 *
 * Called at both ends of a session. On sign-out, because leaving the previous
 * person's share and account names in a shared browser is not what that
 * gesture means. And on sign-in, because signing in is a beginning — and
 * because the next sign-in may be to a different server, where a remembered
 * share name either matches nothing or, worse, matches something else.
 *
 * Sign-out alone is not enough, and the reason is easy to miss: an expired
 * session never passes through sign-out, so the position would outlive the
 * session that chose it and somebody would be dropped into whichever console
 * they had last opened, days earlier, on another machine.
 *
 * A refresh is untouched. It reaches neither end — the session probe restores
 * the session — so F5 still lands where it left off, which is the whole reason
 * any of this is stored.
 */
export function forgetConsoleLocation(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // Nothing to do: if it cannot be removed it was never written either.
  }
}
