import sys

def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        try:
            command = input().strip()
        except EOFError:
            break  # Exit if user sends Ctrl+D

        if not command:
            continue  # Ignore empty input

        # Handle 'exit' builtin
        if command.startswith("exit"):
            parts = command.split()
            if len(parts) > 1 and parts[1].isdigit():
                sys.exit(int(parts[1]))  # exit with given status
            else:
                sys.exit(0)  # default exit code 0

        # Otherwise, invalid command
        print(f"{command}: command not found")

if __name__ == "__main__":
    main()

