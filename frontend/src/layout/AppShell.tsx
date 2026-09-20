import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { cn } from '../lib/cn'
import { trapTab } from '../lib/focus'
import { useAuth } from '../context/AuthContext'
import { useCommands } from '../context/command-context'
import { Button, Dropdown, Tooltip } from '../components/ui'
import {
  ComposeIcon, DocumentsIcon, EditorIcon, MenuIcon, MoonIcon, SearchIcon,
  SettingsIcon, SidebarIcon, SignOutIcon, SunIcon,
} from '../components/icons'
import { Logo } from '../components/Logo'

const NAV = [
  { to: '/app', end: true, label: 'Documents', icon: DocumentsIcon },
  { to: '/app/compose', end: false, label: 'Generate', icon: ComposeIcon },
  { to: '/app/editor', end: false, label: 'Editor', icon: EditorIcon },
  { to: '/app/settings', end: false, label: 'Settings', icon: SettingsIcon },
]

const RAIL_KEY = 'formatly.sidebar.collapsed'

/**
 * The application frame: navigation that stays put on a desktop, a drawer on a
 * phone, and one scroll region for whatever screen is open.
 *
 * The sidebar used to float over the content at every width, which meant a
 * 1536px monitor still got a hamburger menu, and every navigation covered the
 * thing it was navigating to. Here it is a column from 1024px up — collapsible
 * to an icon rail for anyone who wants the width back — and a real dialog
 * below that, with Escape, a focus trap and the focus handed back on close.
 */
