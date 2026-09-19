import { useRef, useState } from 'react'
import { cn } from '../../lib/cn'
import { Button, Input } from '../ui'
import { ChevronDownIcon, PlusIcon, SparkIcon, TrashIcon } from '../icons'

/**
 * The sections the document will have, before a word of it is written.
 *
 * Fixing the structure first is the difference between reading a finished
 * document to find out what it decided to cover and deciding that yourself. It
 * stays optional: with no sections listed, the writer plans its own and says
 * so in as many words.
 */
export function OutlineEditor({
  sections,
  onChange,
  suggestion,
  disabled,
}: {
  sections: string[]
  onChange: (next: string[]) => void
  /** The outline offered for the chosen kind of document. */
  suggestion: string[]
  disabled?: boolean
}) {
  const [draft, setDraft] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const add = () => {
    const value = draft.trim()
    if (!value) return
    onChange([...sections, value])
    setDraft('')
    inputRef.current?.focus()
  }

  const move = (from: number, to: number) => {
    if (to < 0 || to >= sections.length) return
    const next = [...sections]
    const [item] = next.splice(from, 1)
    next.splice(to, 0, item)
    onChange(next)
  }

  const rename = (i: number, value: string) => {
    const next = [...sections]
    next[i] = value
    onChange(next)
  }

  return (
    <div className="space-y-3">
      {sections.length === 0 ? (
        <div className="rounded-lg border border-dashed border-line bg-surface-2/40 px-4 py-6 text-center">
          <p className="text-sm font-medium text-ink">The AI will plan the structure</p>
          <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-muted">
            Leave it this way and the writer decides what sections the document needs. Add
            your own below if the structure is already fixed — by a brief, a template or a
            supervisor.
          </p>
          {suggestion.length > 0 && (
            <Button
              variant="secondary"
              size="sm"
              className="mt-3"
              disabled={disabled}
              leadingIcon={<SparkIcon />}
              onClick={() => onChange(suggestion)}
            >
              Start from a typical outline
            </Button>
          )}
        </div>
      ) : (
        <ol className="space-y-1.5">
          {sections.map((section, i) => (
            <li key={i} className="flex items-center gap-2">
              <span className="w-5 shrink-0 text-right text-xs tabular-nums text-faint">{i + 1}</span>

              <Input
                value={section}
                onChange={(e) => rename(i, e.target.value)}
                aria-label={`Section ${i + 1} heading`}
                disabled={disabled}
                className="flex-1"
              />

              <div className="flex shrink-0 items-center">
                <Button
                  variant="ghost" size="sm" iconOnly
                  aria-label={`Move “${section}” up`}
                  disabled={disabled || i === 0}
                  onClick={() => move(i, i - 1)}
                  leadingIcon={<ChevronDownIcon className="h-4 w-4 rotate-180" />}
                />
                <Button
                  variant="ghost" size="sm" iconOnly
                  aria-label={`Move “${section}” down`}
                  disabled={disabled || i === sections.length - 1}
                  onClick={() => move(i, i + 1)}
                  leadingIcon={<ChevronDownIcon />}
                />
                <Button
                  variant="ghost" size="sm" iconOnly
                  aria-label={`Remove “${section}”`}
                  disabled={disabled}
                  onClick={() => onChange(sections.filter((_, n) => n !== i))}
                  leadingIcon={<TrashIcon />}
                  className="text-faint hover:text-danger"
                />
              </div>
            </li>
          ))}
        </ol>
      )}

      <div className={cn('flex gap-2', sections.length === 0 && 'pt-1')}>
        <Input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); add() }
          }}
          placeholder="Add a section — e.g. Methodology"
          aria-label="New section heading"
          disabled={disabled}
        />
        <Button
          variant="secondary"
          onClick={add}
          disabled={disabled || !draft.trim()}
          leadingIcon={<PlusIcon />}
        >
          Add
        </Button>
      </div>

      {sections.length > 0 && (
        <button
          type="button"
          onClick={() => onChange([])}
          disabled={disabled}
          className="text-xs text-faint underline-offset-2 hover:text-muted hover:underline"
        >
          Clear the outline and let the AI plan it
        </button>
      )}
    </div>
  )
}
