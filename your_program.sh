#!/usr/bin/env bash
# your_program.sh - simple interactive runner used by the test harness.
# Behavior required by the tests:
#  - Before each command, print the prompt string "$ " (and flush).
#  - Do NOT echo the command itself to stdout.
#  - Execute the command and leave only the command output on stdout.
while true; do
  # Print the prompt
  echo -n "$ "
  # Read a command from stdin
  if ! read -r cmd; then
    break
  fi
  # Execute the command and capture its output
  eval "$cmd"
done


