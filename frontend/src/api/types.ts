/**
 * The shapes the API returns.
 *
 * Written by hand rather than generated: the generated version of an OpenAPI
 * schema this small is harder to read than the schema, and these types are
 * what the components are documented against.
 */

export interface ApiErrorBody {
  code: string
  message: string
  hint?: string
  detail?: string
  context?: Record<string, unknown>
}

/** Which kind of server, and therefore how it authenticates. */
export type ServerMode = 'ad_member' | 'standalone' | 'auto'

// ---------------------------------------------------------------------------
// Before signing in
// ---------------------------------------------------------------------------

export interface ServerProfileSummary {
  id: string
  label: string
  host: string
  mode: ServerMode
  realm: string | null
  workgroup: string | null
}

export interface ServerListing {
  profiles: ServerProfileSummary[]
  default: {
    host: string
    mode: ServerMode
    realm: string | null
    workgroup: string | null
  } | null
  allow_custom_servers: boolean
  allow_standalone: boolean
}

/**
 * What the server said about itself, without credentials.
 *
 * `decided` is the field the form turns on: false means the server would not
 * say what it is, and the administrator has to choose. `notes` explains why,
 * so that choice is informed rather than a coin flip.
 */
export interface ServerProbe {
  host: string
  reachable: boolean
  mode: ServerMode
  decided: boolean
  realm: string | null
  workgroup: string | null
  netbios_name: string | null
  server_fqdn: string | null
  os_version: string | null
  comment: string | null
  is_domain_controller: boolean
  notes: string[]
  allow_standalone: boolean
}

export interface AppInfo {
  version: string
  server_host: string | null
  server_mode: ServerMode
  realm: string | null
  workgroup: string | null
  allow_custom_servers: boolean
  allow_standalone: boolean
  has_server_profiles: boolean
  mode_is_discovered: boolean
  smb: { min_protocol: string; encrypt: boolean }
  sessions: { active: number; workers: number; idle_timeout_minutes: number }
}

// ---------------------------------------------------------------------------
// The session
// ---------------------------------------------------------------------------

export interface ServerSummary {
  name: string
  host: string
  comment: string | null
  os_version: string | null
  workgroup: string | null
  realm: string | null
  mode: ServerMode
  is_domain_controller: boolean
}

/**
 * How the connection is protected.
 *
 * `identity_verified` is the one worth reading. Kerberos proves the server is
 * who it claims to be; NTLM proves only the client to the server. Both are
 * signed, and only one of them tells you who you are talking to.
 */
export interface ConnectionState {
  auth: 'kerberos' | 'ntlm'
  server_name: string
  signed: boolean
  encrypted: boolean
  identity_verified: boolean
}

export interface ServerTargetInfo {
  host: string
  mode: ServerMode
  realm: string | null
  workgroup: string | null
  label: string | null
  profile_id: string | null
  netbios_name: string | null
  server_fqdn: string | null
  os_version: string | null
  uses_kerberos: boolean
}

export interface SessionInfo {
  principal: string
  username: string
  realm: string
  csrf_token: string
  expires_at: string
  expires_hard_at?: string
  created_at?: string
  server: ServerSummary
  connection: ConnectionState
  target: ServerTargetInfo
  /**
   * True for a standalone session, whose password stays in the server
   * process's memory for as long as the session lives. Shown for the whole
   * session rather than only at sign-in — it is not a detail to remember on
   * one's own.
   */
  holds_password: boolean
}

export interface LoginOptions {
  server?: string
  profileId?: string
  mode?: ServerMode
  realm?: string
}

// ---------------------------------------------------------------------------
// Identity — the object picker behind the permission editor
// ---------------------------------------------------------------------------

export type SidType =
  | 'user'
  | 'group'
  | 'domain'
  | 'alias'
  | 'well_known_group'
  | 'deleted'
  | 'invalid'
  | 'unknown'
  | 'computer'

export interface Trustee {
  name: string | null
  sid: string | null
  domain?: string | null
  type: SidType
  resolved?: boolean
}

export interface AccountIdentity {
  name: string | null
  authority: string | null
  sid: string | null
  type: SidType | null
  groups: Trustee[]
  /** Domain groups are not enumerated from a file server; the flag says so. */
  groups_are_local_only: boolean
}

/**
 * What this session can actually do, as opposed to what it may attempt.
 *
 * Every field is deliberately nullable. `false` means "checked, and no";
 * `null` means "could not look" — telling an administrator their permissions
 * are missing when the check itself was refused is worse than saying nothing.
 */
/**
 * One reason a capability could not be established.
 *
 * A code rather than a sentence: the server writes English and this interface
 * is bilingual, so a note it composed itself would arrive half-translated in
 * the middle of a German banner — which is what it used to do.
 */
export interface CapabilityNote {
  code: string
  params: Record<string, string>
}

export interface Capabilities {
  registry_config: boolean | null
  registry_writable: boolean | null
  has_disk_operator: boolean | null
  disk_operators: string[]
  can_manage_shares: boolean | null
  notes: CapabilityNote[]
}

export interface WhoAmI {
  account: AccountIdentity
  server: ServerSummary
  connection: ConnectionState
  capabilities: Capabilities
}

// ---------------------------------------------------------------------------
// Shares
// ---------------------------------------------------------------------------

/**
 * One share's stored options, split into what the catalogue describes and what
 * it does not. The second half is shown read-only rather than hidden: a server
 * configured by hand is not wrong, and a console that displayed half a
 * configuration would be misleading about the other half.
 */
export interface ShareOptions {
  known: Record<string, string>
  extra: Record<string, string>
}

