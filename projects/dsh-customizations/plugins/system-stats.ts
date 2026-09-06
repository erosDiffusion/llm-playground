import { readFileSync } from 'node:fs'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import type { Context } from '@deepseek-ai/cordis'

const pExecFile = promisify(execFile)

export const name = 'local-system-stats'

/** RAM in GiB straight from /proc/meminfo (no shell). */
function readMeminfo(): { total_gib: number | null; available_gib: number | null } {
  try {
    const text = readFileSync('/proc/meminfo', 'utf8')
    const pick = (key: string): number | null => {
      const m = text.match(new RegExp(`^${key}:\\s+(\\d+)\\s+kB`, 'm'))
      return m ? Number(m[1]) / 1024 / 1024 : null
    }
    return { total_gib: pick('MemTotal'), available_gib: pick('MemAvailable') }
  } catch {
    return { total_gib: null, available_gib: null }
  }
}

/** Find the local LLM server (llama-server) and its RSS in GiB, pure /proc scan. */
function findLlamaServer(): { pid: number; rss_gib: number | null } | null {
  try {
    //const pids = readFileSync('/proc', 'utf8').split('\n').filter((d) => /^\d+$/.test(d))
    //for (const pid of pids) {
    const pids = readdirSync('/proc').filter((d) => /^\d+$/.test(d))
    for (const pid of pids) {
      let cmd = ''
      try {
        cmd = readFileSync(`/proc/${pid}/cmdline`, 'utf8')
      } catch {
        continue
      }
      if (cmd.includes('llama-server')) {
        const status = readFileSync(`/proc/${pid}/status`, 'utf8')
        const rss = status.match(/^VmRSS:\s+(\d+)\s+kB/m)
        return { pid: Number(pid), rss_gib: rss ? Number(rss[1]) / 1024 / 1024 : null }
      }
    }
  } catch {
    /* no /proc scan possible */
  }
  return null
}

/** Per-GPU VRAM + utilization via nvidia-smi (bounded, non-fatal). */
async function readGpu(): unknown[] {
  try {
    const { stdout } = await pExecFile(
      'nvidia-smi',
      ['--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu', '--format=csv,noheader,nounits'],
      { timeout: 5000 },
    )
    return stdout
      .trim()
      .split('\n')
      .filter(Boolean)
      .map((line) => {
        const [name, total, used, free, util] = line.split(', ').map((s) => s.trim())
        return {
          name,
          vram_total_mib: Number(total),
          vram_used_mib: Number(used),
          vram_free_mib: Number(free),
          util_pct: Number(util),
        }
      })
  } catch (error) {
    return [{ error: String(error).slice(0, 120) }]
  }
}
export const inject = ['tools']

export function apply(ctx: Context) {
  ctx.tools.register({
    name: 'system_stats_local',
    description:
      'Snapshot of this machine before heavy work: RAM total/available (GiB), per-GPU VRAM total/used/free (MiB) + utilization, and the local LLM server (llama-server) footprint. Call it before starting any heavy local task — model load, large download, or GPU work running in parallel with the agent — to decide what fits.',
    parameters: {},
    output: {
      schema: { type: 'object' },
      render(_args, value) {
        return [{ type: 'text', text: JSON.stringify(value) }]
      },
    },
    async execute() {
      const [gpus] = await Promise.all([readGpu()])
      return {
        ts: new Date().toISOString(),
        ram_gib: readMeminfo(),
        gpus,
        llm_server: findLlamaServer(),
      }
    },
  })
}
