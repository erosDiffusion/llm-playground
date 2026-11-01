/**
 * dsh-quota-panel — host half: quota reader + HTTP route + the `quota_panel` tool.
 *
 * Design rule: showing quota must never cost quota. Every number is read locally:
 *   * `agy -p /usage` — the CLI's LOCAL usage command. Measured 2026-11-01: two
 *     back-to-back reads returned byte-identical percentages, so this read moves no
 *     pool counter (verified by the operator before the panel existed; `provenance`
 *     is exposed in the payload so the UI can say where a number came from).
 *   * the local ledger `~/.dsh/quota/acp-ledger.tsv` for Copilot premium requests,
 *   * the PRICE table inside `~/.dsh/bin/acp-budget`, PARSED not copied — one owner
 *     per fact, so the panel and the routing gate can never disagree.
 * Results are cached (TTL) so a page poll never re-probes.
 */
import { execFileSync } from 'node:child_process'
import { readFileSync, writeFileSync, appendFileSync, existsSync, mkdirSync } from 'node:fs'

const HOME = process.env.HOME || ''

export class QuotaPanel {
  constructor(cfg = {}) {
    this.agyBin = cfg.agyBin || 'agy'
    this.ledger = expand(cfg.ledger || '~/.dsh/quota/acp-ledger.tsv')
    this.budgetCli = expand(cfg.budgetCli || '~/.dsh/bin/acp-budget')
    // The engine serving THIS agent. Reading it is free and read-only: it never starts,
    // stops or configures anything (a hard rule on this box), it only reports slots.
    this.engineBase = cfg.engineBase || 'http://127.0.0.1:8080'
    this.cacheFile = expand(cfg.cacheFile || '~/.dsh/quota/panel-cache.json')
    this.ttlMs = Number(cfg.ttlMs ?? 90_000)
    this.floors = { h5: Number(cfg.floorFiveHour ?? 20), wk: Number(cfg.floorWeekly ?? 25) }
    this.hold = Number(cfg.copilotHold ?? 20)
    this.cache = null
    this.provenance = 'none'
  }

  // ── readers ────────────────────────────────────────────────────────────────
  probeAgy() {
    const out = execFileSync(this.agyBin, ['-p', '/usage', '--output-format', 'text'], {
      encoding: 'utf8',
      timeout: 150_000,
      env: { ...process.env, PATH: `${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:${process.env.PATH || ''}` },
    })
    const pools = []
    for (const line of out.split('\n')) {
      const m = line.trim().match(/^(.+?)\t(.+?)\t(\d+)%\t(\S+)$/)
      if (!m) continue
      let pool = m[1].trim()
      // the CLI doubles the name on weekly-only rows ("Gemini 4 Argon Gemini 4 Argon ...")
      pool = pool.replace(/^(.*?)(?:\s+\1)$/, '$1')
      pools.push({
        pool,
        window: /Five/i.test(m[2]) ? '5h' : 'weekly',
        pct: Number(m[3]),
        reset_utc: m[4],
      })
    }
    return pools
  }

