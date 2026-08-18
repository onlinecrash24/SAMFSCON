/**
 * The servers this browser has signed in to before.
 *
 * Kept in localStorage and nowhere else: it is a convenience for one person at
 * one machine, not shared state. **Never a credential** — not a password, not
 * a token, not a user name. A host, a mode and a label, which is exactly what
 * the sign-in form needs to fill itself in.
 *
 * The mode is worth remembering as much as the host: it is the field a
 * server that refuses unauthenticated queries makes the administrator answer
 * every time, and answering it once should be enough.
 */

import type { ServerMode } from '../api/types'

const STORAGE_KEY = 'samfscon.recentServers'
const LIMIT = 8

export interface RecentServer {
  host: string
  mode: ServerMode
  label?: string
  realm?: string | null
  lastUsed: number
}

export function listRecentServers(): RecentServer[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter((entry): entry is RecentServer => {
        return (
          typeof entry === 'object' &&
          entry !== null &&
          typeof (entry as RecentServer).host === 'string'
        )
      })
      .sort((a, b) => (b.lastUsed ?? 0) - (a.lastUsed ?? 0))
      .slice(0, LIMIT)
  } catch {
    // A corrupted entry is not worth an error message; it is a convenience.
    return []
  }
}

export function rememberServer(entry: Omit<RecentServer, 'lastUsed'>): void {
  try {
    const others = listRecentServers().filter(
      (item) => item.host.toLowerCase() !== entry.host.toLowerCase(),
    )
    const next = [{ ...entry, lastUsed: Date.now() }, ...others].slice(0, LIMIT)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // Private browsing, a full quota — neither is a reason to fail a sign-in.
  }
}

export function forgetServer(host: string): void {
  try {
    const next = listRecentServers().filter(
      (item) => item.host.toLowerCase() !== host.toLowerCase(),
    )
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // As above.
  }
}
