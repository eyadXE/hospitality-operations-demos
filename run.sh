#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
demo="${1:-help}"
run_demo() {
  cd "$1"
  [ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
  exec .venv/bin/uvicorn server:app --host 0.0.0.0 --port "${PORT:-8000}"
}
case "$demo" in
  invoice)    run_demo invoice_extraction_demo ;;
  onboarding) run_demo pilgrim_onboarding_demo ;;
  *) echo "Usage: ./run.sh {invoice|onboarding}  (requires Tesseract: sudo apt install tesseract-ocr)" ;;
esac
