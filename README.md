# Fire Risk Detection Probe

2026 Advantech National AIoT Innovation Competition — Preliminary Round
Single-camera vision-based fire risk identification demo

## Architecture

```
video → Detector(YOLO) → RiskEngine(scoring) → Visualizer(dashboard) → annotated video + JSON report
```

**3 risk categories**: vehicle parking (weight 0.6), obstruction (0.7), ebike entry (0.9)

## Project Structure

```
Code/
├── src/
│   ├── main.py           # CLI pipeline entry point
│   ├── detector.py       # YOLO object detection wrapper
│   ├── risk_engine.py    # Multi-factor risk scoring engine
│   ├── visualizer.py     # OpenCV frame annotator
│   ├── roi_config.py     # ROI polygon configuration
│   └── utils.py          # FPS timer, color mapping, reports
├── tests/                # TDD test suites (pytest)
├── configs/
│   ├── default.yaml      # Inference pipeline configuration
│   ├── classes.yaml      # Fire risk class definitions
│   └── training.yaml     # (reserved for training)
├── scripts/
│   └── run_demo.py       # One-click demo runner
├── demo/
│   ├── input/            # Input test videos (gitignored)
│   └── output/           # Annotated output + JSON reports (gitignored)
├── models/               # Model weights (gitignored)
├── datasets/             # Training datasets (gitignored)
├── docs/                 # Reference docs (gitignored)
├── pyproject.toml
└── README.md
```

## Setup

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                          # Install dependencies
uv run pytest tests/ -v          # Run all tests
```

## Quick Start

```bash
# Run demo with defaults
uv run python scripts/run_demo.py

# Or use the CLI directly
uv run python src/main.py --input demo/input/test.mp4 --output demo/output/annotated.mp4

# Override model and device
uv run python src/main.py --input demo/input/test.mp4 --model models/custom.pt --device cuda:0
```

## CLI Reference

```
uv run python src/main.py --help
```

| Option | Default | Description |
|--------|---------|-------------|
| `--input` | (required) | Input video path |
| `--output` | `demo/output/annotated.mp4` | Output video path |
| `--config` | `configs/default.yaml` | YAML config path |
| `--model` | from config | Override model path |
| `--device` | from config | Override device (cpu/cuda:0) |
| `--roi-debug` | off | Draw ROI polygons on output |
| `--no-roi` | off | Disable ROI filtering |

## Test Results

```
uv run pytest tests/ -v     # 79 tests, all passing
```
