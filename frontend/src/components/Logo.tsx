/**
 * Brand assets, drawn inline rather than loaded as images.
 *
 * The light and dark files carry an opaque plate, which is what they are for:
 * a favicon, or a lockup standing on a background nobody controls. On a
 * surface this application draws itself, that plate is a visible rectangle
 * behind the logo — #161826 against a #1b1d2b card is a box, and it looked
 * like one.
 *
 * So the transparent variants are used, and inlining is what makes them
 * usable. Their wordmark is drawn in `currentColor`; through <img> an SVG has
 * no access to the page's colour and would render the name in black. Inline,
 * it takes the colour of whatever it sits in and follows the theme with no
 * second file, no <picture>, and no media query — the palette already switches
 * and the logo now switches with it.
 *
 * The frame and the glyph keep colours of their own rather than taking the
 * palette's — they are what the mark is recognised by. But they are tuned per
 * theme in the brand files, so they are tokens too: the dark file's slate
 * frame is far too heavy on a white card, and the light file's violet glyph
 * disappears on a dark one.
 *
 * Deliberately a sibling of SAMADCON's mark rather than a new idea: same
 * bracket frame, same proportions, with the glyph swapped. Two consoles from
 * one project should look like they came from one project.
 */

// Both switch with the palette; see the token block in styles.css.
const FRAME = 'var(--brand-frame)'
const GLYPH = 'var(--brand-glyph)'
const FONT = 'Inter, Helvetica, Arial, sans-serif'

const ALT = 'SAMFSCON — Samba FileServer Console'

/** The bracket frame and the FS glyph, on a 120 grid. */
function Mark() {
  return (
    <>
      <path
        d="M34 14 H14 V106 H34"
        stroke={FRAME}
        strokeWidth="4.5"
        strokeLinecap="square"
      />
      <path
        d="M86 14 H106 V106 H86"
        stroke={FRAME}
        strokeWidth="4.5"
        strokeLinecap="square"
      />
      <text
        x="60"
        y="72"
        textAnchor="middle"
        fill={GLYPH}
        fontFamily={FONT}
        fontSize="34"
        fontWeight="600"
        letterSpacing="1"
      >
        FS
      </text>
    </>
  )
}

/** Full lockup: mark plus wordmark. For the sign-in card. */
export function LogoLockup({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 420 120"
      width={420}
      height={120}
      fill="none"
      role="img"
      aria-label={ALT}
      className={className ? `logo-lockup ${className}` : 'logo-lockup'}
    >
      <g transform="translate(16 15) scale(0.75)">
        <Mark />
      </g>
      {/* currentColor, which is the whole reason this is inline. */}
      <text
        x="118"
        y="59"
        fill="currentColor"
        fontFamily={FONT}
        fontSize="34"
        fontWeight="500"
        letterSpacing="6.8"
      >
        SAMFSCON
      </text>
      <text
        x="248"
        y="80"
        fill="currentColor"
        fontFamily={FONT}
        fontSize="11"
        fontWeight="400"
        letterSpacing="1.76"
        textAnchor="middle"
        opacity="0.65"
      >
        THE SAMBA FILESERVER CONSOLE
      </text>
    </svg>
  )
}

/** Mark only. For the top bar, where the product name is already text. */
export function LogoMark({ size = 24, className }: { size?: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 120 120"
      width={size}
      height={size}
      fill="none"
      // Decorative here: the adjacent text already names the product.
      aria-hidden="true"
      focusable="false"
      className={className ? `logo-mark ${className}` : 'logo-mark'}
    >
      <Mark />
    </svg>
  )
}
