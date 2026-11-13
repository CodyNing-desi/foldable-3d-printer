#!/usr/bin/env bash
set -euo pipefail
SIMULATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SIMULATION_DIR"
bash uv_run.sh -m unittest discover -s tests -v
bash uv_run.sh scripts/verify_units_and_symbolic.py
bash uv_run.sh scripts/run_screening.py
bash uv_run.sh scripts/run_deepening.py --samples 10000
bash uv_run.sh scripts/run_optimization.py --pop-size 32 --generations 20
bash uv_run.sh scripts/run_sensitivity.py --samples 48
bash uv_run.sh scripts/select_recommendations.py
bash uv_run.sh scripts/generate_figures.py
bash uv_run.sh scripts/generate_cad.py
bash uv_run.sh scripts/record_environment.py
bash uv_run.sh scripts/generate_report.py
bash uv_run.sh scripts/validate_deliverables.py
