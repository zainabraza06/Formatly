import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import clsx from 'clsx'
import { motion } from 'framer-motion'
import { ThemeToggle } from '../components/ThemeToggle'
import { useAuth } from '../context/AuthContext'

const NAV = [
  {
    to: '/app',
    label: 'Home',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
        <path fillRule="evenodd" d="M9.293 2.293a1 1 0 011.414 0l7 7A1 1 0 0117 11h-1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-3a1 1 0 00-1-1H9a1 1 0 00-1 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-6H3a1 1 0 01-.707-1.707l7-7z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    to: '/app/compose',
    label: 'Compose',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
        <path d="M5.433 13.917l1.262-3.155A4 4 0 017.58 9.42l6.92-6.918a2.121 2.121 0 013 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 01-.65-.65z" />
        <path d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0010 3H4.75A2.75 2.75 0 002 5.75v9.5A2.75 2.75 0 004.75 18h9.5A2.75 2.75 0 0017 15.25V10a.75.75 0 00-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5z" />
      </svg>
    ),
  },
  {
    to: '/app/documents',
    label: 'My Uploads',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
        <path d="M3 3.5A1.5 1.5 0 014.5 2h3.879a1.5 1.5 0 011.06.44l1.122 1.12A1.5 1.5 0 0011.62 4H15.5A1.5 1.5 0 0117 5.5v2H3v-4z" />
        <path fillRule="evenodd" d="M3 9h14v5.5a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 013 14.5V9zm7 1.5a.75.75 0 01.75.75v1.19l.47-.47a.75.75 0 111.06 1.06l-1.75 1.75a.75.75 0 01-1.06 0l-1.75-1.75a.75.75 0 111.06-1.06l.47.47v-1.19A.75.75 0 0110 10.5z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    to: '/app/editor',
    label: 'Document OS',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
        <path fillRule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-3.62-3.622A1.5 1.5 0 0011.878 2H4.5zm2 6.5A.75.75 0 017.25 8h5.5a.75.75 0 010 1.5h-5.5A.75.75 0 016.5 8.5zm.75 2.5a.75.75 0 000 1.5h5.5a.75.75 0 000-1.5h-5.5z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    to: '/app/templates',
    label: 'Templates',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    to: '/app/files',
    label: 'Generated Files',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
        <path fillRule="evenodd" d="M2 6a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1H8a3 3 0 00-3 3v1.5a1.5 1.5 0 01-3 0V6z" clipRule="evenodd" />
        <path d="M6 12a2 2 0 012-2h8a2 2 0 012 2v2a2 2 0 01-2 2H2h2a2 2 0 002-2v-2z" />
      </svg>
    ),
  },
  {
    to: '/app/settings',
    label: 'Settings',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
        <path fillRule="evenodd" d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
      </svg>
    ),
  },
]

export function DashboardLayout({
  theme,
  onToggleTheme,
}: {
  theme: 'light' | 'dark'
  onToggleTheme: () => void
}) {
  const [navOpen, setNavOpen] = useState(false)
  const { user, logout } = useAuth()

  return (
    <div className="min-h-full bg-canvas text-ink">
      <div className="relative mx-auto flex min-h-screen max-w-7xl">

        {/* backdrop — click to close the overlaying sidebar */}
        {navOpen && (
          <button
            aria-label="Close menu"
            onClick={() => setNavOpen(false)}
            className="fixed inset-0 z-30 cursor-default bg-ink/20"
          />
        )}

        {/* ── Sidebar (overlays content when open) ── */}
        <aside
          className={clsx(
            'fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-line bg-surface px-3 py-4 transition-transform duration-200',
            navOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          {/* Brand */}
          <div className="flex items-center gap-2.5 px-2">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent text-[13px] font-semibold text-accent-fg">
              F
            </div>
            <div className="text-sm font-semibold tracking-tight">Formatly</div>
          </div>

          {/* Nav */}
          <nav className="mt-6 flex flex-1 flex-col gap-0.5">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/app'}
                onClick={() => setNavOpen(false)}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-surface-2 font-medium text-ink'
                      : 'text-muted hover:bg-surface-2 hover:text-ink',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span className={clsx('shrink-0', isActive ? 'text-ink' : 'text-faint')}>
                      {item.icon}
                    </span>
                    {item.label}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Account */}
          <div className="mt-4 border-t border-line pt-3">
            <div className="flex items-center gap-2.5 px-1">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line bg-surface-2 text-xs font-semibold uppercase text-ink">
                {(user?.name || user?.email || '?').slice(0, 1)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-medium text-ink">{user?.name || 'Account'}</div>
                <div className="truncate text-[10px] text-faint">{user?.email}</div>
              </div>
              <button
                onClick={logout}
                title="Sign out"
                className="flex h-7 w-7 items-center justify-center rounded-md text-faint transition-colors hover:bg-surface-2 hover:text-ink"
              >
                <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                  <path fillRule="evenodd" d="M3 4.75A1.75 1.75 0 014.75 3h4.5a.75.75 0 010 1.5h-4.5a.25.25 0 00-.25.25v10.5c0 .138.112.25.25.25h4.5a.75.75 0 010 1.5h-4.5A1.75 1.75 0 013 15.25V4.75zm9.72 1.72a.75.75 0 011.06 0l3 3a.75.75 0 010 1.06l-3 3a.75.75 0 11-1.06-1.06l1.72-1.72H8a.75.75 0 010-1.5h6.44l-1.72-1.72a.75.75 0 010-1.06z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        </aside>

        {/* ── Main ── */}
        <main className="flex flex-1 flex-col">
          <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-canvas/90 px-4 py-3 backdrop-blur-sm sm:px-6">
            <button
              onClick={() => setNavOpen((o) => !o)}
              aria-label={navOpen ? 'Close menu' : 'Open menu'}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-surface text-muted transition-colors hover:bg-surface-2 hover:text-ink"
            >
              <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
                {navOpen ? (
                  <path fillRule="evenodd" d="M4.28 4.28a.75.75 0 011.06 0L10 8.94l4.66-4.66a.75.75 0 111.06 1.06L11.06 10l4.66 4.66a.75.75 0 11-1.06 1.06L10 11.06l-4.66 4.66a.75.75 0 01-1.06-1.06L8.94 10 4.28 5.34a.75.75 0 010-1.06z" clipRule="evenodd" />
                ) : (
                  <path fillRule="evenodd" d="M2.5 5.5A.75.75 0 013.25 5h13.5a.75.75 0 010 1.5H3.25a.75.75 0 01-.75-.75zm0 4.5A.75.75 0 013.25 9.5h13.5a.75.75 0 010 1.5H3.25A.75.75 0 012.5 10zm.75 3.75a.75.75 0 000 1.5h13.5a.75.75 0 000-1.5H3.25z" clipRule="evenodd" />
                )}
              </svg>
            </button>

            <div className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent text-[11px] font-semibold text-accent-fg sm:hidden">
                F
              </div>
              <span className="text-sm font-medium text-ink">Formatly</span>
            </div>

            <div className="flex-1" />
            <ThemeToggle mode={theme} onToggle={onToggleTheme} />
          </header>

          <motion.div
            key="outlet"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="mx-auto w-full max-w-6xl flex-1 p-4 sm:p-6"
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  )
}
