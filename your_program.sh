#!/usr/bin/env bash
# your_program.sh - simple interactive runner used by the test harness.
# Behavior required by the tests:
#  - Before each command, print the prompt string "$ " (and flush).
#  - Do NOT echo the command itself to stdout.
#  - Execute the command and leave only the command output on stdout.
set -euo pipefail
set +x

strip_prompt() {
  local s="$1"
  # Trim leading whitespace
  s="${s#"${s%%[![:space:]]*}"}"
  # Remove common leading prompt markers such as "$ " or "> "
  s="${s#\$ }"
  s="${s#> }"
  # Trim leading and trailing whitespace
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

# If arguments provided, treat them as a single command string and run it
if [ "$#" -gt 0 ]; then
  cmd="$(printf '%s ' "$@")"
  cmd="$(strip_prompt "$cmd")"
  if [ -n "$cmd" ]; then
    eval "$cmd"
  fi
  exit $?
fi

# Interactive mode: print prompt, read a line, execute it, repeat.
# Print the prompt to stdout (tests expect this). Do NOT echo the command.
while true; do
  # Print prompt and flush
  printf "$ "
  fflush() { : > /dev/null; }  # Dummy function to mimic fflush behavior
  fflush
  # read a line; if EOF, exit loop
  if ! IFS= read -r line; then
    break
  fi
  # Skip empty/whitespace-only lines
  if [ -z "${line//[[:space:]]/}" ]; then
    continue
  fi
  # Remove leading prompt tokens if present
  line="$(strip_prompt "$line")"
  if [ -z "$line" ]; then
    continue
  fi
  # Execute the input line (preserve shell features like pipelines)
  eval "$line"
done
