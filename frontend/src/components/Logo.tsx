/**
 * Brand assets.
 *
 * Light and dark variants are switched with <picture>/<source media>, so the
 * browser picks one before layout instead of rendering both and hiding one.
 * The app follows the system theme, which is exactly what that media query
 * reports.
 *
 * Deliberately a sibling of SAMADCON's mark rather than a new idea: same
 * plate, same bracket frame, same terminals, with the glyph swapped. Two
 * consoles from one project should look like they came from one project.
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
        width={640}
        height={132}
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
