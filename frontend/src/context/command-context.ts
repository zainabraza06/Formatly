import { createContext, useContext, useEffect } from 'react'
import type { Command } from '../components/ui/CommandPalette'

export interface CommandApi {
  open: () => void
  close: () => void
  isOpen: boolean
  /** Add commands for as long as a screen is mounted. Returns the remover. */
  register: (commands: Command[]) => () => void
}

export const CommandContext = createContext<CommandApi | null>(null)

export function useCommands(): CommandApi {
  const ctx = useContext(CommandContext)
  if (!ctx) throw new Error('useCommands must be used inside <CommandProvider>')
  return ctx
}

/**
 * Register commands belonging to the screen that is currently open. They leave
 * the palette when the screen unmounts, so "Export as PDF" is only offered
 * where there is something to export.
 *
 * `deps` are the values the commands close over — the array itself may be
 * rebuilt on every render without re-registering anything.
 */
export function useRegisterCommands(build: () => Command[], deps: unknown[] = []) {
  const { register } = useCommands()
  // The caller names what its commands depend on; rebuilding the array on
  // every render would otherwise re-register the whole set each time.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => register(build()), deps)
}
