/**
 * Which refusals the interface may offer a button for.
 *
 * Two families come back from a settings write and they must not be drawn
 * the same way. A 400 is a value to fix: no dialog helps, and one that
 * offered to proceed anyway would be offering a button that always fails.
 * A 409 carrying `confirm_with` is a check that could not run — nothing is
 * wrong with the request, and the only way past it is somebody saying so.
 *
 * Read off the status and the token rather than off a list of codes, so a
 * check added to the backend next month is offered here without a line
 * changing. A list would have to be kept in step by whoever remembered.
 */

import { ApiError } from '../../api/client'

export interface Acceptable {
  /** What has to travel back in `confirm` for the write to proceed. */
  token: string
  message: string
  hint?: string
  /** The entries that could not be resolved, when the refusal names any. */
  entries: string[]
}

export function acceptableRefusal(error: unknown): Acceptable | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null

  // The token, and not merely the status. `confirmation_required` is a 409
  // too and carries none: the form already sends the risky names it showed,
  // so reaching it means something is out of step, and a button labelled
  // "anyway" that sent nothing new would loop.
  const token = error.context?.confirm_with
  if (typeof token !== 'string' || token === '') return null

  const entries = error.context?.undecidable_entries
  return {
    token,
    message: error.message,
    hint: error.hint,
    entries: Array.isArray(entries) ? entries.map(String) : [],
  }
}
