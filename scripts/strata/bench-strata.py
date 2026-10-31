#!/usr/bin/env python3
"""Strata serve benchmark (deterministic before/after-upgrade probe).

Greedy chat completion against the live engine, timings read from the reply's
`timings` block (llama.cpp names: predicted_per_second, prompt_per_second),
the same fields Strata Control's native benchmark uses. A per-run nonce keeps
the KV prompt cache from flattering later runs. Runs N iterations, reports
medians. Output: JSON to --out and a short human summary on stdout.

Usage: python3 bench-strata.py [--label before] [--runs 3] [--tokens 256]
                               [--port 8080] [--out FILE]
Never touches engine/ or config; pure HTTP. Safe while the engine is live.
"""
import argparse, json, statistics, time, urllib.request, uuid, datetime

PROMPT = ("Explain, in clear simple language, how an expert-routed mixture-of-experts "
          "transformer keeps most weights in RAM and streams only the needed experts to "
          "the GPU, and why this makes a huge sparse model usable on a single desktop "
          "graphics card. {nonce}")

def post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)

def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="run")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--tokens", type=int, default=256)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    base = f"http://127.0.0.1:{a.port}"

    health = get(base + "/health")
    model = (get(base + "/v1/models").get("data") or [{}])[0].get("id")
    try:
        slots = get(base + "/slots")
    except Exception:
        slots = None
    build = {}
    try:
        build = json.load(open("/home/oem/Apps/Strata/engine/BUILD.json"))
    except Exception:
        pass

    decode, prefill, ttft, tokout = [], [], [], []
    for i in range(a.runs):
        body = post(base + "/v1/chat/completions", {
            "model": model,
            "messages": [{"role": "user",
                          "content": PROMPT.format(nonce=f"session-nonce-{uuid.uuid4().hex[:8]}")}],
            "temperature": 0, "max_tokens": a.tokens, "stream": False,
        })
        t = body.get("timings") or {}
        u = body.get("usage") or {}
        d, p = t.get("predicted_per_second"), t.get("prompt_per_second")
        if d is None or p is None:
            print(f"FATAL: run {i}: no timings block in reply: {json.dumps(t)[:200]}")
            return 1
        decode.append(d); prefill.append(p)
        tokout.append(u.get("completion_tokens"))
        ttft.append(round(t.get("prompt_ms", 0)))
        time.sleep(1)  # let the elastic cache settle between runs

    med = lambda xs: round(statistics.median(xs), 1)
    result = {
        "at": datetime.datetime.now().isoformat(timespec="seconds"),
        "label": a.label, "engine_build": build, "health_loaded": health.get("loaded"),
        "model": model, "runs": a.runs, "max_tokens": a.tokens,
        "decode_tok_s_median": med(decode), "decode_all": decode,
        "prefill_tok_s_median": med(prefill), "prefill_all": prefill,
        "prompt_ms_all": ttft, "completion_tokens": tokout, "slots": slots,
    }
    if a.out:
        with open(a.out, "w") as f:
            json.dump(result, f, indent=2)
    print(json.dumps({k: result[k] for k in
                      ("label", "engine_build", "decode_tok_s_median", "decode_all",
                       "prefill_tok_s_median", "prompt_ms_all")}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
