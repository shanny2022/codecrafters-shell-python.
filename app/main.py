# File: app/main.py
# Minimal shell with pipelines + in-process built-ins and required prompt "$ ".

from __future__ import annotations

import os
import shlex
import sys
import threading
from subprocess import Popen

BUILTINS = {"type", "exit"}


def print_prompt() -> None:
    # Required by tester: "$ " with no newline
    sys.stdout.write("$ ")
    sys.stdout.flush()


def is_builtin(name: str) -> bool:
    return name in BUILTINS


def builtin_type(argv: list[str]) -> int:
    if len(argv) < 2:
        return 0
    name = argv[1]
    if is_builtin(name):
        print(f"{name} is a shell builtin", flush=True)
        return 0

    path = os.environ.get("PATH", "/bin:/usr/bin")
    for part in path.split(":"):
        candidate = os.path.join(part if part else ".", name)
        if os.access(candidate, os.X_OK) and os.path.isfile(candidate):
            print(f"{name} is {candidate}", flush=True)
            return 0

    print(f"{name} not found", flush=True)
    return 1


def run_builtin(argv: list[str]) -> int:
    if not argv:
        return 0
    cmd = argv[0]
    if cmd == "type":
        return builtin_type(argv)
    if cmd == "exit":
        # No-op in pipelines; standalone handled in REPL.
        return 0
    return 0


def _drain(reader) -> None:
    # Prevent upstream blocking when builtin doesn't read stdin.
    try:
        for _ in iter(lambda: reader.read(8192), ""):
            pass
    except Exception:
        pass


def execute_pipeline(line: str) -> None:
    stages_raw = line.split("|")
    stages = [shlex.split(s) for s in stages_raw]

    # Standalone 'exit'
    if len(stages) == 1 and stages[0] and stages[0][0] == "exit":
        sys.exit(0)

    n = len(stages)
    prev_read_fd = -1
    procs: list[Popen] = []

    for i, argv in enumerate(stages):
        last = (i == n - 1)

        if not last:
            r_fd, w_fd = os.pipe()
        else:
            r_fd, w_fd = -1, -1

        in_fd = prev_read_fd if prev_read_fd != -1 else sys.stdin.fileno()
        out_fd = w_fd if not last else sys.stdout.fileno()

        if argv and is_builtin(argv[0]):
            saved_in = os.dup(sys.stdin.fileno())
            saved_out = os.dup(sys.stdout.fileno())
            drain_thread = None
            drain_file = None

            try:
                if in_fd != sys.stdin.fileno():
                    os.dup2(in_fd, sys.stdin.fileno())
                if out_fd != sys.stdout.fileno():
                    os.dup2(out_fd, sys.stdout.fileno())

                # Builtins here don't consume stdin → drain to avoid blocking upstream (e.g., ls | type exit)
                if in_fd != -1 and argv[0] in {"type", "exit"}:
                    drain_file = os.fdopen(os.dup(sys.stdin.fileno()), "r", buffering=1, encoding="utf-8", errors="ignore")
                    drain_thread = threading.Thread(target=_drain, args=(drain_file,), daemon=True)
                    drain_thread.start()

                run_builtin(argv)

            finally:
                if drain_file is not None:
                    try:
                        drain_file.close()
                    except Exception:
                        pass
                if drain_thread is not None:
                    drain_thread.join(timeout=0.2)

                os.dup2(saved_in, sys.stdin.fileno())
                os.dup2(saved_out, sys.stdout.fileno())
                os.close(saved_in)
                os.close(saved_out)

                if not last:
                    os.close(w_fd)
                if prev_read_fd != -1 and prev_read_fd != sys.stdin.fileno():
                    os.close(prev_read_fd)

            prev_read_fd = r_fd if not last else -1

        else:
            # External command
            if not argv:
                # Empty stage: just wire through
                if not last:
                    os.close(w_fd)
                if prev_read_fd != -1 and prev_read_fd != sys.stdin.fileno():
                    os.close(prev_read_fd)
                prev_read_fd = r_fd if not last else -1
                continue

            child_in = os.dup(in_fd)
            child_out = os.dup(out_fd)
            try:
                proc = Popen(argv, stdin=child_in, stdout=child_out, stderr=sys.stderr.fileno())
                procs.append(proc)
            except FileNotFoundError:
                sys.stderr.write(f"{argv[0]}: command not found\n")
            finally:
                os.close(child_in)
                os.close(child_out)

                if prev_read_fd != -1 and prev_read_fd != sys.stdin.fileno():
                    os.close(prev_read_fd)
                if not last:
                    os.close(w_fd)

            prev_read_fd = r_fd if not last else -1

    if prev_read_fd != -1 and prev_read_fd != sys.stdin.fileno():
        os.close(prev_read_fd)

    for p in procs:
        try:
            p.wait()
        except Exception:
            pass


def main() -> None:
    # REPL with prompt expected by the tester.
    while True:
        print_prompt()
        line = sys.stdin.readline()
        if line == "":  # EOF
            break
        line = line.rstrip("\r\n")
        if not line.strip():
            continue
        execute_pipeline(line)


if __name__ == "__main__":
    main()
