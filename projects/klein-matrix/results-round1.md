# Klein T2I + I2I effectiveness matrix — analysis report

Date: 2026-09-06 · Model: FLUX.2-klein-9B (Q4_K_M) via remote unsloth images API · 960×544, strength 0.7
Method: each pair = text-to-image generation, then image-to-image edit of its own output. All 20 images visually reviewed against their prompts (local vision).

## Verdicts

| # | Style / camera | Edit instruction | GEN | EDIT | Notes |
|---|---|---|---|---|---|
| 1 | photorealistic · close-up 85mm | lighting → golden hour backlight | ✅ | ✅ | Textbook: light changed (visible shafts), subject/pose/workshop preserved. Hair slightly less silver in edit. |
| 2 | product · macro white | background → pile of strawberries | ✅ | ✅ | Watch is the SAME watch; scale/lighting/perspective matched. BFL's own example pattern works. |
| 3 | Moebius+Ghibli illustration | → oil painting, thick brushstrokes | ✅ | ✅ | Style transfer clean; composition/subject fully preserved. |
| 4 | cyberpunk · low-angle rain | night → daytime, clear sky, dry pavement | ✅ | ⚠️ | Sky/layout/signs/drone all correct for day — but **pavement stayed wet** (puddles remain). Strong reference cue resisted the change. |
| 5 | watercolor · overhead flat-lay | add second steaming cup right | ✅ | ✅ | Cup added with steam, style-matched; original elements untouched. (Gen added unprompted corner flowers — harmless.) |
| 6 | documentary wildlife · tracking | savanna dawn → winter, light snow | ✅ | ✅ | Poses nearly pixel-identical; snow on grass AND fur. Strongest edit of the set. |
| 7 | retro 80s VHS · POV | reskin → modern gaming lounge, RGB | ✅ | ✅ | Cabinet kept in same position/framing (red ball-top intact); room fully re-skinned with LEDs/PCs/sofa. |
| 8 | architectural · symmetrical wide | add potted fern on table | ✅ | ✅ | Fern placed near atlas, correct scale/light; everything else identical. |
| 9 | macro nature · extreme close-up | dewdrop → crystal sphere w/ city skyline | ✅ | ✅ | Sphere now reflects a miniature skyline + water; leaf/background untouched. |
| 10 | fashion editorial · rim light | outfit → fuchsia dress, same drape | ✅ | ⚠️✅ | Color + silhouette applied; neckline drifted boat→V-wrap (minor). |

**Score: generations 10/10 good · edits 8/10 full success, 2 partial (pair 4 wet-pavement miss, pair 10 neckline drift).**

## Prompts used

### Pair 1 — photorealistic editorial, portrait close-up 85mm f/2.8
**GEN:** A weathered female ceramicist in her late sixties with silver-streaked hair pulled back, thick clay dust on her flour-dusted forearms, wearing a salt-faded indigo linen apron over a cream wool sweater, wiping her hands on the apron while she studies a freshly thrown bowl. Workshop of rough oak shelves stacked with unglazed stoneware. Soft diffused window light from camera-left, cool morning temperature, gentle shadows defining her features. Style: documentary editorial photography. Mood: quiet craft, patience.
**EDIT:** Change the lighting to warm golden hour backlighting streaming through the workshop windows, while keeping everything else unchanged.

### Pair 2 — product photography, macro 100mm white seamless
**GEN:** A minimalist titanium wristwatch with a brushed steel case and a matte black leather strap, resting on a slab of polished white Carrara marble with faint grey veining. Studio product lighting: large softbox key light camera-high-left, cool neutral temperature, crisp specular highlights on the bezel, soft contact shadow beneath. Style: luxury product photography. Mood: precise, modern, calm.
**EDIT:** Replace the marble background with a pile of fresh wet strawberries, matching scale, lighting and perspective, while keeping the watch unchanged.

### Pair 3 — Moebius line work + Ghibli watercolor washes, wide establishing
**GEN:** A marine biologist in a worn teal field jacket crouching at the open hatch of a sunken research submersible on a deep ocean floor, her headlamp beam catching drifting silt and a cluster of pale tube worms. Moebius line work with Ghibli watercolor washes, cool blue-green palette with warm amber lamp glow, soft volumetric light shafts from above. Style: painterly science-fiction illustration. Mood: wonder, isolation.
**EDIT:** Turn this into an oil painting with thick textured brushstrokes and a warmer palette, while keeping the composition unchanged.

