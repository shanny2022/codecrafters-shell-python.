import sys
import os
import subprocess
import shlex  # for proper shell-style parsing


def main():
    # Define shell builtins
    builtins = {"echo", "exit", "type", "pwd", "cd"}

    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        try:
            command_line = input().strip()
        except EOFError:
            break  # End on Ctrl+D

        if not command_line:
            continue

        # Use shlex to handle quotes properly
        try:
            parts = shlex.split(command_line)
        except ValueError:
            # Handles unmatched quotes gracefully
            print("Error: unmatched quotes")
            continue

        if not parts:
            continue

        cmd = parts[0]

        # Handle 'exit'
        if cmd == "exit":
            if len(parts) > 1 and parts[1].isdigit():
                sys.exit(int(parts[1]))
            else:
                sys.exit(0)

        # Handle 'echo'
        elif cmd == "echo":
            print(" ".join(parts[1:]))
            continue

        # Handle 'pwd'
        elif cmd == "pwd":
            print(os.getcwd())
            continue

        # Handle 'cd'
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

        # Handle 'type'
        elif cmd == "type":
            if len(parts) == 1:
                print("type: not found")
                continue

            target = parts[1]
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
            continue

        # Handle external programs
        else:
            found_path = None
            for directory in os.environ.get("PATH", "").split(os.pathsep):
                full_path = os.path.join(directory, cmd)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    found_path = full_path
                    break

            if found_path:
                try:
                    # Use original cmd for argv[0], keep quoting behavior
                    subprocess.run([cmd] + parts[1:], executable=found_path)
                except Exception as e:
                    print(f"{cmd}: execution failed ({e})")
            else:
                print(f"{cmd}: command not found")


if __name__ == "__main__":
    main()

