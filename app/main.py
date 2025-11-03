import sys
import os
import shlex
import subprocess
import io
from contextlib import redirect_stdout


# ------------------------------
# BUILTIN HANDLERS
# ------------------------------
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


# ------------------------------
# RUN COMMAND HELPER
# ------------------------------
def run_command(cmd_parts, input_data=None):
    """Runs a command (builtin or external), returns its stdout as bytes."""
    builtins = {"echo", "exit", "type", "pwd", "cd"}

    if cmd_parts[0] in builtins:
        buf = io.StringIO()
        with redirect_stdout(buf):
            handle_builtin(cmd_parts)
        return buf.getvalue().encode()
    else:
        result = subprocess.run(
            cmd_parts,
            input=input_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout


# ------------------------------
# MAIN SHELL LOOP
# ------------------------------
def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        try:
            command_line = input().strip()
        except EOFError:
            break

        if not command_line:
            continue

        # --- Handle pipelines (streaming) ---
        if "|" in command_line:
            commands = [shlex.split(segment.strip()) for segment in command_line.split("|")]
            prev_process = None

            for cmd_parts in commands:
                if cmd_parts[0] in {"echo", "exit", "type", "pwd", "cd"}:
                    # Handle builtins: run, capture output, and stream it via a pipe
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
                    # External command (stream via Popen)
                    process = subprocess.Popen(
                        cmd_parts,
                        stdin=prev_process.stdout if prev_process else None,
                        stdout=subprocess.PIPE
                    )
                    if prev_process:
                        prev_process.stdout.close()
                    prev_process = process

            # Output final process stdout in real-time
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

        # --- Parse command with shlex ---
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

        # --- Redirection flags ---
        stdout_file = None
        stderr_file = None
        append_stdout = False
        append_stderr = False

        # Append redirections
        if ">>" in parts:
            idx = parts.index(">>")
            stdout_file = parts[idx + 1] if idx + 1 < len(parts) else None
            append_stdout = True
            parts = parts[:idx]
        elif "1>>" in parts:
            idx = parts.index("1>>")
            stdout_file = parts[idx + 1] if idx + 1 < len(parts) else None
            append_stdout = True
            parts = parts[:idx]
        elif "2>>" in parts:
            idx = parts.index("2>>")
            stderr_file = parts[idx + 1] if idx + 1 < len(parts) else None
            append_stderr = True
            parts = parts[:idx]

        # Overwrite redirections
        elif ">" in parts:
            idx = parts.index(">")
            stdout_file = parts[idx + 1] if idx + 1 < len(parts) else None
            parts = parts[:idx]
        elif "1>" in parts:
            idx = parts.index("1>")
            stdout_file = parts[idx + 1] if idx + 1 < len(parts) else None
            parts = parts[:idx]
        elif "2>" in parts:
            idx = parts.index("2>")
            stderr_file = parts[idx + 1] if idx + 1 < len(parts) else None
            parts = parts[:idx]

        if not parts:
            continue

        cmd = parts[0]
        builtins = {"echo", "exit", "type", "pwd", "cd"}

        # --- Handle builtins ---
        if cmd in builtins:
            buf = io.StringIO()
            with redirect_stdout(buf):
                handle_builtin(parts)
            output = buf.getvalue()
            if stdout_file:
                mode = "a" if append_stdout else "w"
                with open(stdout_file, mode) as f:
                    f.write(output)
            else:
                sys.stdout.write(output)
                sys.stdout.flush()
            continue

        # --- External programs ---
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
            stdout_target = open(stdout_file, "a" if append_stdout else "w") if stdout_file else None
            stderr_target = open(stderr_file, "a" if append_stderr else "w") if stderr_file else None
            try:
                subprocess.run(
                    [cmd] + parts[1:],
                    executable=found_path,
                    stdout=stdout_target or sys.stdout,
                    stderr=stderr_target or sys.stderr,
                )
            finally:
                if stdout_target:
                    stdout_target.close()
                if stderr_target:
                    stderr_target.close()
        else:
            print(f"{cmd}: command not found")


if __name__ == "__main__":
    main()
