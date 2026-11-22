#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# 기본 실행 파일 경로 (필요 시 명령줄 인자로 변경 가능)
DEFAULT_BIN = "/home/jaytwo/workspace/coredump/hello"


def parse_backtrace(log_path: Path) -> Tuple[List[str], List[Tuple[str, str]]]:
    """크래시 로그에서 메타데이터(헤더)와 바이너리 주소를 추출합니다."""
    header_lines: List[str] = []
    frames: List[Tuple[str, str]] = []  # (raw_line, hex_address)

    # 예: ./hello[0x400c03] 또는 ./hello(main+0x19)[0x400c25] 형태 매칭
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
    """addr2line을 호출해 (함수명, 파일경로, 라인번호)를 반환합니다."""
    try:
        # -f: 함수명, -C: C++ 디맹글링, -i: 인라인 함수 추적
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

    # 인라인 프레임이 여러 개 나올 경우 가장 안쪽(마지막) 프레임 기준
    func_name = lines[-2].strip()
    file_line = lines[-1].strip()

    if ":" in file_line:
        file_part, line_part = file_line.rsplit(":", 1)
        # "main.cpp:42 (discriminator 1)" 같은 부가 정보 제거
        line_num_str = line_part.split()[0]
        if line_num_str.isdigit():
            return func_name, file_part, int(line_num_str)

    return func_name, file_line, None


def show_source_snippet(file_path_str: str, target_line: int, context: int = 3) -> None:
    """소스 파일에서 해당 라인 주변 코드를 출력합니다."""
    src_path = Path(file_path_str)
    if not src_path.exists():
        print(f"    (소스 파일을 찾을 수 없음: {file_path_str})")
        return

    try:
        lines = src_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        print(f"    (소스 파일 읽기 실패: {exc})")
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
        print(f"사용법: {sys.argv[0]} <크래시_로그_경로> [실행_바이너리_경로]")
        print(f"예시  : {sys.argv[0]} dump/crash_20261122_144432.log")
        return 1

    log_path = Path(sys.argv[1])
    bin_path = sys.argv[2] if len(sys.argv) >= 3 else DEFAULT_BIN

    if not log_path.exists():
        print(f"[ERROR] 크래시 로그 파일을 찾을 수 없습니다: {log_path}", file=sys.stderr)
        return 1

    if not Path(bin_path).exists():
        print(f"[ERROR] 바이너리 파일을 찾을 수 없습니다: {bin_path}", file=sys.stderr)
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

        # 대상 바이너리(./hello)에서 나온 주소만 분석 (libc.so 등은 건너뜀)
        if not addr or bin_name not in raw_line:
            continue

        func_name, file_path, line_num = run_addr2line(bin_path, addr)
        if line_num is not None:
            print(f"    -> 함수: {func_name}")
            print(f"    -> 위치: {file_path}:{line_num}")
            show_source_snippet(file_path, line_num, context=3)
        else:
            print(f"    -> 심볼/라인 정보 없음 ({func_name} @ {file_path})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
    