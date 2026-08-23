/**
 * Brand assets.
 *
 * Light and dark variants are switched with <picture>/<source media>, so the
 * browser picks one before layout instead of rendering both and hiding one.
 * The app follows the system theme, which is exactly what that media query
 * reports.
 *
 * Deliberately a sibling of SAMADCON's mark rather than a new idea: same
 * plate, same bracket frame, with the glyph swapped. Two consoles from one
 * project should look like they came from one project.
 *
 * The light and dark files carry their own plate. The transparent variants in
 * docs/brand/ do not, and the lockup among them draws its wordmark in
 * `currentColor` — which is right for an inline SVG and wrong here: an SVG
 * loaded through <img> has no access to the page's colour and would render the
 * name in black. Hence these two and not those.
 */

import lockupDark from '../assets/samfscon-lockup-dark.svg'
import lockupLight from '../assets/samfscon-lockup-light.svg'
import markDark from '../assets/samfscon-mark-dark.svg'
import markLight from '../assets/samfscon-mark-light.svg'

const ALT = 'SAMFSCON — Samba FileServer Console'

/** Full lockup: mark plus wordmark. For the sign-in card. */
export function LogoLockup({ className }: { className?: string }) {
  return (
    <picture>
      <source srcSet={lockupDark} media="(prefers-color-scheme: dark)" />
      <img
        src={lockupLight}
        alt={ALT}
        className={className ? `logo-lockup ${className}` : 'logo-lockup'}
        width={420}
        height={120}
      />
    </picture>
  )
}

/** Mark only. For the top bar, where the product name is already text. */
export function LogoMark({ size = 24, className }: { size?: number; className?: string }) {
  return (
    <picture>
      <source srcSet={markDark} media="(prefers-color-scheme: dark)" />
      <img
        src={markLight}
        // Decorative here: the adjacent text already names the product.
        alt=""
        aria-hidden="true"
        className={className ? `logo-mark ${className}` : 'logo-mark'}
        width={size}
        height={size}
      />
    </picture>
  )
}
