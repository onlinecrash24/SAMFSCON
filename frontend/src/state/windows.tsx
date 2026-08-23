/**
 * Windows that stay open, and the bar that lists them.
 *
 * The reason is comparison: looking at two shares' permissions side by side
 * means having both on screen. Every property sheet in this console lives in
 * the detail pane, of which there is one — so selecting a second share throws
 * the first away, and switching console throws it away silently.
 *
 * A window holds an identity and nothing else. Never a fetched share, never a
 * loaded descriptor: the window asks for what it needs by name, which answers
 * "what if somebody deletes it while this is open" for free — the next fetch
 * says so, rather than the window showing something that is no longer there.
 *
 * Windows are hidden when their console is not the active one, not unmounted.
 * Unmounting would discard a half-edited option list and any write already in
 * flight. The cost is that "hidden" and "closed" look the same from outside,
 * which is why the console tab carries a count.
 *
 * Nothing here is persisted. Restoring N windows means N requests that can each
 * fail, and the stored value would be a list of share names and paths — which
 * is exactly what [consoleLocation] keeps out of the places it can be read back
 * from. Positions are meaningful only against the viewport they were chosen in
 * anyway. What is remembered is one preferred size, which is most of the
 * benefit for none of the risk.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

import type { SnapinId } from '../features/console/snapins'

/**
 * What a window is showing, and enough of it to fetch again.
 *
 * A union rather than one string, because the things this console manages are
 * not identified the same way. A share has a name; a folder needs the share it
 * is in *and* a path within it; a local account needs to say whether it is a
 * user or a group, because a server may have one of each under the same name
 * and they are different objects with different SIDs.
 *
 * SAMADCON gets away with a flat `dn` because in a directory everything has
 * one. Here, flattening would mean inventing a string format and parsing it
 * back — which is a thing to get wrong on the day somebody creates a share
 * whose name contains the separator.
 */
export type WindowTarget =
  | { kind: 'share'; name: string }
  | { kind: 'account'; of: 'user' | 'group'; name: string }
  | { kind: 'folder'; share: string; path: string }

export type WindowKind = WindowTarget['kind']

/**
 * What makes two windows the same window.
 *
 * Opening a share that is already open means the person lost track of the
 * first one, so it comes forward instead of a duplicate appearing that they
 * then have to close twice. Which requires deciding what "already open" means,
 * and that decision is this function.
 *
 * The separator is NUL because a share name may contain almost anything a
 * filesystem tolerates — a colon, a slash, a space — and the one character it
 * cannot contain is the one worth using. It never reaches a screen; this string
 * is only ever compared with another one.
 */
export function keyOf(target: WindowTarget): string {
  switch (target.kind) {
    case 'share':
      return `share\0${target.name.toLowerCase()}`
    // A user and a group may share a name. They are not the same window.
    case 'account':
      return `account\0${target.of}\0${target.name.toLowerCase()}`
    case 'folder':
      // The share is case-insensitive the way SMB treats it; the path is not,
      // because the filesystem underneath may well not be.
      return `folder\0${target.share.toLowerCase()}\0${target.path}`
  }
}

export interface ConsoleWindow {
  id: string
  /** Which console owns it. Windows of other consoles are hidden, not closed. */
  snapin: SnapinId
  target: WindowTarget
  /** keyOf(target), kept alongside so the lookup is a comparison. */
  key: string
  title: string
  x: number
  y: number
  w: number
  h: number
  z: number
  minimised: boolean
  maximised: boolean
}

export interface OpenSpec {
  snapin: SnapinId
  target: WindowTarget
  title: string
}

interface WindowApi {
  windows: ConsoleWindow[]
  open: (spec: OpenSpec) => void
  close: (id: string) => void
  focus: (id: string) => void
  toggleMinimised: (id: string) => void
  toggleMaximised: (id: string) => void
  move: (id: string, at: { x: number; y: number }) => void
  resize: (id: string, size: { w: number; h: number }) => void
  /** What it is showing changed under us — a rename started from the window. */
  retarget: (id: string, target: WindowTarget, title: string) => void
}

