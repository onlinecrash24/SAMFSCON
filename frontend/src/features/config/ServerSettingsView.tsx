/**
 * The server's global settings.
 *
 * One difference from the share sheet runs through everything here. A share's
 * options live in one place, so an option this console does not find is an
 * option the share does not have. A global option lives in two, and the second
 * one is the text smb.conf, which nothing SAMFSCON speaks can read. So an empty
 * field on this screen means "not in the registry" and never "not set", an
 * unstored checkbox is drawn indeterminate rather than at Samba's default, and
 * a save sends only what somebody actually touched.
 *
 * The other difference is at the bottom of the page: this console writes the
 * registry and can make nothing re-read it. Saying so once, permanently, is
 * better than a screen that looks like it applied something.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'

import { api } from '../../api/endpoints'
import type {
  GlobalConfig,
  GlobalOptionSpec,
  InForceEvidence,
  LiveValue,
} from '../../api/types'
import { Badge, Banner, ErrorMessage, Field, Modal, Spinner } from '../../components/primitives'
import { useI18n } from '../../i18n'
import type { MessageKey } from '../../i18n/messages'
import { asPayload, changedOptions, confirmationsFor, type Change } from './changes'
import { acceptableRefusal } from './refusal'

const GROUPS = [
  'server',
  'protocol',
  'access',
  'files',
  'printing',
  'winbind',
  'advanced',
] as const
type Group = (typeof GROUPS)[number]

export function ServerSettingsView({ onChanged }: { onChanged: (message: string) => void }) {
  const { t, language } = useI18n()
  const queryClient = useQueryClient()
  const [group, setGroup] = useState<Group>('server')

  const config = useQuery<GlobalConfig>({ queryKey: ['config'], queryFn: () => api.config() })
  const catalogue = useQuery({
    // The mode is not a parameter — the server resolves it from the session —
    // but it belongs in the key all the same: without it, signing in to a
    // standalone server would be served the member's catalogue from cache.
    queryKey: ['configCatalogue', language, config.data?.mode],
    queryFn: () => api.configCatalogue(language),
    staleTime: Infinity,
  })

  const [draft, setDraft] = useState<Record<string, string>>({})
  // What the confirmation dialog is holding, if anything.
  const [pending, setPending] = useState<Change[] | null>(null)
  // The save that is in the air, kept so a refusal that can be accepted can be
  // retried with one more token rather than making somebody fill the form in
  // again. Cleared on success and on cancel.
  const [attempt, setAttempt] = useState<{ changes: Change[]; extra: string[] } | null>(null)

  useEffect(() => {
    if (config.data) setDraft({ ...config.data.options.stored })
  }, [config.data])

  const specs = useMemo(() => catalogue.data?.options ?? [], [catalogue.data])
  const stored = config.data?.options.stored ?? {}
  const changes = useMemo(() => changedOptions(stored, draft, specs), [stored, draft, specs])

  const save = useMutation({
    mutationFn: ({ changes: confirmed, extra }: { changes: Change[]; extra: string[] }) =>
      api.updateConfig({
        options: asPayload(confirmed),
        // The risky options by name, plus whatever checks could not be run and
        // have been accepted one at a time. Never a blanket flag: a client that
        // sent one would confirm an option it had never shown anybody.
        confirm: [...confirmationsFor(confirmed, specs), ...extra],
        create_section: config.data?.section_present === false,
      }),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ['config'] })
      setPending(null)
      setAttempt(null)
      onChanged(verificationText(result.verification, t))
    },
  })

  // A refusal that names a token is one the server is willing to take an
  // answer on — 409 with `confirm_with`, as against the 400s, which are values
  // to fix and carry no token however hard the interface asks.
  const acceptable = acceptableRefusal(save.error)

  if (config.isLoading) return <Spinner label={t('status.loading')} />
  if (!config.data) return <ErrorMessage error={config.error} />

  const loaded = config.data
  // A confirmed false only. `null` means the capability could not be
  // established, and a form disabled on "we could not look" would be this
  // console reporting could-not-determine as is-so — the same rule
  // SharesView.tsx follows with `!== false`.
  const writable = loaded.capabilities?.registry_writable !== false
  const risky = changes.some(
    (change) => specs.find((spec) => spec.name === change.name)?.safety === 'risky',
  )

  function start(next: { changes: Change[]; extra: string[] }) {
    setAttempt(next)
    save.mutate(next)
  }

  function submit() {
    if (changes.length === 0) return
    if (risky) setPending(changes)
    else start({ changes, extra: [] })
  }

  return (
    <div className="config">
      <div className="pane__header">
        <span className="muted small">{t('snapin.config.note')}</span>
        <div className="pane__actions">
          <button
            type="button"
            className="button"
            onClick={() => void queryClient.invalidateQueries({ queryKey: ['config'] })}
          >
            {t('action.refresh')}
          </button>
        </div>
      </div>

      <div className="table-scroll">
        {/* Always, and first: everything below is about one of the two places
            a global option can live, and the screen has to say which. */}
        <Banner message={t('config.registryOnly')} />

        {loaded.section_present === false && (
          <Banner tone="warning" message={t('config.sectionAbsent')} />
        )}
        {loaded.section_present === null && (
          <Banner tone="warning" message={t('config.sectionUnknown')} />
        )}
        {!writable && <Banner tone="warning" message={t('config.unwritable')} />}

        <InForce config={loaded} />

        {loaded.notes.length > 0 && (
          <ul className="notes">
            {loaded.notes.map((note, index) => (
              <li key={`${note.code}:${index}`} className="muted small">
                {t(`caps.note.${note.code}` as MessageKey, note.params)}
              </li>
            ))}
          </ul>
        )}

        <nav className="tabs">
          {GROUPS.map((entry) => (
            <button
              key={entry}
              type="button"
              className={group === entry ? 'tabs__tab tabs__tab--active' : 'tabs__tab'}
              onClick={() => setGroup(entry)}
            >
              {t(`config.group.${entry}`)}
            </button>
          ))}
        </nav>

        {/* Suppressed while the acceptance dialog is up: it is the same
            refusal, and showing it twice would read as two problems. */}
        {!acceptable && <ErrorMessage error={save.error} onDismiss={() => save.reset()} />}

        {group === 'files' && <p className="muted small">{t('config.filesTabNote')}</p>}
        {group === 'printing' && <PrinterShares count={loaded.printer_shares} />}

        <LiveRows live={loaded.live} specs={specs} group={group} />

        {specs
          .filter((spec) => spec.group === group)
          .map((spec) => (
            <GlobalOptionField
              key={spec.name}
              spec={spec}
              value={draft[spec.name] ?? ''}
              risks={loaded.risks}
              disabled={!writable}
              onChange={(value) => setDraft((current) => ({ ...current, [spec.name]: value }))}
            />
          ))}

        {group === 'winbind' && <Idmap entries={loaded.options.idmap} />}

        {group === 'advanced' && (
          <>
            <StoredBlock
              title={t('config.notApplicable')}
              why={t('config.notApplicable.why')}
              entries={loaded.options.not_applicable}
            />
            <StoredBlock
              title={t('config.otherOptions')}
              why={t('config.otherOptions.why')}
              entries={loaded.options.extra}
            />
          </>
        )}
      </div>

      <footer className="detail__footer">
        <button
          type="button"
          className="button button--primary"
          disabled={!writable || changes.length === 0 || save.isPending}
          onClick={submit}
        >
          {save.isPending ? t('status.loading') : t('action.save')}
        </button>
        <button
          type="button"
          className="button"
          title={t('config.revert.why')}
          disabled={changes.length === 0 || save.isPending}
          onClick={() => setDraft({ ...loaded.options.stored })}
        >
          {t('config.revert')}
        </button>
        <span className="muted small">
          {t('config.notApplied')} {t('config.notApplied.faster')}
        </span>
      </footer>

      {pending && (
        <Modal
          title={t('config.confirmTitle')}
          onClose={() => setPending(null)}
          footer={
            <>
              <button type="button" className="button" onClick={() => setPending(null)}>
                {t('action.cancel')}
              </button>
              <button
                type="button"
                className="button button--danger"
                onClick={() => start({ changes: pending, extra: [] })}
              >
                {t('config.confirmProceed')}
              </button>
            </>
          }
        >
          <p>{t('config.confirmIntro')}</p>
          <ul>
            {pending
              .map((change) => specs.find((spec) => spec.name === change.name))
              .filter((spec): spec is GlobalOptionSpec => spec?.safety === 'risky')
              .map((spec) => (
                <li key={spec.name}>
                  <strong className="mono">{spec.name}</strong>
                  <span className="muted small"> — {riskText(spec, loaded.risks, t)}</span>
                </li>
              ))}
          </ul>
        </Modal>
      )}

      {acceptable && attempt && (
        <Modal
          title={t('config.undecided.title')}
          onClose={() => {
            save.reset()
            setAttempt(null)
          }}
          footer={
            <>
              <button
                type="button"
                className="button"
                onClick={() => {
                  save.reset()
                  setAttempt(null)
                }}
              >
                {t('action.cancel')}
              </button>
              <button
                type="button"
                className="button button--danger"
                onClick={() =>
                  start({ changes: attempt.changes, extra: [...attempt.extra, acceptable.token] })
                }
              >
                {t('config.undecided.accept')}
              </button>
            </>
          }
        >
          <p>{t('config.undecided.intro')}</p>
          <p>
            <strong>{acceptable.message}</strong>
          </p>
          {acceptable.hint && <p className="muted small">{acceptable.hint}</p>}
          {acceptable.entries.length > 0 && (
            <p className="muted small mono">
              {t('config.undecided.entries', { entries: acceptable.entries.join(', ') })}
            </p>
          )}
        </Modal>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// One option
// ---------------------------------------------------------------------------

function GlobalOptionField({
  spec,
  value,
  risks,
  disabled,
  onChange,
}: {
  spec: GlobalOptionSpec
  value: string
  risks: GlobalConfig['risks']
  disabled: boolean
  onChange: (value: string) => void
}) {
  const { t } = useI18n()
  const stored = value !== ''
  const readOnly = spec.safety === 'read_only'
  const locked = disabled || readOnly

  const reference = spec.default
    ? t('config.defaultIs', { value: spec.default })
    : spec.default_note
      ? t(`config.defaultNote.${spec.default_note}` as MessageKey)
      : null

  const badges = (
    <div className="config__badges">
      {readOnly && <Badge tone="muted">{t('config.readOnly')}</Badge>}
      {spec.safety === 'risky' && <Badge tone="warn">{t('config.risky')}</Badge>}
      <span className="muted small">
        {t(`config.effect.${spec.effect}` as MessageKey)}
        {spec.effect === 'restart' && spec.daemons.length > 0
          ? ` · ${t('config.effect.daemons', { names: spec.daemons.join(', ') })}`
          : ''}
      </span>
    </div>
  )

  const under = (
    <>
      {badges}
      {reference && <span className="config__default">{reference}</span>}
      {readOnly && spec.read_only_reason && (
        <span className="config__default">
          {t(`config.readOnly.${spec.read_only_reason}` as MessageKey)}
        </span>
      )}
      {spec.safety === 'risky' && spec.risk && (
        <span className="config__default">{riskText(spec, risks, t)}</span>
      )}
    </>
  )

  if (spec.type === 'bool') {
    // Three states, and the third is drawn differently from the share sheet on
    // purpose. There, unstored means Samba's default really does apply. Here it
    // means "not in the registry", and the text smb.conf this console cannot
    // read may well set it — so a checkbox drawn from Samba's default would be
    // asserting this server's value from something that says nothing about it.
    return (
      <div className="config__option">
        <label className="checkbox">
          <input
            type="checkbox"
            checked={stored && value === 'yes'}
            disabled={locked}
            // `indeterminate` is a DOM property and not an attribute: as a JSX
            // prop it compiles, renders, and does nothing at all.
            ref={(element) => {
              if (element) element.indeterminate = !stored
            }}
            onChange={(event) => onChange(event.target.checked ? 'yes' : 'no')}
          />
          <span className="mono">{spec.name}</span>
          {!stored && (
            <span className="option__default" title={t('config.notSetHere.why')}>
              {t('config.notSetHere')}
            </span>
          )}
        </label>
        <span className="field__hint">{spec.doc}</span>
        {under}
      </div>
    )
  }

  if (spec.type === 'choice') {
    // A stored value the catalogue does not list gets its own entry. Without
    // it the select renders blank and the next save quietly rewrites a value
    // somebody chose — the server's configuration lost to a dropdown.
    const unlisted = stored && !spec.choices.includes(value)
    return (
      <div className="config__option">
        <Field label={spec.name} hint={spec.doc}>
          <select
            value={value}
            disabled={locked}
            onChange={(event) => onChange(event.target.value)}
          >
            <option value="">{t('config.notSetHere')}</option>
            {unlisted && (
              <option value={value}>
                {value} ({t('config.unlistedValue')})
              </option>
            )}
            {spec.choices.map((choice) => (
              <option key={choice} value={choice}>
                {choice}
              </option>
            ))}
          </select>
        </Field>
        {under}
      </div>
    )
  }

  return (
    <div className="config__option">
      <Field label={spec.name} hint={spec.doc}>
        <input
          type={spec.type === 'int' ? 'number' : 'text'}
          value={value}
          disabled={locked}
          spellCheck={false}
          // Never the server's default. In the placeholder position it reads as
          // what this server does, which is exactly what this page cannot know.
          placeholder={t('config.notSetHere')}
          onChange={(event) => onChange(event.target.value)}
        />
      </Field>
      {under}
    </div>
  )
}

// ---------------------------------------------------------------------------
// The blocks above and below the fields
// ---------------------------------------------------------------------------

function InForce({ config }: { config: GlobalConfig }) {
  const { t } = useI18n()

  if (config.in_force === true) return <Banner message={t('config.inForce.confirmed')} />
  if (config.in_force === false)
    return <Banner tone="warning" message={t('config.inForce.contradicted')} />

  // Undecided, and which of the four reasons it was gets said. "We could not
  // establish it" with no reason underneath reads as evasion; with the reason
  // it reads as a fact about what was available to look at.
  const reason = config.in_force_evidence.find(
    (entry: InForceEvidence) => entry.verdict === 'undecided',
  )?.reason
  return (
    <Banner
      message={t(
        `config.inForce.unknown.${reason ?? 'not_stored'}` as MessageKey,
      )}
    />
  )
}

function LiveRows({
  live,
  specs,
  group,
}: {
  live: LiveValue[]
  specs: GlobalOptionSpec[]
  group: Group
}) {
  const { t } = useI18n()
  const here = live.filter(
    (value) => specs.find((spec) => spec.name === value.option)?.group === group,
  )
  if (here.length === 0) return null

  return (
    <section className="detail__section">
      <h3>{t('config.live.heading')}</h3>
      <dl className="kv">
        {here.map((value) => (
        <div key={value.option}>
          <dt className="mono">{value.option}</dt>
          <dd>
            {/* A refused read renders as a dash and says so. A blank here
                would read as the server answering "nothing". */}
            <span className="mono">{value.readable ? (value.value ?? '—') : '—'}</span>
            <span className="muted small">
              {' '}
              {t('config.live.inForce')} ·{' '}
              {t(`config.live.source.${sourceKey(value.source)}` as MessageKey)}
              {!value.readable ? ` · ${t('config.live.unreadable')}` : ''}
            </span>
          </dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function PrinterShares({ count }: { count: number | null }) {
  const { t } = useI18n()
  // Two sentences, because "this server publishes none" and "the share list
  // could not be read" are two different facts and only one of them means the
  // tab is fine.
  if (count === null) return <p className="muted small">{t('config.printing.unknown')}</p>
  if (count === 0) return <p className="muted small">{t('config.printing.noPrinterShares')}</p>
  return null
}

function Idmap({ entries }: { entries: Record<string, string> }) {
  const { t } = useI18n()
  return (
    <section className="detail__section">
      <h3>{t('config.idmap')}</h3>
      {Object.keys(entries).length === 0 ? (
        <p className="muted small">{t('config.idmap.empty')}</p>
      ) : (
        <dl className="kv">
          {Object.entries(entries).map(([key, value]) => (
            <div key={key}>
              <dt className="mono">{key}</dt>
              <dd className="mono">{value}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  )
}

function StoredBlock({
  title,
  why,
  entries,
}: {
  title: string
  why: string
  entries: Record<string, string>
}) {
  if (Object.keys(entries).length === 0) return null
  return (
    <section className="detail__section">
      <h3>{title}</h3>
      <p className="muted small">{why}</p>
      <dl className="kv">
        {Object.entries(entries).map(([key, value]) => (
          <div key={key}>
            <dt className="mono">{key}</dt>
            <dd className="mono">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Text
// ---------------------------------------------------------------------------

type Translate = ReturnType<typeof useI18n>['t']

/** The source labels, mapped from the backend's dotted codes to message keys. */
function sourceKey(source: string): string {
  if (source.startsWith('srvsvc.')) return 'srvsvc'
  if (source.startsWith('observed.')) return 'observed'
  if (source === 'session.workgroup') return 'session_workgroup'
  if (source === 'session.mode') return 'session_mode'
  return 'observed'
}

function riskText(spec: GlobalOptionSpec, risks: GlobalConfig['risks'], t: Translate): string {
  return t(`config.risk.${spec.risk}` as MessageKey, {
    // The address the *server* sees, which is the container's and not the
    // workstation's. Naming the wrong one would send somebody to allow an
    // address that was never being matched.
    address: risks.own_client_address ?? '—',
    floor: risks.console_dialect_floor,
  })
}

function verificationText(
  verification: { code: string; stored?: string; live?: string | null },
  t: Translate,
): string {
  if (verification.code === 'not_yet_visible') {
    return t('config.verify.not_yet_visible', {
      stored: verification.stored ?? '',
      live: verification.live ?? '',
    })
  }
  if (verification.code === 'applied_confirmed') return t('config.verify.applied_confirmed')
  return t('config.verify.not_comparable')
}
