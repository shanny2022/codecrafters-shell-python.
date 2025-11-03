# File: app/main.py
# Shell with: prompt, pipelines, in-process built-ins (type/exit), and TAB autocomplete.

from __future__ import annotations

import os
import shlex
import sys
import threading
from subprocess import Popen
from typing import Iterable, List

BUILTINS = {"type", "exit"}


def print_prompt() -> None:
    sys.stdout.write("$ ")
    sys.stdout.flush()


def is_builtin(name: str) -> bool:
    return name in BUILTINS


def builtin_type(argv: List[str]) -> int:
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


def run_builtin(argv: List[str]) -> int:
    if not argv:
        return 0
    cmd = argv[0]
    if cmd == "type":
        return builtin_type(argv)
    if cmd == "exit":
        return 0  # no-op inside pipelines
    return 0


def _drain(reader) -> None:
    # Why: builtins like `type` don't read stdin; draining prevents upstream writer blocking.
    try:
        for _ in iter(lambda: reader.read(8192), ""):
            pass
    except Exception:
        pass


def execute_pipeline(line: str) -> None:
    stages_raw = line.split("|")
    stages = [shlex.split(s) for s in stages_raw]

    if len(stages) == 1 and stages[0] and stages[0][0] == "exit":
        sys.exit(0)

    n = len(stages)
    prev_read_fd = -1
    procs: List[Popen] = []

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

                if in_fd != -1 and argv[0] in {"type", "exit"}:
                    drain_file = os.fdopen(
                        os.dup(sys.stdin.fileno()),
                        "r",
                        buffering=1,
                        encoding="utf-8",
                        errors="ignore",
                    )
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
            if not argv:
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


# ---------- Autocomplete (TAB) ----------

def list_path_executables_starting_with(prefix: str) -> list[str]:
    """Return unique executable basenames on PATH starting with prefix."""
    results: set[str] = set()
    for part in os.environ.get("PATH", "").split(":"):
        d = part or "."
        try:
            for name in os.listdir(d):
                if not name.startswith(prefix):
                    continue
                full = os.path.join(d, name)
                if os.path.isfile(full) and os.access(full, os.X_OK):
                    results.add(name)
        except FileNotFoundError:
            continue
        except NotADirectoryError:
            continue
        except PermissionError:
            continue
    return sorted(results)


def longest_common_prefix(strings: Iterable[str]) -> str:
    s_list = list(strings)
    if not s_list:
        return ""
    prefix = s_list[0]
    for s in s_list[1:]:
        i = 0
        # find common prefix length
        while i < len(prefix) and i < len(s) and prefix[i] == s[i]:
            i += 1
        prefix = prefix[:i]
        if not prefix:
            break
    return prefix


def complete_buffer_on_tab(buffer: str) -> tuple[str, str]:
    """
    Returns (new_buffer, appended_suffix_to_echo).
    Only expands the last token; if no improvement, returns original buffer and empty suffix.
    """
    # Find last token after whitespace
    stripped_right = buffer.rstrip()
    trailing_ws_len = len(buffer) - len(stripped_right)
    if trailing_ws_len > 0:
        # Cursor at whitespace → nothing to complete
        return buffer, ""

    # Last token boundaries
    last_space = stripped_right.rfind(" ")
    token_start = last_space + 1
    token = stripped_right[token_start:]

    if token == "":
        return buffer, ""

    candidates = list_path_executables_starting_with(token)
    if not candidates:
        return buffer, ""

    lcp = longest_common_prefix(candidates)
    if len(lcp) <= len(token):
        return buffer, ""

    new_token = lcp  # do not append trailing space; tests expect "xyz_baz"
    new_buffer = stripped_right[:token_start] + new_token
    suffix = new_token[len(token):]
    return new_buffer, suffix


# ---------- REPL (char-by-char to support TAB) ----------

def repl() -> None:
    while True:
        print_prompt()
        buf = ""
        while True:
            ch = sys.stdin.read(1)
            if ch == "":
                return  # EOF
            if ch == "\n":
                sys.stdout.write("\n")
                sys.stdout.flush()
                if buf.strip():
                    execute_pipeline(buf)
                break  # re-prompt
            if ch == "\t":
                new_buf, suffix = complete_buffer_on_tab(buf)
                if suffix:
                    buf = new_buf
                    sys.stdout.write(suffix)
                    sys.stdout.flush()
                continue
            if ch in ("\x7f", "\b"):  # Backspace support
                if buf:
                    buf = buf[:-1]
                    # erase last char visually
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue

            buf += ch
            sys.stdout.write(ch)
            sys.stdout.flush()


def main() -> None:
    repl()


if __name__ == "__main__":
    main()
