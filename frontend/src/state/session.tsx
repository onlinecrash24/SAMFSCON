/**
 * Session state.
 *
 * The session cookie is httpOnly, so the browser cannot read it. What the app
 * keeps is the CSRF token and the facts about the server handed out at login;
 * on a page reload it asks the server who it is talking to.
 */

import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { ApiError, setCsrfToken } from '../api/client'
import { api } from '../api/endpoints'
import type { LoginOptions, SessionInfo } from '../api/types'
import { forgetConsoleLocation } from './consoleLocation'
import { rememberServer } from './recentServers'

interface SessionState {
  session: SessionInfo | null
  loading: boolean
  login: (username: string, password: string, options?: LoginOptions) => Promise<void>
  logout: () => Promise<void>
  /** Called when any request comes back 401 — drops local state. */
  expire: () => void
}

const SessionContext = createContext<SessionState | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const queryClient = useQueryClient()

  // Restore an existing session after a reload.
  useEffect(() => {
    let cancelled = false
    api
      .session()
      .then((info) => {
        if (cancelled) return
        setCsrfToken(info.csrf_token)
        setSession(info)
      })
      .catch(() => {
        // No session, or it expired — the login view handles it.
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(
    async (username: string, password: string, options: LoginOptions = {}) => {
      const info = await api.login(username, password, options)
      setCsrfToken(info.csrf_token)

      // Before setSession, and the order matters: setSession mounts the
      // console, which reads the remembered position in a lazy initialiser.
      // Clearing it afterwards would clear it for the sign-in after this one.
      //
      // Cleared on the way *in* as well as on the way out, because an expired
      // session never passes through sign-out — so without this the position
      // outlives the session that chose it, and the next sign-in, possibly to
      // a different server, opens wherever somebody was days ago.
      forgetConsoleLocation()
      setSession(info)

      // Remember only what actually worked, and only when the user named a
      // server themselves — profiles and the default need no history. The mode
      // is remembered with it: on a server that answers no unauthenticated
      // query it is the field the administrator has to fill in by hand, and
      // once is enough.
      if (options.server) {
        rememberServer({
          host: options.server,
          mode: info.target.mode,
          realm: info.target.realm,
          label: info.server.name || undefined,
        })
      }
    },
    [],
  )

  const expire = useCallback(() => {
    setCsrfToken(null)
    setSession(null)
    queryClient.clear()
    // Leaving the previous person's share and account names in a shared
    // browser is not what signing out means. expire() is the one path both
    // logout and a lapsed session go through.
    forgetConsoleLocation()
  }, [queryClient])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } catch (error) {
      // A failed logout must not strand the user in a broken UI; the
      // server-side session expires on its own.
      if (!(error instanceof ApiError)) throw error
    }
    expire()
  }, [expire])

  const value = useMemo<SessionState>(
    () => ({ session, loading, login, logout, expire }),
    [session, loading, login, logout, expire],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionState {
  const context = useContext(SessionContext)
  if (!context) throw new Error('useSession must be used inside SessionProvider')
  return context
}
