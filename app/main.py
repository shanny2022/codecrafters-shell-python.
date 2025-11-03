import sys

def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()  # Ensure "$ " appears immediately
        try:
            command = input()
            if command:  # if not empty
                print(f"{command}: command not found")
        except EOFError:
            # Exit cleanly when user presses Ctrl+D
            break

if __name__ == "__main__":
    main()

