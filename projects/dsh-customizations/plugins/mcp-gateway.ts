/**
 * DSH MCP on-demand gateway.
 *
 * A session starts with ZERO MCP tool context (only the three tiny toggle tools
 * below are always present). When a task actually needs browser / image-video /
 * 3D work, `mcp_enable` connects that one server and registers its tools into
 * the live tool registry; `mcp_disable` tears it back down to reclaim context.
 *
 * This plugin does NOT reimplement MCP transport. It reuses
 * @deepseek-ai/dsh-mcp-client's supervised connection verbatim — reconnect with
 * bounded backoff, image-attachment admission, deterministic `mcp__<server>__*`
 * naming, and tool-list re-sync all come for free from `startConnection`.
 * Disposing the returned handle unregisters exactly the tools that server owns.
 *
 * Plane: HOST. It publishes model tools only (no cross-session service), so it
 * is safe at host scope; the MCP servers it drives are process-local child
 * processes owned by this fiber and cleaned up on disposal.
 */

import type { Context } from '@deepseek-ai/cordis'
import { startConnection, resolveReconnectPolicy } from '@deepseek-ai/dsh-mcp-client'
import type { ConnectionHandle } from '@deepseek-ai/dsh-mcp-client'
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'mcp-gateway'
export const inject = ['tools']

/** Mirrors @deepseek-ai/dsh-mcp-client ReconnectConfig. */
interface ReconnectConfig {
  enabled?: boolean
  initialDelayMs?: number
  maxDelayMs?: number
  maxAttempts?: number
}

/** One configurable MCP server (stdio child process or streamable HTTP). */
interface ServerDef {
  /** Stable namespace for tool names `mcp__<serverName>__*`; `[A-Za-z0-9_-]{1,32}`. */
  serverName: string
  /** Human-facing hint shown by mcp_status / in the GUI. */
  description?: string
  transport: 'stdio' | 'streamable-http'
  // stdio:
  command?: string
  args?: string[]
  env?: Record<string, string>
  cwd?: string
  // streamable-http:
  url?: string
  headers?: Record<string, string>
  toolCallTimeoutMs?: number
  reconnect?: ReconnectConfig
}

interface GatewayConfig {
  servers: ServerDef[]
}

/** Result shape returned to the model / GUI for every verb. */
interface VerbResult {
  server?: string
  state: 'enabled' | 'already-enabled' | 'enabled-unstable' | 'disabled' | 'not-enabled'
  error?: string
  servers?: Array<{ server: string; enabled: boolean; description: string }>
}

