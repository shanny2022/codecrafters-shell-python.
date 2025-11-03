import sys
import os
import subprocess
import shlex

def main():
    builtins = {"echo", "exit", "type", "pwd", "cd"}

    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        try:
            command_line = input().strip()
        except EOFError:
            break

        if not command_line:
            continue

        try:
            lexer = shlex.shlex(command_line, posix=True)
            lexer.whitespace_split = True
            lexer.commenters = ""
            parts = list(lexer)
        except ValueError:
            print("Error: unmatched quotes")
            continue

        if not parts:
            continue

               # --- Handle output redirection (>, 1>, 2>) ---
        output_file = None
        error_file = None

        if ">" in parts:
            idx = parts.index(">")
            if idx + 1 < len(parts):
                output_file = parts[idx + 1]
                parts = parts[:idx]
        elif "1>" in parts:
            idx = parts.index("1>")
            if idx + 1 < len(parts):
                output_file = parts[idx + 1]
                parts = parts[:idx]
        if "2>" in parts:
            idx = parts.index("2>")
            if idx + 1 < len(parts):
                error_file = parts[idx + 1]
                parts = parts[:idx]

        # ✅ Ensure redirection files exist (even if command has no output)
        if output_file:
            open(output_file, "w").close()
        if error_file:
            open(error_file, "w").close()

        if not parts:
            continue
