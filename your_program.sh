#!/bin/sh
#
# Use this script to run your program LOCALLY.
#
# Note: Changing this script WILL NOT affect how CodeCrafters runs your program.
#
# Learn more: https://codecrafters.io/program-interface

set -e # Exit early if any commands fail

log() { printf "%s\n" "$*" >&2; }

# Prefer pipenv only if available and a Pipfile exists, otherwise use python3/python.
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
