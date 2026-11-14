#!/bin/sh
set -eu
SIM_V3_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SIM_V3_DIR"
export PYTHONIOENCODING=utf-8
export PYTHONPATH="$SIM_V3_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s tests -v
python3 scripts/run_all_v3.py
