#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Default executable path (can be overridden with a command-line argument)
DEFAULT_BIN = "/home/jaytwo/workspace/github/linux-cpp-crash-report/hello"

def parse_backtrace(log_path: Path) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Extract metadata (headers) and binary addresses from the crash log."""
    header_lines: List[str] = []
    frames: List[Tuple[str, str]] = []  # (raw_line, hex_address)

    # Match forms such as ./hello[0x400c03] or ./hello(main+0x19)[0x400c25]
    addr_pattern = re.compile(r"\[0x([0-9a-fA-F]+)\]")
    in_backtrace = False

    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped == "Backtrace:":
                in_backtrace = True
                continue

            if not in_backtrace:
                header_lines.append(stripped)
            else:
                match = addr_pattern.search(stripped)
                if match:
                    frames.append((stripped, f"0x{match.group(1)}"))
                else:
                    frames.append((stripped, ""))

    return header_lines, frames


def run_addr2line(bin_path: str, addr: str) -> Tuple[str, str, Optional[int]]:
    """Call addr2line and return (function name, file path, line number)."""
    try:
        # -f: function name, -C: C++ demangling, -i: inline function tracing
        out = subprocess.check_output(
            ["addr2line", "-e", bin_path, "-f", "-C", "-i", addr],
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "??", "??", None

    lines = out.splitlines()
    if len(lines) < 2:
        return "??", "??", None

    # If multiple inline frames are returned, use the innermost (last) frame
    func_name = lines[-2].strip()
    file_line = lines[-1].strip()

    if ":" in file_line:
        file_part, line_part = file_line.rsplit(":", 1)
        # Remove extra information such as "main.cpp:42 (discriminator 1)"
        line_num_str = line_part.split()[0]
        if line_num_str.isdigit():
            return func_name, file_part, int(line_num_str)

    return func_name, file_line, None


def show_source_snippet(file_path_str: str, target_line: int, context: int = 3) -> None:
    """Print source code around the specified line from the source file."""
    src_path = Path(file_path_str)
    if not src_path.exists():
        print(f"    (Source file not found: {file_path_str})")
        return

    try:
        lines = src_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        print(f"    (Failed to read source file: {exc})")
        return

    start = max(1, target_line - context)
    end = min(len(lines), target_line + context)

    print("    --------------------------------------------------")
    for idx in range(start, end + 1):
        marker = ">>>" if idx == target_line else "   "
        print(f"    {marker} {idx:4d} | {lines[idx - 1]}")
    print("    --------------------------------------------------")


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <crash_log_path> [executable_binary_path]")
        print(f"Example: {sys.argv[0]} dump/crash_20261122_144432.log")
        return 1

    log_path = Path(sys.argv[1])
    bin_path = sys.argv[2] if len(sys.argv) >= 3 else DEFAULT_BIN

    if not log_path.exists():
        print(f"[ERROR] Crash log file not found: {log_path}", file=sys.stderr)
        return 1

    if not Path(bin_path).exists():
        print(f"[ERROR] Binary file not found: {bin_path}", file=sys.stderr)
        return 1

    header_lines, frames = parse_backtrace(log_path)

    for h in header_lines:
        print(h)
    print(f"Binary : {bin_path}")
    print("========================================")
    print("Analyzed Call Stack:\n")

    bin_name = Path(bin_path).name

    for idx, (raw_line, addr) in enumerate(frames):
        print(f"#{idx:<2d} {raw_line}")

        # Analyze only addresses from the target binary (./hello); skip shared libraries such as libc.so
        if not addr or bin_name not in raw_line:
            continue

        func_name, file_path, line_num = run_addr2line(bin_path, addr)
        if line_num is not None:
            print(f"    -> Function: {func_name}")
            print(f"    -> Location: {file_path}:{line_num}")
            show_source_snippet(file_path, line_num, context=3)
        else:
            print(f"    -> No symbol or line information ({func_name} @ {file_path})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
    