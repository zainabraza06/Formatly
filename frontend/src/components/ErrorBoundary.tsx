import { Component, type ErrorInfo, type ReactNode } from 'react'
import { isChunkLoadError } from '../lib/lazyRoute'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

/**
 * The last thing between a crash and a blank page.
 *
 * Two failures end up here and they need different words. A screen whose code
 * could not be fetched is almost always a tab left open across a deploy — the
 * answer is to reload, and `lazyRoute` has usually done that already, so
 * arriving here means reloading did not work. Anything else is a bug, and
 * saying so plainly beats a white rectangle.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // The console is where whoever is debugging this will look first.
    console.error('Formatly crashed:', error, info.componentStack)
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    const stale = isChunkLoadError(error)

    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas p-4">
        <div className="w-full max-w-md rounded-xl border border-line bg-surface p-6 shadow-sm">
          <h1 className="text-lg font-semibold text-ink">
            {stale ? 'This page is out of date' : 'Something went wrong'}
          </h1>

          <p className="mt-2 text-sm leading-relaxed text-muted">
            {stale
              ? 'Formatly was updated while this tab was open, and part of the old version is no longer on the server. Reloading loads the new one. Nothing you have saved is affected.'
              : 'The screen could not be drawn. Your documents are unaffected — they live on the server, not in this page.'}
          </p>

          {!stale && (
            <p className="mt-3 break-words rounded-md border border-line bg-surface-2 px-3 py-2 font-mono text-2xs text-muted">
              {error.message}
            </p>
          )}

          <div className="mt-5 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="inline-flex h-9 items-center rounded-md bg-brand px-3.5 text-sm font-medium text-brand-fg transition-colors hover:bg-brand-hover"
            >
              Reload the page
            </button>
            <a
              href="/app"
              className="inline-flex h-9 items-center rounded-md border border-line bg-surface px-3.5 text-sm font-medium text-ink transition-colors hover:bg-surface-2"
            >
              Go to my documents
            </a>
          </div>
        </div>
      </div>
    )
  }
}
