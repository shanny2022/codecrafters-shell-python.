import sys
import os
import subprocess
import shlex
import readline  # NEW: Enables autocompletion and line editing


def completer(text, state):
    """Autocomplete function for builtins."""
    builtins = ["echo", "exit"]
    matches = [b for b in builtins if b.startswith(text)]
    if state < len(matches):
        # readline automatically appends a space after a completion
        return matches[state] + " "
    return None


def main():
    # Register completer
    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")  # Enable TAB completion

    builtins = {"echo", "exit", "type", "pwd", "cd"}

    while True:
        try:
            command_line = input("$ ").strip()
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

        # --- Handle redirections (>, 1>, 2>, >>, 1>>, 2>>) ---
        output_file = None
        error_file = None
        append_stdout = False
        append_stderr = False

        if ">>" in parts:
            idx = parts.index(">>")
            if idx + 1 < len(parts):
                output_file = parts[idx + 1]
                append_stdout = True
                parts = parts[:idx]
        elif "1>>" in parts:
            idx = parts.index("1>>")
            if idx + 1 < len(parts):
                output_file = parts[idx + 1]
                append_stdout = True
                parts = parts[:idx]
        elif ">" in parts:
            idx = parts.index(">")
            if idx + 1 < len(parts):
                output_file = parts[idx + 1]
                parts = parts[:idx]
        elif "1>" in parts:
            idx = parts.index("1>")
            if idx + 1 < len(parts):
                output_file = parts[idx + 1]
                parts = parts[:idx]

        if "2>>" in parts:
            idx = parts.index("2>>")
            if idx + 1 < len(parts):
                error_file = parts[idx + 1]
                append_stderr = True
                parts = parts[:idx]
        elif "2>" in parts:
            idx = parts.index("2>")
            if idx + 1 < len(parts):
                error_file = parts[idx + 1]
                parts = parts[:idx]

        if output_file:
            mode = "a" if append_stdout else "w"
            open(output_file, mode).close()
        if error_file:
            mode = "a" if append_stderr else "w"
            open(error_file, mode).close()

        if not parts:
            continue

        cmd = parts[0]

        # --- Builtins ---
        if cmd == "exit":
            code = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            sys.exit(code)

        elif cmd == "echo":
            text = " ".join(parts[1:])
            if output_file:
                mode = "a" if append_stdout else "w"
                with open(output_file, mode) as f:
                    f.write(text + "\n")
            else:
                print(text)
            continue

        elif cmd == "pwd":
            text = os.getcwd()
            if output_file:
                mode = "a" if append_stdout else "w"
                with open(output_file, mode) as f:
                    f.write(text + "\n")
            else:
                print(text)
            continue

        elif cmd == "cd":
            if len(parts) < 2:
                continue
            path = parts[1]
            if path.startswith("~"):
                path = os.path.expanduser(path)
            try:
                os.chdir(path)
            except FileNotFoundError:
                err_msg = f"cd: {path}: No such file or directory"
                if error_file:
                    mode = "a" if append_stderr else "w"
                    with open(error_file, mode) as ef:
                        ef.write(err_msg + "\n")
                else:
                    print(err_msg)
            continue

        elif cmd == "type":
            if len(parts) == 1:
                text = "type: not found"
            else:
                target = parts[1]
                if target in builtins:
                    text = f"{target} is a shell builtin"
                else:
                    found = False
                    for directory in os.environ.get("PATH", "").split(os.pathsep):
                        full_path = os.path.join(directory, target)
                        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                            text = f"{target} is {full_path}"
                            found = True
                            break
                    if not found:
                        text = f"{target}: not found"
            if output_file:
                mode = "a" if append_stdout else "w"
                with open(output_file, mode) as f:
                    f.write(text + "\n")
            else:
                print(text)
            continue

        # --- External executables ---
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
            try:
                stdout_mode = "a" if append_stdout else "w"
                stderr_mode = "a" if append_stderr else "w"

                stdout_target = open(output_file, stdout_mode) if output_file else None
                stderr_target = open(error_file, stderr_mode) if error_file else None

                subprocess.run(
                    [cmd] + parts[1:],
                    executable=found_path,
                    stdout=stdout_target or None,
                    stderr=stderr_target or None,
                )

                if stdout_target:
                    stdout_target.close()
                if stderr_target:
                    stderr_target.close()

            except Exception as e:
                print(f"{cmd}: execution failed ({e})")

        else:
            err_msg = f"{cmd}: command not found"
            if error_file:
                mode = "a" if append_stderr else "w"
                with open(error_file, mode) as ef:
                    ef.write(err_msg + "\n")
            else:
                print(err_msg)


if __name__ == "__main__":
    main()