export function apply(ctx: Context, config: GatewayConfig): void {
  if (!Array.isArray(config.servers) || config.servers.length === 0) {
    throw new Error('mcp-gateway: `config.servers` must be a non-empty array')
  }
  const defs = new Map<string, ServerDef>()
  for (const s of config.servers) {
    if (!s || typeof s.serverName !== 'string' || !/^[A-Za-z0-9_-]{1,32}$/.test(s.serverName)) {
      throw new Error(`mcp-gateway: invalid serverName ${JSON.stringify(s?.serverName)}`)
    }
    if (defs.has(s.serverName)) throw new Error(`mcp-gateway: duplicate serverName "${s.serverName}"`)
    defs.set(s.serverName, s)
  }

  /** Live connection handles, keyed by serverName. */
  const live = new Map<string, ConnectionHandle>()
  /** In-flight enable promises so concurrent calls don't double-connect one server. */
  const pending = new Map<string, Promise<VerbResult>>()

  function toMcpConfig(def: ServerDef): Parameters<typeof startConnection>[1] {
    if (def.transport === 'stdio') {
      return {
        transport: 'stdio',
        serverName: def.serverName,
        command: def.command ?? '',
        args: def.args ?? [],
        env: def.env ?? {},
        cwd: def.cwd ?? '',
        toolCallTimeoutMs: def.toolCallTimeoutMs ?? 120_000,
        failOnStartupError: false,
        ...(def.reconnect !== undefined ? { reconnect: def.reconnect } : {}),
      }
    }
    return {
      transport: 'streamable-http',
      serverName: def.serverName,
      url: def.url ?? '',
      headers: def.headers ?? {},
      toolCallTimeoutMs: def.toolCallTimeoutMs ?? 120_000,
      failOnStartupError: false,
      ...(def.reconnect !== undefined ? { reconnect: def.reconnect } : {}),
    }
  }

  function status(): VerbResult {
    return {
      state: 'enabled', // state field is unused for the list verb; kept for a stable shape
      servers: config.servers.map((s) => ({
        server: s.serverName,
        enabled: live.has(s.serverName),
        description: s.description ?? '',
      })),
    }
  }

  function enable(serverName: string): Promise<VerbResult> {
    if (live.has(serverName)) return Promise.resolve({ server: serverName, state: 'already-enabled' })
    const existing = pending.get(serverName)
    if (existing) return existing

    const def = defs.get(serverName)
    if (!def) {
      return Promise.reject(new Error(`unknown MCP server "${serverName}". Available: ${[...defs.keys()].join(', ')}`))
    }
    const policy = resolveReconnectPolicy(def.reconnect, `mcp-gateway(${serverName})`)
    const promise = (async () => {
      // startConnection registers tools on connect and owns its own reconnect loop.
      const conn = startConnection(ctx, toMcpConfig(def), policy)
      live.set(serverName, conn)
      const outcome = await conn.ready
      if (outcome.error !== undefined) {
        // Leave it registered: the supervisor may still recover via reconnect.
        return { server: serverName, state: 'enabled-unstable' as const, error: String(outcome.error) }
      }
      return { server: serverName, state: 'enabled' as const }
    })().finally(() => pending.delete(serverName))

    pending.set(serverName, promise)
    return promise
  }

  async function disable(serverName: string): Promise<VerbResult> {
    const conn = live.get(serverName)
    if (!conn) return { server: serverName, state: 'not-enabled' }
    live.delete(serverName)
    await conn.dispose() // stops reconnect, closes client, unregisters its tools
    return { server: serverName, state: 'disabled' }
  }

  const render = (v: unknown) => [{ type: 'text' as const, text: JSON.stringify(v, null, 2) }]
  const names = [...defs.keys()].join(', ')

  ctx.tools.register(defineTool({
    name: 'mcp_enable',
    description:
      'Connect an on-demand MCP server and register its tools into this session. '
      + `Use when a task needs one of the configured servers (${names}). `
      + 'The server stays connected until mcp_disable; enabling again is a no-op. '
      + 'Call mcp_status to list available servers and their state.',
    parameters: {
      server: { type: 'string', required: true, description: `MCP server name to enable (${names})` },
    },
    output: { schema: { type: 'object' }, render },
    async execute(args) { return await enable(String((args as Record<string, unknown>).server)) },
  }))

  ctx.tools.register(defineTool({
    name: 'mcp_disable',
    description:
      `Disconnect an enabled on-demand MCP server (${names}) and remove its tools from this session to reclaim context.`,
    parameters: {
      server: { type: 'string', required: true, description: `MCP server name to disable (${names})` },
    },
    output: { schema: { type: 'object' }, render },
    async execute(args) { return await disable(String((args as Record<string, unknown>).server)) },
  }))

  ctx.tools.register(defineTool({
    name: 'mcp_status',
    description: `List all configured on-demand MCP servers (${names}) and whether each is currently enabled.`,
    parameters: {},
    output: { schema: { type: 'object' }, render },
    async execute() { return status() },
  }))

  // Best-effort log; some contexts expose no logger.
  try { ctx.logger?.info?.(`mcp-gateway ready: ${config.servers.length} on-demand server(s) [${names}]`) } catch { /* noop */ }
}
