# AGENTS.md — Fire Risk Detection Probe

## Project
Single-camera vision-based fire risk identification probe
2026 Advantech National AIoT Innovation Application Competition — Preliminary Round

## Environment
- OS: Windows
- Python: 3.10+ (uv-managed)
- Shell: pwsh 7

## Build & Run
```bash
uv sync                          # Install dependencies
uv run pytest tests/ -v          # Run all tests
uv run python src/main.py --help # CLI usage
uv run python scripts/run_demo.py --input demo/input/test.mp4 --output demo/output/annotated.mp4
```

## Architecture
```
video → Detector(YOLO) → RiskEngine(scoring) → Visualizer(dashboard) → annotated video + JSON report
```

## Conventions
- Type-annotated Python throughout
- TDD: test file written and verified RED before any source code
- Atomic git commits per logical unit (implementation + test together)
- docs/ is model-generated reference — not committed to git
- models/, datasets/, demo/input/, demo/output/ are .gitignored (binaries/large files)
