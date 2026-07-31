import type { ReactNode } from 'react'
import { MiniChart } from './MiniChart'
import type { PaperSpec } from '../../lib/paperApi'

/** Renders the finished document as a readable page — the way it will look once
 *  exported — so the result appears in full when ready, not just as stats. Always
 *  light "paper" regardless of the app theme. */
export function DocumentPreview({ spec }: { spec: PaperSpec }) {
  const counters = { h1: 0, h2: 0, h3: 0, table: 0, figure: 0, equation: 0 }

  return (
    <div
      className="mx-auto w-full max-w-3xl bg-white text-neutral-900 shadow-sm ring-1 ring-black/10"
      style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
    >
      <div className="px-10 py-10 sm:px-14 sm:py-12">
        {/* front matter */}
        <h1 className="text-center text-[22px] font-bold leading-snug">{spec.meta.title}</h1>
        {spec.meta.authors?.length > 0 && (
          <div className="mt-2 text-center text-sm text-neutral-700">
            {spec.meta.authors.map((a, i) => (
              <span key={i}>
                {a.name}
                {a.affiliation ? `, ${a.affiliation}` : ''}
                {i < spec.meta.authors.length - 1 ? ' · ' : ''}
              </span>
            ))}
          </div>
        )}

        {spec.meta.abstract && (
          <p className="mt-5 text-justify text-[13px] leading-relaxed">
            <span className="font-bold italic">Abstract—</span>
            <span className="italic">{spec.meta.abstract}</span>
          </p>
        )}
        {spec.meta.keywords?.length > 0 && (
          <p className="mt-2 text-justify text-[13px] leading-relaxed">
            <span className="font-bold italic">Index Terms—</span>
            <span className="italic">{spec.meta.keywords.join(', ')}.</span>
          </p>
        )}

        <hr className="my-6 border-neutral-200" />

        {/* body */}
        <div className="space-y-3">
          {spec.blocks.map((b, i) => (
            <Block key={i} block={b} counters={counters} />
          ))}
        </div>

        {/* references */}
        {spec.references?.length > 0 && (
          <div className="mt-6">
            <h2 className="mb-2 text-[15px] font-bold">References</h2>
            <ol className="space-y-1">
              {spec.references.map((r, i) => (
                <li key={i} className="pl-6 -indent-6 text-[12px] leading-relaxed">
                  [{i + 1}] {inline(r)}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </div>
  )
}

type Counters = { h1: number; h2: number; h3: number; table: number; figure: number; equation: number }

function Block({ block, counters }: { block: Record<string, any>; counters: Counters }) {
  switch (block.type) {
    case 'heading': {
      const level = Math.min(3, Math.max(1, block.level || 1))
      let label = ''
      if (level === 1) { counters.h1++; counters.h2 = 0; counters.h3 = 0; label = `${counters.h1}. ` }
      else if (level === 2) { counters.h2++; counters.h3 = 0; label = `${counters.h1}.${counters.h2} ` }
      else { counters.h3++; label = `${counters.h1}.${counters.h2}.${counters.h3} ` }
      const cls = level === 1 ? 'mt-4 text-[16px] font-bold'
        : level === 2 ? 'mt-3 text-[14px] font-bold'
        : 'mt-2 text-[13px] font-bold italic'
      return <h2 className={cls}>{label}{block.text}</h2>
    }
    case 'paragraph':
      return <p className="text-justify text-[13px] leading-relaxed" style={{ textIndent: '1.4em' }}>{inline(block.text || '')}</p>
    case 'list':
      return (
        <ul className="ml-5 list-disc space-y-1 text-[13px] leading-relaxed">
          {(block.items || []).map((it: string, i: number) => <li key={i}>{inline(it)}</li>)}
        </ul>
      )
    case 'equation': {
      counters.equation++
      return (
        <div className="flex items-center gap-2 text-[13px]">
          <div className="flex-1 text-center italic">{block.text}</div>
          {block.numbered !== false && <div className="text-neutral-500">({counters.equation})</div>}
        </div>
      )
    }
    case 'code':
      return (
        <pre className="overflow-x-auto rounded bg-neutral-100 p-3 text-[11px] leading-relaxed text-neutral-800"
             style={{ fontFamily: 'Consolas, "Courier New", monospace' }}>
          {block.text}
        </pre>
      )
    case 'table': {
      counters.table++
      const cols: string[] = block.columns || []
      const rows: string[][] = block.rows || []
      return (
        <figure className="my-2">
          <figcaption className="mb-1 text-center text-[11px] font-semibold uppercase tracking-wide">
            Table {counters.table}{block.caption ? ` — ${block.caption}` : ''}
          </figcaption>
          <table className="mx-auto border-collapse text-[12px]">
            <thead>
              <tr>{cols.map((c, i) => <th key={i} className="border-b-2 border-neutral-700 px-3 py-1 font-semibold">{c}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri}>{cols.map((_, ci) => <td key={ci} className="border-b border-neutral-300 px-3 py-1 text-center">{r[ci] ?? ''}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </figure>
      )
    }
    case 'figure': {
      counters.figure++
      return (
        <figure className="my-3 flex flex-col items-center">
          {block.chart ? <MiniChart chart={block.chart} />
            : <div className="flex h-32 w-full max-w-md items-center justify-center rounded border border-dashed border-neutral-300 text-neutral-400">figure</div>}
          <figcaption className="mt-1 text-center text-[11px]">
            <span className="font-semibold">Fig. {counters.figure}.</span> {block.caption}
          </figcaption>
        </figure>
      )
    }
    default:
      return null
  }
}

// **bold** / __bold__ / *italic* / _italic_ → real emphasis (as the DOCX renders it)
const EMPHASIS = /\*\*(.+?)\*\*|__(.+?)__|\*(.+?)\*|_(.+?)_/g
function inline(text: string): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  let key = 0
  let m: RegExpExecArray | null
  EMPHASIS.lastIndex = 0
  while ((m = EMPHASIS.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index))
    const bold = m[1] != null || m[2] != null
    const content = m[1] ?? m[2] ?? m[3] ?? m[4]
    out.push(bold ? <strong key={key++}>{content}</strong> : <em key={key++}>{content}</em>)
    last = EMPHASIS.lastIndex
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}
