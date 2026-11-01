/**
 * dsh-quota-panel — host entry (plain ESM, no runtime dependencies).
 *
 * Loads on any profile that includes the bundle. Tools and HTTP routes are wired
 * through ctx.inject so a profile without a webServer still gets the reader and
 * the `quota_panel` tool.
 */
import { QuotaPanel } from './host/service.js'

export const name = 'dsh-quota-panel'

/** Row config validation via the Standard Schema contract (same shape as the other bundles). */
export const Config = {
  '~standard': {
    version: 1,
    vendor: 'dsh-quota-panel',
    validate(input) {
      const issues = []
      const v = input && typeof input === 'object' && !Array.isArray(input) ? input : {}
      for (const key of ['agyBin', 'ledger', 'budgetCli', 'cacheFile']) {
        if (v[key] !== undefined && typeof v[key] !== 'string') {
          issues.push({ path: [key], message: 'must be a string (path, ~ allowed)' })
        }
      }
      for (const key of ['ttlMs', 'floorFiveHour', 'floorWeekly', 'copilotHold']) {
        if (v[key] !== undefined && !Number.isFinite(Number(v[key]))) {
          issues.push({ path: [key], message: 'must be a number' })
        }
      }
      if (issues.length) return { issues }
      return { value: v }
    },
  },
}

export function apply(ctx, config) {
  const service = new QuotaPanel(config ?? {})
  try {
    ctx.provide?.('quotaPanel', service)
  } catch {
    /* older runtime */
  }
  ctx.effect(
    () => service.attach(ctx),
    'dsh-quota-panel: attach tool + web route',
  )
}
