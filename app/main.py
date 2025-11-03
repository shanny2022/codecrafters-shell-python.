import sys

def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        try:
            command = input().strip()
        except EOFError:
            break  # End program on Ctrl+D

        if not command:
            continue

        # Handle exit
        if command.startswith("exit"):
            parts = command.split()
            if len(parts) > 1 and parts[1].isdigit():
                sys.exit(int(parts[1]))
            else:
                sys.exit(0)

        # Handle echo
        elif command.startswith("echo"):
            parts = command.split(maxsplit=1)
            if len(parts) > 1:
                print(parts[1])
            else:
                print("")  # echo with no args prints a blank line

        # Handle everything else
        else:
            print(f"{command}: command not found")

if __name__ == "__main__":
    main()

