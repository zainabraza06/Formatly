import clsx, { type ClassValue } from 'clsx'

/**
 * The one class-joining helper. `clsx` is already a dependency; this exists so
 * every component imports the same name and a future switch to tailwind-merge
 * happens in one place.
 */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs)
}
