#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
exec python3 -B simulator/python/biobuzz_sim.py "$@"
