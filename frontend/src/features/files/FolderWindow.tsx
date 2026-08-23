/**
 * The permissions of one folder or file, in a window.
 *
 * The same PermissionEditor a share's "file permissions" tab uses, pointed at
 * a path instead of a share root — so what an ACL looks like and how it is
 * edited is written down once, and the effective-access calculation beside it
 * is the same calculation.
 *
 * A window rather than a pane, and this is the console where that matters
 * most: the question people actually have is why a subfolder behaves
 * differently from its parent, and answering it means both on screen.
 */

import { PermissionEditor } from '../permissions/PermissionEditor'
import { Icon } from '../../components/primitives'
import { useI18n } from '../../i18n'

export function FolderWindow({
  share,
  path,
  canWrite,
  onChanged,
}: {
  share: string
  path: string
  canWrite: boolean
  onChanged: (message: string) => void
}) {
  const { t } = useI18n()
  const name = path ? (path.split('/').pop() ?? path) : share

  return (
    <div className="sheet-window">
      <div className="sheet-window__panel">
        <div className="detail__header">
          <Icon type={path ? 'folder' : 'share'} className="icon--large" />
          <div>
            <h2>{name}</h2>
            {/* The whole path, because two folders called "2026" under
                different projects are the reason somebody opened two of these. */}
            <span className="muted small mono">
              {path ? `${share}/${path}` : t('share.root', { name: share })}
            </span>
          </div>
        </div>

        <PermissionEditor
          share={share}
          path={path}
          level="file"
          canWrite={canWrite}
          onChanged={onChanged}
        />
      </div>
    </div>
  )
}
