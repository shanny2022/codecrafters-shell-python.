#!/usr/bin/env bash
# your_program.sh - execute commands read from stdin or passed as arguments
# Do NOT print the command itself; only print the command output.
set -euo pipefail

# Disable debug printing if accidentally left enabled
set +x

# If arguments are provided, treat them as a single command string and run it.
if [ "$#" -gt 0 ]; then
  # Join all args into a single command string and execute it without echoing.
  cmd="$*"
  eval "$cmd"
  exit $?
fi

# Otherwise read lines from stdin and execute each non-empty line.
while IFS= read -r line || [ -n "$line" ]; do
  # Skip empty lines
  if [ -z "${line//[[:space:]]/}" ]; then
    continue
  fi
  # Execute the line without printing it
  eval "$line"
done
