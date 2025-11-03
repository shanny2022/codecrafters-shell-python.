import sys

def main():
    # Define builtins
    builtins = {"echo", "exit", "type"}

    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        try:
            command = input().strip()
        except EOFError:
            break  # Exit cleanly on Ctrl+D

        if not command:
            continue

        parts = command.split(maxsplit=1)
        cmd = parts[0]

        # Handle 'exit'
        if cmd == "exit":
            if len(parts) > 1 and parts[1].isdigit():
                sys.exit(int(parts[1]))
            else:
                sys.exit(0)

        # Handle 'echo'
        elif cmd == "echo":
            if len(parts) > 1:
                print(parts[1])
            else:
                print("")

        # Handle 'type'
        elif cmd == "type":
            if len(parts) == 1:
                print("type: not found")
            else:
                target = parts[1].strip()
                if target in builtins:
                    print(f"{target} is a shell builtin")
                else:
                    print(f"{target}: not found")

        # Handle invalid commands
        else:
            print(f"{command}: command not found")

if __name__ == "__main__":
    main()

