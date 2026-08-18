/**
 * Every call the front end makes, in one place.
 *
 * Grouped the way the console is: what answers before sign-in, the session
 * itself, and then one group per snap-in. A component that needs a new call
 * adds it here rather than reaching for `http` directly, so the URL shapes stay
 * in one file and the types travel with them.
 */

import { http, param } from './client'
import type {
  AppInfo,
  DirectoryListing,
  EffectiveAccess,
  LoginOptions,
  OpenFile,
  OptionSpec,
  ServerSession,
  ServerListing,
  SecurityDescriptor,
  ServerProbe,
  SessionInfo,
  Share,
  ShareCreate,
  ShareConnection,
  ShareListing,
  ShareUpdate,
  Trustee,
  WhoAmI,
} from './types'

export const api = {
  // -- before signing in ---------------------------------------------------

  info: () => http.get<AppInfo>('/info'),

  servers: () => http.get<ServerListing>('/servers'),

  /**
   * Ask a server what it is.
   *
   * Rate limited on the server side: this runs for an unauthenticated caller,
   * and an endpoint that opens outbound connections on request is one to keep
   * on a short leash.
   */
  probe: (host: string, profileId?: string) =>
    http.post<ServerProbe>('/servers/probe', { host, profile_id: profileId ?? null }),

  // -- the session ---------------------------------------------------------

  login: (username: string, password: string, options: LoginOptions = {}) =>
    http.post<SessionInfo>('/auth/login', {
      username,
      password,
      server: options.server ?? null,
      profile_id: options.profileId ?? null,
      mode: options.mode ?? null,
      realm: options.realm ?? null,
    }),

  logout: () => http.post<{ status: string }>('/auth/logout'),

  session: () => http.get<SessionInfo>('/auth/session'),

  /**
   * Who the server thinks we are, and what this account may do here.
   *
   * The capabilities half is what the interface uses to explain a refusal
   * before it happens: a console that offers a button which always fails is
   * worse than one that says why the button is missing.
   */
  whoami: () => http.get<WhoAmI>('/auth/whoami'),

  // -- identity, for the permission editor ---------------------------------

  lookupNames: (names: string[]) =>
    http.post<{ entries: Trustee[] }>('/identity/names', { names }),

  lookupSids: (sids: string[]) => http.post<{ entries: Trustee[] }>('/identity/sids', { sids }),

  wellKnownTrustees: () => http.get<{ entries: Trustee[] }>('/identity/well-known'),

  // -- shares --------------------------------------------------------------

  shares: () => http.get<ShareListing>('/shares'),

  share: (name: string) => http.get<Share>(`/shares/${param(name)}`),

  /**
   * The options the interface builds its forms from.
   *
   * Cached forever by the caller: it describes what SAMFSCON knows how to
   * edit, not what one server happens to have, so it changes only when the
   * application does.
   */
  shareCatalogue: (language: string) =>
    http.get<{ options: OptionSpec[] }>(`/shares/catalogue?language=${param(language)}`),

  createShare: (share: ShareCreate) => http.post<Record<string, unknown>>('/shares', share),

  updateShare: (name: string, changes: ShareUpdate) =>
    http.patch<{ name: string; changes: Record<string, unknown> }>(
      `/shares/${param(name)}`,
      changes,
    ),

  deleteShare: (name: string) =>
    http.delete<{ name: string; status: string }>(`/shares/${param(name)}`),

  // -- sessions and open files ---------------------------------------------

  sessions: () => http.get<{ entries: ServerSession[] }>('/sessions'),

  openFiles: () => http.get<{ entries: OpenFile[] }>('/sessions/files'),

  connections: (share: string) =>
    http.get<{ share: string; entries: ShareConnection[] }>(
      `/sessions/connections?share=${param(share)}`,
    ),

  /**
   * Force one open handle closed.
   *
   * Destructive: the client holding it is not asked and loses unsaved work.
   * The caller confirms first, and the answer carries what was closed so the
   * notice can name it.
   */
  closeFile: (fileId: number) =>
    http.post<{ file_id: number; status: string; file: OpenFile | null }>(
      '/sessions/files/close',
      { file_id: fileId },
    ),

  // -- permissions ---------------------------------------------------------

  sharePermissions: (share: string) =>
    http.get<SecurityDescriptor>(`/permissions/share?share=${param(share)}`),

  setSharePermissions: (share: string, sddl: string) =>
    http.put<{ share: string; status: string }>(`/permissions/share?share=${param(share)}`, {
      sddl,
      apply_to_children: false,
    }),

  pathPermissions: (share: string, path: string) =>
    http.get<SecurityDescriptor>(
      `/permissions/path?share=${param(share)}&path=${param(path)}`,
    ),

  setPathPermissions: (share: string, path: string, sddl: string, protectedDacl: boolean) =>
    http.put<{ share: string; path: string; status: string }>(
      `/permissions/path?share=${param(share)}&path=${param(path)}`,
      { sddl, apply_to_children: protectedDacl },
    ),

  /**
   * What one account may actually do, given both descriptors.
   *
   * Two round trips on the server, so it is asked for only when somebody
   * points at a row rather than for every entry in the list.
   */
  effectiveAccess: (share: string, sid: string, path: string) =>
    http.get<EffectiveAccess>(
      `/permissions/effective?share=${param(share)}&sid=${param(sid)}&path=${param(path)}`,
    ),

  // -- browsing a share ----------------------------------------------------

  listDirectory: (share: string, path: string) =>
    http.get<DirectoryListing>(`/files?share=${param(share)}&path=${param(path)}`),

  createDirectory: (share: string, path: string) =>
    http.post<{ share: string; path: string; status: string }>(
      `/files/directory?share=${param(share)}&path=${param(path)}`,
    ),
}
