/* dsh-quota-panel client — "Quota" main panel + sidebar entry (next to Projects).
 *
 * One card per Antigravity pool: percent left as a big amber read-out, a bar, and a
 * LIVE countdown to that pool's own reset clock (five-hour and weekly windows expire
 * on different timestamps, which is exactly why reading a single "remaining %" is
 * misleading). Below: the per-lane verdict for ONE more job against the floors, the
 * Copilot premium-request total for the month, and the Strata row (free money, two
 * conversation slots).
 *
 * Talks only to the plugin's same-origin route /api/quota-panel/rpc — the same reader
 * the `quota_panel` tool uses, so the panel and the orchestrator cannot disagree.
 * Nothing here triggers a model call: the host reads agy's local /usage command and
 * the local ledger, and caches the result.
 *
 * Hand-written lazy-CJS factory (same shape as dsh-projects-panel — no bundler).
 */
window.__ModuleLoader__.load({
  id: 'dsh-quota-panel',
  factory: (require) => {
    const React = require('react')
    const { createElement: h, useState, useEffect, useCallback } = React
    const API = '/api/quota-panel'
    const AMBER = '#e7b24b'

    const CSS = `
      .qp-wrap { padding: 18px 22px 0; max-width: 1100px; margin: 0 auto; height: 100%;
        display: flex; flex-direction: column; box-sizing: border-box; overflow: hidden; }
      .qp-scroll { flex: 1; min-height: 0; overflow-y: auto; padding-bottom: 40px; }
      .qp-head { display: flex; align-items: baseline; gap: 12px; }
      .qp-head h1 { font-size: 17px; font-weight: 650; margin: 0; }
      .qp-sub { font-size: 12px; opacity: .6; }
      .qp-actions { margin-left: auto; display: flex; gap: 8px; align-items: center; }
      .qp-btn { border: 1px solid color-mix(in srgb, currentColor 30%, transparent);
        background: transparent; color: inherit; border-radius: 7px; padding: 3px 10px;
        font-size: 12px; cursor: pointer; }
      .qp-btn:hover:not(:disabled) { background: color-mix(in srgb, currentColor 10%, transparent); }
      .qp-btn:disabled { opacity: .4; cursor: default; }
      .qp-grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        margin-top: 14px; }
      .qp-card { border: 1px solid color-mix(in srgb, currentColor 16%, transparent);
        border-radius: 11px; padding: 12px 14px; box-sizing: border-box;
        background: color-mix(in srgb, currentColor 4%, transparent); }
      .qp-card h2 { margin: 0 0 8px; font-size: 11px; letter-spacing: .1em; text-transform: uppercase;
        opacity: .6; font-weight: 600; }
      .qp-window { margin-bottom: 12px; }
      .qp-pct { font-size: 26px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.1; }
      .qp-pct.low { color: #e8712a; }
      .qp-bar { height: 5px; border-radius: 3px; margin: 5px 0;
        background: color-mix(in srgb, currentColor 12%, transparent); overflow: hidden; }
      .qp-bar i { display: block; height: 100%; }
      .qp-row { display: flex; justify-content: space-between; gap: 10px; font-size: 11.5px; opacity: .75; }
      .qp-clock { font-variant-numeric: tabular-nums; }
      .qp-clock.due { color: #e8712a; }
      .qp-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
      .qp-table th { text-align: left; font-size: 10.5px; text-transform: uppercase; letter-spacing: .08em;
        opacity: .55; padding: 4px 6px; font-weight: 600; }
      .qp-table td { padding: 5px 6px; border-top: 1px solid color-mix(in srgb, currentColor 12%, transparent);
        vertical-align: top; }
      .qp-go { color: ${AMBER}; font-weight: 650; }
      .qp-no { color: #e8712a; font-weight: 650; }
      .qp-free { opacity: .7; }
      .qp-big { font-size: 26px; font-weight: 700; font-variant-numeric: tabular-nums; }
      .qp-note { font-size: 11.5px; opacity: .6; margin: 10px 0 0; line-height: 1.55; }
      .qp-note code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
      .qp-err { margin-top: 10px; padding: 7px 11px; font-size: 12.5px; border-radius: 8px;
        border: 1px solid color-mix(in srgb, #d05050 45%, transparent); color: #e08585; }
      .qp-wide { grid-column: 1 / -1; }
      .qp-live { display: flex; align-items: center; gap: 8px; }
      .qp-dot { width: 8px; height: 8px; border-radius: 50%; background: #3a424c; flex: none; }
      .qp-dot.on { background: #3fb950; box-shadow: 0 0 0 3px color-mix(in srgb, #3fb950 22%, transparent);
        animation: qp-pulse 1.6s ease-in-out infinite; }
      @keyframes qp-pulse { 0%,100% { opacity: 1 } 50% { opacity: .45 } }
      .qp-run { display: flex; justify-content: space-between; gap: 10px; font-size: 12px;
        min-width: 0; }
      .qp-run > span:first-child { min-width: 0; overflow: hidden; text-overflow: ellipsis;
        white-space: nowrap; }
      .qp-run > span:last-child { flex: none; }
        padding: 4px 0; border-top: 1px solid color-mix(in srgb, currentColor 12%, transparent); }
      .qp-elapsed { font-variant-numeric: tabular-nums; color: #3fb950; }
      .qp-idle { font-size: 12.5px; opacity: .65; }
      .qp-slot { font-size: 11px; padding: 2px 7px; border-radius: 999px;
        border: 1px solid color-mix(in srgb, currentColor 22%, transparent);
        background: color-mix(in srgb, currentColor 7%, transparent); }
      .qp-slot.on { border-color: color-mix(in srgb, #3fb950 55%, transparent);
        background: color-mix(in srgb, #3fb950 16%, transparent); }
      .qp-slotnote { font-size: 11.5px; opacity: .8; flex: 1; min-width: 120px; }
      .qp-urge { font-size: 11.5px; opacity: .75; }
      .qp-urge b { color: #e8712a; }
      @media (prefers-reduced-motion: reduce) {
        .qp-dot.on { animation: none; }
      }
    `
    let styled = false
    function ensureStyle() {
      if (styled || typeof document === 'undefined') return
      const s = document.createElement('style')
      s.textContent = CSS
      document.head.appendChild(s)
      styled = true
    }

    function countdown(iso, now) {
      const ms = new Date(iso).getTime() - now
      if (!Number.isFinite(ms)) return { text: 'no reset reported', cls: '' }
      if (ms <= 0) return { text: 'window rolled — re-probe', cls: 'due' }
      const s = Math.floor(ms / 1000)
      const d = Math.floor(s / 86400)
      const hr = Math.floor((s % 86400) / 3600)
      const mn = Math.floor((s % 3600) / 60)
      // The warning is about the TOTAL, never about hours-after-modulo: a weekly pool
      // two days out has hr === 0 and was lighting up as if it were about to roll.
      const text = d ? `${d}d ${hr}h left` : hr ? `${hr}h ${mn}m left` : `${mn}m left`
      return { text, cls: s < 3600 ? 'due' : '' }
    }
    const stamp = (iso) => {
      const d = new Date(iso)
      return Number.isFinite(d.getTime()) ? d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : iso
    }

    function PoolCard({ name, windows, now }) {
      return h('div', { className: 'qp-card' },
        h('h2', null, name),
        windows.map((w) => {
          const c = countdown(w.reset_utc, now)
          const low = w.pct < 25
          return h('div', { className: 'qp-window', key: w.window },
            h('div', { className: 'qp-row' },
              h('span', null, `${w.window} window`),
              h('span', { className: 'qp-pct' + (low ? ' low' : '') }, `${w.pct}%`),
            ),
            h('div', { className: 'qp-bar' },
              h('i', { style: { width: `${w.pct}%`, background: low ? '#e8712a' : AMBER } })),
            h('div', { className: 'qp-row' },
              h('span', { className: 'qp-clock ' + c.cls }, c.text),
              h('span', null, `resets ${stamp(w.reset_utc)}`),
            ),
          )
        }),
      )
    }

    const mmss = (sec) => `${Math.floor(sec / 60)}:${String(Math.floor(sec % 60)).padStart(2, '0')}`

    function ActivityCard({ act, now, fetchedAt }) {
      // elapsed = what the host measured at fetch time + how long ago THIS browser
      // fetched it. Mixing the host's clock with the browser's produced jumps.
      const sinceFetch = Math.max(0, Math.floor((now - fetchedAt) / 1000))
      const running = (act && act.running) || []
      const seen = (act && act.seen) || []
      const cur = (act && act.currencies) || {}
      return h('div', { className: 'qp-card qp-wide' },
        h('h2', null, 'Agents running right now'),
        h('div', { className: 'qp-live' },
          h('span', { className: 'qp-dot' + (running.length ? ' on' : '') }),
          ...(((act && act.strata && act.strata.slots) || []).map((sl) =>
            h('span', { className: 'qp-slot' + (sl.is_processing ? ' on' : ''), key: 'slot' + sl.id,
                        title: `slot ${sl.id}: ${sl.n_prompt_tokens} of ${sl.n_ctx} tokens in context` },
              `slot ${sl.id}`))),
          act && act.strata && act.strata.online
            ? h('span', { className: 'qp-slotnote' }, act.strata.note)
            : h('span', { className: 'qp-slotnote' }, 'Strata engine not answering on ' + (act && act.strata && act.strata.base)),
          h('span', { className: running.length ? null : 'qp-idle' },
            running.length ? `${running.length} external agent process(es) live` : 'nothing running — the external lanes are idle'),
        ),
        running.map((r) => h('div', { className: 'qp-run', key: r.lane + r.pid },
          h('span', null, `${r.lane}  pid ${r.pid}${r.model ? '  ·  ' + r.model : ''}`),
          h('span', { className: 'qp-elapsed' }, `${mmss(r.seconds + sinceFetch)} running`),
        )),
        !running.length && seen.length
          ? h('div', null, h('p', { className: 'qp-note' }, 'last seen:'),
              seen.slice(0, 5).map((s) => h('div', { className: 'qp-run', key: s.pid },
                h('span', null, `${s.lane}  pid ${s.pid}${s.model ? '  ·  ' + s.model : ''}`),
                h('span', null, `${new Date(s.ts_last).toLocaleTimeString()}  ·  ${mmss(s.seconds)}+`))))
          : null,
        h('p', { className: 'qp-urge' },
          'Detected by a ', h('code', null, 'ps'), ' scan of the ACP rows’ own command lines — no provider call, no notch, no premium request. Billable unit per lane: ',
          Object.entries(cur).map(([k, v]) => `${k} = ${v}`).join(' · ')),
      )
    }

    function QuotaPage() {
      const [data, setData] = useState(null)
      const [fatal, setFatal] = useState(null)
      const [busy, setBusy] = useState(false)
      const [now, setNow] = useState(Date.now())
      const [act, setAct] = useState(null)
      const [actFetchedAt, setActFetchedAt] = useState(Date.now())

      const load = useCallback(async (force) => {
        setBusy(true)
        try {
          const res = await fetch(`${API}/rpc`, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ action: force ? 'refresh' : 'status' }),
          })
          const j = await res.json()
          if (j && j.error) setFatal(j.error)
          else { setFatal(null); setData(j) }
        } catch (err) {
          setFatal(String(err && err.message ? err.message : err))
        } finally {
          setBusy(false)
        }
      }, [])

      const loadAct = useCallback(async () => {
        try {
          setAct(await (await fetch(`${API}/rpc`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ action: 'activity' }) })).json())
          setActFetchedAt(Date.now())
        } catch { /* keep the last view */ }
      }, [])

      useEffect(() => { ensureStyle(); load(false); loadAct() }, [load, loadAct])
      // activity is a process read, so it is cheap enough to poll every 2 s; the pools
      // themselves still only refresh on the host's TTL, never per poll
      useEffect(() => { const t = setInterval(loadAct, 2000); return () => clearInterval(t) }, [loadAct])
      // one-second tick drives only the countdowns; the pools themselves re-read on the
      // host's own TTL, so polling the page never re-probes the provider
      useEffect(() => {
        const t = setInterval(() => setNow(Date.now()), 1000)
        return () => clearInterval(t)
      }, [])

      const groups = new Map()
      for (const p of (data && data.pools) || []) {
        if (!groups.has(p.pool)) groups.set(p.pool, [])
        groups.get(p.pool).push(p)
      }
      const cop = data && data.copilot

      return h('div', { className: 'qp-wrap' },
        h('div', { className: 'qp-head' },
          h('h1', null, 'Quota'),
          h('span', { className: 'qp-sub' },
            data ? `read ${new Date(data.ts).toLocaleTimeString()} · source: ${data.source}` : 'reading…'),
          h('span', { className: 'qp-actions' },
            busy ? h('span', { className: 'qp-sub' }, 'probing…') : null,
            h('button', { className: 'qp-btn', disabled: busy, onClick: () => load(true), title: 'agy /usage is a local read: it moves no pool counter' },
              're-probe (free)'),
          ),
        ),
        fatal ? h('div', { className: 'qp-err' }, `reader: ${fatal}`) : null,
        h('div', { className: 'qp-scroll' },
          h('div', { className: 'qp-grid' },
            h(ActivityCard, { act, now, fetchedAt: actFetchedAt }),
            [...groups.entries()].map(([name, wins]) => h(PoolCard, { key: name, name, windows: wins, now })),
            cop ? h('div', { className: 'qp-card' },
              h('h2', null, 'Copilot · premium requests'),
              h('div', { className: 'qp-big' }, cop.premium_used.toFixed(2),
                h('span', { className: 'qp-sub' }, ` / ${cop.hold} held`)),
              h('div', { className: 'qp-bar' },
                h('i', { style: { width: `${Math.max(0, Math.min(100, (cop.premium_used / cop.hold) * 100))}%`, background: AMBER } })),
              h('div', { className: 'qp-row' },
                h('span', null, `${cop.calls} logged job(s) this month`),
                h('span', null, `${cop.headroom.toFixed(2)} left`),
              ),
              h('p', { className: 'qp-note' }, 'Billed once per prompt × model multiplier; tool calls are free and effort never changes the multiplier. The 20 is a self-imposed hold, not the account allowance.'),
            ) : null,
            h('div', { className: 'qp-card' },
              h('h2', null, 'Strata · local'),
              h('div', { className: 'qp-big' }, 'unlimited'),
              h('p', { className: 'qp-note' }, 'Free in money (electricity). The constraint is 2 conversation slots and latency — which is why hard reasoning stays local and external quota is only for parallel independence or a different model family.'),
            ),
            data && data.plans ? h('div', { className: 'qp-card qp-wide' },
              h('h2', null, `One more job — verdict against the floors (5h ≥ ${data.floors.h5}%, weekly ≥ ${data.floors.wk}%)`),
              h('table', { className: 'qp-table' },
                h('thead', null, h('tr', null, h('th', null, 'lane'), h('th', null, 'what one job does'), h('th', null, 'verdict'))),
                h('tbody', null,
                ...data.plans.map((r) => h('tr', { key: r.lane },
                  h('td', null, r.lane),
                  h('td', null, r.windows.length
                    ? r.windows.map((w) => `${w.window} ${w.before}% → ${w.after}%`).join(' · ')
                    : 'weekly-only pool'),
                  h('td', { className: r.fits ? 'qp-go' : 'qp-no' }, r.fits ? 'GO' : 'NO-GO'),
                )),
                h('tr', null, h('td', null, 'copilot'),
                  h('td', null, '0.25 premium per prompt (mai-code); 6× for gpt-5.3, 9× sonnet-4.6 (retiring)'),
                  h('td', { className: 'qp-go' }, 'see above')),
                h('tr', null, h('td', null, 'strata'), h('td', null, 'free · 1 of 2 slots'),
                  h('td', { className: 'qp-free' }, 'free · slots are the limit')),
                ),
              ),
              h('p', { className: 'qp-note' },
                'Prices are parsed out of ', h('code', null, '~/.dsh/bin/acp-budget'),
                ' at read time, so this panel and the routing gate can never disagree. A NO-GO is not advisory. The five-hour windows ROLL: a notch frees about five hours after it was spent, so the wait is the age of the oldest spend, not a fixed reset — the gate prints it (`acp-budget need LANE`). Waiting, or dropping to a cheaper lane, is the answer.',
              ),
            ) : null,
          ),
          h('p', { className: 'qp-note' },
            'Nothing on this page costs quota: pools come from ', h('code', null, 'agy -p /usage'),
            ' (a local command — measured 2026-11-01 to move no pool counter), Copilot totals from ',
            h('code', null, '~/.dsh/quota/acp-ledger.tsv'),
            ', and results are cached on the host so repeated polls never re-probe.'),
        ),
      )
    }

    function QuotaIcon({ size = 16 }) {
      return h('svg', { width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
        stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round' },
        h('path', { d: 'M4 17a8 8 0 1 1 16 0' }),
        h('path', { d: 'M12 17l4.2-5' }),
        h('path', { d: 'M4 20h16' }),
      )
    }

    return {
      inject: ['slots'],
      apply(ctx) {
        ctx.slots.inject('main', () =>
          ctx.slots.register({ name: 'main', key: 'quota-panel' }, QuotaPage))
        ctx.slots.inject('sidebar.panellist', () =>
          ctx.slots.register(
            { name: 'sidebar.panellist', id: 'quota-panel', order: 22, label: () => 'Quota' },
            QuotaIcon,
          ))
      },
    }
  },
})
