/* dsh-strata-flex client — two footer buttons in the composer dock:
 *   "lower brain"  -> flex the Strata expert cache to the floor (~512 experts, frees ~20 GB for Comfy)
 *   "reclaim"      -> reserve_mib null, engine takes the cache back (agent full speed)
 * Calls only the plugin's own same-origin route (/api/strata-flex); the host
 * half talks to the Strata engine. State label = expert slots resident + free VRAM.
 *
 * Update survival: the React path uses the slots API with the
 * 'conversation.composer.dock' slot; if a harness update renames/removes that
 * internal, we fall back to plain-DOM injection into [data-composer-dock]
 * (stable data-attribute the built-in footer row renders). Both paths drive the
 * same host route, so the buttons keep working across DSH updates unless the
 * webServer service contract itself changes.
 */
window.__ModuleLoader__.load({
  id: 'dsh-strata-flex',
  factory: (require) => {
    const API = '/api/strata-flex'
    const gb = (mib) => (mib == null ? '?' : (mib / 1024).toFixed(1) + 'G')

    async function getState() {
      const r = await fetch(API + '/state')
      const j = await r.json()
      return j && j.ok ? j.state : null
    }
    async function doAction(action, reserveMib) {
      const r = await fetch(API, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(reserveMib == null ? { action } : { action, reserve_mib: reserveMib }),
      })
      const j = await r.json()
      if (j && j.ok) return { state: j.state, note: j.note, applied: j.reserve_applied }
      throw new Error((j && j.error) || 'failed')
    }
    const label = (s) => (s ? `${s.expert_slots}/${s.expert_slots_full} experts · ${gb(s.vram_free_mib)} free` : 'vram ?')
    // Bounds mirror the host's clamp. The engine resizes in 512 MiB segments and accepts any
    // integer with no floor, so the guard is ours. Probed 2026-11-01: full cache 18,734 MiB,
    // 1,933 MiB free, one proven window at reserve 22016 giving ~19.4 GiB free.
    const SEG = 512, SET_MIN = 2048, SET_MAX = 22016
    const snap = (n) => Math.min(SET_MAX, Math.max(SET_MIN, Math.round(n / SEG) * SEG))
    const gib = (mib) => (mib / 1024).toFixed(1)
    const lowered = (s) => s && s.expert_slots != null && s.expert_slots_full != null
      ? s.expert_slots < s.expert_slots_full * 0.9 : false

    // ── primary: React into the documented slot ─────────────────────────────
    function reactPath() {
      const React = require('react')
      const { useState, useEffect, useCallback, useRef } = React
      const h = React.createElement

      function FlexButtons() {
        const [state, setState] = useState(null)
        const [err, setErr] = useState(null)
        const [busy, setBusy] = useState(null)

        const load = useCallback(async () => {
          try { const s = await getState(); if (s) setState(s) } catch { /* stale label */ }
        }, [])
        useEffect(() => { load() }, [load])

        const act = useCallback(async (action, value) => {
          setBusy(action === 'set' ? `set ${value}` : action); setErr(null)
          try {
            const r = await doAction(action, value)
            if (r.state) setState(r.state)
            if (r.note) setErr(r.note)
            // The engine resizes BETWEEN requests, so its own reply can be a beat ahead of
            // what /metrics reports. Re-read twice so the numbers visibly move under the
            // slider instead of looking frozen.
            if (action === 'set' || action === 'reclaim' || action === 'flex') refreshSoon()
            return r
          } catch (e) { setErr(String(e && e.message ? e.message : e)) }
          finally { setBusy(null); setTimeout(() => setErr(null), 8000) }
        }, [])

        const pill = {
          border: '1px solid color-mix(in srgb, currentColor 35%, transparent)',
          background: 'transparent',
          color: 'inherit',
          borderRadius: 999,
          padding: '2px 9px',
          fontSize: '11.5px',
          lineHeight: '16px',
          cursor: 'pointer',
          opacity: 0.85,
        }
        // Hover the lower-brain button and the slider appears. The value is applied ONCE IT
        // SETTLES (700 ms after the last change), on drag release, or on mouse out — never per
        // pixel, because each apply is a real engine call that may wait for a gap between
        // requests. Clicking the button itself still does the fixed lower, as before.
        const [open, setOpen] = useState(false)
        const [val, setVal] = useState(14336)
        const [applied, setApplied] = useState(null)
        const [settling, setSettling] = useState(false)
        const hideTimer = useRef(null)
        const settleTimer = useRef(null)
        const pollTimers = useRef([])

        useEffect(() => () => {
          if (hideTimer.current) clearTimeout(hideTimer.current)
          if (settleTimer.current) clearTimeout(settleTimer.current)
          for (const t of pollTimers.current) clearTimeout(t)
        }, [])

        const refreshSoon = () => {
          for (const t of pollTimers.current) clearTimeout(t)
          pollTimers.current = [setTimeout(load, 700), setTimeout(load, 1800)]
        }

        const show = () => { if (hideTimer.current) clearTimeout(hideTimer.current); setOpen(true) }
        const scheduleHide = () => {
          if (hideTimer.current) clearTimeout(hideTimer.current)
          hideTimer.current = setTimeout(() => setOpen(false), 250)
        }

        const applyNow = (value) => {
          if (settleTimer.current) { clearTimeout(settleTimer.current); settleTimer.current = null }
          setSettling(false)
          if (applied === value) return
          act('set', value).then((r) => { setApplied(r && r.applied != null ? r.applied : value) }).catch(() => undefined)
        }

        const onSlide = (n) => {
          const v = snap(n)
          setVal(v); setSettling(true)
          if (settleTimer.current) clearTimeout(settleTimer.current)
          settleTimer.current = setTimeout(() => { settleTimer.current = null; applyNow(v) }, 700)
        }
        const flush = () => { if (settleTimer.current) applyNow(val) }
        const engineApplied = state && state.reserve_mib != null ? state.reserve_mib : null
        const shownApplied = applied != null ? applied : engineApplied
        const low = lowered(state)
        return h('span', {
          style: { display: 'inline-flex', alignItems: 'center', gap: 6, margin: '0 6px', position: 'relative' },
          title: 'Strata agent-engine VRAM flex (expert cache). Lower = room for local ComfyUI; reclaim = full-speed brain.',
          onMouseEnter: show, onMouseLeave: scheduleHide, onFocus: show, onBlur: scheduleHide,
        },
          open ? h('span', {
            style: {
              position: 'absolute', bottom: '100%', left: 0, marginBottom: 6, zIndex: 60,
              display: 'flex', flexDirection: 'column', gap: 6, padding: '8px 10px',
              border: '1px solid color-mix(in srgb, currentColor 30%, transparent)',
              background: 'color-mix(in srgb, currentColor 8%, transparent)',
              borderRadius: 8, minWidth: 244, cursor: 'default',
            },
            onMouseEnter: show, onMouseLeave: scheduleHide,
          },
            h('span', { style: { fontSize: '11.5px', opacity: 0.85 } },
              `keep ${gib(val)} GiB free`,
              h('span', { style: { opacity: 0.6 } },
                shownApplied != null ? `  ·  applied ${gib(shownApplied)} GiB` : '  ·  engine at full speed')),
            h('input', {
              type: 'range', min: SET_MIN, max: SET_MAX, step: SEG, value: val,
              'aria-label': 'VRAM to keep free for other programs, in MiB',
              style: { width: '100%', accentColor: 'currentColor' },
              onChange: (e) => onSlide(Number(e.target.value)),
              onPointerUp: flush, onKeyUp: () => { if (settleTimer.current) applyNow(val) },
            }),
            h('span', { style: { display: 'flex', gap: 6, alignItems: 'center' } },
              h('button', { type: 'button', style: pill, onClick: () => onSlide(14336) }, 'mid'),
              h('button', { type: 'button', style: pill, onClick: () => onSlide(SET_MAX) }, 'max window'),
              h('button', { type: 'button', style: pill, onClick: () => onSlide(SET_MIN) }, 'min'),
              h('span', { style: { fontSize: '10.5px', opacity: 0.6, marginLeft: 'auto' } },
                settling ? 'settling…' : 'applies when you stop'),
            ),
            h('span', { style: { fontSize: '11px', opacity: 0.8 } },
              state && state.expert_slots != null
                ? `engine right now: ${state.expert_slots}/${state.expert_slots_full} experts resident · ${gb(state.expert_cache_mib || 0)} GiB cache · ${gb(state.vram_free_mib || 0)} GiB free`
                : 'engine state unknown — click the dotted pill to re-read'),
            h('span', { style: { fontSize: '10.5px', opacity: 0.6 } },
              'one engine call per settle · snapped to the 512 MiB segment · the resize lands between engine requests, so the numbers can take a beat'),
          ) : null,
          h('button', { type: 'button', style: { ...pill, fontWeight: low ? 700 : 400 }, disabled: !!busy, onClick: () => act('flex') }, busy === 'flex' ? '…' : '⬇ lower brain'),
          h('button', { type: 'button', style: { ...pill, fontWeight: low ? 400 : 700 }, disabled: !!busy, onClick: () => act('reclaim') }, busy === 'reclaim' ? '…' : '⬆ reclaim'),
          h('button', { type: 'button', title: 'Click to refresh engine state', style: { ...pill, borderStyle: 'dotted', opacity: 0.6 }, onClick: () => load() }, label(state)),
          err ? h('span', { style: { fontSize: '11px', opacity: 0.75 } }, err) : null,
        )
      }
      return {
        inject: ['slots'],
        apply(ctx) { installSlot(ctx, FlexButtons) },
      }
    }

    function installSlot(ctx, FlexButtons) {
      try {
        if (!ctx.slots || typeof ctx.slots.inject !== 'function') throw new Error('slots service unavailable')
        ctx.slots.inject('conversation.composer.dock', () => ctx.slots.register({
          name: 'conversation.composer.dock', id: 'strata-flex', order: 50,
        }, FlexButtons))
      } catch (e) {
        try { console.warn('[dsh-strata-flex] slot API unavailable, DOM fallback active:', e) } catch { /* ignore */ }
        domFallback()
      }
    }

    // ── fallback: plain DOM into the stable data-attribute of the footer row ─
    function domFallback() {
      const style = {
        border: '1px solid rgba(128,128,128,0.4)', background: 'transparent', color: 'inherit',
        borderRadius: 999, padding: '2px 9px', font: 'inherit', fontSize: '11.5px', cursor: 'pointer', opacity: 0.85,
      }
      let mounted = false
      const mount = () => {
        const dock = document.querySelector('[data-composer-dock]')
        if (!dock || dock.querySelector('[data-strata-flex]')) return
        const span = document.createElement('span')
        span.setAttribute('data-strata-flex', '')
        span.style.cssText = 'display:inline-flex;align-items:center;gap:6px;margin:0 6px;'
        const mk = (text, title) => {
          const b = document.createElement('button')
          b.type = 'button'; b.textContent = text; b.title = title
          Object.assign(b.style, style)
          return b
        }
        const down = mk('⬇ lower brain', 'Flex Strata expert cache down (~20 GB free for ComfyUI)')
        const up = mk('⬆ reclaim', 'Reclaim the expert cache (full-speed agent)')
        const stat = mk('vram ?', 'Click to refresh engine state')
        stat.style.borderStyle = 'dotted'
        let busy = false
        const render = (s) => { stat.textContent = label(s) }
        const run = async (action) => {
          if (busy) return
          busy = true; down.disabled = up.disabled = true
          try { const r = await doAction(action); if (r.state) render(r.state) }
          catch (e) { stat.textContent = String(e && e.message ? e.message : e) }
          finally { busy = false; down.disabled = up.disabled = false }
        }
        down.addEventListener('click', () => run('flex'))
        up.addEventListener('click', () => run('reclaim'))
        stat.addEventListener('click', async () => { try { render(await getState()) } catch { /* ignore */ } })
        span.append(down, up, stat)
        dock.appendChild(span)
        getState().then(render).catch(() => { /* ignore */ })
        mounted = true
      }
      mount()
      if (window.MutationObserver) {
        const mo = new MutationObserver(() => { if (mounted) mo.disconnect(); else mount() })
        mo.observe(document.body, { childList: true, subtree: true })
        setTimeout(() => mo.disconnect(), 60000)
      }
    }

    return reactPath()
  },
})
