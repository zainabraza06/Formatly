// The auth API client. Token storage is in token.ts, which both this and the
// request plumbing depend on.
import { getJson, sendJson } from './http'

export { clearToken, getToken, setToken } from './token'

export interface AuthUser {
  id: string
  email: string
  name: string
  created_at: string
}


export const authApi = {
  signup: (email: string, password: string, name: string) =>
    sendJson<{ token: string; user: AuthUser }>('/auth/signup', 'POST', { email, password, name }),

  login: (email: string, password: string) =>
    sendJson<{ token: string; user: AuthUser }>('/auth/login', 'POST', { email, password }),

  me: (token: string) =>
    getJson<AuthUser>('/auth/me', { headers: { Authorization: `Bearer ${token}` } }),

  updateName: (token: string, name: string) =>
    sendJson<AuthUser>('/auth/me', 'PATCH', { name }, {
      headers: { Authorization: `Bearer ${token}` },
    }),

  changePassword: (token: string, current_password: string, new_password: string) =>
    sendJson<{ ok: boolean }>('/auth/password', 'POST', { current_password, new_password }, {
      headers: { Authorization: `Bearer ${token}` },
    }),
}
