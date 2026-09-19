/**
 * Where the session token lives.
 *
 * Its own module because both sides of the API plumbing need it: `http.ts`
 * attaches it to every request, and `auth.ts` is what puts it there after a
 * sign-in. With it in either of those two, they import each other — a cycle
 * that happens to work today and breaks the moment one of them reads the other
 * at module load.
 */
const TOKEN_KEY = 'docos.token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null // private mode: the session simply does not persist
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch { /* private mode */ }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch { /* private mode */ }
}
