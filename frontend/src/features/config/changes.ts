/**
 * What the settings form actually asks the server to change.
 *
 * Pulled out of the view so it can be tested without a browser, the way
 * `features/files/location.ts` is. Everything sharp about this screen is in
 * here: a global option lives in two places, this console reads one of them,
 * and the whole risk is the form writing a value nobody chose.
 */

import type { GlobalOptionSpec } from '../../api/types'

export interface Change {
  name: string
  value: string | null
}

/**
 * What differs between what the server holds and what the form shows.
 *
 * An emptied field becomes `null` — a deletion, restoring the server's default
 * — because smb.conf honours an empty string as a value, so "clear this field"
 * written literally would set one.
 *
 * A field the user never touched produces nothing. And a boolean the server
 * does not store produces nothing until it is clicked: an unset global is not
 * "no", and saving it as Samba's default on the first save would be the form
 * writing a decision nobody made into the server's configuration.
 *
 * A read-only option can never enter the diff, whatever the draft holds. The
 * control is disabled, but a disabled control is a statement about the DOM and
 * this is a statement about the wire.
 */
export function changedOptions(
  stored: Record<string, string>,
  draft: Record<string, string>,
  specs: GlobalOptionSpec[],
): Change[] {
  const byName = new Map(specs.map((spec) => [spec.name, spec]))
  const changes: Change[] = []

  for (const [name, shown] of Object.entries(draft)) {
    const spec = byName.get(name)
    if (spec?.safety === 'read_only') continue

    const before = stored[name] ?? null
    const after = shown === '' ? null : shown
    if (before === after) continue

    // The indeterminate checkbox, on the wire. An unstored boolean whose draft
    // is still empty has not been clicked; anything else here would be this
    // console deciding for the administrator.
    if (before === null && after === null) continue

    changes.push({ name, value: after })
  }

  return changes.sort((left, right) => left.name.localeCompare(right.name))
}

/**
 * The names that must travel in `confirm`, from the catalogue's own `safety`.
 *
 * Named one by one rather than a boolean, because the boolean a client sends
 * today would confirm an option the catalogue grows next month — which that
 * client never showed anybody.
 */
export function confirmationsFor(changed: Change[], specs: GlobalOptionSpec[]): string[] {
  const risky = new Set(
    specs.filter((spec) => spec.safety === 'risky').map((spec) => spec.name),
  )
  return changed
    .map((change) => change.name)
    .filter((name) => risky.has(name))
    .sort()
}

/** The changes as the API wants them: a plain object, deletions as null. */
export function asPayload(changed: Change[]): Record<string, string | null> {
  return Object.fromEntries(changed.map((change) => [change.name, change.value]))
}
