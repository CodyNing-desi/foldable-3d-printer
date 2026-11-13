#!/usr/bin/env bash
set -euo pipefail
SIMULATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SIMULATION_DIR"
export PYTHONIOENCODING=utf-8
export PYTHONPATH="$SIMULATION_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
uv run --isolated --no-project --python 3.13 \
  --with "numpy>=2.0" \
  --with "scipy>=1.14" \
  --with "sympy>=1.14" \
  --with "pandas>=2.2" \
  --with "matplotlib>=3.9" \
  --with "pymoo==0.6.1.6" \
  --with "shapely>=2.0" \
  --with "trimesh>=4.6" \
  --with "build123d==0.11.1" \
  --with "pillow>=11" \
  --with "imageio>=2.36" \
  --with "imageio-ffmpeg>=0.5" \
  --with "pyDOE3>=1.0" \
  --with "pint>=0.24" \
  --with "uncertainties>=3.2" \
  python "$@"
