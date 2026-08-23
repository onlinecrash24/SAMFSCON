/**
 * Which refusals get a button, and which must not.
 *
 * Both mistakes are quiet. Offer one for a decided lockout and the person
 * clicks it, the server refuses again, and the interface has taught them that
 * this dialog does nothing. Withhold one from a check that merely could not run
 * and the field becomes unusable on every server it cannot be run against —
 * could-not-determine reported as is-so, from the interface side.
 */

import { describe, expect, it } from 'vitest'

import { ApiError } from '../../api/client'
import { acceptableRefusal } from './refusal'

function refusal(status: number, body: Record<string, unknown>): ApiError {
  return new ApiError(status, {
    code: String(body.code ?? 'x'),
    message: String(body.message ?? 'refused'),
    hint: body.hint as string | undefined,
    context: body.context as Record<string, unknown> | undefined,
  })
}

describe('what the interface may offer to push through', () => {
  it('offers the check that could not run, and carries what it could not read', () => {
    const found = acceptableRefusal(
      refusal(409, {
        code: 'hosts_allow_undecidable',
        message: 'Whether this list still admits this console could not be decided.',
        hint: 'Not the same as excluded.',
        context: {
          confirm_with: 'hosts allow:undecidable',
          undecidable_entries: ['fs1.example.lan'],
        },
      }),
    )
    expect(found).toEqual({
      token: 'hosts allow:undecidable',
      message: 'Whether this list still admits this console could not be decided.',
      hint: 'Not the same as excluded.',
      entries: ['fs1.example.lan'],
    })
  })

  it('refuses to offer anything for a decided lockout', () => {
    // 400, and it stays 400 however the message is worded: we looked, and it
    // shuts this console out. Recovery would need a shell on the server, which
    // is the need this console exists to remove.
    expect(
      acceptableRefusal(
        refusal(400, {
          code: 'hosts_allow_excludes_console',
          context: { address: '172.19.0.4' },
        }),
      ),
    ).toBeNull()
  })

  it('does not offer a button for a 409 that names no token', () => {
    // `confirmation_required` is a 409 too. The form already sends the risky
    // names it showed, so a button here would send nothing new and loop.
    expect(acceptableRefusal(refusal(409, { code: 'confirmation_required' }))).toBeNull()
  })

  it('ignores a token on the wrong family', () => {
    // The status is the family and the token is the answer; one without the
    // other is not an offer. Belt and braces against a backend that grew a
    // token onto a refusal it did not mean to make acceptable.
    expect(
      acceptableRefusal(refusal(400, { code: 'x', context: { confirm_with: 'anything' } })),
    ).toBeNull()
  })

  it('says nothing about an error that never reached the server', () => {
    expect(acceptableRefusal(new TypeError('network'))).toBeNull()
    expect(acceptableRefusal(null)).toBeNull()
  })

  it('survives a refusal whose entries are not a list', () => {
    const found = acceptableRefusal(
      refusal(409, { code: 'own_address_unknown', context: { confirm_with: 'own address:unknown' } }),
    )
    expect(found?.token).toBe('own address:unknown')
    expect(found?.entries).toEqual([])
  })
})
