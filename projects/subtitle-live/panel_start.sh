#!/usr/bin/env bash
# Projects-panel start: brings up sublive (pidfile-managed) + the control
# server; exec subctl last so the panel's tracked pid == the control server.
cd "$(dirname "$0")"
./start.sh || true
exec .venv/bin/python subctl.py
