#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
[[ -x build/savagewind && -x tools/venv/bin/python ]] || { echo 'Run tools/arch/setup.sh first.' >&2; exit 1; }
# Source-mode resources are resolved relative to the starting directory even
# when the runtime switches to its per-user data directory.
export SAVAGEWIND_CC="$(command -v clang)"
exec ./build/savagewind "$@"
