import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { CommandPalette, type Command } from '../components/ui/CommandPalette'
import { CommandContext, type CommandApi } from './command-context'

export function CommandProvider({
  children,
  globalCommands,
}: {
  children: ReactNode
  /** Commands available everywhere — navigation, theme, account. */
  globalCommands: Command[]
}) {
  const [isOpen, setOpen] = useState(false)
  const [scoped, setScoped] = useState<Command[][]>([])

  const register = useCallback((commands: Command[]) => {
    setScoped((all) => [...all, commands])
    return () => setScoped((all) => all.filter((group) => group !== commands))
  }, [])

  // Cmd/Ctrl+K from anywhere, including from inside a text field: it is the one
  // shortcut that has to work while someone is typing and cannot find a button.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen((o) => !o)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const api = useMemo<CommandApi>(() => ({
    isOpen,
    open: () => setOpen(true),
    close: () => setOpen(false),
    register,
  }), [isOpen, register])

  // Screen commands first: they are about what is on screen right now.
  const commands = useMemo(
    () => [...scoped.flat(), ...globalCommands],
    [scoped, globalCommands],
  )

  return (
    <CommandContext.Provider value={api}>
      {children}
      <CommandPalette open={isOpen} onClose={() => setOpen(false)} commands={commands} />
    </CommandContext.Provider>
  )
}
