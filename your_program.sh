#!/usr/bin/env bash
# your_program.sh - execute a single command or a pipeline passed as arguments
# Do not print the command itself; only print the command's stdout/stderr.

set -euo pipefail

# If you previously had `set -x` for debugging, remove it or disable it:
# set +x

# If you used an explicit echo of the command, remove that.
# Example of running the passed command(s):
if [ "$#" -eq 0 ]; then
  echo "No command provided" >&2
  exit 1
fi

# Execute the command exactly as given (preserve pipelines)
# Use "$@" so that quoted args are preserved.
# Note: If you expect a single string command you need eval, but avoid echoing it first.
if [ "$#" -eq 1 ]; then
  # single argument — could be a pipeline string; use eval but do NOT echo it
  eval "$1"
else
  # multiple args — run them directly
  "$@"
fi
