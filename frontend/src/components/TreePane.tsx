/**
 * The navigation tree.
 *
 * Flatter than SAMADCON's, and for a reason that is not laziness: a directory
 * is a tree and a file server is not. What a file server has is a handful of
 * lists — shares, sessions, accounts — so the tree is a list of snap-ins, with
 * children only where there genuinely are any.
 *
 * Snap-ins that are not built yet stay in the list, greyed out with a note. An
 * administrator coming from the Windows Computer Management console looks for
 * "Shared Folders" here; finding it disabled with an explanation is far less
 * confusing than finding nothing.
 */

import { SNAPINS, type SnapinId } from '../features/console/snapins'
import { useI18n } from '../i18n'
import type { ServerSummary } from '../api/types'
import { Icon } from './primitives'

interface TreePaneProps {
  server: ServerSummary
  active: SnapinId
  onSelect: (id: SnapinId) => void
}

export function TreePane({ server, active, onSelect }: TreePaneProps) {
  const { t } = useI18n()
  const standalone = server.mode === 'standalone'

  return (
    <nav className="tree" aria-label={t('nav.server')}>
      <div className="tree__root">
        <Icon type="server" />
        <div className="tree__rootText">
          <strong>{server.name}</strong>
          <span className="muted small">
            {server.mode === 'ad_member' ? (server.realm ?? server.workgroup) : server.workgroup}
          </span>
        </div>
      </div>

      <ul className="tree__list">
        {SNAPINS.map((snapin) => {
          // Two different reasons an entry can be inactive, and they are not
          // the same thing: "not built yet" is a gap, "not applicable to this
          // server" is an answer. Both disable the row; only the first will
          // ever change.
          const notApplicable = snapin.standaloneOnly === true && !standalone
          const disabled = !snapin.available || notApplicable

          return (
            <li key={snapin.id}>
              <button
                type="button"
                className={
                  active === snapin.id ? 'tree__item tree__item--active' : 'tree__item'
                }
                aria-current={active === snapin.id ? 'page' : undefined}
                aria-disabled={disabled || undefined}
                onClick={() => onSelect(snapin.id)}
                title={
                  notApplicable
                    ? t('snapin.accounts.domainMember', {
                        domain: server.realm ?? server.workgroup ?? '',
                      })
                    : !snapin.available
                      ? t('snapin.unavailable')
                      : undefined
                }
              >
                <Icon type={snapin.icon} />
                <span>{t(snapin.label)}</span>
                {disabled && <span className="tree__badge">·</span>}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
