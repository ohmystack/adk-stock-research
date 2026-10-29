#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ]; then
  selected=""
  for candidate in "${WORKSHOP_PYTHON:-python3}" python3.13 python3.12 python3.11; do
    if "$candidate" -c 'import sys; assert sys.version_info >= (3,11)' 2>/dev/null; then
      selected="$candidate"
      break
    fi
  done
  if [ -z "$selected" ]; then
    echo 'Python >=3.11 required. Set WORKSHOP_PYTHON=/path/to/python3.12 and retry.' >&2
    exit 1
  fi
  "$selected" -m venv .venv
fi
.venv/bin/python -c 'import sys; assert sys.version_info >= (3,11), "Python >=3.11 required"'
.venv/bin/python -m ensurepip --upgrade
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m stock_research.cli doctor
