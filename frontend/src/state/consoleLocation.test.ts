/**
 * Reading back a position that may not be ours.
 *
 * sessionStorage holds a string a person can edit, it survives a sign-out into
 * a different session in the same tab, and the same browser can be pointed at
 * another file server entirely. So the read path decides what happens when the
 * stored value is not what was written — and that is behaviour no screen shows.
 *
 * The failure worth guarding is the quiet one: not a crash, but landing
 * somewhere that looks plausible and is wrong.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  forgetConsoleLocation,
  readConsoleLocation,
  writeConsoleLocation,
} from './consoleLocation'

const KEY = 'samfscon.console'

let entries: Map<string, string>

beforeEach(() => {
  entries = new Map()
  ;(globalThis as { sessionStorage?: unknown }).sessionStorage = {
    getItem: (k: string) => entries.get(k) ?? null,
    setItem: (k: string, v: string) => void entries.set(k, v),
    removeItem: (k: string) => void entries.delete(k),
  }
})

const DEFAULT = { snapin: 'shares', selected: null, search: '' }

describe('with nothing stored', () => {
  it('opens at the share list', () => {
    expect(readConsoleLocation()).toEqual(DEFAULT)
  })
})

describe('a round trip', () => {
  it('comes back unchanged', () => {
    writeConsoleLocation({ snapin: 'sessions', selected: 'projects', search: 'admin' })
    expect(readConsoleLocation()).toEqual({
      snapin: 'sessions',
      selected: 'projects',
      search: 'admin',
    })
  })
})

describe('a value that is not what we wrote', () => {
  it.each([
    ['not JSON', '{'],
    ['not an object', '"shares"'],
    ['null', 'null'],
    ['an empty object', '{}'],
  ])('falls back rather than failing, given %s', (_name, raw) => {
    entries.set(KEY, raw)
    expect(readConsoleLocation()).toEqual(DEFAULT)
  })

  it('refuses a console that does not exist', () => {
    entries.set(KEY, JSON.stringify({ snapin: 'gpo', selected: 'x' }))
    expect(readConsoleLocation()).toEqual(DEFAULT)
  })

  it('refuses a console that exists but is not built yet', () => {
    // Restoring one would land somebody on a placeholder they never chose,
    // which reads as the console having lost their work.
    entries.set(KEY, JSON.stringify({ snapin: 'config', selected: null }))
    expect(readConsoleLocation()).toEqual(DEFAULT)
  })

  it('drops the selection when the console is refused', () => {
    // Not merely tidiness: a share name carried into a different console names
    // nothing there, and the pane would ask the server for it anyway.
    entries.set(KEY, JSON.stringify({ snapin: 'nonsense', selected: 'projects' }))
    expect(readConsoleLocation().selected).toBeNull()
  })

  it.each([
    ['a number', 42],
    ['an object', { name: 'projects' }],
    ['the empty string', ''],
  ])('treats %s as no selection', (_name, value) => {
    entries.set(KEY, JSON.stringify({ snapin: 'shares', selected: value }))
    expect(readConsoleLocation().selected).toBeNull()
  })

  it('caps a hand-edited selection instead of carrying it into a query key', () => {
    entries.set(KEY, JSON.stringify({ snapin: 'shares', selected: 'x'.repeat(50_000) }))
    expect(readConsoleLocation().selected).toHaveLength(4096)
  })

  it('caps a hand-edited search the same way', () => {
    entries.set(KEY, JSON.stringify({ snapin: 'shares', search: 'y'.repeat(50_000) }))
    expect(readConsoleLocation().search).toHaveLength(256)
  })
})

describe('forgetting', () => {
  it('leaves nothing behind', () => {
    writeConsoleLocation({ snapin: 'sessions', selected: 'projects', search: '' })
    forgetConsoleLocation()

    expect(entries.has(KEY)).toBe(false)
    expect(readConsoleLocation()).toEqual(DEFAULT)
  })
})

describe('a browser that refuses to store anything', () => {
  it('does not fail to open the console', () => {
    ;(globalThis as { sessionStorage?: unknown }).sessionStorage = {
      getItem: () => {
        throw new Error('locked down')
      },
      setItem: () => {
        throw new Error('locked down')
      },
      removeItem: () => {
        throw new Error('locked down')
      },
    }

    expect(readConsoleLocation()).toEqual(DEFAULT)
    expect(() => writeConsoleLocation(DEFAULT as never)).not.toThrow()
    expect(() => forgetConsoleLocation()).not.toThrow()
    vi.restoreAllMocks()
  })
})
