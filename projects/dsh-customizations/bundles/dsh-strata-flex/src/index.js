/**
 * dsh-strata-flex — host entry.
 *
 * Registers /api/strata-flex on the DSH web server so the browser half
 * (client.js footer buttons) can flex the Strata engine's elastic expert
 * cache through the server. The engine accepts the flex only from its own
 * origin or config trusted_origins; server-side node:http calls carry no
 * Origin header and are accepted (curl-equivalent), and the browser never
 * talks to the engine directly (same-origin to the DSH server only).
 *
 * Config (cordis.patch.yml row):
 *   strata_url        default http://127.0.0.1:8080
 *   flex_reserve_mib  default 22016   (~512 experts resident -> ~21 GB window)
 *   busy_reserve_mib  default 14336   (mid-flow target, engine ~18 GB)
 */
import http from 'node:http'

export const name = 'dsh-strata-flex'

/** Minimal node:http JSON client (no Origin header, generous timeouts). */
function engineRequest(strataUrl, path, { method = 'GET', body, timeoutMs = 15000 } = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(strataUrl)
    const payload = body === undefined ? null : Buffer.from(JSON.stringify(body))
    const req = http.request(
      {
        host: u.hostname,
        port: u.port || 80,
        path,
        method,
        headers: payload
          ? { 'content-type': 'application/json', 'content-length': payload.length }
          : {},
        timeout: timeoutMs,
      },
      (res) => {
        const chunks = []
        res.on('data', (c) => chunks.push(c))
        res.on('end', () => {
          const text = Buffer.concat(chunks).toString('utf8')
          try {
            resolve({ status: res.statusCode ?? 0, json: JSON.parse(text) })
          } catch {
            reject(new Error(`strata ${path}: non-JSON response (HTTP ${res.statusCode})`))
          }
        })
      },
    )
    req.on('timeout', () => {
      req.destroy(new Error(`strata ${path}: timeout after ${timeoutMs} ms`))
    })
    req.on('error', reject)
    if (payload) req.write(payload)
    req.end()
  })
}

/** Pick the fields worth surfacing out of /metrics and the flex response. */
function vramSummary(src) {
  const v = src?.vram ?? src ?? {}
  return {
    reserve_mib: v.reserve_mib ?? null,
    expert_slots: v.expert_slots ?? null,
    expert_slots_full: v.expert_slots_full ?? null,
    expert_cache_mib: v.expert_cache_mib ?? null,
    vram_free_mib: v.vram_free_mib ?? null,
  }
}

class Flex {
  constructor(cfg = {}) {
    this.base = String(cfg.strata_url || 'http://127.0.0.1:8080').replace(/\/+$/, '')
    this.floor = Number.isInteger(cfg.flex_reserve_mib) ? cfg.flex_reserve_mib : 22016
    this.busy = Number.isInteger(cfg.busy_reserve_mib) ? cfg.busy_reserve_mib : 14336
  }

  /** Wire the HTTP route onto the plugin context; returns a disposer. */
  attach(ctx) {
    let registered = null
    ctx.inject(['webServer'], (wsCtx) => {
      registered = wsCtx.webServer.register({
        kind: 'prefix',
        path: '/api/strata-flex',
        handler: (req, res) => this.handle(req, res),
      })
    })
    return () => {
      try {
        registered?.dispose?.() ?? registered?.()
      } catch {
        /* already gone */
      }
    }
  }

  sendJson(res, status, obj) {
    const body = JSON.stringify(obj)
    res.writeHead(status, { 'content-type': 'application/json', 'content-length': Buffer.byteLength(body) })
    res.end(body)
  }

  async handle(req, res) {
    const url = new URL(req.url ?? '/', 'http://localhost')
    const p = url.pathname.replace(/\/+$/, '')
    try {
      if (req.method === 'GET' && (p === '/api/strata-flex' || p === '/api/strata-flex/state')) {
        const m = await engineRequest(this.base, '/metrics', { timeoutMs: 10000 })
        this.sendJson(res, 200, { ok: true, state: vramSummary(m.json?.engine), config: { floor: this.floor, busy: this.busy } })
        return
      }
      if (req.method === 'POST' && (p === '/api/strata-flex' || p === '/api/strata-flex/flex')) {
        const chunks = []
        for await (const c of req) chunks.push(c)
        let action = 'state'
        try {
          action = (JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}').action ?? 'state')
        } catch {
          /* default */
        }
        let reserve = null
        if (action === 'flex') reserve = this.floor
        else if (action === 'busy') reserve = this.busy
        else if (action === 'reclaim' || action === 'state') reserve = null
        else return this.sendJson(res, 400, { ok: false, error: `unknown action: ${action}` })
        // the engine applies this between requests and may wait up to 300 s
        const out = await engineRequest(this.base, '/v1/vram', { method: 'POST', body: { reserve_mib: reserve }, timeoutMs: 310000 })
        if ((out.status ?? 0) >= 400) {
          this.sendJson(res, 502, { ok: false, error: out.json?.error?.message ?? `engine HTTP ${out.status}` })
          return
        }
        this.sendJson(res, 200, { ok: true, action, state: vramSummary(out.json) })
        return
      }
      this.sendJson(res, 404, { ok: false, error: `no route: ${p}` })
    } catch (e) {
      this.sendJson(res, 502, { ok: false, error: String(e?.message ?? e) })
    }
  }
}

export function apply(ctx, config) {
  const flex = new Flex(config ?? {})
  ctx.effect(() => flex.attach(ctx), 'dsh-strata-flex: web routes')
}
