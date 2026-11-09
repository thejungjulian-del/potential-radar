#!/usr/bin/env bash
# Start Potential Radar locally. Creates a venv on first run, installs Flask,
# loads .env if present, then serves the dashboard on http://127.0.0.1:8799
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

pip install -q -r requirements.txt

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

python app.py
