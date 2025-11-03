import subprocess
import io
import os
import sys
from contextlib import redirect_stdout, redirect_stderr


def handle_builtin(parts):
    """Handles shell builtin commands (echo, cd, pwd, type, exit)."""
    cmd = parts[0]

    if cmd == "echo":
        print(" ".join(parts[1:]))

    elif cmd == "pwd":
        print(os.getcwd())

    elif cmd == "cd":
        path = parts[1] if len(parts) > 1 else os.path.expanduser("~")
        try:
            os.chdir(os.path.expanduser(path))
        except FileNotFoundError:
            print(f"cd: {path}: No such file or directory")

    elif cmd == "type":
        target = parts[1] if len(parts) > 1 else ""
        builtins = {"echo", "exit", "type", "pwd", "cd"}
        if target in builtins:
            print(f"{target} is a shell builtin")
        else:
            found = False
            for directory in os.environ.get("PATH", "").split(os.pathsep):
                full_path = os.path.join(directory, target)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    print(f"{target} is {full_path}")
                    found = True
                    break
            if not found:
                print(f"{target}: not found")

    elif cmd == "exit":
        sys.exit(0)


def run_command(cmd_parts, input_data=None):
    """Runs a command (builtin or external), feeding input_data to stdin if provided.
    Returns the command's stdout output as bytes."""
    builtins = {"echo", "exit", "type", "pwd", "cd"}

    if cmd_parts[0] in builtins:
        buf = io.StringIO()
        with redirect_stdout(buf):
            handle_builtin(cmd_parts)
        return buf.getvalue().encode()  # Return stdout as bytes
    else:
        result = subprocess.run(
            cmd_parts,
            input=input_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout
