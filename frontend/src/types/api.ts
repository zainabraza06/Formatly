export type StylePreset =
  | 'academic'
  | 'business'
  | 'research'
  | 'technical'
  | 'resume'
  | 'presentation'

/** One generated paper, as the library lists it. */
export type RecentDocument = {
  document_id: string
  title: string
  style_preset: StylePreset
  /** ISO timestamp. The server has always sent it; nothing used to read it. */
  created_at?: string
}
