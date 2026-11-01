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
    // Slider envelope for action:"set". Max defaults to the proven flex window; the
    // engine itself has NO floor, so clamping here is the only thing between a slider
    // drag and a starved engine. 512 MiB is the engine's own resize segment.
    this.segment = Number.isInteger(cfg.resize_segment_mib) ? cfg.resize_segment_mib : 512
    this.setMin = Number.isInteger(cfg.set_min_mib) ? cfg.set_min_mib : 2048
    // Default ceiling = the point where the engine stops delivering, not the largest number
    // it will echo back. (Proven: asking 26,624 still yields 19,261 free.)
    // The engine takes reserve_mib (keep free for other programs). The UI asks in the
    // other direction — how much the brain HOLDS — so the conversion lives here:
    //   expert_cache_mib = cache_span_mib - reserve_mib, floored at cache_floor_mib.
    // Verified against live probes on 2026-11-01: reserve 2048 -> cache 17,920;
    // 14,336 -> 5,632; 20,480 and 22,016 -> 1,024 (the floor). Span = 19,968.
    this.cacheSpan = Number.isInteger(cfg.cache_span_mib) ? cfg.cache_span_mib : 19968
    this.cacheFloor = Number.isInteger(cfg.cache_floor_mib) ? cfg.cache_floor_mib : 1024
    // The engine's own hard floor, measured 2026-11-01: it never shrinks below 515 expert
    // slots (1,024 MiB cache) and free VRAM stops at ~19.3 GiB. Above that the ask is
    // reported back but NOT delivered, so the useful ceiling is where delivery stops:
    //   reserve_max = cache_span - cache_floor = 18,944.
    this.deliveredCeilingMib = Number.isInteger(cfg.delivered_ceiling_mib) ? cfg.delivered_ceiling_mib : 19261
    this.setMax = Number.isInteger(cfg.set_max_mib) ? cfg.set_max_mib : (this.cacheSpan - this.cacheFloor)
    this.blockOnComfy = cfg.block_reclaim_on_comfy !== false
    this.comfyBase = String(cfg.comfy_url || 'http://127.0.0.1:8188').replace(/\/+$/, '')
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

  /** Read-only ComfyUI queue probe. A refusal to reclaim under a live queue is a
      safety property, not a preference; if ComfyUI is down the probe says "not busy". */
  async comfyBusy() {
    try {
      const ac = new AbortController()
      const t = setTimeout(() => ac.abort(), 1500)
      const r = await fetch(`${this.comfyBase}/queue_prompt`, { signal: ac.signal })
      clearTimeout(t)
      if (!r.ok) return false
      const j = await r.json()
      const q = j?.queue_remaining ?? j?.queue_running?.length ?? 0
      return Number(q) > 0
    } catch {
      return false
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
        this.sendJson(res, 200, {
          ok: true,
          state: vramSummary(m.json?.engine),
          // The UI needs the conversion constants to draw its slider honestly.
          config: { floor: this.floor, busy: this.busy, set_min: this.setMin, set_max: this.setMax, segment: this.segment, cache_span: this.cacheSpan, cache_floor: this.cacheFloor, cache_max: this.cacheSpan - this.setMin, cache_min: this.cacheFloor, delivered_ceiling_mib: this.deliveredCeilingMib },
        })
        return
      }
      if (req.method === 'POST' && (p === '/api/strata-flex' || p === '/api/strata-flex/flex')) {
        const chunks = []
        for await (const c of req) chunks.push(c)
        let payload = {}
        try {
          const parsed = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')
          if (parsed && typeof parsed === 'object') payload = parsed
        } catch {
          /* default */
        }
        const action = payload.action ?? 'state'
        let reserve = null
        let note = null
        if (action === 'flex') reserve = this.floor
        else if (action === 'busy') reserve = this.busy
        else if (action === 'reclaim' || action === 'state') reserve = null
        else if (action === 'set' && payload.cache_mib != null) {
          // Preferred form: the UI speaks "VRAM the brain holds", the engine speaks
          // "keep this much free". One conversion, in the owner of the guard.
          const raw = Number(payload.cache_mib)
          if (!Number.isFinite(raw)) return this.sendJson(res, 400, { ok: false, error: 'cache_mib must be a number' })
          const seg = this.segment
          const hiCache = this.cacheSpan - this.setMin
          const snapped = Math.round(raw / seg) * seg
          const c = Math.min(hiCache, Math.max(this.cacheFloor, snapped))
          reserve = this.cacheSpan - c
          note = c !== raw ? `cache ${raw} -> ${c} MiB (segment ${seg}, floor ${this.cacheFloor}, max ${hiCache})` : `cache ${c} MiB -> keep ${reserve} MiB free`
        }
        else if (action === 'set') {
          // The engine takes ANY integer >= 0 with no floor of its own, so the guard
          // lives here: a slider that can ask for 0 would starve the engine mid-request.
          const raw = Number(payload.reserve_mib)
          if (!Number.isFinite(raw)) return this.sendJson(res, 400, { ok: false, error: 'set needs a numeric reserve_mib' })
          const seg = this.segment   // the engine resizes in segments; snap or the value bounces
          const lo = this.setMin
          const hi = this.setMax
          const snapped = Math.round(raw / seg) * seg
          const clamped = Math.min(hi, Math.max(lo, snapped))
          note = clamped !== raw ? `${raw} snapped to ${clamped} (segment ${seg}, range ${lo}-${hi})` : null
          reserve = clamped
        } else return this.sendJson(res, 400, { ok: false, error: `unknown action: ${action}` })
        // A dry run answers the clamped value and the current state WITHOUT touching the
        // engine — how a slider previews, and how the route is tested without flexing.
        if (payload.dry_run === true) {
          const m = await engineRequest(this.base, '/metrics', { timeoutMs: 10000 })
          this.sendJson(res, 200, { ok: true, action, dry_run: true, reserve_requested: Number(payload.reserve_mib ?? null), reserve_applied: reserve, note, state: vramSummary(m.json?.engine) })
          return
        }
        // Reclaiming refills the expert cache; never do that under a live render queue.
        if (reserve === null && action === 'reclaim' && this.blockOnComfy && await this.comfyBusy()) {
          return this.sendJson(res, 409, { ok: false, error: 'ComfyUI has jobs queued or running — reclaiming could OOM the render. Wait for the queue, or lower instead.' })
        }
        // the engine applies this between requests and may wait up to 300 s
        const out = await engineRequest(this.base, '/v1/vram', { method: 'POST', body: { reserve_mib: reserve }, timeoutMs: 310000 })
        if ((out.status ?? 0) >= 400) {
          this.sendJson(res, 502, { ok: false, error: out.json?.error?.message ?? `engine HTTP ${out.status}` })
          return
        }
        this.sendJson(res, 200, { ok: true, action, reserve_applied: reserve, ...(note ? { note } : {}), state: vramSummary(out.json) })
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
