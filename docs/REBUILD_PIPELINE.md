# The rebuild pipeline

`validate.py` *detects* drift; it never *rebuilds*. This doc covers how to turn
the detection primitive into a reliable rebuild pipeline — and, just as
important, what you must **not** automate.

## Two pipelines, opposite verdicts

A project's outputs depend on the data through two distinct flows:

```
VERIFICATION:   raw-data ─▶ DR-NNN ─▶ code_path ─▶ value ─▶ findings.json ─▶ validate replays
PRESENTATION:   raw-data ─▶ DR-NNN ─▶ (plot/memo's own reduction) ───────────▶ figure / prose
                            └────── shared: same source, same decisions ──────┘
```

- **Automate the presentation pipeline.** Once `findings.json` is green (human
  blessed), re-rendering a vignette/memo is pure mechanical derivation. Stale
  rendered output has no upside and is invisible to `validate.py`.
- **Do NOT automate refreshing `findings.json` values.** A stored value going red
  is the alarm that forces a human to look ("median dropped 108→87 — is the new
  data corrupt, or did the world change?"). A cron job that silently recomputes
  the stored value turns a corrupted refresh into the new "truth" and replays
  green — the alarm is gone. The stored value is a human-blessed snapshot;
  automating the blessing removes the human, which is the one thing the contract
  exists to keep in the loop.

So: **automate the derivation, never the judgment.** Compute → human blessing
(review the `findings.json` git diff) → mechanical render.

## The Makefile

The scaffold ships a `Makefile` whose load-bearing rule is `render: validate` —
a vignette can never be built off a red ledger:

```
make findings       # run analysis/NN_*.py -> refresh findings.json (then REVIEW THE DIFF)
make validate       # full replay; non-zero exit on drift
make validate-fast  # structural checks only (~1s, no data needed)
make render         # render vignettes — gated on validate, clears the freeze cache
make all            # validate + render
```

`findings` is the deliberate human step: run it after a data refresh, then
`git diff analysis/output/findings.json` and bless the value changes before
committing.

## The freeze trap

Quarto's `freeze: auto` (in `_quarto.yml`) re-executes a chunk only when the
`.qmd` **source** changes — *not* when the data or `findings.json` changes. So a
render after a data refresh can serve **stale** numbers. There is **no
`--no-freeze` flag**; the reliable fix (which `make render` does) is to delete
the `_freeze/` cache before rendering, forcing re-execution.

## CI is the unbypassable gate

Local `.claude/hooks` are convenience — they can be skipped (`--no-verify`, a
fresh clone). The scaffold ships `.github/workflows/trust-contract.yml`, which
runs full `validate.py` on push/PR. Make it a **required status check** on the
default branch so a red ledger cannot merge.

Caveat: full replay needs the raw data, which is gitignored. CI must fetch it
from the team's data store before validating, or fall back to `--fast`
(structural only). See the comments in the workflow.

## Determinism (or the gate is flaky)

- **Pin exact versions** of `pandas`/`numpy`/`pandera` once you have findings —
  replay compares floats to a tight tolerance, so an unpinned bump can flip a
  finding red with no real data change.
- **Render deps must be declared.** Full-tier vignettes need `matplotlib` +
  `jupyter` + `pyyaml`; they ship in the full-tier `requirements.txt`.
