/**
 * What went wrong, in words a person can act on.
 *
 * Every API client throws an `ApiError` carrying the status, so the screens do
 * not have to read HTTP out of a string. `explain` turns any of them — plus the
 * failures that never reach the server at all — into a title, a detail, and
 * whether trying again could possibly help.
 */
export class ApiError extends Error {
  readonly status: number
  /** The server's own one-line technical note, when it sent one. */
  readonly hint?: string
  /** The server said this is worth retrying (a 503 from a database outage). */
  readonly retryable: boolean

  constructor(status: number, message: string, options?: { hint?: string; retryable?: boolean }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.hint = options?.hint
    this.retryable = options?.retryable ?? status >= 500
  }
}

export interface Explained {
  title: string
  detail: string
  /** Trying the same thing again could work. */
  retryable: boolean
  /** The session is gone: the only way forward is signing in again. */
  unauthorized: boolean
}

/** True for a request the app itself called off — never an error to report. */
export function isAbort(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === 'AbortError') ||
    (error instanceof Error && error.name === 'AbortError')
  )
}

export function explain(error: unknown, doing = 'that'): Explained {
  // The browser could not reach the server at all: no status, no body. This is
  // the one people actually see most — a laptop asleep, a VPN, a dead API.
  if (error instanceof TypeError || (error instanceof Error && /fetch|network/i.test(error.message))) {
    return {
      title: 'Cannot reach the Formatly server',
      detail: 'The request never arrived. Check your connection, and whether the server is running.',
      retryable: true,
      unauthorized: false,
    }
  }

  if (error instanceof ApiError) {
    const server = error.message?.trim()

    if (error.status === 401) {
      return {
        title: 'Your session has ended',
        detail: 'Sign in again to carry on. Nothing you have saved is affected.',
        retryable: false,
        unauthorized: true,
      }
    }

    if (error.status === 403) {
      return {
        title: 'That is not yours to open',
        detail: server || 'This document belongs to another account.',
        retryable: false,
        unauthorized: false,
      }
    }

    if (error.status === 404) {
      return {
        title: 'That document is gone',
        detail: server || 'It may have been deleted from another tab or another device.',
        retryable: false,
        unauthorized: false,
      }
    }

    if (error.status === 413) {
      return {
        title: 'That file is too large',
        detail: server || 'Try a smaller document.',
        retryable: false,
        unauthorized: false,
      }
    }

    if (error.status === 422 || error.status === 400) {
      return {
        title: `Could not ${doing}`,
        detail: server || 'The server would not accept that request.',
        retryable: false,
        unauthorized: false,
      }
    }

    if (error.status === 503) {
      // A 503 from this API is a dependency being down — the database, or
      // LibreOffice for a PDF — and the server says which in its detail.
      return {
        title: 'Formatly is temporarily unavailable',
        detail: [server || 'A service it depends on is not responding.', error.hint]
          .filter(Boolean)
          .join(' '),
        retryable: true,
        unauthorized: false,
      }
    }

    if (error.status >= 500) {
      return {
        title: 'The server hit an error',
        detail: server && server !== 'Internal Server Error'
          ? server
          : 'Something failed on the server. If it keeps happening, the server log will say what.',
        retryable: true,
        unauthorized: false,
      }
    }

    return {
      title: `Could not ${doing}`,
      detail: server || `The request failed (${error.status}).`,
      retryable: error.retryable,
      unauthorized: false,
    }
  }

  return {
    title: `Could not ${doing}`,
    detail: error instanceof Error && error.message
      ? error.message
      : 'Something went wrong. Please try again.',
    retryable: true,
    unauthorized: false,
  }
}

/**
 * Build an ApiError from a response the caller has already decided is a
 * failure. Reads the API's shape — `detail`, and `cause`/`retryable` where the
 * server sends them — and falls back to the body text for anything else,
 * including a proxy's HTML error page.
 */
export async function apiErrorFrom(res: Response): Promise<ApiError> {
  let detail = ''
  let hint: string | undefined
  let retryable: boolean | undefined

  try {
    const body = await res.clone().json()
    if (typeof body?.detail === 'string') detail = body.detail
    else if (Array.isArray(body?.detail)) {
      // FastAPI validation errors arrive as a list of objects.
      detail = body.detail.map((d: { msg?: string }) => d?.msg).filter(Boolean).join('; ')
    }
    if (typeof body?.cause === 'string') hint = body.cause
    if (typeof body?.retryable === 'boolean') retryable = body.retryable
  } catch {
    const text = await res.text().catch(() => '')
    // An HTML page here means something in front of the API answered, not the
    // API; its markup is no use to anybody.
    detail = text && !text.trimStart().startsWith('<') ? text : ''
  }

  return new ApiError(res.status, detail || `Request failed: ${res.status}`, { hint, retryable })
}
