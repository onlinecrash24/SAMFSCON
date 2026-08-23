/**
 * A share and a path, packed into the one field the remembered position has.
 *
 * Worth its own test for the same reason keyOf is: it is a small decision that
 * fails quietly. Split on the wrong character and a share called `data/2026`
 * becomes a share called `data` in a folder called `2026`, which exists on
 * plenty of servers — so the console would open something real and wrong,
 * rather than failing.
 */

import { describe, expect, it } from 'vitest'

import {
  childOf,
  decodeLocation,
  displayPath,
  encodeLocation,
  parentOf,
} from './location'

describe('a round trip', () => {
  it.each([
    ['a share root', 'projects', ''],
    ['one level down', 'projects', '2026'],
    ['several levels down', 'projects', '2026/plans/draft'],
    ['a share name with a slash in it', 'data/2026', 'q1'],
    ['a path with a space', 'projects', 'old plans'],
    ['a share name with a colon', 'user:backup', 'anna'],
  ])('survives %s', (_name, share, path) => {
    expect(decodeLocation(encodeLocation(share, path))).toEqual({ share, path })
  })

  it('does not mistake a slash in the share for the start of the path', () => {
    // The failure this separator exists to prevent. Both of these are real
    // shapes a server can have, and a `/` split would confuse them.
    expect(decodeLocation(encodeLocation('data/2026', 'q1'))).toEqual({
      share: 'data/2026',
      path: 'q1',
    })
    expect(decodeLocation(encodeLocation('data', '2026/q1'))).toEqual({
      share: 'data',
      path: '2026/q1',
    })
  })
})

describe('reading something we did not write', () => {
  it.each([
    ['nothing', null],
    ['the empty string', ''],
  ])('is no folder, given %s', (_name, value) => {
    expect(decodeLocation(value)).toBeNull()
  })

  it('is no folder when there is no share name in front', () => {
    expect(decodeLocation('\u0000projects')).toBeNull()
  })

  it('takes a bare name as a share at its root', () => {
    // What every other console stores looks like this, and landing on the
    // share root is a sane reading of it.
    expect(decodeLocation('projects')).toEqual({ share: 'projects', path: '' })
  })
})

describe('moving about', () => {
  it('goes up one level at a time', () => {
    const deep = { share: 'projects', path: '2026/plans/draft' }
    expect(parentOf(deep)).toEqual({ share: 'projects', path: '2026/plans' })
    expect(parentOf({ share: 'projects', path: '2026' })).toEqual({
      share: 'projects',
      path: '',
    })
  })

  it('stops at the share root rather than leaving the share', () => {
    expect(parentOf({ share: 'projects', path: '' })).toBeNull()
  })

  it('does not put a slash in front of a child of the root', () => {
    // An absolute-looking path is a different path to the server, and the
    // listing would come back empty with nothing to say why.
    expect(childOf({ share: 'projects', path: '' }, '2026')).toBe('2026')
    expect(childOf({ share: 'projects', path: '2026' }, 'q1')).toBe('2026/q1')
  })
})

describe('what a header shows', () => {
  it('is the share alone at its root', () => {
    expect(displayPath({ share: 'projects', path: '' })).toBe('projects')
  })

  it('reads like a path people write', () => {
    expect(displayPath({ share: 'projects', path: '2026/q1' })).toBe('projects/2026/q1')
  })
})
