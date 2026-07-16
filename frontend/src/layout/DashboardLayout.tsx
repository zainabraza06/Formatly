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
    <div className="min-h-full bg-gradient-to-br from-neutral-50 via-white to-neutral-100 dark:from-neutral-950 dark:via-neutral-900 dark:to-neutral-950">
      {/* ambient glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-60 left-0 h-[500px] w-[500px] rounded-full bg-violet-500/6 blur-[100px]" />
      </div>

      <div className="relative mx-auto flex min-h-screen max-w-7xl">

        {/* backdrop — click to close the overlaying sidebar */}
        {navOpen && (
          <button
            aria-label="Close menu"
            onClick={() => setNavOpen(false)}
            className="absolute inset-0 z-30 cursor-default bg-black/20 backdrop-blur-[1px]"
          />
        )}

        {/* ── Sidebar (overlays content when open) ── */}
        <aside
          className={clsx(
            'absolute inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-neutral-200/60 bg-white/80 p-4 shadow-xl backdrop-blur-md transition-transform duration-300 dark:border-white/8 dark:bg-neutral-950/85',
            navOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >

          {/* Brand */}
          <div className="rounded-2xl border border-neutral-200/60 bg-white/60 p-4 shadow-sm backdrop-blur-sm dark:border-white/8 dark:bg-white/5">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-purple-600 shadow-md shadow-violet-500/30">
                <span className="text-sm font-bold text-white">F</span>
              </div>
              <div>
                <div className="text-sm font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
                  Formatly
                </div>
                <div className="text-[10px] text-neutral-500 dark:text-neutral-400">
                  AI Document Platform
                </div>
              </div>
            </div>
          </div>

          {/* Nav */}
          <nav className="mt-4 flex flex-1 flex-col gap-1">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/app'}
                onClick={() => setNavOpen(false)}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition-all',
                    isActive
                      ? 'bg-gradient-to-r from-violet-500/15 to-purple-500/10 font-semibold text-violet-700 ring-1 ring-violet-500/20 dark:text-violet-300'
                      : 'text-neutral-600 hover:bg-neutral-100/80 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-white/8 dark:hover:text-neutral-200',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span className={clsx('shrink-0 transition-colors', isActive ? 'text-violet-600 dark:text-violet-400' : '')}>
                      {item.icon}
                    </span>
                    {item.label}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Account */}
          <div className="mt-4 rounded-xl border border-neutral-200/60 bg-white/60 p-3 dark:border-white/8 dark:bg-white/5">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-600 to-purple-600 text-xs font-bold uppercase text-white">
                {(user?.name || user?.email || '?').slice(0, 1)}
              </div>
              <div className="min-w-0">
                <div className="truncate text-xs font-semibold text-neutral-900 dark:text-neutral-100">{user?.name || 'Account'}</div>
                <div className="truncate text-[10px] text-neutral-500">{user?.email}</div>
              </div>
            </div>
            <button
              onClick={logout}
              className="mt-2 w-full rounded-lg border border-neutral-200/60 bg-white/70 px-2 py-1.5 text-[11px] font-medium text-neutral-600 hover:bg-white dark:border-white/8 dark:bg-white/5 dark:text-neutral-300"
            >
              Sign out
            </button>
          </div>
        </aside>

        {/* ── Main ── */}
        <main className="flex flex-1 flex-col p-4 sm:p-6">
          <div className="mb-5 flex items-center justify-between gap-3">
            {/* Menu toggle */}
            <button
              onClick={() => setNavOpen((o) => !o)}
              aria-label={navOpen ? 'Close menu' : 'Open menu'}
              className="z-40 flex h-9 w-9 items-center justify-center rounded-xl border border-neutral-200/60 bg-white/70 text-neutral-700 shadow-sm transition-colors hover:bg-white dark:border-white/8 dark:bg-white/5 dark:text-neutral-200"
            >
              <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
                {navOpen ? (
                  <path fillRule="evenodd" d="M4.28 4.28a.75.75 0 011.06 0L10 8.94l4.66-4.66a.75.75 0 111.06 1.06L11.06 10l4.66 4.66a.75.75 0 11-1.06 1.06L10 11.06l-4.66 4.66a.75.75 0 01-1.06-1.06L8.94 10 4.28 5.34a.75.75 0 010-1.06z" clipRule="evenodd" />
                ) : (
                  <path fillRule="evenodd" d="M2.5 5.5A.75.75 0 013.25 5h13.5a.75.75 0 010 1.5H3.25a.75.75 0 01-.75-.75zm0 4.5A.75.75 0 013.25 9.5h13.5a.75.75 0 010 1.5H3.25A.75.75 0 012.5 10zm.75 3.75a.75.75 0 000 1.5h13.5a.75.75 0 000-1.5H3.25z" clipRule="evenodd" />
                )}
              </svg>
            </button>

            {/* Mobile brand */}
            <div className="flex items-center gap-2 sm:hidden">
              <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-purple-600">
                <span className="text-xs font-bold text-white">F</span>
              </div>
              <span className="text-sm font-bold text-neutral-900 dark:text-neutral-100">Formatly</span>
            </div>

            <div className="hidden text-xs text-neutral-500 dark:text-neutral-400 sm:block">
              AI document production platform
            </div>

            <ThemeToggle mode={theme} onToggle={onToggleTheme} />
          </div>

          <motion.div
            key="outlet"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="flex-1"
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  )
}
