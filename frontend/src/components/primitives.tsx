/** Small shared building blocks: icons, error display, modal shell, fields. */

import {
  useEffect,
  useRef,
  useSyncExternalStore,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from 'react'
import { createPortal } from 'react-dom'

import { ApiError } from '../api/client'
import { useI18n } from '../i18n'
import type { MessageKey } from '../i18n/messages'
import { popOverlay, pushOverlay, subscribeToOverlays, topOverlay } from './overlayStack'

// ---------------------------------------------------------------------------
// Icons
//
// Phosphor Regular (MIT), inlined as path data rather than pulled from a
// package: the CSP names no external sources, and an icon set that is a
// dependency is a dependency that can be missing at build time. Credited in
// THIRD-PARTY-NOTICES.md, which covers material shipped inside the product.
//
// The viewBox travels with the path. Phosphor draws on a 256 grid and the
// hand-drawn set this replaced drew on 24 — carrying only the path would have
// rendered every glyph at a tenth of its size, which is the kind of thing that
// looks like the icon is missing rather than wrong.
// ---------------------------------------------------------------------------

const ICONS: Record<string, { box: string; d: string }> = {
  // Phosphor user — one account
  user: { box: '0 0 256 256', d: 'M230.92,212c-15.23-26.33-38.7-45.21-66.09-54.16a72,72,0,1,0-73.66,0C63.78,166.78,40.31,185.66,25.08,212a8,8,0,1,0,13.85,8c18.84-32.56,52.14-52,89.07-52s70.23,19.44,89.07,52a8,8,0,1,0,13.85-8ZM72,96a56,56,0,1,1,56,56A56.06,56.06,0,0,1,72,96Z' },
  // Phosphor users — several, which is what a group is
  group: { box: '0 0 256 256', d: 'M117.25,157.92a60,60,0,1,0-66.5,0A95.83,95.83,0,0,0,3.53,195.63a8,8,0,1,0,13.4,8.74,80,80,0,0,1,134.14,0,8,8,0,0,0,13.4-8.74A95.83,95.83,0,0,0,117.25,157.92ZM40,108a44,44,0,1,1,44,44A44.05,44.05,0,0,1,40,108Zm210.14,98.7a8,8,0,0,1-11.07-2.33A79.83,79.83,0,0,0,172,168a8,8,0,0,1,0-16,44,44,0,1,0-16.34-84.87,8,8,0,1,1-5.94-14.85,60,60,0,0,1,55.53,105.64,95.83,95.83,0,0,1,47.22,37.71A8,8,0,0,1,250.14,206.7Z' },
  // Phosphor desktop-tower — a client machine
  computer: { box: '0 0 256 256', d: 'M216,72a8,8,0,0,1-8,8H176a8,8,0,0,1,0-16h32A8,8,0,0,1,216,72Zm-8,24H176a8,8,0,0,0,0,16h32a8,8,0,0,0,0-16Zm40-48V208a16,16,0,0,1-16,16H152a16,16,0,0,1-16-16V192H96v16h16a8,8,0,0,1,0,16H64a8,8,0,0,1,0-16H80V192H32A24,24,0,0,1,8,168V96A24,24,0,0,1,32,72H136V48a16,16,0,0,1,16-16h80A16,16,0,0,1,248,48ZM136,176V88H32a8,8,0,0,0-8,8v72a8,8,0,0,0,8,8Zm96,32V48H152V208h80Zm-40-40a12,12,0,1,0,12,12A12,12,0,0,0,192,168Z' },
  // Phosphor hard-drives — the file server itself
  server: { box: '0 0 256 256', d: 'M208,136H48a16,16,0,0,0-16,16v48a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V152A16,16,0,0,0,208,136Zm0,64H48V152H208v48Zm0-160H48A16,16,0,0,0,32,56v48a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V56A16,16,0,0,0,208,40Zm0,64H48V56H208v48ZM192,80a12,12,0,1,1-12-12A12,12,0,0,1,192,80Zm0,96a12,12,0,1,1-12-12A12,12,0,0,1,192,176Z' },
  // Phosphor folder-user — a folder published to people
  share: { box: '0 0 256 256', d: 'M214.61,198.62a32,32,0,1,0-45.23,0,40,40,0,0,0-17.11,23.32,8,8,0,0,0,5.67,9.79A8.15,8.15,0,0,0,160,232a8,8,0,0,0,7.73-5.95C170.56,215.42,180.54,208,192,208s21.44,7.42,24.27,18.05a8,8,0,1,0,15.46-4.11A40,40,0,0,0,214.61,198.62ZM192,160a16,16,0,1,1-16,16A16,16,0,0,1,192,160Zm24-88H131.31L104,44.69A15.86,15.86,0,0,0,92.69,40H40A16,16,0,0,0,24,56V200.61A15.4,15.4,0,0,0,39.38,216h81.18a8,8,0,0,0,0-16H40V88H216v32a8,8,0,0,0,16,0V88A16,16,0,0,0,216,72ZM92.69,56l16,16H40V56Z' },
  // Phosphor folder
  folder: { box: '0 0 256 256', d: 'M216,72H131.31L104,44.69A15.86,15.86,0,0,0,92.69,40H40A16,16,0,0,0,24,56V200.62A15.4,15.4,0,0,0,39.38,216H216.89A15.13,15.13,0,0,0,232,200.89V88A16,16,0,0,0,216,72ZM40,56H92.69l16,16H40ZM216,200H40V88H216Z' },
  // Phosphor file
  file: { box: '0 0 256 256', d: 'M213.66,82.34l-56-56A8,8,0,0,0,152,24H56A16,16,0,0,0,40,40V216a16,16,0,0,0,16,16H200a16,16,0,0,0,16-16V88A8,8,0,0,0,213.66,82.34ZM160,51.31,188.69,80H160ZM200,216H56V40h88V88a8,8,0,0,0,8,8h48V216Z' },
  // Phosphor lock-key — permissions
  lock: { box: '0 0 256 256', d: 'M128,112a28,28,0,0,0-8,54.83V184a8,8,0,0,0,16,0V166.83A28,28,0,0,0,128,112Zm0,40a12,12,0,1,1,12-12A12,12,0,0,1,128,152Zm80-72H176V56a48,48,0,0,0-96,0V80H48A16,16,0,0,0,32,96V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V96A16,16,0,0,0,208,80ZM96,56a32,32,0,0,1,64,0V80H96ZM208,208H48V96H208V208Z' },
  // Phosphor clock-user — a person and a duration, which is what the table shows
  session: { box: '0 0 256 256', d: 'M136,72v43.05l36.42-18.21a8,8,0,0,1,7.16,14.31l-48,24A8,8,0,0,1,120,128V72a8,8,0,0,1,16,0Zm-8,144a88,88,0,1,1,88-88,8,8,0,0,0,16,0A104,104,0,1,0,128,232a8,8,0,0,0,0-16Zm103.73,5.94a8,8,0,1,1-15.46,4.11C213.44,215.42,203.46,208,192,208s-21.44,7.42-24.27,18.05A8,8,0,0,1,160,232a8.15,8.15,0,0,1-2.06-.27,8,8,0,0,1-5.67-9.79,40,40,0,0,1,17.11-23.32,32,32,0,1,1,45.23,0A40,40,0,0,1,231.73,221.94ZM176,176a16,16,0,1,0,16-16A16,16,0,0,0,176,176Z' },
  // Phosphor folder-dashed
  container: { box: '0 0 256 256', d: 'M96,208a8,8,0,0,1-8,8H39.38A15.4,15.4,0,0,1,24,200.62V192a8,8,0,0,1,16,0v8H88A8,8,0,0,1,96,208Zm64-8H128a8,8,0,0,0,0,16h32a8,8,0,0,0,0-16Zm64-56a8,8,0,0,0-8,8v48H200a8,8,0,0,0,0,16h16.89A15.13,15.13,0,0,0,232,200.89V152A8,8,0,0,0,224,144Zm-8-72H168a8,8,0,0,0,0,16h48v24a8,8,0,0,0,16,0V88A16,16,0,0,0,216,72ZM24,80V56A16,16,0,0,1,40,40H92.69A15.86,15.86,0,0,1,104,44.69l29.66,29.65A8,8,0,0,1,128,88H32A8,8,0,0,1,24,80Zm16-8h68.69l-16-16H40Zm-8,88a8,8,0,0,0,8-8V120a8,8,0,0,0-16,0v32A8,8,0,0,0,32,160Z' },
  // Phosphor tree-structure
  domain: { box: '0 0 256 256', d: 'M160,112h48a16,16,0,0,0,16-16V48a16,16,0,0,0-16-16H160a16,16,0,0,0-16,16V64H128a24,24,0,0,0-24,24v32H72v-8A16,16,0,0,0,56,96H24A16,16,0,0,0,8,112v32a16,16,0,0,0,16,16H56a16,16,0,0,0,16-16v-8h32v32a24,24,0,0,0,24,24h16v16a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V160a16,16,0,0,0-16-16H160a16,16,0,0,0-16,16v16H128a8,8,0,0,1-8-8V88a8,8,0,0,1,8-8h16V96A16,16,0,0,0,160,112ZM56,144H24V112H56v32Zm104,16h48v48H160Zm0-112h48V96H160Z' },
  // Phosphor address-book
  contact: { box: '0 0 256 256', d: 'M83.19,174.4a8,8,0,0,0,11.21-1.6,52,52,0,0,1,83.2,0,8,8,0,1,0,12.8-9.6A67.88,67.88,0,0,0,163,141.51a40,40,0,1,0-53.94,0A67.88,67.88,0,0,0,81.6,163.2,8,8,0,0,0,83.19,174.4ZM112,112a24,24,0,1,1,24,24A24,24,0,0,1,112,112Zm96-88H64A16,16,0,0,0,48,40V64H32a8,8,0,0,0,0,16H48v40H32a8,8,0,0,0,0,16H48v40H32a8,8,0,0,0,0,16H48v24a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V40A16,16,0,0,0,208,24Zm0,192H64V40H208Z' },
  // Phosphor cube — the fallback
  object: { box: '0 0 256 256', d: 'M223.68,66.15,135.68,18h0a15.88,15.88,0,0,0-15.36,0l-88,48.17a16,16,0,0,0-8.32,14v95.64a16,16,0,0,0,8.32,14l88,48.17a15.88,15.88,0,0,0,15.36,0l88-48.17a16,16,0,0,0,8.32-14V80.18A16,16,0,0,0,223.68,66.15ZM128,32h0l80.34,44L128,120,47.66,76ZM40,90l80,43.78v85.79L40,175.82Zm96,129.57V133.82L216,90v85.78Z' },
  // Phosphor folder-user
  'tab-shares': { box: '0 0 256 256', d: 'M214.61,198.62a32,32,0,1,0-45.23,0,40,40,0,0,0-17.11,23.32,8,8,0,0,0,5.67,9.79A8.15,8.15,0,0,0,160,232a8,8,0,0,0,7.73-5.95C170.56,215.42,180.54,208,192,208s21.44,7.42,24.27,18.05a8,8,0,1,0,15.46-4.11A40,40,0,0,0,214.61,198.62ZM192,160a16,16,0,1,1-16,16A16,16,0,0,1,192,160Zm24-88H131.31L104,44.69A15.86,15.86,0,0,0,92.69,40H40A16,16,0,0,0,24,56V200.61A15.4,15.4,0,0,0,39.38,216h81.18a8,8,0,0,0,0-16H40V88H216v32a8,8,0,0,0,16,0V88A16,16,0,0,0,216,72ZM92.69,56l16,16H40V56Z' },
  // Phosphor clock-user
  'tab-sessions': { box: '0 0 256 256', d: 'M136,72v43.05l36.42-18.21a8,8,0,0,1,7.16,14.31l-48,24A8,8,0,0,1,120,128V72a8,8,0,0,1,16,0Zm-8,144a88,88,0,1,1,88-88,8,8,0,0,0,16,0A104,104,0,1,0,128,232a8,8,0,0,0,0-16Zm103.73,5.94a8,8,0,1,1-15.46,4.11C213.44,215.42,203.46,208,192,208s-21.44,7.42-24.27,18.05A8,8,0,0,1,160,232a8.15,8.15,0,0,1-2.06-.27,8,8,0,0,1-5.67-9.79,40,40,0,0,1,17.11-23.32,32,32,0,1,1,45.23,0A40,40,0,0,1,231.73,221.94ZM176,176a16,16,0,1,0,16-16A16,16,0,0,0,176,176Z' },
  // Phosphor tree-view
  'tab-files': { box: '0 0 256 256', d: 'M176,152h32a16,16,0,0,0,16-16V104a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H88V80h8a16,16,0,0,0,16-16V32A16,16,0,0,0,96,16H64A16,16,0,0,0,48,32V64A16,16,0,0,0,64,80h8V192a24,24,0,0,0,24,24h64v8a16,16,0,0,0,16,16h32a16,16,0,0,0,16-16V192a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H96a8,8,0,0,1-8-8V128h72v8A16,16,0,0,0,176,152ZM64,32H96V64H64ZM176,192h32v32H176Zm0-88h32v32H176Z' },
  // Phosphor users-three
  'tab-accounts': { box: '0 0 256 256', d: 'M244.8,150.4a8,8,0,0,1-11.2-1.6A51.6,51.6,0,0,0,192,128a8,8,0,0,1-7.37-4.89,8,8,0,0,1,0-6.22A8,8,0,0,1,192,112a24,24,0,1,0-23.24-30,8,8,0,1,1-15.5-4A40,40,0,1,1,219,117.51a67.94,67.94,0,0,1,27.43,21.68A8,8,0,0,1,244.8,150.4ZM190.92,212a8,8,0,1,1-13.84,8,57,57,0,0,0-98.16,0,8,8,0,1,1-13.84-8,72.06,72.06,0,0,1,33.74-29.92,48,48,0,1,1,58.36,0A72.06,72.06,0,0,1,190.92,212ZM128,176a32,32,0,1,0-32-32A32,32,0,0,0,128,176ZM72,120a8,8,0,0,0-8-8A24,24,0,1,1,87.24,82a8,8,0,1,0,15.5-4A40,40,0,1,0,37,117.51,67.94,67.94,0,0,0,9.6,139.19a8,8,0,1,0,12.8,9.61A51.6,51.6,0,0,1,64,128,8,8,0,0,0,72,120Z' },
  // Phosphor pulse
  'tab-diagnostics': { box: '0 0 256 256', d: 'M240,128a8,8,0,0,1-8,8H204.94l-37.78,75.58A8,8,0,0,1,160,216h-.4a8,8,0,0,1-7.08-5.14L95.35,60.76,63.28,131.31A8,8,0,0,1,56,136H24a8,8,0,0,1,0-16H50.85L88.72,36.69a8,8,0,0,1,14.76.46l57.51,151,31.85-63.71A8,8,0,0,1,200,120h32A8,8,0,0,1,240,128Z' },
  // Phosphor sliders-horizontal
  'tab-config': { box: '0 0 256 256', d: 'M40,88H73a32,32,0,0,0,62,0h81a8,8,0,0,0,0-16H135a32,32,0,0,0-62,0H40a8,8,0,0,0,0,16Zm64-24A16,16,0,1,1,88,80,16,16,0,0,1,104,64ZM216,168H199a32,32,0,0,0-62,0H40a8,8,0,0,0,0,16h97a32,32,0,0,0,62,0h17a8,8,0,0,0,0-16Zm-48,24a16,16,0,1,1,16-16A16,16,0,0,1,168,192Z' },
}

// What an object *type* from the API is drawn as. Separate from the table
// above because several types share a glyph and because a type is the server's
// word, not the icon set's.
const TYPE_ICON: Record<string, string> = {
  user: 'user',
  group: 'group',
  alias: 'group',
  well_known_group: 'group',
  computer: 'computer',
  server: 'server',
  share: 'share',
  folder: 'folder',
  directory: 'folder',
  file: 'file',
  permissions: 'lock',
  session: 'session',
  container: 'container',
  domain: 'domain',
  contact: 'contact',
  diagnostics: 'tab-diagnostics',
}

/**
 * One glyph, named either by an object type or by an icon directly.
 *
 * Both, because the console tabs want icons that are not any object's type —
 * `tab-shares` is a console, not a thing on a server — and requiring a
 * TYPE_ICON entry for each would mean a table of names mapping to themselves.
 * An unknown name draws the fallback rather than nothing: a missing glyph
 * should look like a glyph nobody chose, not like a broken row.
 */
export function Icon({ type, className }: { type: string; className?: string }) {
  const icon = ICONS[TYPE_ICON[type] ?? type] ?? ICONS.object!
  return (
    <svg
      className={className ? `icon ${className}` : 'icon'}
      viewBox={icon.box}
      aria-hidden="true"
      focusable="false"
    >
      <path d={icon.d} />
    </svg>
  )
}

export function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={open ? 'chevron chevron--open' : 'chevron'}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M9 6l6 6-6 6" />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export function ErrorMessage({ error, onDismiss }: { error: unknown; onDismiss?: () => void }) {
  const { t, te, th } = useI18n()
  if (!error) return null

  const hint = th(error)
  const detail = error instanceof ApiError ? error.detail : undefined

  return (
    <div className="alert alert--error" role="alert">
      <div className="alert__body">
        <strong>{te(error)}</strong>
        {hint && (
          <p className="alert__hint">
            {t('error.hint')}: {hint}
          </p>
        )}
        {detail && (
          <details className="alert__details">
            <summary>{t('error.details')}</summary>
            <code>{detail}</code>
          </details>
        )}
      </div>
      {onDismiss && (
        <button type="button" className="alert__close" onClick={onDismiss} aria-label="×">
          ×
        </button>
      )}
    </div>
  )
}

