import { NavLink, Outlet } from 'react-router-dom'
import clsx from 'clsx'
import { motion } from 'framer-motion'
import { ThemeToggle } from '../components/ThemeToggle'

const NAV = [
  { to: '/app', label: 'Home' },
  { to: '/app/new', label: 'New Document' },
  { to: '/app/templates', label: 'Templates' },
  { to: '/app/files', label: 'Generated Files' },
  { to: '/app/assistant', label: 'AI Assistant' },
  { to: '/app/settings', label: 'Settings' },
]

export function DashboardLayout({
  theme,
  onToggleTheme,
}: {
  theme: 'light' | 'dark'
  onToggleTheme: () => void
}) {
  return (
    <div className="min-h-full bg-gradient-to-br from-neutral-50 to-neutral-200 dark:from-neutral-950 dark:to-neutral-900">
      <div className="mx-auto flex min-h-screen max-w-7xl">
        <aside className="hidden w-64 shrink-0 border-r border-white/10 p-4 sm:block">
          <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-md dark:bg-white/5">
            <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
              DocPilot AI
            </div>
            <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
              Autonomous document production
            </div>
          </div>

          <nav className="mt-4 flex flex-col gap-2">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/app'}
                className={({ isActive }) =>
                  clsx(
                    'rounded-xl px-3 py-2 text-sm transition',
                    'border border-transparent',
                    isActive
                      ? 'bg-white/15 text-neutral-900 ring-1 ring-white/20 dark:text-neutral-100'
                      : 'text-neutral-700 hover:bg-white/10 dark:text-neutral-300',
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        <main className="flex-1 p-4 sm:p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="text-sm text-neutral-700 dark:text-neutral-300">
              Futuristic AI productivity tool
            </div>
            <ThemeToggle mode={theme} onToggle={onToggleTheme} />
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.25 }}
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  )
}