  /** The PRICE table is owned by `~/.dsh/bin/acp-budget`; we read it, never restate it.
      Parsed with a strict scanner over the known shape (`lane: { 'k': value, … }`) instead of
      turning object-literal text into JSON: comments, nested braces or a stray brace inside a
      string cannot desynchronise it, and nothing from the file is ever executed. */
  priceTable() {
    if (!existsSync(this.budgetCli)) return {}
    const src = readFileSync(this.budgetCli, 'utf8')
    const start = src.indexOf('PRICE = {')
    if (start < 0) return {}
    const end = src.indexOf('\n}', start)
    const block = src.slice(start + 'PRICE = '.length, end < 0 ? src.length : end + 2)
    const out = {}
    // Lane keys are QUOTED in acp-budget ("flash-low": { … }) — an earlier version of
    // this scanner required a bare key and silently priced nothing.
    for (const laneMatch of block.matchAll(/['"]?([A-Za-z][A-Za-z0-9_-]*)['"]?\s*:\s*\{([^{}]*)\}/g)) {
      const [, lane, body] = laneMatch
      const entry = {}
      // keys are quoted here as well ("pool": "Gemini Models") — requiring a bare
      // identifier priced zero lanes, which is how the plans table went empty
      for (const kv of body.matchAll(/['"]?([A-Za-z_][A-Za-z0-9_]*)['"]?\s*:\s*(?:'([^']*)'|"([^"]*)"|(-?\d+(?:\.\d+)?))/g)) {
        const key = kv[1]
        entry[key] = kv[2] !== undefined ? kv[2] : kv[3] !== undefined ? kv[3] : Number(kv[4])
      }
      // a lane without a pool and at least one numeric price is not a lane we can price
      if (typeof entry.pool === 'string' && Object.keys(entry).some((k) => typeof entry[k] === 'number')) {
        out[lane] = entry
      }
    }
    return out
  }

  copilotMonth() {
    const ym = new Date().toISOString().slice(0, 7)
    let used = 0
    let calls = 0
    if (existsSync(this.ledger)) {
      for (const line of readFileSync(this.ledger, 'utf8').split('\n')) {
        const f = line.split('\t')
        if (f.length > 2 && f[0].startsWith(ym) && f[1] === 'copilot') {
          used += Number(f[2]) || 0
          calls++
        }
      }
    }
    return { premium_used: Math.round(used * 100) / 100, calls, hold: this.hold, headroom: Math.round((this.hold - used) * 100) / 100 }
  }

  // ── the verdict the orchestrator lives by ─────────────────────────────────
  plans(pools) {
    const by = new Map()
    for (const p of pools) {
      if (!by.has(p.pool)) by.set(p.pool, {})
      by.get(p.pool)[p.window] = p.pct
    }
    const rows = []
    for (const [lane, pr] of Object.entries(this.priceTable())) {
      if (lane === 'strata' || lane === 'copilot') continue
      const w = by.get(pr.pool) || {}
      const windows = []
      let fits = true
      for (const [key, win, floor] of [['h5', '5h', this.floors.h5], ['wk', 'weekly', this.floors.wk]]) {
        if (pr[key] && w[win] != null) {
          const after = w[win] - pr[key]
          fits = fits && after >= floor
          windows.push({ window: win, before: w[win], after: Math.round(after), floor, ok: after >= floor })
        }
      }
      rows.push({ lane, unit: pr.unit || '', windows, fits })
    }
    return rows.sort((a, b) => a.lane.localeCompare(b.lane))
  }

  /** Cold start reads the on-disk cache: a page (or the Projects launcher) must get an
      answer in milliseconds, not wait 2-4 s for the first CLI read. A stale cache is still
      shown immediately and refreshed on the NEXT call — stale-but-fast beats fresh-but-late
      for a dashboard, and the payload says which one you are looking at. */
  loadDiskCache() {
    if (this.cache || !existsSync(this.cacheFile)) return null
    try {
      this.cache = JSON.parse(readFileSync(this.cacheFile, 'utf8'))
      this.provenance = 'disk cache'
    } catch {
      /* corrupt or unreadable: fall through to a probe */
    }
    return this.cache
  }

  validCache(c) {
    return !!c && typeof c.ts === 'number' && Array.isArray(c.pools) && c.pools.length > 0 &&
      c.pools.every((p) => p && typeof p.pool === 'string' && typeof p.window === 'string' &&
        typeof p.pct === 'number' && typeof p.reset_utc === 'string')
  }

  status(force = false) {
    if (!this.cache) this.loadDiskCache()
    if (this.cache && !this.validCache(this.cache)) this.cache = null   // corrupt or torn file
    const fresh = this.cache && Date.now() - this.cache.ts < this.ttlMs
    if (this.probing) {
      // single flight: a second caller inside a probe gets the current (possibly stale,
      // clearly labelled) view instead of firing a second CLI read
      return { ...(this.cache ?? { ts: 0, pools: [] }), source: 'probe-in-flight', ttl_ms: this.ttlMs,
               copilot: this.copilotMonth(), floors: this.floors, plans: this.plans(this.cache?.pools ?? []) }
    }
    if (force || !fresh) {
      this.probing = true
      try { return this.probeAndCache() } finally { this.probing = false }
    }
    this.provenance = 'cache'
    return { ...this.cache, source: this.provenance, ttl_ms: this.ttlMs, copilot: this.copilotMonth(),
             floors: this.floors, plans: this.plans(this.cache.pools) }
  }

  probeAndCache() {
      try {
        const next = { ts: Date.now(), pools: this.probeAgy() }
        if (!this.validCache(next)) throw new Error('probe returned an unusable shape')
        this.cache = next
        this.provenance = 'probe'
        mkdirSync(dirnameOf(this.cacheFile), { recursive: true })
        try {
          writeFileSync(this.cacheFile, JSON.stringify(next, null, 1))
        } catch {
          /* the cache is an optimisation, never a reason to fail a read */
        }
      } catch (err) {
        // last-good cache survives a failed probe; the payload says so
        this.provenance = this.cache ? 'probe-failed (showing last good)' : 'probe-failed (no data)'
        this.lastError = String(err && err.message ? err.message : err)
      }
    return {
      ...this.cache,
      ...(this.lastError ? { error: this.lastError } : {}),
      source: this.provenance,
      ttl_ms: this.ttlMs,
      copilot: this.copilotMonth(),
      floors: this.floors,
      plans: this.plans(this.cache.pools),
    }
  }

// ── who is running RIGHT NOW ──────────────────────────────────────────────
  /** Process scan, not a provider call: a `ps` read costs nothing and cannot move a
      quota counter. Lanes are identified from the ACP rows' own command lines (the
      adapter names the model and effort it was launched with), so the panel reports
      the same lanes the gate prices. Runs are appended to a small activity log so a
      short job that started and finished between two polls is still visible. */
  activity() {
    let out = ''
    try {
      out = execFileSync('ps', ['-eo', 'pid,ppid,etimes,comm,args', '--no-headers'], { encoding: 'utf8', timeout: 4000 })
    } catch {
      return { running: [], error: 'ps failed', seen: this.recentActivity() }
    }
    const running = []
    for (const line of out.split('\n')) {
      const m = line.trim().match(/^(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(.*)$/)
      if (!m) continue
      const [, pid, ppid, etimes, comm, args] = m
      // Match the EXECUTABLE, never a substring of the command line: a shell whose
      // script merely MENTIONS "copilot" is not a Copilot run (that false positive
      // was produced by this very patch script, 2026-11-01).
      if (/-eo pid,ppid,etimes,comm,args/.test(args)) continue
      const lane = this.laneOf(comm, args)
      if (!lane) continue
      running.push({ lane, pid: Number(pid), ppid: Number(ppid), seconds: Number(etimes), model: this.modelOf(args), args: args.slice(0, 160) })
    }
    const sig = running.map((r) => r.lane + ':' + r.pid).sort().join(',')
    if (sig !== this.lastSig) {
      this.lastSig = sig
      this.logActivity(running)
    }
    return { running, seen: this.recentActivity(), currencies: this.currencies(), strata: this.slots() }
  }

  laneOf(comm, args) {
    const argv = args.trim().split(/\s+/)
    const exe = (argv[0] || '').split('/').pop().toLowerCase()
    const c = comm.toLowerCase()   // the kernel truncates comm at 15 chars
    // Exact executable names only. A shell script that merely MENTIONS a name is not
    // that program — an earlier rule matched this very project's own patch script.
    const isAgy = exe === 'agy' || c === 'agy'
    const isAdapter = exe === 'google-antigravity-acp' || c.startsWith('google-antigrav')
    if (isAgy || isAdapter) {
      const model = this.modelOf(args)
      if (/opus|claude/i.test(model)) return 'agy-opus'
      if (/argon/i.test(model)) return 'agy-argon'
      return 'agy-flash'
    }
    if (exe === 'copilot' || c === 'copilot') return 'copilot'
    // node running the Copilot ACP shim: the SCRIPT must be argv[1] and the flag must be real
    const second = (argv[1] || '').split('/').pop().toLowerCase()
    if ((c === 'node' || exe === 'node') && second === 'copilot' && /--acp(\s|$)/.test(args)) return 'copilot'
    return null
  }

  modelOf(args) {
    const m = args.match(/--(?:model|m)[= ]+['"]?([A-Za-z][A-Za-z0-9._-]*)/)
    return m ? m[1] : ''
  }

  currencies() {
    return {
      'agy-flash': 'notches per JOB from the Gemini pool (five-hour AND weekly clocks)',
      'agy-opus': 'notches per JOB from the Claude and GPT pool (~14 per real job)',
      'agy-argon': 'weekly-only pool, rationed',
      'copilot': 'premium requests per PROMPT x multiplier (tool calls free)',
    }
  }

  logActivity(running) {
    const f = expand('~/.dsh/quota/activity.jsonl')
    try {
      mkdirSync(dirnameOf(f), { recursive: true })
      const ts = new Date().toISOString()
      for (const r of running) {
        const line = JSON.stringify({ ts, lane: r.lane, pid: r.pid, seconds: r.seconds, model: r.model })
        appendFileSync(f, line + '\n')
      }
    } catch {
      /* the activity log is telemetry, never a reason to fail a read */
    }
  }

  /** Recently-seen runs, collapsed per pid, so a finished job still shows its duration. */
  recentActivity(limit = 12) {
    const f = expand('~/.dsh/quota/activity.jsonl')
    if (!existsSync(f)) return []
    const byPid = new Map()
    for (const line of readFileSync(f, 'utf8').split('\n')) {
      if (!line.trim()) continue
      try {
        const j = JSON.parse(line)
        const prev = byPid.get(j.pid)
        if (!prev || j.ts > prev.ts_last) byPid.set(j.pid, { ...j, ts_last: j.ts, ts_first: prev ? prev.ts_first : j.ts })
      } catch { /* skip a torn line */ }
    }
    return [...byPid.values()].sort((a, b) => (a.ts_last < b.ts_last ? 1 : -1)).slice(0, limit)
  }
  /** The engine's own slot report: GET <engine>/slots -> [{id, n_ctx, is_processing,
      n_prompt_tokens}]. The engine serves 2 conversations; when both are processing,
      a third agent in-process is KV thrash and the honest move is an external lane.
      Read with a short synchronous curl so the tool/HTTP handlers stay synchronous. */
  slots() {
    try {
      const body = execFileSync('curl', ['-s', '-m', '2', `${this.engineBase}/slots`], { encoding: 'utf8', timeout: 2600 })
      const slots = JSON.parse(body)
      if (!Array.isArray(slots)) throw new Error('not an array')
      const busy = slots.filter((x) => x.is_processing).length
      return {
        online: true,
        base: this.engineBase,
        slots,
        busy,
        idle: slots.length - busy,
        saturated: busy >= slots.length,
        note: busy >= slots.length
          ? 'every slot is working: new in-process subagents would thrash KV re-prefill — route to a Gemini flash job, an Opus job if the gate says GO, or a Copilot prompt'
          : `${slots.length - busy} slot(s) free for in-process subagents`,
      }
    } catch (err) {
      return { online: false, base: this.engineBase, error: String(err && err.message ? err.message : err) }
    }
  }

  // ── wiring ────────────────────────────────────────────────────────────────
  attach(ctx) {
    const disposers = []
    ctx.inject(['tools'], (toolCtx) => {
      disposers.push(this.registerTools(toolCtx.tools))
    })
    ctx.inject(['webServer'], (wsCtx) => {
      disposers.push(
        wsCtx.webServer.register({
          kind: 'prefix',
          path: '/api/quota-panel',
          handler: (req, res) => this.handleHttp(req, res),
        }),
      )
    })
    return () => {
      for (const d of disposers) {
        try {
          d()
        } catch {
          /* ignore */
        }
      }
      this.disposed = true
    }
  }

  registerTools(tools) {
    const render = (args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }]
    return tools.register({
      name: 'quota_panel',
      description:
        'Third-party agent quota and live activity, read locally (never spends quota to report quota). actions: status (pools + reset clocks + Copilot totals + per-lane plans), activity (which agy / copilot processes are running right now, with model and elapsed seconds), plan (lane[,jobs] against the floors), refresh (force one free re-probe). Floors: keep a five-hour pool >=20% and a weekly pool >=25%.',
      parameters: {
        type: 'object',
        properties: {
          action: { type: 'string', enum: ['status', 'activity', 'plan', 'refresh'] },
          lane: { type: 'string', description: 'lane id for action=plan (flash-low, flash-high, opus, argon)' },
        },
        required: ['action'],
      },
      output: { schema: { type: 'object' }, render },
      execute: (raw) => {
        try {
          return this.rpc((raw && raw.action) || 'status', raw)
        } catch (err) {
          return { error: String(err && err.message ? err.message : err) }
        }
      },
    })
  }

  rpc(action, rawArgs = {}) {
    const args = rawArgs && typeof rawArgs === 'object' && !Array.isArray(rawArgs) ? rawArgs : {}
    if (action === 'activity') return this.activity()
    if (action === 'ping') {
      if (!this.cache) this.loadDiskCache()
      return { ok: true, ts: Date.now(), source: this.provenance, pools: this.cache ? this.cache.pools.length : 0 }
    }
    if (action === 'refresh') return this.status(true)
    if (action === 'plan') {
      const s = this.status(false)
      const rows = this.plans(s.pools)
      if (args.lane) {
        const row = rows.find((r) => r.lane === args.lane)
        return row ?? { error: `unknown lane ${args.lane}`, lanes: rows.map((r) => r.lane) }
      }
      return { floors: s.floors, plans: rows }
    }
    return this.status(false)
  }

  handleHttp(req, res) {
    const url = new URL(req.url || '/', 'http://localhost')
    const send = (code, obj) => {
      const raw = JSON.stringify(obj)
      res.writeHead(code, { 'content-type': 'application/json', 'content-length': Buffer.byteLength(raw) })
      res.end(raw)
    }
    let action = url.searchParams.get('action') || 'status'
    const lane = url.searchParams.get('lane') || undefined
    if ((req.method || 'GET').toUpperCase() === 'POST') {
      return this.readBody(req)
        .then((body) => send(200, this.rpc(body.action || action, body)))
        .catch((err) => send(400, { error: String(err && err.message ? err.message : err) }))
    }
    if (!url.pathname.endsWith('/rpc') && url.pathname !== '/api/quota-panel') {
      return send(404, { error: 'use /api/quota-panel/rpc' })
    }
    try {
      send(200, this.rpc(action, { lane }))
    } catch (err) {
      send(500, { error: String(err && err.message ? err.message : err) })
    }
  }

  readBody(req) {
    return new Promise((resolve, reject) => {
      let data = ''
      req.on('data', (c) => {
        data += c
        if (data.length > 65536) reject(new Error('body too large'))
      })
      req.on('end', () => {
        try {
          resolve(data ? JSON.parse(data) : {})
        } catch {
          resolve({})
        }
      })
      req.on('error', reject)
    })
  }
}

function expand(p) {
  return p.startsWith('~') ? HOME + p.slice(1) : p
}
function dirnameOf(p) {
  const i = p.lastIndexOf('/')
  return i > 0 ? p.slice(0, i) : '.'
}
