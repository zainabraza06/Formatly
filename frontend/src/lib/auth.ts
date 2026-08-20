// Token storage + auth API client.

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const TOKEN_KEY = 'docos.token'

export interface AuthUser {
  id: string
  email: string
  name: string
  created_at: string
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

async function json<T>(p: Promise<Response>): Promise<T> {
  const res = await p
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error((body as { detail?: string }).detail || `Request failed: ${res.status}`)
  }
  return body as T
}

export const authApi = {
  signup: (email: string, password: string, name: string) =>
    json<{ token: string; user: AuthUser }>(
      fetch(`${API_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name }),
      }),
    ),

  login: (email: string, password: string) =>
    json<{ token: string; user: AuthUser }>(
      fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      }),
    ),

  me: (token: string) =>
    json<AuthUser>(
      fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    ),

  updateName: (token: string, name: string) =>
    json<AuthUser>(
      fetch(`${API_URL}/auth/me`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name }),
      }),
    ),

  changePassword: (token: string, current_password: string, new_password: string) =>
    json<{ updated: boolean }>(
      fetch(`${API_URL}/auth/password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ current_password, new_password }),
      }),
    ),
}
