/**
 * What each row offers on a right-click.
 *
 * Deciding is here; doing is in the shell. The split is worth insisting on:
 * this file is a pure function of what a row *is*, so it can be checked without
 * a browser, a server or a session — and the thing worth checking is not that a
 * menu appears but that it never offers something the row cannot do.
 *
 * Two rules run through all of it.
 *
 * **Nothing is offered that no endpoint can perform.** A session cannot be
 * disconnected and an account cannot be unlocked, because there is no call for
 * either — `locked_out` is reported and nothing acts on it. A greyed-out entry
 * would be a promise for later; an absent one is the truth today.
 *
 * **What a row cannot do, it does not show.** A share defined in the server's
 * text smb.conf is readable and not changeable, so it keeps Properties and
 * loses everything that writes. The alternative is a menu of items that fail
 * one at a time.
 */

import type { LocalAccount, LocalGroup, OpenFile, ServerSession, Share } from '../../api/types'
import type { MenuNode } from '../../components/ContextMenu'

/**
 * Every action id the shell knows how to run.
 *
 * A union rather than a string, so that adding an entry to a menu without
 * teaching runAction what it means is a compile error rather than a click that
 * does nothing.
 */
export type ActionId =
  | 'refresh'
  | 'share.new'
  | 'share.open'
  | 'share.properties'
  | 'share.permissions'
  | 'share.delete'
  | 'session.files'
  | 'file.close'
  | 'account.new'
  | 'account.properties'
  | 'account.enable'
  | 'account.disable'
  | 'account.password'
  | 'account.delete'
  | 'group.properties'

const SEPARATOR: MenuNode = 'separator'

/** Drop the entries that were left out, and any separator left stranded. */
function tidy(nodes: (MenuNode | null)[]): MenuNode[] {
  const present = nodes.filter((node): node is MenuNode => node !== null)
  const out: MenuNode[] = []
  for (const node of present) {
    // No separator first, and never two in a row — both happen as soon as the
    // entries between them are the ones a read-only share loses.
    if (node === SEPARATOR && (out.length === 0 || out[out.length - 1] === SEPARATOR)) continue
    out.push(node)
  }
  while (out[out.length - 1] === SEPARATOR) out.pop()
  return out
}

export function shareMenu(
  share: Share,
  { canWrite, filesAvailable }: { canWrite: boolean; filesAvailable: boolean },
): MenuNode[] {
  // Editable is where the share is *configured*, canWrite is whether this
  // account may configure anything. Both have to hold, and they fail for
  // different reasons — which is why the row badges the first and the pane
  // banners the second.
  const writable = share.editable && canWrite

  return tidy([
    { id: 'refresh', labelKey: 'action.refresh' },
    SEPARATOR,
    canWrite ? { id: 'share.new', labelKey: 'share.new' } : null,
    filesAvailable ? { id: 'share.open', labelKey: 'action.openFolder' } : null,
    { id: 'share.permissions', labelKey: 'share.group.permissions' },
    SEPARATOR,
    writable ? { id: 'share.delete', labelKey: 'action.delete', danger: true } : null,
    SEPARATOR,
    // Always. Reading a share is the point, and a share nobody may change is
    // still a share somebody needs to look at.
    { id: 'share.properties', labelKey: 'action.properties' },
  ])
}

export function sessionMenu(session: ServerSession): MenuNode[] {
  return tidy([
    { id: 'refresh', labelKey: 'action.refresh' },
    SEPARATOR,
    // There is no call that ends a session. Offering one would be inventing an
    // ability out of a menu entry.
    session.user ? { id: 'session.files', labelKey: 'sessions.showFiles' } : null,
  ])
}

export function openFileMenu(file: OpenFile): MenuNode[] {
  return tidy([
    { id: 'refresh', labelKey: 'action.refresh' },
    SEPARATOR,
    // A handle with no id cannot be named to the server, so it cannot be
    // closed however much somebody would like to.
    file.id !== null ? { id: 'file.close', labelKey: 'sessions.close', danger: true } : null,
  ])
}

export function localUserMenu(account: LocalAccount, { canWrite }: { canWrite: boolean }): MenuNode[] {
  return tidy([
    { id: 'refresh', labelKey: 'action.refresh' },
    SEPARATOR,
    canWrite ? { id: 'account.new', labelKey: 'accounts.new' } : null,
    SEPARATOR,
    // Named for what pressing it does, not for the state the account is in. A
    // menu has nowhere to put a tick, so "Disabled" with no mark beside it
    // says nothing about which way it would go.
    canWrite
      ? account.disabled
        ? { id: 'account.enable', labelKey: 'accounts.enable' }
        : { id: 'account.disable', labelKey: 'accounts.disable' }
      : null,
    canWrite ? { id: 'account.password', labelKey: 'accounts.setPassword' } : null,
    SEPARATOR,
    // A built-in account cannot be removed, and the server would refuse it.
    canWrite && !account.protected
      ? { id: 'account.delete', labelKey: 'action.delete', danger: true }
      : null,
    SEPARATOR,
    { id: 'account.properties', labelKey: 'action.properties' },
  ])
}

export function localGroupMenu(_group: LocalGroup): MenuNode[] {
  return tidy([
    { id: 'refresh', labelKey: 'action.refresh' },
    SEPARATOR,
    // Membership is readable and not yet editable — api.setGroupMembers exists
    // and nothing calls it. Properties shows who is in it.
    { id: 'group.properties', labelKey: 'action.properties' },
  ])
}