const WindowContext = createContext<WindowApi | null>(null)

const SIZE_KEY = 'samfscon.windowSize'
const DEFAULT_SIZE = { w: 900, h: 620 }
export const MIN_SIZE = { w: 380, h: 260 }

function preferredSize(): { w: number; h: number } {
  try {
    const raw = localStorage.getItem(SIZE_KEY)
    if (!raw) return DEFAULT_SIZE
    const stored: unknown = JSON.parse(raw)
    if (typeof stored !== 'object' || stored === null) return DEFAULT_SIZE
    const { w, h } = stored as Record<string, unknown>
    if (typeof w !== 'number' || typeof h !== 'number') return DEFAULT_SIZE
    if (!Number.isFinite(w) || !Number.isFinite(h)) return DEFAULT_SIZE
    return { w: Math.max(MIN_SIZE.w, w), h: Math.max(MIN_SIZE.h, h) }
  } catch {
    return DEFAULT_SIZE
  }
}

function rememberSize(size: { w: number; h: number }): void {
  try {
    localStorage.setItem(SIZE_KEY, JSON.stringify(size))
  } catch {
    // A preference, never the thing that breaks.
  }
}

export function WindowProvider({ children }: { children: ReactNode }) {
  const [windows, setWindows] = useState<ConsoleWindow[]>([])
  // Local to the window layer's own stacking context, so a window can never
  // climb into the band the dialogs use.
  const nextZ = useRef(1)

  const focus = useCallback((id: string) => {
    setWindows((current) =>
      current.map((window) =>
        window.id === id ? { ...window, z: ++nextZ.current, minimised: false } : window,
      ),
    )
  }, [])

  const open = useCallback((spec: OpenSpec) => {
    setWindows((current) => {
      const key = keyOf(spec.target)
      const existing = current.find((window) => window.key === key)
      if (existing) {
        return current.map((window) =>
          window.id === existing.id ? { ...window, z: ++nextZ.current, minimised: false } : window,
        )
      }

      const size = preferredSize()
      // Cascaded, so a second window does not land exactly on the first.
      const step = (current.length % 8) * 24
      return [
        ...current,
        {
          id: crypto.randomUUID(),
          snapin: spec.snapin,
          target: spec.target,
          key,
          title: spec.title,
          x: 60 + step,
          y: 48 + step,
          w: size.w,
          h: size.h,
          z: ++nextZ.current,
          minimised: false,
          maximised: false,
        },
      ]
    })
  }, [])

  const close = useCallback((id: string) => {
    setWindows((current) => {
      const remaining = current.filter((window) => window.id !== id)
      if (remaining.length === 0) nextZ.current = 1
      return remaining
    })
  }, [])

  const update = useCallback((id: string, change: (window: ConsoleWindow) => ConsoleWindow) => {
    setWindows((current) => current.map((window) => (window.id === id ? change(window) : window)))
  }, [])

  const api = useMemo<WindowApi>(
    () => ({
      windows,
      open,
      close,
      focus,
      toggleMinimised: (id) => update(id, (w) => ({ ...w, minimised: !w.minimised })),
      toggleMaximised: (id) => update(id, (w) => ({ ...w, maximised: !w.maximised })),
      move: (id, at) => update(id, (w) => ({ ...w, x: at.x, y: at.y })),
      resize: (id, size) => {
        update(id, (w) => ({ ...w, w: size.w, h: size.h }))
        rememberSize(size)
      },
      retarget: (id, target, title) =>
        update(id, (w) => ({ ...w, target, key: keyOf(target), title })),
    }),
    [windows, open, close, focus, update],
  )

  return <WindowContext.Provider value={api}>{children}</WindowContext.Provider>
}

export function useWindows(): WindowApi {
  const api = useContext(WindowContext)
  if (!api) throw new Error('useWindows outside WindowProvider')
  return api
}
