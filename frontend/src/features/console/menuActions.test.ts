/**
 * What a right-click offers, and what it must never offer.
 *
 * The interesting failures here are not crashes. They are a menu entry that
 * exists for something the row cannot do: a Delete on a share written into the
 * server's text smb.conf, which fails on the wire; a Close on a handle that
 * has no id to name it by. Both look fine until somebody presses them, and both
 * are decided by a pure function that can be checked here rather than found
 * against a live server.
 */

import { describe, expect, it } from 'vitest'

import type { LocalAccount, LocalGroup, OpenFile, ServerSession, Share } from '../../api/types'
import type { MenuNode } from '../../components/ContextMenu'
import {
  localGroupMenu,
  localUserMenu,
  openFileMenu,
  sessionMenu,
  shareMenu,
} from './menuActions'

function ids(nodes: MenuNode[]): string[] {
  return nodes.filter((node): node is Exclude<MenuNode, 'separator'> => node !== 'separator')
    .map((node) => node.id)
}

const share = (over: Partial<Share> = {}): Share =>
  ({
    name: 'projects',
    path: '/tank/projects',
    comment: null,
    editable: true,
    options: { known: {}, unknown: {} },
    vfs: [],
    current_users: 0,
    ...over,
  }) as Share

const account = (over: Partial<LocalAccount> = {}): LocalAccount =>
  ({ name: 'anna', disabled: false, locked_out: false, protected: false, ...over }) as LocalAccount

const WRITE = { canWrite: true, filesAvailable: false }

// ---------------------------------------------------------------------------
// Shares
// ---------------------------------------------------------------------------

describe('a share', () => {
  it('can always be looked at', () => {
    for (const s of [share(), share({ editable: false })]) {
      for (const write of [true, false]) {
        expect(ids(shareMenu(s, { canWrite: write, filesAvailable: false }))).toContain(
          'share.properties',
        )
      }
    }
  })

  it('offers deletion only when it is this console that configures it', () => {
    // A share from the text smb.conf is readable and not changeable. Offering
    // Delete produces a menu item whose whole behaviour is to fail.
    expect(ids(shareMenu(share({ editable: false }), WRITE))).not.toContain('share.delete')
    expect(ids(shareMenu(share(), WRITE))).toContain('share.delete')
  })

  it('offers nothing that writes when the account may not write', () => {
    const offered = ids(shareMenu(share(), { canWrite: false, filesAvailable: true }))
    expect(offered).not.toContain('share.delete')
    expect(offered).not.toContain('share.new')
  })

  it('offers the folder only when there is a console to open it in', () => {
    expect(ids(shareMenu(share(), { canWrite: true, filesAvailable: false }))).not.toContain(
      'share.open',
    )
    expect(ids(shareMenu(share(), { canWrite: true, filesAvailable: true }))).toContain(
      'share.open',
    )
  })
})

// ---------------------------------------------------------------------------
// Sessions and open files
// ---------------------------------------------------------------------------

describe('a session', () => {
  it('is never offered a disconnect, because there is no call for one', () => {
    const offered = ids(sessionMenu({ user: 'anna' } as ServerSession))
    expect(offered.some((id) => id.includes('disconnect') || id.includes('close'))).toBe(false)
  })

  it('offers its files only when it knows whose they are', () => {
    expect(ids(sessionMenu({ user: 'anna' } as ServerSession))).toContain('session.files')
    expect(ids(sessionMenu({ user: null } as ServerSession))).not.toContain('session.files')
  })
})

describe('an open file', () => {
  it('can be closed when the server gave it an id', () => {
    expect(ids(openFileMenu({ id: 42 } as OpenFile))).toContain('file.close')
  })

  it('cannot be closed when it has no id to name it by', () => {
    expect(ids(openFileMenu({ id: null } as OpenFile))).not.toContain('file.close')
  })
})

// ---------------------------------------------------------------------------
// Local accounts
// ---------------------------------------------------------------------------

describe('a local account', () => {
  it('is never offered an unlock', () => {
    // locked_out is reported and no endpoint acts on it. An entry here would
    // be a promise the API cannot keep.
    const offered = ids(localUserMenu(account({ locked_out: true }), { canWrite: true }))
    expect(offered.some((id) => id.includes('unlock'))).toBe(false)
  })

  it('is offered the switch that changes its state, never the one it is in', () => {
    expect(ids(localUserMenu(account({ disabled: false }), { canWrite: true }))).toContain(
      'account.disable',
    )
    expect(ids(localUserMenu(account({ disabled: true }), { canWrite: true }))).toContain(
      'account.enable',
    )
    expect(ids(localUserMenu(account({ disabled: true }), { canWrite: true }))).not.toContain(
      'account.disable',
    )
  })

  it("does not offer to delete one the server owns", () => {
    expect(ids(localUserMenu(account({ protected: true }), { canWrite: true }))).not.toContain(
      'account.delete',
    )
  })

  it('keeps only reading when the account may not write', () => {
    expect(ids(localUserMenu(account(), { canWrite: false }))).toEqual([
      'refresh',
      'account.properties',
    ])
  })
})

describe('a local group', () => {
  it('offers reading and nothing else, because nothing else is wired', () => {
    expect(ids(localGroupMenu({ name: 'backup' } as LocalGroup))).toEqual([
      'refresh',
      'group.properties',
    ])
  })
})

// ---------------------------------------------------------------------------
// The shape of the menu itself
// ---------------------------------------------------------------------------

describe('separators', () => {
  const every = [
    shareMenu(share({ editable: false }), { canWrite: false, filesAvailable: false }),
    shareMenu(share(), { canWrite: true, filesAvailable: true }),
    sessionMenu({ user: null } as ServerSession),
    openFileMenu({ id: null } as OpenFile),
    localUserMenu(account(), { canWrite: false }),
    localUserMenu(account(), { canWrite: true }),
    localGroupMenu({ name: 'backup' } as LocalGroup),
  ]

  it('never open a menu, close one, or appear twice running', () => {
    // Every one of these happens the moment the entries between two rules are
    // the ones a read-only row loses, which is the ordinary case rather than
    // an edge one.
    for (const nodes of every) {
      expect(nodes[0]).not.toBe('separator')
      expect(nodes[nodes.length - 1]).not.toBe('separator')
      for (let i = 1; i < nodes.length; i += 1) {
        expect(nodes[i] === 'separator' && nodes[i - 1] === 'separator').toBe(false)
      }
    }
  })

  it('leave every menu with something in it', () => {
    for (const nodes of every) expect(ids(nodes).length).toBeGreaterThan(0)
  })
})
