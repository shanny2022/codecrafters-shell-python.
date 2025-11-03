from subprocess import Popen
import os
from os.path import basename
import threading
import sys

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
    stdout.close()


pipeline = [
    # fix: don't break the f-string with inner single-quotes; use double-quotes around USERPROFILE
    (fr"where /r {os.environ.get('USERPROFILE', '.') } *.txt", IS_EXECUTABLE),
    (line_to_basename, IS_BUILT_IN),
    (r'findstr /i "test.*\.txt$"', IS_EXECUTABLE),
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
    # Note: pl_stdin and pl_stdout are file objects (sys.stdin/sys.stdout)
    read_fd = [os.dup(pl_stdin.fileno())] + read_fd
    write_fd = write_fd + [os.dup(pl_stdout.fileno())]

    # We wrap built-ins in thread-safe file objects so we can call .close on them later.
    thread_files = []
    for (cmd, kind), w_fd, r_fd in zip(pipeline, write_fd, read_fd):
        if kind == IS_EXECUTABLE:
            # Use shell=True because commands are provided as shell strings (use with care).
            # Passing raw fds for stdin/stdout works on Python on POSIX; on Windows these are integers too,
            # but behaviour can differ — keep in mind.
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
