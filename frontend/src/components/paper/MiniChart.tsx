// Lightweight SVG charts for the document preview. The DOCX embeds matplotlib
// PNGs; here we draw the same data as clean inline SVG so the preview shows real
// figures rather than placeholders. Matches the backend palette.

const PALETTE = ['#4f86f7', '#22c55e', '#f43f5e', '#a855f7', '#f59e0b', '#06b6d4', '#84cc16', '#ec4899']

interface Chart {
  kind: string
  title?: string
  x_label?: string
  y_label?: string
  labels?: string[]
  values?: number[]
  series?: { name?: string; values?: number[] }[]
}

const W = 360
const H = 220
const PAD = { top: 20, right: 16, bottom: 34, left: 34 }

export function MiniChart({ chart }: { chart: Chart }) {
  const kind = (chart.kind || 'bar').toLowerCase()
  const body =
    kind === 'pie' ? <Pie chart={chart} />
    : kind === 'line' ? <Line chart={chart} />
    : kind === 'scatter' ? <Scatter chart={chart} />
    : kind === 'grouped_bar' ? <Grouped chart={chart} />
    : <Bars chart={chart} />

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full max-w-md" role="img"
         aria-label={chart.title || 'chart'}>
      {chart.title && (
        <text x={W / 2} y={13} textAnchor="middle" className="fill-neutral-700"
              style={{ fontSize: 11, fontWeight: 600 }}>{chart.title}</text>
      )}
      {body}
    </svg>
  )
}

const plotW = W - PAD.left - PAD.right
const plotH = H - PAD.top - PAD.bottom

function axes(maxV: number) {
  return (
    <>
      <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + plotH} stroke="#d4d4d4" />
      <line x1={PAD.left} y1={PAD.top + plotH} x2={PAD.left + plotW} y2={PAD.top + plotH} stroke="#d4d4d4" />
      <text x={PAD.left - 4} y={PAD.top + 4} textAnchor="end" className="fill-neutral-400" style={{ fontSize: 8 }}>
        {fmt(maxV)}
      </text>
    </>
  )
}

function Bars({ chart }: { chart: Chart }) {
  const values = (chart.values || []).map(Number)
  const labels = chart.labels || values.map((_, i) => `${i + 1}`)
  if (!values.length) return <Empty />
  const max = Math.max(...values, 0) || 1
  const bw = plotW / values.length
  return (
    <>
      {axes(max)}
      {values.map((v, i) => {
        const h = (v / max) * plotH
        const x = PAD.left + i * bw + bw * 0.18
        const y = PAD.top + plotH - h
        return (
          <g key={i}>
            <rect x={x} y={y} width={bw * 0.64} height={h} rx={2} fill={PALETTE[i % PALETTE.length]} />
            <text x={x + bw * 0.32} y={y - 3} textAnchor="middle" className="fill-neutral-600" style={{ fontSize: 8 }}>{fmt(v)}</text>
            <text x={x + bw * 0.32} y={PAD.top + plotH + 11} textAnchor="middle" className="fill-neutral-500" style={{ fontSize: 8 }}>{trunc(labels[i])}</text>
          </g>
        )
      })}
    </>
  )
}

function Line({ chart }: { chart: Chart }) {
  const values = (chart.values || []).map(Number)
  const labels = chart.labels || values.map((_, i) => `${i + 1}`)
  if (!values.length) return <Empty />
  const max = Math.max(...values, 0) || 1
  const step = values.length > 1 ? plotW / (values.length - 1) : 0
  const pts = values.map((v, i) => [PAD.left + i * step, PAD.top + plotH - (v / max) * plotH] as const)
  return (
    <>
      {axes(max)}
      <polyline points={pts.map((p) => p.join(',')).join(' ')} fill="none" stroke={PALETTE[0]} strokeWidth={2} />
      {pts.map(([x, y], i) => (
        <g key={i}>
          <circle cx={x} cy={y} r={2.6} fill="#fff" stroke={PALETTE[0]} strokeWidth={1.6} />
          <text x={x} y={PAD.top + plotH + 11} textAnchor="middle" className="fill-neutral-500" style={{ fontSize: 8 }}>{trunc(labels[i])}</text>
        </g>
      ))}
    </>
  )
}

