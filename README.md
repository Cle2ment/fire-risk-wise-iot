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

Nine fire-hazard categories with multi-factor scoring:

**Score** = weight × confidence × duration_factor × area_factor × 100, clamped [0,100]
**Level**: low < 20, 20 ≤ medium < 60, high ≥ 60

| Class | Weight | Persist | Description |
|-------|--------|---------|-------------|
| vehicle | 0.6 | 3s | Vehicles parked in fire lanes |
| obstruction | 0.7 | 2s | Large objects blocking passages |
| ebike | 0.9 | 0s | Electric bikes indoors (immediate) |
| debris_wood | 0.6 | 5s | Wooden furniture, timber piles |
| debris_paper | 0.8 | 3s | Cardboard, paper stacks |
| debris_mixed | 0.7 | 4s | Mixed clutter, bags, textiles |
| congested_space | 0.75 | 3s | Narrow/blocked corridors |
| flammable_liquid | 0.95 | 0s | Containers with liquids (immediate) |
| electrical_hazard | 0.85 | 2s | Exposed wires, appliances |

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
│   ├── run_demo.py        # Convenience demo launcher
│   ├── finetune_pipeline.py # COCO-based auto-label + train
│   ├── vlm_autolabel.py   # VLM auto-labeling (Gemini 2.5 Flash)
│   └── vlm_label.py       # VLM→YOLO format converter
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


## Fine-Tuned Models

| Version | Frames | Method | mAP50 | Peak Score | Classes Detected |
|---------|--------|--------|-------|------------|------------------|
| v1 (5.9MB) | 25 | COCO car→vehicle mapping | 0.995 | 8.4 | vehicle |
| v2 (23.3MB) | 94 | 74-class COCO→fire mapping | ~0.7 | 19.7 | vehicle + congested_space |
| v3 (23.3MB) | 55 | Gemini VLM annotation | ~0.3 | 13.7 | vehicle |

## Fine-Tuning Pipelines

### COCO Auto-Label
```bash
uv run python scripts/finetune_pipeline.py
```
Extracts frames, labels via COCO→fire mapping, trains YOLOv8n.

### VLM Auto-Label (Gemini 2.5 Flash)
```bash
$env:CHERRYIN_API_KEY = "sk-..."
uv run python scripts/vlm_autolabel.py
uv run python scripts/vlm_label.py --train
```