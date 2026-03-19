#!/usr/bin/env bash
# ── Render Build Script ──────────────────────────────────────────────────────
# This script is NOT used when deploying via Docker (which is the recommended
# approach).  It is kept as a reference for native Python deployments where
# the host already provides the Chromium system dependencies.
set -o errexit

pip install -r requirements.txt
playwright install chromium