export interface Share {
  name: string
  type: 'disk' | 'printer' | 'device' | 'ipc' | 'unknown'
  path: string | null
  comment: string | null
  special: boolean
  administrative: boolean
  current_users: number | null
  max_users: number | null
  /**
   * False for a share that exists only in the server's text smb.conf. It can
   * be read here and not changed — SAMFSCON edits the registry configuration,
   * which is what is reachable over the network.
   */
  editable: boolean
  options: ShareOptions
  vfs: string[]
}

export interface ShareListing {
  entries: Share[]
  /** Sent with the list so the interface can explain a missing button. */
  capabilities: Capabilities
}

/** One option from the catalogue, as a form control. */
export interface OptionSpec {
  name: string
  type: 'bool' | 'text' | 'list' | 'mode' | 'int' | 'choice'
  group: 'basic' | 'access' | 'files' | 'vfs' | 'advanced'
  default: string | null
  choices: string[]
  doc: string
  /** Set when the option only means anything with a VFS module loaded. */
  requires_vfs: string | null
}

export interface ShareCreate {
  name: string
  path: string
  comment: string | null
  read_only: boolean
  browseable: boolean
  guest_ok: boolean
  options: Record<string, string>
}

export interface ShareUpdate {
  path?: string
  comment?: string
  read_only?: boolean
  browseable?: boolean
  guest_ok?: boolean
  /** A key set to null removes the option, restoring the server's default. */
  options?: Record<string, string | null>
}

// ---------------------------------------------------------------------------
// Sessions and open files
// ---------------------------------------------------------------------------

/** One authenticated user on one client machine. */
export interface ServerSession {
  user: string | null
  client: string | null
  open_files: number | null
  connected_seconds: number | null
  idle_seconds: number | null
  /** Surfaced on its own: a guest session is usually a surprise. */
  guest: boolean
}

/** One share a session has open. */
export interface ShareConnection {
  id: number | null
  share: string | null
  user: string | null
  client: string | null
  open_files: number | null
  connected_seconds: number | null
}

/** One open handle, with what it may do and how it is locked. */
export interface OpenFile {
  id: number | null
  path: string | null
  user: string | null
  locks: number | null
  permissions: Array<'read' | 'write' | 'create'>
}

// ---------------------------------------------------------------------------
// Permissions
// ---------------------------------------------------------------------------

/** Which of the two descriptors is being edited. */
export type PermissionLevel = 'share' | 'file'

export interface Ace {
  trustee: string
  kind: 'allow' | 'deny'
  mask: number
  flags: number
  /** From a parent directory: shown, and not editable in place. */
  inherited: boolean
  /** The named level this mask sits on, or null when it sits on none exactly. */
  preset: string | null
  /** The rights field exactly as the descriptor spelled it. */
  raw_rights: string
  /** False when the parser could not read all of that field. */
  understood: boolean
  rights: string[]
  applies_to:
    | 'this_only'
    | 'this_and_children'
    | 'children_only'
    | 'folders'
    | 'files'
}

/**
 * What a trustee string in an ACE actually refers to.
 *
 * Keyed by the string the ACE carried, because that is what the editor has in
 * hand — an SDDL alias like `WD`, a Unix mapping like `S-1-22-2-0`, or a real
 * SID. The server expands the first, names the second locally and looks the
 * third up; any of them may come back unresolved, which is itself worth seeing.
 */
export interface ResolvedTrustee {
  sid: string | null
  name: string | null
  domain?: string | null
  type?: string
  /** An alias that only means something relative to a domain, e.g. `DA`. */
  alias?: string
  /** Samba's mapping of a Unix uid or gid into the SID space. */
  unix?: { kind: 'unix_user' | 'unix_group'; id: string }
  resolved?: boolean
}

export interface SecurityDescriptor {
  share: string
  path?: string
  level: PermissionLevel
  sddl: string
  owner: string | null
  group: string | null
  /** True when the parent's entries no longer flow in. */
  protected: boolean
  aces: Ace[]
  trustees: Record<string, ResolvedTrustee>
}

/**
 * What one account may actually do.
 *
 * The intersection of both descriptors, because that is how SMB decides.
 * `limited_by_share` names the case that causes the arguments: the file ACL
 * permits it and the share does not.
 */
export interface EffectiveAccess {
  share: string
  path: string
  sid: string
  share_mask: number
  file_mask: number
  effective_mask: number
  rights: string[]
  limited_by_share: boolean
  /** True: this counts the entries naming the SID, not full group evaluation. */
  direct_entries_only: boolean
}

/** One entry of a directory listing inside a share. */
export interface DirectoryEntry {
  name: string
  path: string
  is_directory: boolean
  size: number
  modified: unknown
  /** Shown because they explain behaviour people otherwise blame on the ACL. */
  hidden: boolean
  read_only: boolean
  system: boolean
  attributes: number
}

export interface DirectoryListing {
  share: string
  path: string
  entries: DirectoryEntry[]
  truncated: boolean
}

// ---------------------------------------------------------------------------
// Local users and groups — standalone servers only
// ---------------------------------------------------------------------------

export interface LocalAccount {
  name: string
  rid: number
  sid: string | null
  full_name: string | null
  description: string | null
  disabled: boolean
  locked_out: boolean
  password_never_expires: boolean
  /** The server's own accounts: not offered for deletion. */
  protected: boolean
}

export interface LocalGroup {
  name: string
  rid: number
  sid: string | null
  description: string | null
  /** SIDs, because a local group can contain domain accounts. */
  members: string[]
}

export interface AccountCreate {
  name: string
  password: string
  full_name: string | null
  description: string | null
  disabled: boolean
  password_never_expires: boolean
}

export interface AccountUpdate {
  full_name?: string
  description?: string
  disabled?: boolean
  password_never_expires?: boolean
}