export function AppShell({
  theme,
  onToggleTheme,
}: {
  theme: 'light' | 'dark'
  onToggleTheme: () => void
}) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(RAIL_KEY) === '1',
  )
  const { user, logout } = useAuth()
  const commands = useCommands()
  const navigate = useNavigate()
  const location = useLocation()
  const drawerRef = useRef<HTMLDivElement>(null)
  const openerRef = useRef<HTMLButtonElement>(null)

  const toggleRail = useCallback(() => {
    setCollapsed((c) => {
      localStorage.setItem(RAIL_KEY, c ? '0' : '1')
      return !c
    })
  }, [])

  useEffect(() => {
    if (!drawerOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setDrawerOpen(false)
    }
    document.addEventListener('keydown', onKey)
    const first = drawerRef.current?.querySelector<HTMLElement>('a, button')
    first?.focus()
    // Captured now: by the time this runs, the button may be a different node.
    const opener = openerRef.current
    return () => {
      document.removeEventListener('keydown', onKey)
      opener?.focus()
    }
  }, [drawerOpen])

  const nav = (
    <SidebarNav collapsed={collapsed} onNavigate={() => setDrawerOpen(false)} />
  )

  const accountItems = [
    {
      id: 'settings',
      label: 'Account settings',
      icon: <SettingsIcon />,
      onSelect: () => navigate('/app/settings'),
    },
    {
      id: 'signout',
      label: 'Sign out',
      icon: <SignOutIcon />,
      destructive: true,
      onSelect: logout,
    },
  ]

  return (
    <div className="flex h-screen overflow-hidden bg-canvas text-ink">
      <a href="#main" className="skip-link rounded-md bg-brand px-3 py-2 text-sm font-medium text-brand-fg shadow-lg">
        Skip to content
      </a>

      {/* ── Desktop column ───────────────────────────────────────────────── */}
      <aside
        className={cn(
          'hidden shrink-0 flex-col border-r border-line bg-surface transition-[width] duration-slow ease-out lg:flex',
          collapsed ? 'w-16' : 'w-60',
        )}
      >
        <div className={cn('flex h-12 items-center gap-2 px-3', collapsed && 'justify-center px-0')}>
          <Logo compact={collapsed} />
        </div>
        <div className="flex-1 overflow-y-auto px-2 py-1">{nav}</div>

        <div className="border-t border-line p-2">
          {user && (
            <div className={cn('mb-1', collapsed && 'flex justify-center')}>
              <Dropdown
                label="Account menu"
                align="start"
                triggerVariant="ghost"
                triggerSize="md"
                triggerClassName={cn('w-full justify-start gap-2 px-2', collapsed && 'w-auto px-1')}
                triggerIcon={<Avatar user={user} />}
                triggerLabel={collapsed ? undefined : user.name || user.email || 'Account'}
                items={accountItems}
              />
            </div>
          )}
          <Tooltip content={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} side="right">
            <Button
              variant="ghost"
              size="sm"
              iconOnly
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              onClick={toggleRail}
              leadingIcon={<SidebarIcon />}
              className={cn(collapsed && 'mx-auto')}
            />
          </Tooltip>
        </div>
      </aside>

      {/* ── Mobile drawer ────────────────────────────────────────────────── */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 animate-fade-in bg-ink/40 backdrop-blur-[2px]"
            onClick={() => setDrawerOpen(false)}
            aria-hidden
          />
          <div
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="Main navigation"
            onKeyDown={(e) => drawerRef.current && trapTab(drawerRef.current, e)}
            className="relative flex h-full w-64 max-w-[85vw] flex-col border-r border-line bg-surface shadow-xl"
            style={{ animation: 'fade-up 200ms cubic-bezier(0.16, 1, 0.3, 1)' }}
          >
            <div className="flex h-12 items-center justify-between gap-2 border-b border-line px-3">
              <Logo />
              <Button
                variant="ghost"
                size="sm"
                iconOnly
                aria-label="Close navigation"
                onClick={() => setDrawerOpen(false)}
                leadingIcon={
                  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4 w-4" aria-hidden>
                    <path d="m5 5 10 10M15 5 5 15" strokeLinecap="round" />
                  </svg>
                }
              />
            </div>
            <div className="flex-1 overflow-y-auto p-2">{nav}</div>
          </div>
        </div>
      )}

      {/* ── Main ─────────────────────────────────────────────────────────── */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-line bg-surface px-3 sm:px-4">
          <Button
            ref={openerRef}
            variant="ghost"
            size="md"
            iconOnly
            aria-label="Open navigation"
            aria-expanded={drawerOpen}
            onClick={() => setDrawerOpen(true)}
            leadingIcon={<MenuIcon />}
            className="lg:hidden"
          />
          <div className="lg:hidden">
            <Logo compact />
          </div>

          {/* The search field is the palette: one place to find anything, and
              the same place whether it is reached by click or by ⌘K. */}
          <button
            type="button"
            onClick={commands.open}
            className={cn(
              'group ml-1 hidden h-8 max-w-xs flex-1 items-center gap-2 rounded-md border border-line bg-surface-2/50 px-2.5 text-sm text-faint',
              'transition-colors duration-fast hover:border-line-strong hover:text-muted sm:flex',
            )}
          >
            <SearchIcon className="h-4 w-4 shrink-0" />
            <span className="flex-1 truncate text-left">Search or jump to…</span>
            <kbd className="rounded-sm border border-line bg-surface px-1.5 py-0.5 text-2xs">⌘K</kbd>
          </button>

          <Button
            variant="ghost"
            size="md"
            iconOnly
            aria-label="Search documents and commands"
            onClick={commands.open}
            leadingIcon={<SearchIcon />}
            className="sm:hidden"
          />

          <div className="flex-1 sm:flex-none" />

          <Tooltip content={theme === 'dark' ? 'Switch to light' : 'Switch to dark'}>
            <Button
              variant="ghost"
              size="md"
              iconOnly
              aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
              onClick={onToggleTheme}
              leadingIcon={theme === 'dark' ? <SunIcon /> : <MoonIcon />}
            />
          </Tooltip>

        </header>

        <main id="main" className="flex-1 overflow-y-auto overflow-x-hidden">
          {/* Screens arrive rather than appear. Keyed on the path, so moving
              between them is a movement and not a repaint. */}
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            // Margins per the grid: 16px on a phone, 32px from 1024px up.
            // The width belongs to the Page inside it, which knows whether the
            // screen is one you scan or one you read.
            className="flex min-h-full flex-col px-4 py-6 lg:px-8"
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  )
}

function SidebarNav({ collapsed, onNavigate }: { collapsed: boolean; onNavigate: () => void }) {
  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5">
      {NAV.map(({ to, end, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          title={collapsed ? label : undefined}
          className={({ isActive }) =>
            cn(
              'relative flex h-row items-center gap-2.5 rounded-md px-2.5 text-sm transition-colors duration-fast',
              collapsed && 'justify-center px-0',
              // The selected row is a surface change, not a block of colour:
              // one item in a list of four should not be the loudest thing on
              // the screen.
              isActive ? 'font-medium text-ink' : 'text-muted hover:bg-surface-2/60 hover:text-ink',
            )
          }
        >
          {({ isActive }) => (
            <>
              {isActive && (
                <motion.span
                  layoutId="nav-indicator"
                  className="absolute inset-0 rounded-md bg-surface-2"
                  transition={{ type: 'spring', stiffness: 480, damping: 40, mass: 0.6 }}
                />
              )}
              <span className="relative flex items-center gap-2.5">
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed && label}
              </span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}

function Avatar({ user }: { user: { name?: string; email?: string } | null }) {
  const initial = (user?.name || user?.email || '?').slice(0, 1).toUpperCase()
  return (
    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent text-2xs font-semibold text-accent-fg">
      {initial}
    </span>
  )
}

export function ShellFallback({ children }: { children?: ReactNode }) {
  return <div className="p-6 text-sm text-muted">{children ?? 'Loading…'}</div>
}
