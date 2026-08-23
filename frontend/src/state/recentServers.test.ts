/**
 * The recent-server list, read back as the untrusted string it is.
 *
 * localStorage holds text a person can edit, it outlives a sign-out, and the
 * same browser can be pointed at a different file server tomorrow. So the read
 * path is the interesting half: what it does with a value that is not what it
 * wrote is the whole behaviour worth pinning down, and it is behaviour no
 * screen makes visible.
 *
 * Node, no DOM — so localStorage is stood up here. It is eight lines and it
 * behaves exactly like the real one for these purposes, which a mock would not
 * have to.
 */

import { beforeEach, describe, expect, it } from 'vitest'

import { forgetServer, listRecentServers, rememberServer } from './recentServers'

const KEY = 'samfscon.recentServers'

class MemoryStorage {
  private items = new Map<string, string>()
  getItem(key: string) {
    return this.items.get(key) ?? null
  }
  setItem(key: string, value: string) {
    this.items.set(key, value)
  }
  removeItem(key: string) {
    this.items.delete(key)
  }
  clear() {
    this.items.clear()
  }
}

beforeEach(() => {
  ;(globalThis as { localStorage?: unknown }).localStorage = new MemoryStorage()
})

function store(value: unknown) {
  localStorage.setItem(KEY, typeof value === 'string' ? value : JSON.stringify(value))
}

describe('reading back what may not be ours', () => {
  it('has nothing to say before anything was written', () => {
    expect(listRecentServers()).toEqual([])
  })

  it.each([
    ['not JSON at all', '{'],
    ['JSON that is not a list', '{"host":"fs1"}'],
    ['a list of the wrong thing', '["fs1","fs2"]'],
    ['null', 'null'],
  ])('treats %s as nothing rather than failing', (_name, raw) => {
    store(raw)
    expect(listRecentServers()).toEqual([])
  })

  it('keeps the entries that carry a host and drops the ones that do not', () => {
    store([
      { host: 'fs1.example.lan', mode: 'ad_member', lastUsed: 2 },
      { mode: 'standalone', lastUsed: 3 },
      { host: 42, lastUsed: 4 },
      { host: 'fs2.example.lan', mode: 'standalone', lastUsed: 1 },
    ])
    expect(listRecentServers().map((entry) => entry.host)).toEqual([
      'fs1.example.lan',
      'fs2.example.lan',
    ])
  })

  it('puts the most recently used first, whatever order it was stored in', () => {
    store([
      { host: 'old.example.lan', lastUsed: 1 },
      { host: 'new.example.lan', lastUsed: 999 },
    ])
    expect(listRecentServers().map((entry) => entry.host)).toEqual([
      'new.example.lan',
      'old.example.lan',
    ])
  })

  it('sorts an entry with no timestamp last instead of dropping it', () => {
    store([{ host: 'undated.example.lan' }, { host: 'dated.example.lan', lastUsed: 5 }])
    expect(listRecentServers().map((entry) => entry.host)).toEqual([
      'dated.example.lan',
      'undated.example.lan',
    ])
  })
})

describe('writing', () => {
  it('holds at most eight, discarding the oldest', () => {
    for (let index = 0; index < 12; index += 1) {
      rememberServer({ host: `fs${index}.example.lan`, mode: 'standalone' })
    }
    const kept = listRecentServers()
    expect(kept).toHaveLength(8)
    // The newest at the front, and the four oldest gone.
    expect(kept.map((entry) => entry.host)).toEqual([
      'fs11.example.lan',
      'fs10.example.lan',
      'fs9.example.lan',
      'fs8.example.lan',
      'fs7.example.lan',
      'fs6.example.lan',
      'fs5.example.lan',
      'fs4.example.lan',
    ])
  })

  it('moves a host to the front instead of listing it twice', () => {
    rememberServer({ host: 'fs1.example.lan', mode: 'standalone' })
    rememberServer({ host: 'fs2.example.lan', mode: 'standalone' })
    rememberServer({ host: 'fs1.example.lan', mode: 'ad_member' })

    const kept = listRecentServers()
    expect(kept).toHaveLength(2)
    expect(kept[0]).toMatchObject({ host: 'fs1.example.lan', mode: 'ad_member' })
  })

  it('matches a host without regard to case, the way a host name works', () => {
    rememberServer({ host: 'FS1.example.lan', mode: 'standalone' })
    rememberServer({ host: 'fs1.EXAMPLE.lan', mode: 'ad_member' })
    expect(listRecentServers()).toHaveLength(1)

    forgetServer('Fs1.Example.Lan')
    expect(listRecentServers()).toEqual([])
  })

  it('never writes a field it was not given', () => {
    rememberServer({ host: 'fs1.example.lan', mode: 'ad_member', label: 'Datei' })
    const [entry] = JSON.parse(localStorage.getItem(KEY) as string)
    // The point of the list, restated as an assertion: it remembers where to
    // go, never how to get in.
    expect(Object.keys(entry).sort()).toEqual(['host', 'label', 'lastUsed', 'mode'])
  })
})

describe('a browser that refuses to store anything', () => {
  it('does not fail a sign-in over it', () => {
    ;(globalThis as { localStorage?: unknown }).localStorage = {
      getItem() {
        throw new Error('private browsing')
      },
      setItem() {
        throw new Error('private browsing')
      },
    }
    expect(() => rememberServer({ host: 'fs1.example.lan', mode: 'standalone' })).not.toThrow()
    expect(listRecentServers()).toEqual([])
  })
})
