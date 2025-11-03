#!/bin/sh
#
# This script is used to run your program on CodeCrafters
#
# This runs after .codecrafters/compile.sh
#
# Learn more: https://codecrafters.io/program-interface

set -e

# Prefer pipenv only if available and a Pipfile exists, otherwise use python3/python.
# IMPORTANT: do not print any diagnostic text to stdout or stderr at startup,
# because some tests expect the very first program output to be the prompt "$ ".
if command -v pipenv >/dev/null 2>&1 && [ -f "Pipfile" ]; then
  exec pipenv run python3 -u -m app.main "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 -u -m app.main "$@"
fi

if command -v python >/dev/null 2>&1; then
  exec python -u -m app.main "$@"
fi

# If we get here, there is no python runtime. Print an error on stderr and exit.
printf "No python runtime found (pipenv, python3, or python).\n" >&2
exit 127
