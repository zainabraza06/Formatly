/** Finding the equations in a paragraph's text.
 *
 * Kept apart from the component that draws them: a module that exports both a
 * component and plain functions cannot be hot-reloaded as either.
 */

/** `$…$` and `$$…$$`, but not an escaped `\$` or a lone dollar in prose.
 *
 *  Built fresh for each use rather than shared. A global regex carries
 *  `lastIndex` between calls: `test()` leaves it just after whatever it found,
 *  and `matchAll` resumes from there — so asking "does this hold maths?" and
 *  then "where is it?" answered yes, and then found nothing.
 */
const maths = () => /\$\$([\s\S]+?)\$\$|(?<!\\)\$([^$\n]+?)(?<!\\)\$/g

export interface MathsPiece {
  kind: 'text' | 'inline' | 'display'
  value: string
}

/** Split text into prose and equations, in order. */
export function splitMaths(text: string): MathsPiece[] {
  const pieces: MathsPiece[] = []
  let at = 0

  for (const match of text.matchAll(maths())) {
    const start = match.index ?? 0
    if (start > at) pieces.push({ kind: 'text', value: text.slice(at, start) })
    const display = match[1] !== undefined
    pieces.push({ kind: display ? 'display' : 'inline', value: (match[1] ?? match[2]).trim() })
    at = start + match[0].length
  }
  if (at < text.length) pieces.push({ kind: 'text', value: text.slice(at) })
  return pieces
}

export function hasMaths(text: string): boolean {
  return maths().test(text)
}

