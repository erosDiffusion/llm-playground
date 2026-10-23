#!/bin/sh
# Strata IQ3_S — CURRENT params: 262144 ctx (trained range, no rope scaling).
# Config: strata-iq3_s.json (the original, untouched). Log: strata-iq3_s.log
# Only one Strata at a time — this one refuses to start if :8080 is taken.
if ss -ltn 2>/dev/null | grep -q ':8080 '; then
  echo "START-262k: port 8080 already in use — stop the running Strata first." >&2
  exit 1
fi
cd "/home/oem/Apps/Strata"
exec "/home/oem/Apps/Strata/.venv/bin/python" "/home/oem/Apps/Strata/serve/server.py" "--engine" "strata" "--config" "/home/oem/Apps/Strata/strata-iq3_s.json" "--port" "8080" "--open"
