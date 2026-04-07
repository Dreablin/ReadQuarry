#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is not installed or not on PATH." >&2
  exit 1
fi

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
if [ ! -d .venv ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt

echo "Starting ReadQuarry at http://127.0.0.1:8000/"
( sleep 1 && ( xdg-open "http://127.0.0.1:8000/" 2>/dev/null || open "http://127.0.0.1:8000/" 2>/dev/null || true ) ) &
exec python main.py
