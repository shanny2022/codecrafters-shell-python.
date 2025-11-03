import subprocess
from subprocess import Popen
import os
from os.path import basename
import threading
import sys
import shutil
import platform

def run_command(command):
    """Run a shell command and return its output."""
    process = Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    return stdout.decode(), stderr.decode(), process.returncode
def list_executables_in_path():
    """List all executable files in the system PATH."""
    paths = os.getenv('PATH', '').split(os.pathsep)
    executables = set()
    for path in paths:
        if os.path.isdir(path):
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.access(item_path, os.X_OK) and not os.path.isdir(item_path):
                    executables.add(item)
    return sorted(executables)
def longest_common_prefix(strs):
    """Find the longest common prefix string amongst an array of strings."""
    if not strs:
        return ""
    shortest = min(strs, key=len)
    for i, char in enumerate(shortest):
        for other in strs:
            if other[i] != char:
                return shortest[:i]
    return shortest
class Completer:
    def __init__(self, commands):
        self.commands = commands

    def complete(self, text):
        matches = [cmd for cmd in self.commands if cmd.startswith(text)]
        if not matches:
            return text  # No matches, return original text
        if len(matches) == 1:
            return matches[0] + ' '  # Single match, return with space
        prefix = longest_common_prefix(matches)
        if prefix != text:
            return prefix  # Return the longest common prefix
        return text  # No further completion possible
def main():
    executables = list_executables_in_path()
    completer = Completer(executables)

    while True:
        try:
            user_input = input("$ ")
            completed_input = completer.complete(user_input)
            print(completed_input)
        except EOFError:
            break
        except KeyboardInterrupt:
            print("\nExiting shell.")
            break
if __name__ == "__main__":
    main()