export function Banner({ message, tone = 'info' }: { message: string; tone?: 'info' | 'warning' }) {
  return <div className={`alert alert--${tone}`}>{message}</div>
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]),' +
  ' textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/** The host every overlay is portalled into. See index.html. */
function overlayHost(): HTMLElement {
  return document.getElementById('overlays') ?? document.body
}

export function Modal({
  title,
  onClose,
  children,
  footer,
}: {
  title: string
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}) {
  // There used to be a `size` for a dialog that wanted the screen. Nothing in
  // this project ever passed it and the CSS behind it was dead from the first
  // commit; what would have wanted it is a window now, with a title bar and a
  // position. Every dialog here is a form or a confirmation.
  const ref = useRef<HTMLDivElement>(null)
  const token = useRef(0)

  // Read from a ref so that registering can happen once, on mount, without the
  // stack entry going stale when the caller passes a new arrow each render.
  const close = useRef(onClose)
  close.current = onClose

  useEffect(() => {
    token.current = pushOverlay(() => close.current())

    // Where focus was, so it can be handed back. Moving focus into the dialog
    // is required — a keyboard user left outside an aria-modal dialog has
    // nowhere to go — but never returning it is how people end up back at the
    // top of the page after every confirmation.
    const opener = document.activeElement as HTMLElement | null
    ref.current?.querySelector<HTMLElement>(FOCUSABLE)?.focus()

    return () => {
      popOverlay(token.current)
      token.current = 0
      // Only if focus is still ours to give back. If the person has clicked
      // elsewhere in the meantime, yanking it would be the rude thing.
      if (opener && ref.current?.contains(document.activeElement)) opener.focus()
    }
  }, [])

  // Only the topmost overlay tints the page. Two dialogs each drawing 45%
  // black gave 70%, and the one underneath became unreadable in a pair while
  // being perfectly legible alone.
  const top = useSyncExternalStore(subscribeToOverlays, topOverlay, () => 0)
  const isTop = token.current !== 0 && token.current === top

  // aria-modal is asserted below, so Tab has to honour it. It did not: focus
  // walked straight out into the console behind. Portalling made that worse —
  // the dialog is no longer even in the console's document order.
  const trapFocus = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Tab' || !ref.current) return
    const items = [...ref.current.querySelectorAll<HTMLElement>(FOCUSABLE)]
    if (items.length === 0) return

    const first = items[0]!
    const last = items[items.length - 1]!
    const active = document.activeElement

    if (event.shiftKey && active === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && active === last) {
      event.preventDefault()
      first.focus()
    }
  }

  return createPortal(
    // Portalled out of wherever it was used, and this is load-bearing rather
    // than tidiness: a dialog rendered inside a positioned window resolves its
    // z-index within that window's stacking context, so a confirmation opened
    // from a background window would paint underneath the window in front.
    // Silently.
    //
    // The backdrop does nothing on click, on purpose, and this is not an
    // omission to be tidied up later. It used to close the dialog on
    // mousedown, so a click landing slightly wide of the new-share form threw
    // away everything typed into it without a word. The three dialogs here
    // that hold typing are exactly the three that would lose it.
    //
    // Windows dialogs do not close when you click beside them either, and this
    // console is read against those.
    <div className={isTop ? 'modal__backdrop' : 'modal__backdrop modal__backdrop--stacked'}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        ref={ref}
        onKeyDown={trapFocus}
      >
        <header className="modal__header">
          <h2>{title}</h2>
          <button type="button" className="modal__close" onClick={onClose} aria-label="×">
            ×
          </button>
        </header>
        <div className="modal__body">{children}</div>
        {footer && <footer className="modal__footer">{footer}</footer>}
      </div>
    </div>,
    overlayHost(),
  )
}

