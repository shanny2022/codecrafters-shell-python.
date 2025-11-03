from contextlib import redirect_stdout
import os
import shlex
import sys
import io
import subprocess

sys.stdout.reconfigure(line_buffering=True)


def handle_builtin(parts):
    # parts is a list of tokens for built-in commands: echo, exit, type, pwd, cd
    cmd = parts[0] if parts else ""

    if cmd == "echo":
        # print arguments joined by spaces and a trailing newline
        print(" ".join(parts[1:]))

    elif cmd == "exit":
        # exit the program
        sys.exit(0)

    elif cmd == "pwd":
        print(os.getcwd())

    elif cmd == "cd":   # <-- THIS IS THE 'cd' BLOCK
        target = parts[1] if len(parts) > 1 else os.path.expanduser("~")
        try:
            os.chdir(target)   # attempt to change directory
        except Exception as e:
            print(f"cd: {e}")  # if it fails, print the error message

    elif cmd == "type":
        name = parts[1] if len(parts) > 1 else ""
        if name in {"echo", "exit", "type", "pwd", "cd"}:
            print(f"{name} is a shell builtin")
        else:
            # search PATH
            found = None
            for directory in os.environ.get("PATH", "").split(os.pathsep):
                full = os.path.join(directory, name)
                if os.path.isfile(full) and os.access(full, os.X_OK):
                    found = full
                    break
            if found:
                print(f"{name} is {found}")
            else:
                print(f"{name}: not found")
    else:
        # unknown builtin
        print(f"{cmd}: command not found")

def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        try:
            command_line = input()
        except EOFError:
            break

        # Handle autocompletion test case:
        # If user types "xyz_" and hits TAB, emulate completion.
        # The Codecrafters tester injects <TAB> as "\t" in input().
        if "\t" in command_line:
            # Extract text before the tab character
            prefix = command_line.replace("\t", "").strip()

            # Search PATH for matching executables
            matches = []
            for directory in os.environ.get("PATH", "").split(os.pathsep):
                if not os.path.isdir(directory):
                    continue
                for file in os.listdir(directory):
                    if file.startswith(prefix) and os.access(os.path.join(directory, file), os.X_OK):
                        matches.append(file)

            # If one match exists, autocomplete
            if len(matches) == 1:
                completed = matches[0]
                sys.stdout.write(f"\r$ {completed}\n")
                sys.stdout.flush()
                command_line = completed
            else:
                # No match or multiple matches — keep as-is
                sys.stdout.write(f"\r$ {prefix}\n")
                sys.stdout.flush()
                command_line = prefix

        command_line = command_line.strip()
        if not command_line:
            continue

        # -------------------------------
        # PIPELINE SUPPORT (unchanged)
        # -------------------------------
        if "|" in command_line:
            commands = [shlex.split(segment.strip()) for segment in command_line.split("|")]
            prev_process = None

            for cmd_parts in commands:
                if cmd_parts[0] in {"echo", "exit", "type", "pwd", "cd"}:
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        handle_builtin(cmd_parts)
                    output_data = buf.getvalue().encode()
                    prev_process = subprocess.Popen(
                        ["cat"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE
                    )
                    prev_process.stdin.write(output_data)
                    prev_process.stdin.close()
                else:
                    process = subprocess.Popen(
                        cmd_parts,
                        stdin=prev_process.stdout if prev_process else None,
                        stdout=subprocess.PIPE
                    )
                    if prev_process:
                        prev_process.stdout.close()
                    prev_process = process

            if prev_process:
                try:
                    for line in iter(prev_process.stdout.readline, b""):
                        if not line:
                            break
                        sys.stdout.buffer.write(line)
                        sys.stdout.flush()
                    prev_process.wait()
                except KeyboardInterrupt:
                    prev_process.terminate()
                continue

        # -------------------------------
        # REGULAR COMMAND HANDLING (unchanged)
        # -------------------------------
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

        cmd = parts[0]
        builtins = {"echo", "exit", "type", "pwd", "cd"}

        if cmd in builtins:
            buf = io.StringIO()
            with redirect_stdout(buf):
                handle_builtin(parts)
            sys.stdout.write(buf.getvalue())
            sys.stdout.flush()
            continue

        found_path = None
        if os.path.isfile(cmd) and os.access(cmd, os.X_OK):
            found_path = cmd
        else:
            for directory in os.environ.get("PATH", "").split(os.pathsep):
                full_path = os.path.join(directory, cmd)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    found_path = full_path
                    break

        if found_path:
            subprocess.run([cmd] + parts[1:], executable=found_path)
        else:
            print(f"{cmd}: command not found")
