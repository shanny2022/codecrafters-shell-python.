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
        except:
            pass
    stdout.close()


pipeline = [
    (fr'where /r {os.environ['USERPROFILE']} *.txt', IS_EXECUTABLE),
    (line_to_basename, IS_BUILT_IN),
    (r'findstr /i "test.*\.txt$"', IS_EXECUTABLE),
]

def pipeline_test(pipeline, pl_stdin=sys.stdin, pl_stdout=sys.stdout):
    processes = []
    threads = []

    # Create pipes
    read_fd = []
    write_fd = []
    for _i in range(len(pipeline)-1):
        r, w = os.pipe()
        read_fd.append(r)
        write_fd.append(w)
    # Add the ends. We dup to ensure we don't lose our Shell's hold
    read_fd = [os.dup(pl_stdin.fileno())] + read_fd
    write_fd = write_fd + [os.dup(pl_stdout.fileno())]

    # We wrap in thread in normal files to avoid double free later
    # in case thread forgot to close properly.
    thread_files = []
    for (cmd, kind), w_fd, r_fd in zip(pipeline, write_fd, read_fd):
        if kind == IS_EXECUTABLE:
            process = Popen(cmd, stdin=r_fd, stdout=w_fd)
            # Subprocess closes the handles now.
            # Close our hold on the handles
            os.close(r_fd)
            os.close(w_fd)
            processes.append(process)
        elif kind == IS_BUILT_IN:
            # We wrap in File to prevent double os.close later.
            r_file = os.fdopen(r_fd, 'r')
            w_file = os.fdopen(w_fd, 'w')
            thread_files.extend((r_file, w_file,))
            thread = threading.Thread(target=cmd, args=(r_file, w_file, "unused built-in arg"))
            threads.append(thread)
            thread.start()

    for p in processes:
        p.wait()
    for t in threads:
        t.join()
    # Ensure we closed our thread files
    for f in thread_files:
        f.close()


if __name__ == '__main__':
    pipeline_test(pipeline)
