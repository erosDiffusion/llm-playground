#!/usr/bin/env python3
"""MT bench for subtitle translation: same prompt shape as sublive.translate().

  .venv/bin/python mtbench.py --url http://127.0.0.1:8097 --to English
Reads LINES (real Prime cues) and prints "src || translation" + timing.
"""
import argparse, json, time, urllib.request

LINES = [
    'Ach du Schande.',
    'Bleib cool, Mann.',
    'Bin ausgebucht. Tut mir leid.',
    'Bei Typen wie Ihnensollte ich die Cops rufen.',
    'Bevor wir anfangen: Bist du versichert?',
    'Aber das Krankenhausist nur 20 Minuten entfernt.',
    'Als Barkeeper?',
    'Also kämpfen Sie gerne.',
    'Betreibst du den Buchladen ganz allein?',
    'Brauchen Sie \'nen Notarzt oder so?',
    'Aber es heißt "Road House". Verstanden?',
    'bitten kann, das Gelände zu verlassen.',
]

ap = argparse.ArgumentParser()
ap.add_argument("--url", required=True)
ap.add_argument("--model", default="bench")
ap.add_argument("--to", default="English")
ap.add_argument("--out", default=None)
a = ap.parse_args()

sysmsg = (f"Input is one German subtitle line from a TV show, with speaker context. "
          f"Output ONLY the {a.to} translation, natural spoken style, same length. "
          "Preserve register (formal vs informal).")
msgs = [{"role": "system", "content": sysmsg}]
tot = 0.0
rows = []
for ln in LINES:
    body = {"model": a.model, "temperature": 0, "max_tokens": 120,
            "messages": msgs + [{"role": "user", "content": ln}],
            "chat_template_kwargs": {"enable_thinking": False}}
    t0 = time.time()
    r = urllib.request.Request(a.url.rstrip("/") + "/chat/completions",
                              data=json.dumps(body).encode(),
                              headers={"Content-Type": "application/json"})
    out = json.load(urllib.request.urlopen(r, timeout=120))["choices"][0]["message"]["content"].strip()
    dt = time.time() - t0
    tot += dt
    rows.append({"src": ln, "tr": out, "s": round(dt, 3)})
    print(f"[{dt:.2f}s] {ln}  ||  {out}")
print(f"--- total {tot:.2f}s  avg {tot/len(LINES):.3f}s")
if a.out:
    json.dump(rows, open(a.out, "w"), ensure_ascii=False, indent=1)
