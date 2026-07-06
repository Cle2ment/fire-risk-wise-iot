#!/usr/bin/env python3
"""One-click demo runner for fire risk detection probe."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    args = sys.argv[1:]

    # sensible defaults
    input_video = "demo/input/test.mp4"
    output_video = "demo/output/annotated.mp4"

    for a in args:
        if a.startswith("--input="):
            input_video = a.split("=", 1)[1]
        elif a.startswith("--output="):
            output_video = a.split("=", 1)[1]
        elif a in ("-h", "--help"):
            print("Usage: uv run python scripts/run_demo.py [--input=PATH] [--output=PATH]")
            print(f"  default input : {input_video}")
            print(f"  default output: {output_video}")
            return

    cmd = [
        sys.executable,
        str(ROOT / "src" / "main.py"),
        "--input", input_video,
        "--output", output_video,
    ] + args

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(ROOT), check=True)


if __name__ == "__main__":
    main()
