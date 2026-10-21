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
    async function doAction(action) {
      const r = await fetch(API, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ action }),
      })
      const j = await r.json()
      if (j && j.ok) return { state: j.state }
      throw new Error((j && j.error) || 'failed')
    }
    const label = (s) => (s ? `${s.expert_slots}/${s.expert_slots_full} experts · ${gb(s.vram_free_mib)} free` : 'vram ?')
    const lowered = (s) => s && s.expert_slots != null && s.expert_slots_full != null
      ? s.expert_slots < s.expert_slots_full * 0.9 : false

    // ── primary: React into the documented slot ─────────────────────────────
    function reactPath() {
      const React = require('react')
      const { useState, useEffect, useCallback } = React
      const h = React.createElement

      function FlexButtons() {
        const [state, setState] = useState(null)
        const [err, setErr] = useState(null)
        const [busy, setBusy] = useState(null)

        const load = useCallback(async () => {
          try { const s = await getState(); if (s) setState(s) } catch { /* stale label */ }
        }, [])
        useEffect(() => { load() }, [load])

        const act = useCallback(async (action) => {
          setBusy(action); setErr(null)
          try {
            const r = await doAction(action)
            if (r.state) setState(r.state)
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
        const low = lowered(state)
        return h('span', {
          style: { display: 'inline-flex', alignItems: 'center', gap: 6, margin: '0 6px' },
          title: 'Strata agent-engine VRAM flex (expert cache). Lower = room for local ComfyUI; reclaim = full-speed brain.',
        },
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
