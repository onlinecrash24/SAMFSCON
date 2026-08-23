/**
 * What stands out on this server.
 *
 * Three things sit above the list, and each is there because the list alone
 * would be read as more than it is.
 *
 * **Coverage first.** A report showing findings on four shares and nothing on
 * the other nine reads as "the other nine are fine". They are not — their
 * configuration is in the text smb.conf, which this console cannot read. The
 * count says so before anybody starts counting rows.
 *
 * **Then what nobody could look at**, in its own block. "We did not look" is
 * not a statement about the server, and mixing it into the findings would make
 * it one.
 *
 * **And the evidence is shown, not hidden behind a disclosure.** A finding
 * saying "create mask is 0777, measured against world-write" can be argued
 * with. One saying "the permissions are weak" can only be believed.
 *
 * Read-only, and that is the design rather than a stage. Everything here that
 * could be fixed is either a line in the text smb.conf, which nothing SAMFSCON
 * speaks can write, or a global option belonging to the Server settings
 * console. A button would be a promise this endpoint cannot keep.
 */

import { useQuery } from '@tanstack/react-query'

import { api } from '../../api/endpoints'
import type { Finding, FindingReport, Severity, Unreadable } from '../../api/types'
import { Badge, ErrorMessage, Spinner, useDateFormat } from '../../components/primitives'
import { useI18n } from '../../i18n'
import type { MessageKey } from '../../i18n/messages'

const TONE = {
  high: 'danger',
  medium: 'warn',
  low: 'muted',
  info: 'muted',
} as const satisfies Record<Severity, 'danger' | 'warn' | 'muted'>

export function DiagnosticsView() {
  const { t } = useI18n()
  const format = useDateFormat()

  const report = useQuery<FindingReport>({
    queryKey: ['findings'],
    queryFn: () => api.serverFindings(),
  })

  return (
    <div className="diagnostics">
      <div className="pane__header">
        <span className="muted small">{t('snapin.diagnostics.heading')}</span>
        {report.data && (
          <span className="muted small">
            {t('findings.generatedAt', { when: format(report.data.generated_at) })}
          </span>
        )}
      </div>

      <div className="table-scroll">
        {report.isLoading && <Spinner label={t('status.loading')} />}
        <ErrorMessage error={report.error} />

        {report.data && (
          <>
            <Coverage report={report.data} />
            <NotLookedAt entries={report.data.unreadable} />

            {report.data.findings.length === 0 && report.data.unreadable.length === 0 && (
              <div className="alert alert--success">{t('findings.none')}</div>
            )}

            {report.data.findings.map((finding) => (
              // Keyed by both: several shares share an id, and the id alone
              // would collapse them into one row.
              <FindingCard key={`${finding.id}:${finding.subject}`} finding={finding} />
            ))}
          </>
        )}
      </div>
    </div>
  )
}

/**
 * How much of the server the findings speak for.
 *
 * Above the list rather than below it. A number that arrives after the reader
 * has drawn a conclusion is a number that changes nothing.
 */
function Coverage({ report }: { report: FindingReport }) {
  const { t } = useI18n()
  const { coverage } = report
  const uncovered = coverage.shares_without_readable_configuration

  return (
    <section className="card">
      <p>
        {t('findings.coverage', {
          readable: coverage.shares_with_readable_configuration,
          total: coverage.shares_total,
        })}
      </p>
      {uncovered > 0 && (
        <p className="muted small">{t('findings.coverage.rest', { count: uncovered })}</p>
      )}
      {/* Nothing in this version connects to a share, so the report is silent
          about whether any of them can be opened — and silence on a screen
          reads as "all fine". */}
      {!coverage.connectivity_examined && (
        <p className="muted small">{t('findings.coverage.notProbed')}</p>
      )}
    </section>
  )
}

function NotLookedAt({ entries }: { entries: Unreadable[] }) {
  const { t } = useI18n()
  if (entries.length === 0) return null

  return (
    <section className="alert alert--warning">
      <strong>{t('findings.unreadableHeading')}</strong>
      <p>{t('findings.unreadableWhy')}</p>
      <ul className="plain-list">
        {entries.map((entry) => (
          <li key={`${entry.area}:${entry.subject}:${entry.reason}`}>
            {entry.subject && <span className="mono">{entry.subject}</span>}{' '}
            {reasonText(t, entry.reason)}
          </li>
        ))}
      </ul>
    </section>
  )
}

function FindingCard({ finding }: { finding: Finding }) {
  const { t } = useI18n()
  const evidence = Object.entries(finding.evidence)

  return (
    <section className="card">
      <div className="detail__badges">
        <Badge tone={TONE[finding.severity] ?? 'muted'}>
          {t(`findings.severity.${finding.severity}` as MessageKey)}
        </Badge>
        <Badge tone="muted">{t(`findings.area.${finding.area}` as MessageKey)}</Badge>
        {/* Which share, before what is wrong with it: somebody scanning
            twenty rows is looking for the name first. */}
        {finding.subject && <span className="mono small">{finding.subject}</span>}
      </div>

      <h3>{text(t, `findings.${finding.id}`, finding.id)}</h3>
      <p>{text(t, `findings.${finding.id}.why`, '')}</p>

      {evidence.length > 0 && (
        <p className="muted small mono">
          <span className="findings__label">{t('findings.evidence')}:</span>{' '}
          {evidence.map(([key, value]) => `${key}=${render(value)}`).join('  ')}
        </p>
      )}
    </section>
  )
}

type Translate = (key: MessageKey, params?: Record<string, string | number>) => string

/**
 * A message, or the fallback when the catalogue has not caught up.
 *
 * A rule shipped before its text would otherwise render as an empty heading —
 * which reads as a finding with nothing wrong. The id is at least something a
 * person can search for.
 */
function text(t: Translate, key: string, fallback: string): string {
  const rendered = t(key as MessageKey)
  return rendered === key ? fallback : rendered
}

function reasonText(t: Translate, reason: string): string {
  return text(t, `findings.unreadable.${reason}`, reason)
}

/**
 * One evidence value, printed rather than summarised.
 *
 * `null` is rendered as such and never dropped. A rule that carries
 * `unix_extensions: null` is saying it could not read that option, and an
 * evidence line that quietly omitted the key would let a reader believe it had.
 */
function render(value: unknown): string {
  if (value === null) return 'null'
  if (Array.isArray(value)) return `[${value.map(render).join(',')}]`
  if (typeof value === 'object') {
    return `{${Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${key}=${render(item)}`)
      .join(',')}}`
  }
  return String(value)
}
