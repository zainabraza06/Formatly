import { getToken } from './token'
import { apiErrorFrom } from './errors'

/**
 * Where the API is, and how to call it.
 *
 * Four files used to carry their own copy of this — the base URL, the
 * development-port rule, the auth header, the response check — which meant
 * four places to change when any one of them was wrong, and they had already
 * drifted apart in how they read a failure.
 *
 * Empty base by default: every path is relative, so the page calls whatever
 * origin served it, which in a deployment is the API itself. Except on Vite's
 * own port, where the page is served by Vite and the API is on another one.
 *
 * Decided here rather than at build time: `import.meta.env.DEV` survived
 * minification once, and a page that calls 127.0.0.1 from a real host fails in
 * a way that reads like the server being down.
 */
export const API_URL: string =
  import.meta.env.VITE_API_URL || (window.location.port === '5173' ? 'http://127.0.0.1:8000' : '')

/** A WebSocket URL for the same API — absolute, and wss on an https page. */
export function wsUrl(path: string): string {
  const base = (API_URL || window.location.origin).replace(/^http/, 'ws')
  return `${base}${path}`
}

/** Every route is owner-scoped, so the token travels with the request. */
export function authHeaders(extra?: HeadersInit): Record<string, string> {
  const token = getToken()
  return {
    ...(extra as Record<string, string> | undefined),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

/** A request that carries the token and throws an ApiError on failure. */
export async function request(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(`${API_URL}${path}`, { ...init, headers: authHeaders(init?.headers) })
  if (!res.ok) throw await apiErrorFrom(res)
  return res
}

/** The JSON body of a successful request. */
export async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  return (await request(path, init)).json() as Promise<T>
}

/** A JSON request with a JSON body, which is most of the writes. */
export async function sendJson<T>(
  path: string,
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  body?: unknown,
  init?: RequestInit,
): Promise<T> {
  return getJson<T>(path, {
    ...init,
    method,
    headers: { 'Content-Type': 'application/json', ...(init?.headers as Record<string, string>) },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

/** The bytes of a successful request, for exports and previews. */
export async function getBlob(path: string, init?: RequestInit): Promise<Blob> {
  return (await request(path, init)).blob()
}

/**
 * Fetch a file with the token and hand it to the browser to save.
 *
 * A protected route cannot be reached by a plain link — following one lands on
 * `{"detail":"authentication required"}` instead of a file — so the bytes come
 * back here and the download is made from them.
 */
export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const res = await request(path)
  const disposition = res.headers.get('content-disposition') || ''
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition)
  saveBlob(await res.blob(), match ? decodeURIComponent(match[1]) : fallbackName)
}

/** Hand bytes to the browser to save under a name. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/** A filename that a file system will accept. */
export function safeFilename(title: string | undefined, fallback: string, ext: string): string {
  const base = (title || fallback).replace(/[/:*?"<>|]/g, '').trim() || fallback
  return `${base}.${ext}`
}
