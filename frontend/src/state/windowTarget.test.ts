/**
 * What makes two windows the same window.
 *
 * `keyOf` is the whole of that decision, and the only part of the window layer
 * that can be checked without a browser — everything else is geometry, pointer
 * capture and stacking, which in a stand-in DOM would only be asserting against
 * the stand-in.
 *
 * Getting it wrong goes in two directions and both are quiet. Too strict and a
 * second window opens on the share that is already open, so two sheets edit the
 * same options and the last save wins. Too loose and a window is brought
 * forward when a different object was asked for — the person clicked a group
 * and is looking at a user.
 */

import { describe, expect, it } from 'vitest'

import { keyOf, type WindowTarget } from './windows'

const share = (name: string): WindowTarget => ({ kind: 'share', name })
const user = (name: string): WindowTarget => ({ kind: 'account', of: 'user', name })
const group = (name: string): WindowTarget => ({ kind: 'account', of: 'group', name })
const folder = (s: string, path: string): WindowTarget => ({ kind: 'folder', share: s, path })

describe('the same thing', () => {
  it('is the same key', () => {
    expect(keyOf(share('projects'))).toBe(keyOf(share('projects')))
  })

  it('however it was capitalised', () => {
    // SMB does not distinguish them and neither does the server, so two
    // windows for Projects and projects would be two views of one share.
    expect(keyOf(share('Projects'))).toBe(keyOf(share('projects')))
    expect(keyOf(user('Administrator'))).toBe(keyOf(user('administrator')))
  })
})

describe('different things', () => {
  it('are different keys, across kinds', () => {
    const keys = [keyOf(share('backup')), keyOf(user('backup')), keyOf(folder('backup', ''))]
    expect(new Set(keys).size).toBe(3)
  })

  it('separate a user from a group of the same name', () => {
    // A server may have both, with different SIDs. They are not one object and
    // must not be one window.
    expect(keyOf(user('backup'))).not.toBe(keyOf(group('backup')))
  })

  it('separate the same path in two shares', () => {
    expect(keyOf(folder('projects', '/2026'))).not.toBe(keyOf(folder('archive', '/2026')))
  })

  it('keep a folder path case-sensitive', () => {
    // The share name is matched the way SMB matches it. The path is not: the
    // filesystem underneath is very likely case-sensitive, and two directories
    // differing only in case are two directories.
    expect(keyOf(folder('projects', '/Plans'))).not.toBe(keyOf(folder('projects', '/plans'))) //
    expect(keyOf(folder('Projects', '/plans'))).toBe(keyOf(folder('projects', '/plans')))
  })
})

describe('names that would break a flat key', () => {
  it('does not confuse a share whose name contains the separator between fields', () => {
    // The reason the parts are joined with NUL rather than a colon or a
    // slash: a share name may legally contain either, and a key built from
    // them could then be produced by two different objects.
    expect(keyOf(folder('a/b', 'c'))).not.toBe(keyOf(folder('a', 'b/c')))
    expect(keyOf(share('user:backup'))).not.toBe(keyOf(user('backup')))
  })

  it('gives every kind a key that is not empty', () => {
    for (const target of [share(''), user(''), folder('', '')]) {
      expect(keyOf(target).length).toBeGreaterThan(0)
    }
  })
})
