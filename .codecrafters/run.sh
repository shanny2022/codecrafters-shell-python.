#!/bin/sh
#
# This script is used to run your program on CodeCrafters
#
# This runs after .codecrafters/compile.sh
#
# Learn more: https://codecrafters.io/program-interface

set -e

# Print diagnostics to stderr so tests that check stdout aren't affected
log() { printf "%s\n" "$*" >&2; }

# If there's a Pipfile and pipenv is available, use it. Otherwise fall back to system python.
if command -v pipenv >/dev/null 2>&1 && [ -f "Pipfile" ]; then
  log "Using pipenv to run the program"
  exec pipenv run python3 -u -m app.main "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  log "pipenv not found — falling back to python3"
  exec python3 -u -m app.main "$@"
fi

if command -v python >/dev/null 2>&1; then
  log "Falling back to python"
  exec python -u -m app.main "$@"
fi

log "No python runtime found (pipenv, python3, or python)."
exit 127
