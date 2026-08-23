/**
 * Where the file console is, as one string.
 *
 * Every other console selects one thing with one name. This one selects a
 * folder, which is a share *and* a path inside it — and the remembered
 * position has a single field, on purpose: it only ever means anything
 * alongside the console it belongs to, and one field per console would be
 * storing where somebody had been in consoles they are not returning to.
 *
 * So the two are joined, and the separator is NUL. A share name may contain
 * almost anything a file system tolerates, and a path certainly contains
 * slashes; the one character neither can hold is the one worth using. It never
 * reaches a screen — this string is written to sessionStorage and read back,
 * and nothing else.
 *
 * Reading is total: anything that is not a location this wrote comes back as
 * "no folder", because the value survives a sign-out into a session pointed at
 * a different server, where a share name either matches nothing or matches
 * something else.
 */

// Written as an escape rather than as the byte: a raw control character in a
// source file is a thing editors, diffs and grep quietly mangle.
const SEPARATOR = '\u0000'

export interface FileLocation {
  share: string
  /** Relative to the share root. Empty is the root itself. */
  path: string
}

export function encodeLocation(share: string, path = ''): string {
  return path ? `${share}${SEPARATOR}${path}` : share
}

export function decodeLocation(value: string | null): FileLocation | null {
  if (!value) return null

  const at = value.indexOf(SEPARATOR)
  const share = at === -1 ? value : value.slice(0, at)
  if (!share) return null

  // Only the first separator splits. A second cannot occur in anything this
  // wrote; if one is there the value is not ours, and the path goes to the
  // server, which is the thing that decides whether it exists.
  const path = at === -1 ? '' : value.slice(at + 1)
  return { share, path }
}

/** The folder one level up, or null at the share root. */
export function parentOf(location: FileLocation): FileLocation | null {
  if (!location.path) return null
  const at = location.path.lastIndexOf('/')
  return { share: location.share, path: at === -1 ? '' : location.path.slice(0, at) }
}

/** The path of a child, without inventing a leading slash at the root. */
export function childOf(location: FileLocation, name: string): string {
  return location.path ? `${location.path}/${name}` : name
}

/** What a pane header shows: the share, then the path as people write it. */
export function displayPath(location: FileLocation): string {
  return location.path ? `${location.share}/${location.path}` : location.share
}
