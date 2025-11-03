from subprocess import Popen
import os
from os.path import basename
import threading
import sys
import shutil
import platform

IS_EXECUTABLE = 1
IS_BUILT_IN = 0

# "built-in"
def line_to_basename(stdin, stdout, _unused_args):
    for line in stdin:
        line = line.strip()
        try:
            print(basename(line), file=stdout)
        except Exception:
            pass
    try:
        stdout.close()
    except Exception:
        pass


def is_windows():
    return platform.system().lower().startswith("win")


# Build pipeline commands in a platform-aware way
if is_windows():
    # Windows: use where and findstr
    userprofile = os.environ.get('USERPROFILE', '.')
    cmd_where = fr'where /r "{userprofile}" *.txt'
    cmd_filter = r'findstr /i "test.*\.txt$"'
else:
    # POSIX: use find and grep
    # Search from HOME if available, else current directory
    homedir = os.environ.get('HOME', '.')
    # find prints full paths; use -type f and -name pattern
    # The pattern '*.txt' is quoted to be interpreted by find, not the shell.
    cmd_where = fr'find "{homedir}" -type f -name "*.txt"'
    # grep -i -E to use the regex with case-insensitive matching
    cmd_filter = r'grep -i -E "test.*\.txt$" || true'  # || true prevents non-zero exit when grep finds nothing

pipeline = [
    (cmd_where, IS_EXECUTABLE),
    (line_to_basename, IS_BUILT_IN),
    (cmd_filter, IS_EXECUTABLE),
]


def pipeline_test(pipeline, pl_stdin=sys.stdin, pl_stdout=sys.stdout):
    processes = []
    threads = []

    # Create pipes (one per connection between pipeline stages)
    read_fd = []
    write_fd = []
    for _i in range(len(pipeline) - 1):
        r, w = os.pipe()
        read_fd.append(r)
        write_fd.append(w)

    # Add the ends. We dup to ensure we don't lose our Shell's hold
    read_fd = [os.dup(pl_stdin.fileno())] + read_fd
    write_fd = write_fd + [os.dup(pl_stdout.fileno())]

    # We wrap built-ins in thread-safe file objects so we can call .close on them later.
    thread_files = []
    for (cmd, kind), w_fd, r_fd in zip(pipeline, write_fd, read_fd):
        if kind == IS_EXECUTABLE:
            # Use shell=True because commands are provided as shell strings (use with care).
            # Ensure the command exists on PATH where relevant; on POSIX we used find/grep so they should exist.
            process = Popen(cmd, stdin=r_fd, stdout=w_fd, shell=True)
            # Subprocess inherited the fd, so close our copies
            try:
                os.close(r_fd)
            except OSError:
                pass
            try:
                os.close(w_fd)
            except OSError:
                pass
            processes.append(process)
        elif kind == IS_BUILT_IN:
            # Wrap fds in file objects for the Python built-in implementation
            r_file = os.fdopen(r_fd, 'r')
            w_file = os.fdopen(w_fd, 'w')
            thread_files.extend((r_file, w_file))
            thread = threading.Thread(target=cmd, args=(r_file, w_file, "unused built-in arg"))
            threads.append(thread)
            thread.start()

    for p in processes:
        p.wait()
    for t in threads:
        t.join()

    # Ensure we closed our thread files
    for f in thread_files:
        try:
            f.close()
        except Exception:
            pass


if __name__ == '__main__':
    pipeline_test(pipeline)
