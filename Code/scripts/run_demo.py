#!/usr/bin/env python3
"""Convenience demo entry point for the Fire Risk Detection Probe.

Usage
-----
    uv run python scripts/run_demo.py --input demo/input/test.mp4

    uv run python scripts/run_demo.py --input demo/input/test.mp4 --roi-debug

    uv run python scripts/run_demo.py --camera 0 --output demo/output/live.mp4

    uv run python scripts/run_demo.py --list-models

    uv run python scripts/run_demo.py -h  # full help
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path so `src` is importable.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.main import main as pipeline_main  # noqa: E402


def _resolve_input(args: argparse.Namespace) -> str:
    """Return a video path or camera index string."""
    if args.input:
        p = Path(args.input)
        if not p.is_file():
            print(f"ERROR: input file not found: {p}", file=sys.stderr)
            sys.exit(1)
        return str(p)
    if args.camera is not None:
        return str(args.camera)
    print("ERROR: specify --input <video> or --camera <index>", file=sys.stderr)
    sys.exit(1)


def _show_models() -> None:
    """List available .pt model files under the models/ directory."""
    models_dir = _PROJECT_ROOT / "models"
    if models_dir.is_dir():
        files = sorted(models_dir.glob("*.pt"))
        if files:
            print("Available model files:")
            for f in files:
                print(f"  {f.relative_to(_PROJECT_ROOT)}")
        else:
            print("No .pt model files found under models/ (dummy model present)")
    else:
        print("models/ directory not found")


def main() -> None:
    p = argparse.ArgumentParser(description="Fire Risk Detection Probe — demo launcher")

    src = p.add_argument_group("Input source (one required)")
    src.add_argument("--input", help="Path to input video file")
    src.add_argument("--camera", type=int, default=None, help="Camera device index")

    out = p.add_argument_group("Output")
    out.add_argument("--output", default="demo/output/annotated.mp4",
                     help="Video output path (default: demo/output/annotated.mp4)")

    cfg = p.add_argument_group("Configuration")
    cfg.add_argument("--config", default="configs/default.yaml",
                     help="YAML config (default: configs/default.yaml)")
    cfg.add_argument("--model", default=None, help="Override model path")
    cfg.add_argument("--device", default=None, help="Override device (cuda:0 | cpu)")
    cfg.add_argument("--roi-debug", action="store_true",
                     help="Draw ROI zone polygons on output")

    info = p.add_argument_group("Info")
    info.add_argument("--list-models", action="store_true",
                      help="Show available model files and exit")

    args = p.parse_args()

    # --- info mode ---
    if args.list_models:
        _show_models()
        sys.exit(0)

    # --- resolve input and delegate ---
    args.input = _resolve_input(args)

    # argparse namespace → sys.argv for src.main
    built = ["--input", args.input, "--output", args.output, "--config", args.config]
    if args.model:
        built += ["--model", args.model]
    if args.device:
        built += ["--device", args.device]
    if args.roi_debug:
        built.append("--roi-debug")

    import subprocess  # noqa: TID251
    cmd = [sys.executable, str(_PROJECT_ROOT / "src" / "main.py"), *built]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(_PROJECT_ROOT), check=True)


if __name__ == "__main__":
    main()
