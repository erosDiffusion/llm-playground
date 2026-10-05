/**
 * dsh-video-scene-extractor v2 — local host entry (replaces the bundle row).
 *
 * Same contract as the bundle's src/index.js (MIT, erosDiffusion/dsh @ 7dc012c1),
 * but SKILLS_DIR resolves to THIS folder's skills/ (the v2 skill: runbook fixes +
 * patched scripts, see ../CHANGELOG.md). Registered by the web-lite profile patch:
 *   - id: video-scene-extractor        disabled: true   (bundle row)
 *   - id: video-scene-extractor-v2     name: <abs path to this file>
 *
 * Registers on every session of the profile:
 *   1. DSH_VIDEO_SKILL_DIR (shell-env) -> <v2>/skills/video-scene-extractor
 *   2. /video-extractor slash command -> injects the pipeline turn pointing at the
 *      v2 SKILL.md runbook.
 */

import { randomUUID } from 'node:crypto'
import { existsSync, statSync } from 'node:fs'
import { homedir } from 'node:os'
import { basename, dirname, isAbsolute, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export const name = 'dsh-video-scene-extractor-v2'

const SKILLS_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'skills')
const SKILL_DIR = resolve(SKILLS_DIR, 'video-scene-extractor')
const RUNBOOK = resolve(SKILL_DIR, 'SKILL.md')

const VIDEO_EXT = /\.(webm|mp4|mov|mkv|avi|ogv|ogg|m4v|ts|mpg|mpeg|wmv|flv)$/iu
const USAGE = 'Usage: /video-extractor <absolute-video-path> [notes]  —  e.g. /video-extractor /home/oem/Downloads/clip.webm instrumental, no speech'

function buildPrompt(video, notes) {
  const label = basename(video)
  const steps = [
    `Run the video-scene-extractor pipeline on the video at ${video} (${label}).`,
    `Load the runbook at ${RUNBOOK} FIRST and execute every step in order (0 probe → 1 transcript → 2 candidates → 3 sheets → 4 verify → 5 consolidate → 6 re-extract → 7 spot-verify → 8 deliver). Follow its PATH CONTRACT, Deterministic Invocation, Environment quickstart, and Hard-won catalog sections exactly.`,
    `Deliver the canonical artifacts into the project root (~/Apps/generated/${label}/ by the skill's path contract): scenes.json, scenes.md (tabular cue sheet), ref2va_prompts.md (six-section MiniMax-H3 ref2va), frames/ (exact start frame per scene), and the data/ intermediates.`,
    'If a goal tool is available in this session, create a goal for this run so the pipeline persists across rounds.',
  ]
  if (notes !== '') steps.push(`User notes from the request: ${notes}`)
  return steps.join('\n\n')
}

export function apply(ctx) {
  ctx.inject(['shellEnv'], (runtimeCtx) => {
    runtimeCtx.shellEnv.register({
      name: 'video-scene-extractor-v2',
      variables: {
        DSH_VIDEO_SKILL_DIR: {
          description: 'Skill directory shipped by dsh-video-scene-extractor v2 (patched runbook + scripts).',
        },
      },
      resolve: () => ({ DSH_VIDEO_SKILL_DIR: SKILL_DIR }),
    })
  })

  ctx.inject(['commands'], (commandCtx) => {
    const registry = commandCtx.commands
    let taken = false
    try {
      const existing = typeof registry.get === 'function' ? registry.get('video-extractor')
        : (typeof registry.has === 'function' ? registry.has('video-extractor') : undefined)
      taken = existing !== undefined && existing !== false
    } catch { taken = false }
    if (taken) return
    registry.register({
      name: 'video-extractor',
      description: 'Run the video-scene-extractor (v2) skill pipeline on a video: start frame of every cut, dialogue cued per scene, per-shot descriptions, verified start frames (deliverables in the project root per the skill path contract).',
      input: { hint: '<absolute-video-path> [notes]' },
      handler: ({ agent, rawInput }) => {
        const input = rawInput.trim()
        if (input === '') {
          return { kind: 'error', text: USAGE }
        }
        const [first, ...rest] = input.split(/\s+/u)
        const notes = rest.join(' ').trim()
        let video = first.startsWith('@') ? first.slice(1) : first
        if (video === '~') video = homedir()
        else if (video.startsWith('~/')) video = resolve(homedir(), video.slice(2))
        if (!isAbsolute(video)) {
          return { kind: 'error', text: `The video path must be absolute (got "${first}"). ${USAGE}` }
        }
        if (!existsSync(video) || !statSync(video).isFile()) {
          return { kind: 'error', text: `No such file: ${video}. ${USAGE}` }
        }
        if (!VIDEO_EXT.test(video)) {
          return { kind: 'error', text: `"${basename(video)}" does not look like a video (expected .webm/.mp4/.mov/.mkv/...). ${USAGE}` }
        }
        if (!existsSync(RUNBOOK)) {
          return { kind: 'error', text: `Runbook not found at ${RUNBOOK} — the dsh-video-scene-extractor-v2 folder is incomplete.` }
        }
        agent.steer({
          id: randomUUID(),
          role: 'user',
          content: [{ type: 'text', text: buildPrompt(video, notes) }],
          source: { kind: 'user' },
        })
        return {
          kind: 'success',
          text: `Video scene extraction started (v2 runbook): ${basename(video)} — the agent will load the runbook and run the full pipeline (probe → transcript → candidates → visual verification → scenes.json + scenes.md + ref2va_prompts.md + verified frames).`,
        }
      },
    })
  })
}
