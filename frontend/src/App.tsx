import { Suspense, useEffect, useMemo, useState } from 'react'
import { MotionConfig } from 'framer-motion'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import { RequireAuth } from './components/RequireAuth'
import { AuthProvider, useAuth } from './context/AuthContext'
import { CommandProvider } from './context/CommandContext'
import { Spinner, ToastProvider } from './components/ui'
import type { Command } from './components/ui/CommandPalette'
import { AppShell } from './layout/AppShell'
import { lazyRoute } from './lib/lazyRoute'
import { applyTheme, getInitialTheme, type ThemeMode } from './lib/theme'
import {
  ComposeIcon, DocumentsIcon, EditorIcon, MoonIcon, SettingsIcon, SignOutIcon, SunIcon,
} from './components/icons'

/* Each screen is its own chunk. The editor alone pulls in KaTeX and the whole
   document renderer, which nobody visiting the landing page should have to
   download first.

   `lazyRoute` rather than `lazy`: a deploy replaces every hashed chunk, so a
   tab left open across one asks for files that no longer exist. It reloads
   once, which is all that is needed, and gives up rather than looping. */
const LandingPage = lazyRoute(() => import('./pages/LandingPage').then((m) => ({ default: m.LandingPage })))
const Login = lazyRoute(() => import('./pages/Login').then((m) => ({ default: m.Login })))
const DocumentsPage = lazyRoute(() => import('./pages/DocumentsPage').then((m) => ({ default: m.DocumentsPage })))
const ComposePaper = lazyRoute(() => import('./pages/ComposePaper').then((m) => ({ default: m.ComposePaper })))
const DocumentEditor = lazyRoute(() => import('./pages/DocumentEditor').then((m) => ({ default: m.DocumentEditor })))
const Settings = lazyRoute(() => import('./pages/Settings').then((m) => ({ default: m.Settings })))

export default function App() {
  const [theme, setTheme] = useState<ThemeMode>(() => getInitialTheme())

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))

  return (
    <AuthProvider>
      <ToastProvider>
        {/* One place to honour the system's "less movement" setting: every
            animation in the app goes through Framer Motion or a CSS
            transition, and the stylesheet handles the second kind. */}
        <MotionConfig reducedMotion="user">
          {/* Outside the router, so a crash while rendering a screen still has
              something to render. */}
          <ErrorBoundary>
            <Shell theme={theme} onToggleTheme={toggleTheme} />
          </ErrorBoundary>
        </MotionConfig>
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
      <Suspense fallback={<ScreenLoading />}>
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
      </Suspense>
    </CommandProvider>
  )
}

/** Shown while a screen's code is on its way. Deliberately quiet: on a fast
 *  connection it is gone before it registers, and a skeleton of a screen we
 *  have not loaded yet would be a guess. */
function ScreenLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas">
      <Spinner size="lg" label="Loading" className="text-faint" />
    </div>
  )
}
