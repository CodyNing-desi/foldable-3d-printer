#!/bin/sh
set -eu
SIM_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SIM_DIR"
export PYTHONIOENCODING=utf-8
export PYTHONPATH="$SIM_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s tests -v
python3 scripts/run_v3_1_audit.py
