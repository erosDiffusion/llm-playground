# scripts/ninfer/ — NInfer local fixes kit (survives NInfer updates)

Local fixes for the NInfer checkout at `/home/oem/Apps/ninfer` that are **not
upstreamed** and must be re-applied after any `git pull` / tag checkout /
re-clone, or they silently disappear. Durable copy lives here; the live
locations on the agent box are listed per file below.

## `ninfer-decode-probe-hint.patch` — media decode probe anchoring (2026-10-03)

### The bug

Symptom (exactly): HTTP 400 `{"message":"media has no decodable video
stream"}` from `POST /v1/messages` or `/v1/chat/completions` on requests
containing images; the server log shows `[mpegts] changing packet size to
188/192/204` lines right before the rejection.

Root cause: `src/media/decode/decode.cpp` opened media with
`avformat_open_input(&raw, nullptr, nullptr, nullptr)` — no filename. With
no filename, FFmpeg's demuxer probe can only use raw bytes, and the byte
pattern of **sharp/libvips-encoded JPEGs** (what the DSH harness's pi-ai
adapter produces when it re-encodes history images into the ≤1 MiB
request-image budget) scores well enough against the **mpegts demuxer
probe** that mpegts wins. The mpegts demuxer exposes no stream, so
`av_find_best_stream(...)` fails → "media has no decodable video stream".
The identical bytes decode perfectly when given a filename with a matching
extension (`ffmpeg -i x.jpg` OK, `ffmpeg -i x` picks mpegts, no stream).

Why it was intermittent: the probe tie is byte-pattern-dependent. Raw
stored bytes (PNGs, PIL/libjpeg JPEGs, mozjpeg, 4:4:4 encodings) probe
cleanly; only specific sharp 4:2:0 baseline q85 outputs mis-probe.

### The fix

`Decoder` now passes a synthetic filename derived from the container magic
to `avformat_open_input`: `media.jpg` (FFD8FF), `media.png` (89504E47…),
`media.webp` (RIFF…WEBP), `media.gif` (GIF8); unknown magic → `nullptr`
(behavior unchanged). This restores FFmpeg's extension-based demuxer
preference without changing any other probing path.

Files touched: `src/media/decode/decode.cpp` (helper `probe_filename_hint`
+ the `avformat_open_input` call), `tests/test_media_decode.cpp`
(regression test), `tests/cmake/ProductTests.cmake` (`NEEDS_SOURCE_DIR` for
the test).

### Files

| file | what it is | live location on the agent box |
| --- | --- | --- |
| `ninfer-decode-probe-hint.patch` | the source fix (3 files; text patch, reverse-checks clean on base `d44ab584`) | `~/.dsh/ninfer/patches/ninfer-decode-probe-hint.patch` |
| `fixtures/sharp_jpeg_mpegts_misprobe.jpg` | 142,524 B regression fixture (914×734 sharp q85 JPEG that mis-probes as mpegts without the hint; the test fails with the exact 400 error on unpatched code) | `tests/fixtures/media/sharp_jpeg_mpegts_misprobe.jpg` in the NInfer checkout (applier installs it) |
| `apply-ninfer-patches.sh` | the applier: reverse-check (already applied → skip) → `git apply` → `git apply --3way` fallback on drifted context → **CONFLICT exits 1 without rebuilding**; installs the fixture if missing; rebuild tail = `ninja ninfer_media_decode_test apps/ninfer-serve` + run the test binary (only when `build/` exists). `--install` syncs patches+fixtures+script into `~/.dsh/` | `~/.dsh/bin/apply-ninfer-patches.sh` |

### Update protocol (after ANY NInfer update)

1. `cd /home/oem/Apps/ninfer && git pull --ff-only` (or tag checkout / re-clone).
2. `bash ~/.dsh/bin/apply-ninfer-patches.sh` — idempotent; expect clean skip
   on the current base, 3-way auto-merge on small drift, or CONFLICT
   (exit 1, nothing rebuilt) on big drift. On CONFLICT: resolve by hand
   (keep upstream structure, splice `probe_filename_hint` + the
   `avformat_open_input` change + the test back in), then re-run the
   script's rebuild tail manually.
3. Rebuild + verify (the applier does this when `build/` exists):
   - `ctest -R media_decode` in `build/` → `ok`
   - live wire check (server running): the sharp JPEG must return 200:
     the previously-failing repro is any sharp/libvips q85 4:2:0 JPEG of
     photo content; fixture + `decode_image` unit test cover it offline.
4. Restart the server via the user's `./start.sh` (server is user-managed;
   get the user's OK before restarting — 2026-10-03 protocol).
5. **Refresh this vault copy** if a patch was re-merged by hand: regenerate
   from the worktree diff (`git diff -- <paths> > ~/.dsh/ninfer/patches/<p>`;
   verify with `git apply -R --check`) and update the copies here through
   the llm-playground gh-git per-session worktree flow (see repo AGENTS.md),
   recording the new upstream base commit below.

### Start snapshot (untracked user files in the NInfer repo)

`start.sh`, `install_ninfer.sh`, and `README_INSTALL.md` are **untracked**
in the NInfer repo (they survive `git pull` but not a re-clone). `start.sh`
as of 2026-10-03: kills any local ComfyUI whose cwd is
`/home/oem/Progetti/ComfyUI` (VRAM), then runs

```
./build/apps/ninfer-serve models/qwen3_8_27b_nvfp4.ninfer \
  --max-context 240000 --kv-capacity 240000 --max-concurrency 2 \
  --kv-dtype fp8 --device-state-slots 2 --host-state-slots 8 \
  --host-kv-mib 8192 --spec mtp --draft-tokens 2 --lm-head-draft \
  --preserve-thinking --vision
```

Note: the model path is a **required positional** — omitting it makes the
binary print usage and exit (learned the hard way 2026-10-03).

### Provenance

- Created 2026-10-03 against upstream base **`d44ab584`**
  (`perf(attention): extend grouped small prefill`, origin/master at that
  date) in DSH session `1cf7b2c2` (web-lite profile, port 3080).
- Found while debugging the "media has no decodable video stream" 400s that
  blocked resuming a captured-video scene-extraction session; every DSH
  session routes through NInfer, so the bug hit every image-bearing
  request on the sharp-reencoded path.
- No secrets in any file. The fixture is a crop of generated test content
  (video cut-sheet), not a secret.