### Pair 4 — cyberpunk photography, low-angle street level rain
**GEN:** A narrow neon-soaked alley in a dense megacity at night, wet asphalt mirroring magenta and cyan signage, steam rising from a street vent, a lone delivery drone hovering mid-frame. Harsh mixed artificial light, cool blue base with hot pink accents, rain streaks catching the glow. Style: cyberpunk cinematic photography. Mood: electric, lonely, restless.
**EDIT:** Change the scene to bright daytime with a clear blue sky and dry pavement, while keeping the alley layout and signage unchanged.

### Pair 5 — watercolor still life, overhead flat lay
**GEN:** A rustic wooden table seen from directly above: a flaky croissant with golden buttery layers catching soft light, a ceramic cup of black coffee in a speckled stoneware glaze, a small bowl of raspberries, linen napkin with visible weave. Soft diffused overhead daylight, warm neutral temperature, gentle watercolor blooms at the edges. Style: loose watercolor still life. Mood: slow morning, warmth.
**EDIT:** Add a second cup of coffee with visible rising steam on the right side of the table, matching the existing lighting and style.

### Pair 6 — documentary wildlife, medium tracking shot
**GEN:** A lioness with two tawny cubs moving through tall golden savanna grass at dawn, dust motes in the air, the cubs' fur showing individual guard hairs. Golden hour backlight with a warm break in low clouds, long soft shadows stretching toward camera. Style: National Geographic documentary photography. Mood: tender vigilance.
**EDIT:** Change the season to winter with light snow falling and dusted grass, while keeping the lions' poses and the composition unchanged.

### Pair 7 — retro 1980s VHS, POV handheld
**GEN:** A glowing arcade cabinet in a dim 1980s game room, its screen showing a vector starfield, plastic joystick with a red ball top, carpet in faded geometric pattern. Harsh fluorescent practical light mixed with the cabinet's blue glow, warm orange temperature on the walls, visible video noise and slight chromatic aberration. Style: retro VHS home video, 1984. Mood: nostalgic electricity.
**EDIT:** Reskin this into a photorealistic modern gaming lounge in 2025 with RGB LED strips, while keeping the cabinet's position and framing unchanged.

### Pair 8 — architectural interior, wide-angle symmetrical
**GEN:** A grand old library interior: floor-to-ceiling dark walnut bookshelves filled with leather-bound volumes, a long oak reading table with an open atlas and a brass magnifying glass stand, deep green wall panels. Golden hour light raking through tall leaded windows from camera-right, warm amber temperature, dust in the light beams. Style: architectural digest photography. Mood: scholarly calm.
**EDIT:** Add a small potted fern on the reading table near the atlas, matching scale, lighting and perspective.

### Pair 9 — macro nature, extreme close-up f/2.8
**GEN:** A single dewdrop on the edge of a broad green leaf at first light, the droplet perfectly spherical with a tiny inverted reflection of the fern frond inside it, fine vein texture of the leaf visible around the contact point. Soft diffused dawn light from behind, cool blue-green temperature with a warm rim highlight on the droplet edge. Style: macro nature photography. Mood: stillness before the world wakes.
**EDIT:** Replace the dewdrop with a tiny crystal sphere reflecting a miniature city skyline, while keeping the leaf and lighting unchanged.

### Pair 10 — fashion editorial, full body rim light
**GEN:** A model in her early twenties standing in an empty concrete studio, wearing a flowing indigo-dyed linen dress with visible slub texture and rolled hems, bare feet on polished concrete. Strong rim light from camera-beft-high separating her silhouette from the grey background, cool neutral key fill, soft floor reflection. Style: high-fashion editorial. Mood: confident minimalism.
**EDIT:** Change her outfit to a bold fuchsia pink dress with the same flowing linen drape, while keeping her pose and the lighting unchanged.

## Findings (new, for the KB)

1. **Layout preservation is excellent even under big environment swaps** — snow/season (6), era reskin (7), full background replace (2), style transfer (3): "while keeping … unchanged" phrasing held in every case.
2. **Failure mode found — strongly-baked reference cues resist change:** pair 4's wet pavement survived a "dry pavement" instruction because the reference image's puddles/reflections are dominant visual evidence. Lesson: for attribute flips that contradict strong reference content, phrase as an explicit REPLACEMENT ("Replace the wet asphalt and puddles with dry sunlit concrete") or reroll; plain adjectives lose to pixels.
3. **Minor drift is normal on outfit/shape changes** (pair 10 neckline) — expect it, judge silhouette+color first.
4. **Gen-side extras are harmless** (pair 5 corner flowers) — klein adds tasteful filler consistent with the style; not a defect.
5. Confirmed working: lighting-only edits, add-element edits, object replacement, era/style reskins, background swaps — all at strength 0.7, 960×544, ~20–30s per call on the 10GB box.
