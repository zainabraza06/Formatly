import { useEffect, useMemo, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { RequireAuth } from './components/RequireAuth'
import { AuthProvider, useAuth } from './context/AuthContext'
import { CommandProvider } from './context/CommandContext'
import { ToastProvider } from './components/ui'
import type { Command } from './components/ui/CommandPalette'
import { AppShell } from './layout/AppShell'
import { applyTheme, getInitialTheme, type ThemeMode } from './lib/theme'
import {
  ComposeIcon, DocumentsIcon, EditorIcon, MoonIcon, SettingsIcon, SignOutIcon, SunIcon,
} from './components/icons'
import { ComposePaper } from './pages/ComposePaper'
import { DocumentEditor } from './pages/DocumentEditor'
import { DocumentsPage } from './pages/DocumentsPage'
import { LandingPage } from './pages/LandingPage'
import { Login } from './pages/Login'
import { Settings } from './pages/Settings'

export default function App() {
  const [theme, setTheme] = useState<ThemeMode>(() => getInitialTheme())

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))

  return (
    <AuthProvider>
      <ToastProvider>
        <Shell theme={theme} onToggleTheme={toggleTheme} />
      </ToastProvider>
    </AuthProvider>
  )
}

/**
 * Routes, plus the commands that are available everywhere. Screens add their
 * own on top — see `useRegisterCommands`.
 */
function Shell({ theme, onToggleTheme }: { theme: ThemeMode; onToggleTheme: () => void }) {
  const navigate = useNavigate()
  const { logout, user } = useAuth()

  const globalCommands = useMemo<Command[]>(() => [
    { id: 'go-documents', group: 'Go to', label: 'Documents', icon: <DocumentsIcon />,
      keywords: 'files list library', run: () => navigate('/app') },
    { id: 'go-compose', group: 'Go to', label: 'Generate a document', icon: <ComposeIcon />,
      keywords: 'new paper write compose ai', run: () => navigate('/app/compose') },
    { id: 'go-editor', group: 'Go to', label: 'Editor', icon: <EditorIcon />,
      keywords: 'document os format edit', run: () => navigate('/app/editor') },
    { id: 'go-settings', group: 'Go to', label: 'Settings', icon: <SettingsIcon />,
      keywords: 'account profile password', run: () => navigate('/app/settings') },
    { id: 'toggle-theme', group: 'Preferences',
      label: theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme',
      icon: theme === 'dark' ? <SunIcon /> : <MoonIcon />,
      keywords: 'dark light mode appearance', run: onToggleTheme },
    ...(user ? [{
      id: 'sign-out', group: 'Account', label: 'Sign out', icon: <SignOutIcon />,
      keywords: 'log out leave', run: logout,
    }] : []),
  ], [navigate, theme, onToggleTheme, logout, user])

  return (
    <CommandProvider globalCommands={globalCommands}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />

        <Route
          path="/app"
          element={
            <RequireAuth>
              <AppShell theme={theme} onToggleTheme={onToggleTheme} />
            </RequireAuth>
          }
        >
          <Route index element={<DocumentsPage />} />
          <Route path="compose" element={<ComposePaper />} />
          <Route path="editor" element={<DocumentEditor />} />
          <Route path="settings" element={<Settings />} />

          {/* Three screens used to list documents: the home page's "recent",
              "My Uploads" and "Generated Files". They are one screen now, and
              the old addresses still work. */}
          <Route path="documents" element={<Navigate to="/app" replace />} />
          <Route path="files" element={<Navigate to="/app" replace />} />
          <Route path="new" element={<Navigate to="/app/compose" replace />} />
          <Route path="assistant" element={<Navigate to="/app/editor" replace />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </CommandProvider>
  )
}
