import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { explain, isAbort } from '../lib/errors'

/**
 * One way to report a failure to the person using the app.
 *
 * Screens used to write their own `e instanceof Error ? e.message : '…'`, which
 * meant a dead database read as "Internal Server Error", an expired session
 * read as "401", and a laptop that had gone to sleep read as "Failed to fetch".
 * Here every failure gets a sentence, a retry where retrying could help, and —
 * when the session is the thing that failed — the sign-in page instead of an
 * error the reader can do nothing about.
 */
export function useReportError() {
  const toast = useToast()
  const { logout, user } = useAuth()
  const navigate = useNavigate()

  return useCallback(
    (error: unknown, doing = 'do that', retry?: () => void) => {
      // A request the app itself called off is not a failure to report.
      if (isAbort(error)) return

      const { title, detail, retryable, unauthorized } = explain(error, doing)

      if (unauthorized) {
        // Only if we thought we were signed in — otherwise this is a page that
        // needs a login, and the router is already sending them there.
        if (user) logout()
        navigate('/login', { replace: true })
        toast.error(title, detail)
        return
      }

      toast.toast({
        tone: 'error',
        title,
        description: detail,
        action: retryable && retry ? { label: 'Try again', onClick: retry } : undefined,
      })
    },
    [toast, logout, navigate, user],
  )
}
