#!/usr/bin/env bash
# your_program.sh - execute commands read from stdin or passed as arguments
# Do NOT print the command itself; only print the command output.
set -euo pipefail

# Disable debug printing if accidentally left enabled
set +x

strip_prompt() {
  local s="$1"
  # Remove common leading prompt markers such as "$ " or "> "
  # Remove leading and trailing whitespace
  # First remove leading whitespace
  s="${s#"${s%%[![:space:]]*}"}"
  # Remove leading prompt markers
  s="${s#\$ }"
  s="${s#> }"
  # Remove any remaining leading whitespace
  s="${s#"${s%%[![:space:]]*}"}"
  # Trim trailing whitespace
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

# If arguments are provided, treat them as a single command string and run it.
if [ "$#" -gt 0 ]; then
  # Join all args into a single command string and execute it without echoing.
  cmd="$*"
  cmd="$(strip_prompt "$cmd")"
  # If the command is empty after stripping, exit
  if [ -z "$cmd" ]; then
    exit 0
  fi
  eval "$cmd"
  exit $?
fi

# Otherwise read lines from stdin and execute each non-empty line.
while IFS= read -r line || [ -n "$line" ]; do
  # Skip empty lines
  if [ -z "${line//[[:space:]]/}" ]; then
    continue
  fi
  # Remove prompt prefixes and trim whitespace
  line="$(strip_prompt "$line")"
  # Skip again if empty after stripping
  if [ -z "$line" ]; then
    continue
  fi
  # Execute the line without printing it
  eval "$line"
done