// ---------------------------------------------------------------------------
// Form fields
// ---------------------------------------------------------------------------

export function Field({
  label,
  children,
  hint,
}: {
  label: string
  children: ReactNode
  hint?: string
}) {
  return (
    <label className="field">
      <span className="field__label">{label}</span>
      {children}
      {hint && <span className="field__hint">{hint}</span>}
    </label>
  )
}

export function TextRow({ label, value }: { label: string; value: ReactNode }) {
  if (value === null || value === undefined || value === '') return null
  return (
    <div className="row">
      <span className="row__label">{label}</span>
      <span className="row__value">{value}</span>
    </div>
  )
}

export function Badge({ tone, children }: { tone: 'ok' | 'warn' | 'danger' | 'muted'; children: ReactNode }) {
  return <span className={`badge badge--${tone}`}>{children}</span>
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="spinner" role="status">
      <span className="spinner__dot" />
      {label && <span>{label}</span>}
    </div>
  )
}

/** Format an ISO timestamp in the user's locale, or a dash when absent. */
export function useDateFormat() {
  const { language } = useI18n()
  return (value: string | null | undefined): string => {
    if (!value) return '—'
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return '—'
    return parsed.toLocaleString(language === 'de' ? 'de-DE' : 'en-GB', {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  }
}

/** Just the clock, for "read at 20:35" — a date there is noise. */
export function useTimeFormat() {
  const { language } = useI18n()
  return (value: number | string | null | undefined): string => {
    if (value === null || value === undefined || value === 0) return '—'
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return '—'
    return parsed.toLocaleTimeString(language === 'de' ? 'de-DE' : 'en-GB', {
      timeStyle: 'medium',
    })
  }
}

export function useTypeLabel() {
  const { t } = useI18n()
  return (type: string): string => t(`type.${type}` as MessageKey)
}
