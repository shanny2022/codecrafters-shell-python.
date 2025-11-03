'''
Build your own Shell project - Implementing in python

Features i have Worked on till now :
> builtins
> quoting
> I/O redirection

'''

import os
import sys
from typing import List, Tuple, Optional
import readline

class Shell:

    # Redirection mapping - 'operator' : (stdout/err, true/false)
    REDIRECT_OPS = {
        '>': (1, False),
        '1>': (1, False),
        '>>': (1, True),
        '1>>': (1, True),
        '2>': (2, False),
        '2>>': (2, True),
    }

    def __init__(self):

        self.builtins = {   # storing builtin functions
            'echo' : self.builtin_echo,
            'exit' : self.builtin_exit,
            'pwd' : self.builtin_pwd,
            'type' : self.builtin_type,
            'cd' : self.builtin_cd,
            'history' : self.builtin_history,
        }

        try:
            histfile = os.environ.get('HISTFILE')

            if histfile and os.path.isfile(histfile):
                with open(histfile, 'r') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                    self.history = lines
            else:
                self.history: List[str] = []

            self.initial_history_size = len(self.history)

        except Exception as e:
            print(f"history : error accessig the memory for history : {e}", file=sys.stderr)

        self.setup_autocomplete() # making a autocomplete function

    # --- Builtin Commands ---

    def builtin_echo(self, *args): # printing arg sep by spaces
        print(" ".join(args))

    def builtin_exit(self, *args): # exit shell - with given exit code

        # adding the memory history to the file specified
        histfile = os.environ.get("HISTFILE")

        if histfile and os.path.isfile(histfile):
            try:
                new_commands = self.history[self.initial_history_size:]

                with open(histfile, 'a') as f:
                    for line in new_commands:
                        f.write(line + '\n')

            except Exception as e:
                print(f"history: error with writing memory to history file : {e}")

        exit_code = int(args[0]) if args else 0
        sys.exit(exit_code)

    def builtin_pwd(self, *args): # printing working directory
        print(os.getcwd())

    def builtin_type(self, *args): # showing type of command
        if not args:
            return

        cmd = args[0]
        if cmd in self.builtins:
            print(f"{cmd} is a shell builtin")
        elif executable_path := self.find_in_path(cmd):
            print(f"{cmd} is {executable_path}")
        else:
            print(f"{cmd}: not found")

    def builtin_cd(self, *args): # changing directory
        path = args[0] if args else "~"
        expanded_path = os.path.expanduser(path)

        try:
            os.chdir(expanded_path)
        except FileNotFoundError:
            print(f"cd: {path}: No such file or directory", file=sys.stderr)
        except PermissionError:
            print(f"cd: {path}: Permission denied", file=sys.stderr)

    def builtin_history(self, *args):

        if not args:
            # printing full history when no arguments provided
            history_to_print = self.history
            start_number = 1

        elif args[0].isdigit(): # history <n>
            try:
                n = int(args[0])
                history_to_print = self.history[-n:]
                start_number = len(self.history) - len(history_to_print) + 1
            except (ValueError, IndexError):
                print("history: invalid argument", file=sys.stderr)
                return

        else:
            match args[0]:
                case "-r":
                    if len(args) < 2:
                        print("history: option requires an argument", file=sys.stderr)
                        return
                    file_path = args[1]

                    try:
                        with open(file_path, 'r') as f:
                            lines = [line.strip() for line in f.readlines() if line.strip()]
                            self.history.extend(lines)

                    except FileNotFoundError:
                        print(f"history: {file_path}: no such file or directory", file=sys.stderr)

                    except Exception as e:
                        print(f"history: error reading file: {e}", file=sys.stderr)
                    return

                case "-w":
                    if len(args) < 2:
                        print("history: option requires an argument", file=sys.stderr)
                        return
                    file_path = args[1]

                    try:
                        with open(file_path, 'w') as f:
                            for line in self.history:
                                f.write(line + '\n') # manually adding a newline at end of each character
                    except Exception as e:
                        print(f"history: error writing to file : {e}", file=sys.stderr)
                    return

                case "-a":
                    if len(args) < 2:
                        print("history: option requires an argument", file=sys.stderr)
                        return
                    file_path = args[1]
                    try:
                        with open(file_path, 'a') as f:
                            for line in self.history:
                                f.write(line + '\n') # manually adding a newline at end of each character

                        self.history = []
                    except Exception as e:
                        print(f"history: error writing to file : {e}", file=sys.stderr)
                    return

                case _: # any other invalid options
                    print(f"history: invalid option -- '{args[0]}'", file=sys.stderr)
                    return

        for i, cmd in enumerate(history_to_print, start_number):
            print(f"{i} {cmd}")


    # --- Command Execution ---

    def find_in_path(self, command: str) -> Optional[str]:    # searching for executable in path directories
        for directory in os.environ.get('PATH', '').split(":"):
            full_path = os.path.join(directory, command)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                return full_path
        return None

    def execute_command(self, command: str, args:List[str], redirect_info: Optional[Tuple[str, int, bool]] = None):
        # Executing command with optional redirections

        if redirect_info:
            file_path, fd_num, append_mode = redirect_info
            self._execute_with_redirect(command, args, file_path, fd_num, append_mode)
        else:
            # normal exe without redir
            if command in self.builtins:
                self.builtins[command](*args)
            elif self.find_in_path(command):
                self._execute_external(command, args)
            else:
                print(f"{command}: command not found", file=sys.stderr)

    def _execute_external(self, command: str, args: List[str]):
        pid = os.fork()

        if pid == 0:
            try:
                os.execvp(command, [command] + args)
            except OSError:
                print(f"{command}: command not found", file=sys.stderr)
                os._exit(127)
        else:
            os.waitpid(pid, 0)

    def _execute_with_redirect(self, command: str, args: List[str], file_path: str, fd_num: int, append: bool):
        # executing command with output redirection
        if command in self.builtins:
            self._redirect_builtin(command, args, file_path, fd_num, append)
        elif self.find_in_path(command):
            self._redirect_external(command, args, file_path, fd_num, append)
        else:
            print(f"{command}: command not found", file=sys.stderr)

    def _redirect_builtin(self, command: str, args: List[str], file_path: str, fd_num: int, append: bool):
        # Redirect Builtin command output
        original = sys.stdout if fd_num == 1 else sys.stderr # changing std reference

        try:
            with open(file_path, 'a' if append else 'w') as f:
                if fd_num == 1:
                    sys.stdout = f  # shifting pipe output
                else:
                    sys.stderr = f

                self.builtins[command](*args)
        finally:
            if fd_num == 1:
                sys.stdout = original # restoring default pipe str
            else:
                sys.stderr = original

    def _redirect_external(self, command: str, args: List[str], file_path: str, fd_num: int, append: bool) -> None:
        # Redirect external command output
        pid = os.fork()

        if pid == 0:    # child process
            try:
                flags = os.O_WRONLY | os.O_CREAT # flags needed in both the cases
                flags |= os.O_APPEND if append else os.O_TRUNC

                fd = os.open(file_path, flags, 0o644)
                os.dup2(fd, fd_num)
                os.close(fd)

                os.execvp(command, [command] + args) # executing external command
            except OSError:
                print(f"{command}: command not found", file=sys.stderr)
                os._exit(127)
        else:   # parent process
            os.waitpid(pid, 0)


    # --- parsing ---

    def parse_command_line(self, user_input: str) -> List[str]: # adressing quotes
        curr_word = []
        words = []
        in_squotes = False
        in_dquotes = False
        i = 0

        while i < len(user_input): # parsing each char, keeping record
            char = user_input[i]

            # handling the escape backslash
            if char == "\\" and i + 1 < len(user_input): # if backslash is last char
                next_char = user_input[i+1]

                if in_squotes: # in single quote, \ is literal \
                    curr_word.append(char)

                elif in_dquotes:
                    if next_char in ['"', '\\', '$', '`']: # handling edge cases
                        curr_word.append(next_char)
                        i += 1
                    else:
                        curr_word.append(char)

                else: # non single quotes case
                    curr_word.append(next_char)
                    i += 1

            # handling quote
            elif char == "'" and not (in_squotes or in_dquotes): # for single quote in double quote
                in_squotes = True
            elif char == "'" and in_squotes:
                in_squotes = False
            elif char == "\"" and not (in_dquotes or in_squotes): # for double q in single quote
                in_dquotes = True
            elif char == "\"" and in_dquotes:
                in_dquotes = False

            # handling spaces
            elif char == " " and not (in_squotes or in_dquotes):
                if curr_word:
                    words.append(''.join(curr_word))
                    curr_word = []
            else:
                curr_word.append(char)

            i += 1

        if curr_word:   # last curr word not added yet
            words.append(''.join(curr_word))

        return words

    def find_redirection(self, parts: List[str]) -> Tuple[ Optional[str], List[str], Optional[Tuple[str, int, bool]]]:
        '''
        find and parse redirection operators in command parts
        tuple (command(optional as null), argumnets list, tuple of path(optional), file descriptor, and the append yes no)
        finding and parsing any redirection operator
        '''
        for op in self.REDIRECT_OPS:
            if op in parts:
                index = parts.index(op)

                # edge cases - working on syntax - missing command or target path
                if index == 0:
                    print("syntax error: missing command", file=sys.stderr)
                    return None, [], None

                if index + 1 >= len(parts):
                    print("syntax error: missing target path", file=sys.stderr)
                    return None, [], None

                # Extracting the info
                command = parts[0]
                args = parts[1: index]
                file_path = parts[index + 1]
                fd_num, append = self.REDIRECT_OPS[op]

                return command, args, (file_path, fd_num, append)

        # No redirection case
        if parts:
            return parts[0], parts[1:], None
        return None, [], None # hanling all edge cases


    # -- Autocompletion --

    def setup_autocomplete(self):

        readline.set_completer(self.complete_command)    # setting completer function
        readline.parse_and_bind('tab: complete')    # binding
        readline.set_completer_delims(' \t\n;')     # delimiter

    def complete_command(self, text: str, state: int) -> Optional[str]:

        if state == 0: # enabling
            line = readline.get_line_buffer()

            if not line.strip() or line.strip() == text:
                all_commands = set(self.builtins.keys())

                for dir in os.environ.get('PATH', '').split(':'):
                # get ensures a safe output if the key not present, environ is a dictionary with 'PATH' as a key
                    if os.path.isdir(dir):

                        try:
                            for filename in os.listdir(dir):
                                full_path = os.path.join(dir, filename)

                                if os.access(full_path, os.X_OK): # checking execution perm
                                    all_commands.add(filename)

                        except (PermissionError, OSError):
                            continue

                self.matches = sorted([cmd for cmd in all_commands if cmd.startswith(text)])

                if not self.matches: # this is for no matches
                    print('\x07', end='', flush=True)

            else:
                self.matches = []

        if state < len(self.matches):
            if len(self.matches) == 1:
                return self.matches[state] + " " # adding a space for single match
            else:
                return self.matches[state]

        return None

    # ----- Pipeline -----
    # works for both buitin and path exectuble commands

    def execute_pipeline(self, parts: List[str]):
        # Handling execution of more than one pipeline
        try:
            # Workign on Commands first
            current_command = []
            commands = []

            for part in parts:
                if part == "|":
                    if not current_command: # edge case
                        print("Syntax error: Empty command in pipe", file=sys.stderr)
                        return

                    else:
                        commands.append(current_command)
                        current_command = []

                else:
                    current_command.append(part)

            if current_command: # adding the last command
                commands.append(current_command)

            if len(commands) < 2: # edge case
                print("Atleast two command required with a pipe operator.", file=sys.stderr)
                return

            # Working on the Pipeline now
            child_pids = []
            in_fd = sys.stdin.fileno() # first input is std input

            for i, command_parts in enumerate(commands):
                read_fd, write_fd = os.pipe() # new pipe for a process

                pid = os.fork()

                if pid == 0:

                    if in_fd != sys.stdin.fileno(): # this will be true only when i = 0, on the very first command
                        os.dup2(in_fd, sys.stdin.fileno()) # both in_fd and sys.stdin point to same file descriptor 0 now
                        os.close(in_fd) # so we can close the in_fd fd to prevent any deadlocks

                    if i < len(commands) - 1: # if not the last command, output goes to the pipe
                        os.dup2(write_fd, sys.stdout.fileno())

                    # closing unwanted fd's to avoid deadlocks
                    os.close(read_fd)
                    os.close(write_fd)

                    # now we can work on the specific command - and also take in consideration redirection if any
                    cmd, args, redirect_info = self.find_redirection(command_parts)
                    if cmd:
                        self.execute_command(cmd, args, redirect_info)

                    os._exit(1) # exiting if the command execution dails for any reason

                elif pid > 0:   # parent process

                    child_pids.append(pid) # storing all the child pids to check later

                    os.close(write_fd) # clsoing the write end, not needed

                    if in_fd != sys.stdin.fileno(): # closing the previous read end
                        os.close(in_fd)

                    in_fd = read_fd # current read end becomes the input for the next

            for pid in child_pids: # waiting for all the child process to finish
                os.waitpid(pid, 0)

        except Exception as e: # any other error
            print(f"Pipeline execution error: {e}", file=sys.stderr)

    # ----- Main Loop -----

    def run(self):  # Main loop - the repl

        while True:
            try:
                prompt = "$ "
                user_input = input(prompt).strip()

                if not user_input:  # empty input
                    continue

                self.history.append(user_input)

                parts = self.parse_command_line(user_input) # parsing command line
                if not parts:
                    continue

                if "|" in parts:
                    self.execute_pipeline(parts)
                else:
                    # configuring redirection if any
                    command, args, redirect_info = self.find_redirection(parts)
                    if command is None:
                        continue

                    self.execute_command(command, args, redirect_info)


            except EOFError: # ctrlD usage
                print()
                break
            except KeyboardInterrupt: # ctrlC usage
                print()
                continue

def main():
    shell = Shell()
    shell.run()

if __name__ == "__main__":
    main()
