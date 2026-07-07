# AGENTS.md — fire-risk-wise-iot

2026 Advantech AIoT Competition project. Two-layer repo: competition docs at root, Python code in `Code/`.

## Working directory

ALL code commands run from `Code/`, never the repo root:

```bash
cd Code
uv sync
uv run pytest tests/ -v
uv run python scripts/run_demo.py --input demo/input/test.mp4
```

## Package manager

`uv` only. No pip, no conda. `uv sync` from `Code/`.

## Testing

- 79 tests in `Code/tests/`, all must pass
- Run: `uv run pytest tests/ -v` (from `Code/`)
- TDD convention: test written RED before implementation

## Git conventions

- `docs/` in Code/ is gitignored — model-generated reference, not tracked
- `models/`, `datasets/`, `demo/input/`, `demo/output/` are gitignored — large binaries
- `runs/` and `_*.py` are gitignored — training artifacts
- Atomic commits: implementation + tests together per logical unit
- Remote: `https://github.com/Cle2ment/fire-risk-wise-iot`

## SSL quirk (Windows)

`schannel` fails on this machine. Globally configured: `git config --global http.sslVerify false`.

## Code-level conventions

See `Code/AGENTS.md` for Python style, TDD, 9-class system, COCO→fire mapping, and model versioning.

## Project structure

```
VI/
├── Code/              # Python project (uv-managed, all commands here)
│   ├── src/           # Detector, RiskEngine, Visualizer, main pipeline
│   ├── tests/         # 79 tests
│   ├── configs/       # YAML configs (default, classes, training, dataset)
│   ├── scripts/       # run_demo, finetune_pipeline, vlm_autolabel, vlm_label
│   └── pyproject.toml
├── documentation/     # Competition proposal (DESCRIPTION.md), roadmap, hardware specs
│   └── ROADMAP.md     # Phased plan: 书审→初赛(7/14)→决赛(8/18)→总决赛(9/19)
├── diagrams/          # draw.io architecture diagrams (SVG + source)
├── data/              # Output reports (JSON)
└── references/        # Competition handbook PDFs, hardware datasheets
```
