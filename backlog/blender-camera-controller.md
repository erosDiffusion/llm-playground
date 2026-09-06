# blender-camera-controller — garuh143

- **Link:** https://github.com/garuh143/blender-camera-controller
- **What it is:** Drive Blender's camera from a phone or gamepad over the LAN — gyro head, touch sticks, two-way video monitor. No app to install (browser-based). Python addon.
- **Why I want to try it:** Directly implements the "camera control possibly done by me (via phone or gamepad)" part of the north star — and covers *both* input options at once with zero new hardware (the phone is already there). The two-way video monitor gives live feedback while framing a shot before committing to an H3 render.
- **Fits stage:** User-driven camera control. First candidate to try: lowest setup cost (no gesture tracking, no gamepad required), LAN-based like our other tooling.
- **Open questions:** Blender 5.1.2 addon compatibility; does it drive the *active scene camera* (what `blender-director` scenes use) or only viewport navigation; gyro-head latency; how it behaves headless (Blender running without a display, as on this box).
- **Status log:**
  - 2026-09-06 — added to backlog (want-to-try) from user link.
