#!/bin/sh
set -e
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"
python3 tests/test_v3_2_collision_suite.py
python3 scripts/run_v3_2_verification.py
