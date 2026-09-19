import { lazy, type ComponentType } from 'react'

/**
 * A lazily loaded screen that survives a deploy.
 *
 * Every build names its chunks by content hash, and a deploy replaces the lot.
 * A tab opened before the deploy is still running the old entry bundle, so the
 * first time it navigates to a screen it has not loaded yet it asks for a file
 * that no longer exists and gets a 404 — which React reports as a blank page
 * and "Failed to fetch dynamically imported module".
 *
 * There is nothing to retry: that file is gone for good. The page has to be
 * fetched again, which is safe because index.html is served with no-cache and
 * so comes back pointing at the new chunks.
 *
 * The reload happens once. If the very next attempt fails the same way, the
 * problem is not a stale tab — the file is missing from the deployment itself
 * — and reloading for ever would hide that behind a flickering page, so the
 * error is allowed through to the boundary, which says so and offers the
 * button.
 */
const RELOAD_KEY = 'formatly.chunk-reload'
const RELOAD_WINDOW_MS = 15_000

// The routes here take no props, which is the only shape this wraps.
export function lazyRoute<T extends ComponentType<Record<string, never>>>(
  load: () => Promise<{ default: T }>,
) {
  return lazy(async () => {
    try {
      const module = await load()
      // Loaded cleanly: whatever went wrong before is over.
      safeRemove(RELOAD_KEY)
      return module
    } catch (error) {
      if (!isChunkLoadError(error) || recentlyReloaded()) throw error

      safeSet(RELOAD_KEY, String(Date.now()))
      window.location.reload()

      // The page is going away; never resolve, so nothing renders in the
      // moment before it does.
      return new Promise<never>(() => {})
    }
  })
}

/** A module the browser could not fetch — as opposed to one that threw. */
export function isChunkLoadError(error: unknown): boolean {
  if (!(error instanceof Error)) return false
  return /dynamically imported module|Importing a module script failed|Failed to fetch|error loading dynamically imported module|ChunkLoadError/i
    .test(`${error.name} ${error.message}`)
}

function recentlyReloaded(): boolean {
  const last = Number(safeGet(RELOAD_KEY) ?? 0)
  return Number.isFinite(last) && Date.now() - last < RELOAD_WINDOW_MS
}

// Storage can throw in a private window, and a page that cannot recover from a
// deploy is still better than one that crashes trying.
function safeGet(key: string): string | null {
  try {
    return sessionStorage.getItem(key)
  } catch {
    return null
  }
}

function safeSet(key: string, value: string): void {
  try {
    sessionStorage.setItem(key, value)
  } catch { /* private mode */ }
}

function safeRemove(key: string): void {
  try {
    sessionStorage.removeItem(key)
  } catch { /* private mode */ }
}
