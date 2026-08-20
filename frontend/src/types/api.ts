export type StylePreset =
  | 'academic'
  | 'business'
  | 'research'
  | 'technical'
  | 'resume'
  | 'presentation'

export type Tone = 'formal' | 'simple' | 'technical'

export type ChartKind = 'bar' | 'line' | 'pie'

export type ChartSpec = {
  kind: ChartKind
  title?: string
  labels: string[]
  values: number[]
  x_label?: string
  y_label?: string
  explanation?: string
}

export type PipelineStep = {
  name: string
  status: 'pending' | 'running' | 'done' | 'error'
  detail?: string
}

export type DocumentSection = {
  id: string
  heading: string
  content: string
}

export type GenerateRequest = {
  prompt: string
  formatting_instructions: string
  style_preset: StylePreset
  tone: Tone
  include_toc: boolean
  include_title_page: boolean
  include_charts: boolean
  charts: ChartSpec[]
}

export type GenerateResponse = {
  document_id: string
  title: string
  outline: string[]
  sections: DocumentSection[]
  extracted_rules: Record<string, unknown>
  pipeline: PipelineStep[]
  suggested_charts: ChartSpec[]
}


export type Draft = {
  document_id: string
  title: string
  outline: string[]
  sections: DocumentSection[]
  extracted_rules: Record<string, unknown>
  style_preset: StylePreset
  tone: Tone
  include_title_page: boolean
  include_toc: boolean
  chart_pngs?: string[]
  chart_specs?: ChartSpec[]
  suggested_charts?: ChartSpec[]
}

export type RecentDocument = {
  document_id: string
  title: string
  style_preset: StylePreset
}

export type AnalyzeChartsResponse = {
  suggested_charts: ChartSpec[]
}
