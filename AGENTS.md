# AGENTS.md — fire-risk-wise-iot

2026 Advantech AIoT Competition project. Two-layer repo: competition docs at root, Python code in `code/`.

## Working directory

ALL code commands run from `code/`, never the repo root:

```bash
cd code
uv sync
uv run pytest tests/ -v
uv run python scripts/run_demo.py --input demo/input/test.mp4
uv sync
uv run pytest tests/ -v
uv run python scripts/run_demo.py --input demo/input/test.mp4
```

## Package manager

`uv` only. No pip, no conda. `uv sync` from `code/`.

## Testing

- 79 tests in `code/tests/`, all must pass
- Run: `uv run pytest tests/ -v` (from `code/`)
- Run: `uv run pytest tests/ -v` (from `code/`)
- TDD convention: test written RED before implementation

## Git conventions

- `docs/` in code/ is gitignored — model-generated reference, not tracked
- `models/`, `datasets/`, `demo/input/`, `demo/output/` are gitignored — large binaries
- `runs/` and `_*.py` are gitignored — training artifacts
- Atomic commits: implementation + tests together per logical unit
- Remote: `https://github.com/Cle2ment/fire-risk-wise-iot`

## SSL quirk (Windows)

`schannel` fails on this machine. Globally configured: `git config --global http.sslVerify false`.

## Code-level conventions

See `code/AGENTS.md` for Python style, TDD, 9-class system, COCO→fire mapping, and model versioning.

## Project structure

```
VI/
├── code/              # Python project (uv-managed, all commands here)
│   ├── src/           # Detector, RiskEngine, Visualizer, main pipeline
│   ├── tests/         # 79 tests
│   ├── configs/       # YAML configs (default, classes, training, dataset)
│   ├── scripts/       # run_demo, finetune_pipeline, vlm_autolabel, vlm_label
│   ├── data/          # Demo pipeline output (JSON reports)
│   └── pyproject.toml
├── visualization/     # WISE-PaaS/Dashboard panel exports (Grafana JSON)
├── documentation/     # Competition proposal (DESCRIPTION.md), roadmap, hardware specs
│   └── ROADMAP.md     # Phased plan: 书审→初赛(7/14)→决赛(8/18)→总决赛(9/19)
├── diagrams/          # draw.io architecture diagrams (SVG + source)
└── references/        # Competition handbook PDFs, hardware datasheets
```
