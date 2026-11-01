#!/usr/bin/env node
/**
 * selftest.cjs — renders the footer control outside the browser.
 *
 * Why: the client half of a bundle has no build step and no test runner, and a plain
 * `node --check` passes on code that throws the moment React renders it. On 2026-11-01 a
 * scripted edit left `low` undeclared and dropped a `return`, the component threw on first
 * render, and the footer buttons simply disappeared in the GUI — no visible error. That is
 * the failure this file catches: it drives the real module, registers into a fake slot,
 * renders it, and asserts what a user would see at rest and on hover.
 *
 * Run:  NODE_PATH=<any tree with react+react-dom> node selftest.cjs
 * (the workspace's flights-of-events/node_modules works fine.)
 */
const path = require('path')

global.window = global
let mod = null
global.__ModuleLoader__ = { load: (m) => { mod = m } }
require(path.join(__dirname, 'client.js'))

const React = require('react')
const { renderToStaticMarkup } = require('react-dom/server')

function render (forceOpen = false) {
  let n = 0
  const real = React.useState
  if (forceOpen) React.useState = function (init) { n += 1; return n === 4 ? [true, () => {}] : real(init) }
  const captured = {}
  mod.factory((name) => require(name)).apply({
    slots: { inject: (_name, fn) => fn(), register: (_meta, Comp) => { captured.Comp = Comp } },
  })
  try {
    return renderToStaticMarkup(React.createElement(captured.Comp))
  } finally {
    if (forceOpen) React.useState = real
  }
}

const fails = []
let atRest
try {
  atRest = render(false)
} catch (err) {
  fails.push(`render at rest threw: ${err && err.message}`)
}

if (atRest) {
  for (const want of ['⬇ lower brain', '⬆ reclaim']) {
    if (!atRest.includes(want)) fails.push(`missing control at rest: ${want}`)
  }
  if (/type="range"/.test(atRest)) fails.push('slider visible at rest — it should only open on hover')
}

const opened = render(true)
const input = (opened.match(/<input[^>]*>/) || [''])[0]
if (!/type="range"/.test(opened)) fails.push('hover state has no range input')
for (const attr of ['min="1024"', 'max="17920"', 'step="512"']) {
  if (!input.includes(attr)) fails.push(`range input missing ${attr} (got: ${input.slice(0, 120)})`)
}
for (const want of ['full speed', 'half', 'yield everything', 'brain holds', 'model weights', 'engine state unknown', 'between engine requests']) {
  if (!opened.includes(want)) fails.push(`hover popover missing: ${want}`)
}

if (fails.length) {
  console.error('SELFTEST FAILED')
  for (const f of fails) console.error(' - ' + f)
  process.exit(1)
}
console.log('selftest OK — at rest: lower + reclaim + state pill; on hover: slider 1024..17920 MiB (brain-held cache) with presets')
