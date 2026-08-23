/**
 * The five ways this form could write something nobody asked for.
 *
 * Every one of them is silent: the save succeeds, the screen says "saved", and
 * the server now holds a value the administrator never chose. That is why the
 * diff is a module with tests rather than a loop inside the view.
 */

import { describe, expect, it } from 'vitest'

import { changedOptions, confirmationsFor } from './changes'
import type { GlobalOptionSpec } from '../../api/types'

function spec(over: Partial<GlobalOptionSpec> & { name: string }): GlobalOptionSpec {
  return {
    type: 'text',
    group: 'server',
    default: null,
    default_note: null,
    choices: [],
    doc: '',
    safety: 'safe',
    risk: null,
    read_only_reason: null,
    effect: 'reload',
    daemons: [],
    live_source: null,
    ...over,
  }
}

const SPECS: GlobalOptionSpec[] = [
  spec({ name: 'server string' }),
  spec({ name: 'guest ok', type: 'bool', default: 'no' }),
  spec({ name: 'hosts allow', safety: 'risky', risk: 'lockout_hosts' }),
  spec({ name: 'netbios name', safety: 'read_only', read_only_reason: 'bound_at_startup' }),
]

describe('what the form sends', () => {
  it('turns an emptied field into a deletion, not an empty string', () => {
    // smb.conf honours an empty value, so "clear this field" written literally
    // sets one — and the option then does not go back to Samba's default.
    const changes = changedOptions({ 'server string': 'Dateiserver' }, { 'server string': '' }, SPECS)
    expect(changes).toEqual([{ name: 'server string', value: null }])
  })

  it('produces nothing for a field that was rendered and not touched', () => {
    const stored = { 'server string': 'Dateiserver' }
    expect(changedOptions(stored, { 'server string': 'Dateiserver' }, SPECS)).toEqual([])
  })

  it('produces nothing for an unstored boolean until it is clicked', () => {
    // The indeterminate checkbox, on the wire. An option this server does not
    // store is not "no" — it is "not in the registry", and the text smb.conf
    // this console cannot read may well set it.
    expect(changedOptions({}, { 'guest ok': '' }, SPECS)).toEqual([])
    expect(changedOptions({}, { 'guest ok': 'no' }, SPECS)).toEqual([
      { name: 'guest ok', value: 'no' },
    ])
  })

  it('never lets a read-only option into the diff', () => {
    // The strongest of the five: the control is disabled, but that is a fact
    // about the DOM and this is a fact about the wire.
    expect(changedOptions({}, { 'netbios name': 'FS1' }, SPECS)).toEqual([])
  })

  it('leaves an option it has no catalogue entry for alone but still sends it', () => {
    // A hand-configured server is not wrong, and a change the operator made on
    // purpose must survive a save from a console that never heard of it.
    const changes = changedOptions({ 'panic action': '' }, { 'panic action': '/bin/true' }, SPECS)
    expect(changes).toEqual([{ name: 'panic action', value: '/bin/true' }])
  })
})

describe('what has to be confirmed', () => {
  it('lists a risky change and not a safe one', () => {
    const changes = changedOptions(
      {},
      { 'hosts allow': '10.0.0.0/8', 'server string': 'Dateiserver' },
      SPECS,
    )
    expect(confirmationsFor(changes, SPECS)).toEqual(['hosts allow'])
  })

  it('asks for nothing when the risky option was not changed', () => {
    const stored = { 'hosts allow': '10.0.0.0/8' }
    const changes = changedOptions(stored, { 'hosts allow': '10.0.0.0/8' }, SPECS)
    expect(confirmationsFor(changes, SPECS)).toEqual([])
  })
})
