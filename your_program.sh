#!/bin/sh
#
# Use this script to run your program LOCALLY.
#
# Note: Changing this script WILL NOT affect how CodeCrafters runs your program.
#
# Learn more: https://codecrafters.io/program-interface

set -e # Exit early if any commands fail

# Local runner should also be silent so tests that invoke ./your_program.sh see the exact prompt.
if command -v pipenv >/dev/null 2>&1 && [ -f "Pipfile" ]; then
  exec pipenv run python3 -u -m app.main "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 -u -m app.main "$@"
fi

if command -v python >/dev/null 2>&1; then
  exec python -u -m app.main "$@"
fi

printf "No python runtime found (pipenv, python3, or python).\n" >&2
exit 127
