/**
 * A share's property sheet, in a window rather than in the pane.
 *
 * The same `ShareDetail` the detail pane renders, so what a share's properties
 * *are* is written down once. It already takes a name and fetches by it, which
 * is exactly the shape a window needs — the sheet reloads itself, and a share
 * deleted from under it says so instead of showing what used to be true.
 *
 * Two of them open at once is the whole reason this exists: comparing two
 * shares' options or two shares' permissions is otherwise a matter of clicking
 * back and forth and remembering.
 */

import type { ShareGroup } from './ShareDetail'
import { ShareDetail } from './ShareDetail'

export function ShareWindow({
  name,
  canWrite,
  initialGroup,
  onChanged,
  onDelete,
}: {
  name: string
  canWrite: boolean
  initialGroup?: ShareGroup
  onChanged: (message: string) => void
  /** Asks the shell to delete it; the shell owns the confirmation. */
  onDelete: () => void
}) {
  return (
    <div className="sheet-window">
      <div className="sheet-window__panel">
        <ShareDetail
          name={name}
          canWrite={canWrite}
          initialGroup={initialGroup}
          onChanged={onChanged}
          onDelete={onDelete}
        />
      </div>
    </div>
  )
}