function Scatter({ chart }: { chart: Chart }) {
  const ys = (chart.values || []).map(Number)
  if (!ys.length) return <Empty />
  const xs = (chart.labels || []).map(Number)
  const useIndex = xs.length < ys.length || xs.some((n) => Number.isNaN(n))
  const xv = ys.map((_, i) => (useIndex ? i : xs[i]))
  const maxY = Math.max(...ys, 0) || 1
  const maxX = Math.max(...xv, 1)
  return (
    <>
      {axes(maxY)}
      {ys.map((y, i) => (
        <circle key={i} cx={PAD.left + (xv[i] / maxX) * plotW} cy={PAD.top + plotH - (y / maxY) * plotH}
                r={3} fill={PALETTE[0]} opacity={0.8} />
      ))}
    </>
  )
}

function Grouped({ chart }: { chart: Chart }) {
  const series = (chart.series || []).filter((s) => (s.values || []).length)
  const labels = chart.labels || []
  if (!series.length) return <Bars chart={chart} />
  const groups = Math.max(...series.map((s) => s.values!.length), labels.length)
  const max = Math.max(...series.flatMap((s) => s.values!.map(Number)), 0) || 1
  const gw = plotW / groups
  const bw = (gw * 0.7) / series.length
  return (
    <>
      {axes(max)}
      {Array.from({ length: groups }).map((_, gi) => (
        <g key={gi}>
          {series.map((s, si) => {
            const v = Number(s.values![gi] ?? 0)
            const h = (v / max) * plotH
            const x = PAD.left + gi * gw + gw * 0.15 + si * bw
            return <rect key={si} x={x} y={PAD.top + plotH - h} width={bw * 0.9} height={h} rx={1.5}
                         fill={PALETTE[si % PALETTE.length]} />
          })}
          <text x={PAD.left + gi * gw + gw / 2} y={PAD.top + plotH + 11} textAnchor="middle"
                className="fill-neutral-500" style={{ fontSize: 8 }}>{trunc(labels[gi] || `${gi + 1}`)}</text>
        </g>
      ))}
      {/* legend */}
      {series.map((s, si) => (
        <g key={si} transform={`translate(${PAD.left + si * 82}, ${H - 6})`}>
          <rect width={7} height={7} y={-7} rx={1.5} fill={PALETTE[si % PALETTE.length]} />
          <text x={10} y={-1} className="fill-neutral-500" style={{ fontSize: 8 }}>{trunc(s.name || `S${si + 1}`, 10)}</text>
        </g>
      ))}
    </>
  )
}

function Pie({ chart }: { chart: Chart }) {
  const values = (chart.values || []).map(Number).filter((v) => v > 0)
  const labels = chart.labels || []
  if (!values.length) return <Empty />
  const total = values.reduce((a, b) => a + b, 0)
  const cx = PAD.left + plotW / 2 - 40
  const cy = PAD.top + plotH / 2
  const r = Math.min(plotW, plotH) / 2 - 6
  let angle = -Math.PI / 2
  return (
    <>
      {values.map((v, i) => {
        const slice = (v / total) * Math.PI * 2
        const x1 = cx + r * Math.cos(angle)
        const y1 = cy + r * Math.sin(angle)
        angle += slice
        const x2 = cx + r * Math.cos(angle)
        const y2 = cy + r * Math.sin(angle)
        const large = slice > Math.PI ? 1 : 0
        return <path key={i} d={`M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} Z`}
                     fill={PALETTE[i % PALETTE.length]} />
      })}
      {values.map((v, i) => (
        <g key={i} transform={`translate(${cx + r + 14}, ${cy - r + i * 14})`}>
          <rect width={8} height={8} rx={1.5} fill={PALETTE[i % PALETTE.length]} />
          <text x={12} y={7} className="fill-neutral-600" style={{ fontSize: 8 }}>
            {trunc(labels[i] || `${i + 1}`, 12)} {Math.round((v / total) * 100)}%
          </text>
        </g>
      ))}
    </>
  )
}

function Empty() {
  return <text x={W / 2} y={H / 2} textAnchor="middle" className="fill-neutral-400" style={{ fontSize: 10 }}>no data</text>
}

function fmt(n: number): string {
  if (!isFinite(n)) return '0'
  return Number.isInteger(n) ? String(n) : n.toFixed(2)
}
function trunc(s: string, n = 8): string {
  s = String(s ?? '')
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}
