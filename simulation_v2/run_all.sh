#!/usr/bin/env bash
set -euo pipefail
SIM_V2_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SIM_V2_DIR"
export PYTHONIOENCODING=utf-8
export PYTHONPATH="$SIM_V2_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s tests -v
python3 scripts/run_all_v2.py
