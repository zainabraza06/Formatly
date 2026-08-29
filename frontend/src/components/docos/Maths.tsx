import katex from 'katex'
import 'katex/dist/katex.min.css'

/**
 * Maths, set as maths.
 *
 * Equations reach the editor as LaTeX between dollars — the ones an author
 * typed that way, and the ones Word stored as its own XML, which the parser
 * translates. Showing that raw made the page read like source code, which is
 * why "convert the equations into something readable" seemed like the fix: it
 * replaced `\sum_{i=1}^{N}` with the words "sum from i=1 to N", which is
 * readable in the sense that a shopping list is readable, and destroyed the
 * equation on the way past.
 *
 * Rendering it instead costs nothing, changes nothing, and leaves the original
 * intact for export.
 */

/**
 * One equation. KaTeX renders synchronously, which matters here: the page is
 * measured off screen to decide where it breaks, and an equation that arrived
 * a frame later would be measured at the wrong height and paginate wrongly.
 */
export function Maths({ latex, display }: { latex: string; display?: boolean }) {
  let html: string
  try {
    html = katex.renderToString(latex, {
      displayMode: Boolean(display),
      throwOnError: false,     // an unparseable formula shows as itself, in red
      strict: false,           // a paper's LaTeX is not a validator's LaTeX
      output: 'html',
    })
  } catch {
    // Even with throwOnError off: whatever happens, show the source rather
    // than nothing. Losing an equation is the one outcome worth avoiding.
    return <span className="font-mono text-[0.9em]">{latex}</span>
  }

  return (
    <span
      className={display ? 'my-2 block text-center' : 'inline'}
      // KaTeX's output is markup it generated from the LaTeX above, not
      // anything a document supplied verbatim.
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
