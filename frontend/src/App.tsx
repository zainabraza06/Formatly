import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireAuth } from './components/RequireAuth'
import { AuthProvider } from './context/AuthContext'
import { DashboardLayout } from './layout/DashboardLayout'
import { applyTheme, getInitialTheme, type ThemeMode } from './lib/theme'
import { ComposePaper } from './pages/ComposePaper'
import { DashboardHome } from './pages/DashboardHome'
import { DocumentEditor } from './pages/DocumentEditor'
import { GeneratedFiles } from './pages/GeneratedFiles'
import { LandingPage } from './pages/LandingPage'
import { Login } from './pages/Login'
import { MyDocuments } from './pages/MyDocuments'
import { Settings } from './pages/Settings'

export default function App() {
  const [theme, setTheme] = useState<ThemeMode>(() => getInitialTheme())

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />

        <Route
          path="/app"
          element={
            <RequireAuth>
              <DashboardLayout
                theme={theme}
                onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
              />
            </RequireAuth>
          }
        >
          <Route index element={<DashboardHome />} />
          <Route path="compose" element={<ComposePaper />} />
          <Route path="documents" element={<MyDocuments />} />
          <Route path="editor" element={<DocumentEditor />} />
          {/* /app/new was the old generator — Compose supersedes it */}
          <Route path="new" element={<Navigate to="/app/compose" replace />} />
          <Route path="files" element={<GeneratedFiles />} />
          {/* The assistant is not a place you go — it lives in Document OS,
              where you prompt it while formatting a real document. */}
          <Route path="assistant" element={<Navigate to="/app/editor" replace />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
