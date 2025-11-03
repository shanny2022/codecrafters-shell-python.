# File: app/main.py
# Minimal pipeline-capable shell with in-process built-ins: type, exit.
# Behavior matches tests like:
#   echo "raspberry\nblueberry" | wc
#   ls | type exit   -> prints only: "exit is a shell builtin"

from __future__ import annotations

import os
import shlex
import sys
import threading
from subprocess import Popen

BUILTINS = {"type", "exit"}


def is_builtin(name: str) -> bool:
    return name in BUILTINS


def builtin_type(argv: list[str]) -> int:
    # Expected outputs:
    # - "exit is a shell builtin"       (when querying a builtin)
    # - "name is /path/to/name"         (when found on PATH)
    # - "name not found"                (else)
    if len(argv) < 2:
        return 0
    name = argv[1]
    if is_builtin(name):
        print(f"{name} is a shell builtin", flush=True)
        return 0

    path = os.environ.get("PATH", "/bin:/usr/bin")
    for part in path.split(":"):
        candidate = os.path.join(part if part else ".", name)
        # Executable regular file on UNIX
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
        # Standalone "exit" is handled at the top level.
        # In a pipeline, it behaves like a no-op and does not terminate the shell.
        return 0
    return 0


def drain_stdin_to_void(stream) -> None:
    # Important to prevent upstream writer blocking (e.g., ls | type exit).
    try:
        for _ in iter(lambda: stream.read(8192), ""):
            pass
    except Exception:
        pass


def execute_pipeline(line: str) -> None:
    stages_raw = [s for s in line.split("|")]
    stages = [shlex.split(s) for s in stages_raw]

    # Handle standalone 'exit'
    if len(stages) == 1 and stages[0] and stages[0][0] == "exit":
        sys.exit(0)

    n = len(stages)
    prev_read_fd = -1
    procs: list[Popen] = []

    for i, argv in enumerate(stages):
        last = i == n - 1

        # Create pipe for this stage's stdout if not last
        if not last:
            r_fd, w_fd = os.pipe()
        else:
            r_fd, w_fd = -1, -1

        # Determine stdio fds for this stage
        in_fd = prev_read_fd if prev_read_fd != -1 else sys.stdin.fileno()
        out_fd = w_fd if not last else sys.stdout.fileno()

        if argv and is_builtin(argv[0]):
            # Run builtin in the parent with temporary redirections.
            saved_stdin = os.dup(sys.stdin.fileno())
            saved_stdout = os.dup(sys.stdout.fileno())

            try:
                if in_fd != sys.stdin.fileno():
                    os.dup2(in_fd, sys.stdin.fileno())
                if out_fd != sys.stdout.fileno():
                    os.dup2(out_fd, sys.stdout.fileno())

                # Drain stdin in a helper thread so upstream can't block if builtin doesn't read.
                drain_thread = None
                if in_fd != -1 and argv[0] in {"type", "exit"}:
                    # These builtins do not consume stdin; drain to avoid blocking.
                    drain_file = os.fdopen(os.dup(sys.stdin.fileno()), "r", buffering=1, encoding="utf-8", errors="ignore")
                    drain_thread = threading.Thread(target=drain_stdin_to_void, args=(drain_file,), daemon=True)
                    drain_thread.start()

                run_builtin(argv)

                if drain_thread is not None:
                    # Close to signal EOF to the drain and join.
                    try:
                        drain_file.close()  # type: ignore[name-defined]
                    except Exception:
                        pass
                    drain_thread.join(timeout=0.2)

            finally:
                # Restore stdio
                os.dup2(saved_stdin, sys.stdin.fileno())
                os.dup2(saved_stdout, sys.stdout.fileno())
                os.close(saved_stdin)
                os.close(saved_stdout)

                # Close pipe ends we created/used
                if not last:
                    os.close(w_fd)
                if prev_read_fd != -1:
                    os.close(prev_read_fd)

            # Prepare next stage's input
            prev_read_fd = r_fd if not last else -1

        else:
            # External command
            # Duplicate fds for child; Popen will take ownership and close as needed.
            child_in = os.dup(in_fd)
            child_out = os.dup(out_fd)

            try:
                proc = Popen(argv if argv else [], stdin=child_in, stdout=child_out, stderr=sys.stderr.fileno())
                procs.append(proc)
            except FileNotFoundError:
                # Match simple shell error style.
                sys.stderr.write(f"{argv[0]}: command not found\n")
            finally:
                # Parent closes its duplicates.
                os.close(child_in)
                os.close(child_out)

                # Close previous read end now that child has its own.
                if prev_read_fd != -1 and prev_read_fd != sys.stdin.fileno():
                    os.close(prev_read_fd)

                # Close our write end for non-last stage
                if not last:
                    os.close(w_fd)

            # Prepare next stage's input
            prev_read_fd = r_fd if not last else -1

    # Close any remaining read end (last pipeline handoff)
    if prev_read_fd != -1 and prev_read_fd != sys.stdin.fileno():
        os.close(prev_read_fd)

    # Wait for all external processes
    for p in procs:
        try:
            p.wait()
        except Exception:
            pass


def main() -> None:
    # No prompt; tester feeds stdin.
    for line in sys.stdin:
        line = line.rstrip("\r\n")
        if not line.strip():
            continue
        execute_pipeline(line)


if __name__ == "__main__":
    main()
