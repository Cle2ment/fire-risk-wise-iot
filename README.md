# Fire Risk Detection Probe

单摄像头视觉消防风险识别探头 — 2026 研华全国 AIoT 创新应用大赛初赛

## Architecture

```
video → Detector(YOLO) → RiskEngine(scoring) → Visualizer(dashboard) → annotated video + JSON report
```

| Module | File | Responsibility |
|--------|------|----------------|
| **Detector** | `src/detector.py` | YOLO inference, returns `Detection` list |
| **RiskEngine** | `src/risk_engine.py` | Per-frame risk score (0–100) + level (low/medium/high) |
| **Visualizer** | `src/visualizer.py` | Draws bounding boxes, dashboard gauge, status bar |
| **Main Pipeline** | `src/main.py` | Config → loop → report orchestration |
| **ROI Config** | `src/roi_config.py` | Zone polygon definition & hit-test |
| **Utils** | `src/utils.py` | FPS timer, colour gradient, JSON report writer |
| **Demo Launcher** | `scripts/run_demo.py` | Convenience CLI with camera / model list support |

## Quick Start

```bash
# Install
uv sync

# Run all tests (79 tests, all pass)
uv run pytest tests/ -v

# Process a video
uv run python scripts/run_demo.py --input demo/input/test.mp4

# With ROI zone overlay
uv run python scripts/run_demo.py --input demo/input/test.mp4 --roi-debug

# Live camera
uv run python scripts/run_demo.py --camera 0 --output demo/output/live.mp4

# List available models
uv run python scripts/run_demo.py --list-models

# Direct pipeline usage
uv run python src/main.py --input demo/input/test.mp4 --output demo/output/annotated.mp4 \
  --config configs/default.yaml --model models/yolo26n.pt --device cpu
```

## Risk Scoring

Three fire-hazard detection categories:

| Class | Risk Weight | Persistence | Colour |
|-------|-------------|-------------|--------|
| 车辆违停 (vehicle) | 0.6 | 10 s | Orange |
| 通道堵塞 (obstruction) | 0.7 | 5 s | Red |
| 电动车入楼 (ebike) | 0.9 | instant | Magenta |

Score = `weight × confidence × duration_factor × area_factor × 100`, smoothed over 30 frames.

## Project Structure

```
Code/
├── configs/
│   ├── default.yaml       # Inference, ROI, risk, output settings
│   └── classes.yaml       # Class definitions with risk weights & colours
├── src/
│   ├── __init__.py
│   ├── main.py            # Pipeline orchestration
│   ├── detector.py        # YOLO wrapper → Detection dataclass
│   ├── risk_engine.py     # FrameRisk scoring
│   ├── visualizer.py      # OpenCV annotation overlay
│   ├── roi_config.py      # ROI zone polygon config
│   └── utils.py           # Timer, colour, report generation
├── scripts/
│   └── run_demo.py        # Convenience demo launcher
├── tests/                 # TDD test suite (79 tests)
├── models/                # Model weights (.gitignored)
├── datasets/              # Training data (.gitignored)
├── docs/                  # Reference documentation
└── pyproject.toml         # uv-managed project config
```

## Dependencies

- Python ≥ 3.10
- `ultralytics` (YOLO inference)
- `opencv-python` (video I/O + annotation)
- `numpy`, `pyyaml`
- `pytest` (dev, for testing)

Managed via `uv` — no conda or pip-tools needed.
