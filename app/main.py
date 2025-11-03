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

        # --- Handle output redirection (>, 1>) ---
        output_file = None
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

        if not parts:
            continue

        cmd = parts[0]

        # Builtins
        if cmd == "exit":
            code = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            sys.exit(code)

        elif cmd == "echo":
            output_text = " ".join(parts[1:])
            if output_file:
                with open(output_file, "w") as f:
                    f.write(output_text + "\n")
            else:
                print(output_text)
            continue

        elif cmd == "pwd":
            result = os.getcwd()
            if output_file:
                with open(output_file, "w") as f:
                    f.write(result + "\n")
            else:
                print(result)
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
                print(f"cd: {path}: No such file or directory")
            continue

        elif cmd == "type":
            if len(parts) == 1:
                print("type: not found")
                continue
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
                with open(output_file, "w") as f:
                    f.write(text + "\n")
            else:
                print(text)
            continue

        # External programs
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
                if output_file:
                    with open(output_file, "w") as f:
                        subprocess.run([cmd] + parts[1:], executable=found_path, stdout=f)
                else:
                    subprocess.run([cmd] + parts[1:], executable=found_path)
            except Exception as e:
                print(f"{cmd}: execution failed ({e})")
        else:
            print(f"{cmd}: command not found")

if __name__ == "__main__":
    main()
