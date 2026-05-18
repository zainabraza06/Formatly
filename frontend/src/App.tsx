import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { DashboardLayout } from './layout/DashboardLayout'
import { applyTheme, getInitialTheme, type ThemeMode } from './lib/theme'
import { AIAssistant } from './pages/AIAssistant'
import { DashboardHome } from './pages/DashboardHome'
import { GeneratedFiles } from './pages/GeneratedFiles'
import { LandingPage } from './pages/LandingPage'
import { NewDocument } from './pages/NewDocument'
import { Settings } from './pages/Settings'
import { Templates } from './pages/Templates'

export default function App() {
  const [theme, setTheme] = useState<ThemeMode>(() => getInitialTheme())

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />

      <Route
        path="/app"
        element={
          <DashboardLayout
            theme={theme}
            onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
          />
        }
      >
        <Route index element={<DashboardHome />} />
        <Route path="new" element={<NewDocument />} />
        <Route path="templates" element={<Templates />} />
        <Route path="files" element={<GeneratedFiles />} />
        <Route path="assistant" element={<AIAssistant />} />
        <Route path="settings" element={<Settings />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
