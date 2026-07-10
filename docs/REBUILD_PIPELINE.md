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

## Large sources: materialised intermediates with a freshness gate

Full-mode replay reads each finding's source *whole* and re-applies its DRs. When
a source outgrows memory (hundreds of MB / millions of rows), that's non-viable —
loading it on every commit OOMs or crawls.

**When to reach for this** is a per-*source* decision, and the default is raw:
replay directly over the source until a *measured* constraint (it won't fit in
RAM whole, or it makes the commit gate crawl) forces you off. `validate.py`
surfaces the prompt — `check_source_sizes` warns (advisory, never a gate) when a
finding cites a source past ~256 MB (tune with `AKIT_LARGE_SOURCE_MB`), pointing
here. Small sources (a 366-row weather CSV) stay on raw replay even in a project
that materialises a big one; don't let one source's decision spread. The pattern:

1. **Build once, stream.** A build script (`analysis/NN_*.py`) reads the raw
   source in chunks, applies the DR-NNN filters at build time, and writes a small
   derived table (e.g. a daily aggregate) to `analysis/output/`.
2. **Findings replay against the small table**, not the raw source — milliseconds,
   `filters: []` (the DRs already ran at build).
3. **Pin the derivation.** After writing the table, call
   `analysis/_provenance.py:write_manifest(output=…, sources=[…], dr_set=[…])`. It
   writes a sidecar manifest pinning the content hashes of the output, the raw
   source(s), and a fingerprint of the whole `_decisions.py`.

The risk this closes is **staleness**: a materialised table can drift from (a) the
raw source or (b) a changed DR, and native sha256 pinning on a *finding* only
catches a tampered table — not one stale against its inputs. `validate.py`'s
`check_aggregate_freshness` re-derives the manifest hashes and, on any drift,
fails (full mode) / warns (`--fast`) with a rebuild instruction. Like the rest of
the contract it **detects, never rebuilds** — a source or DR change surfaces as an
explicit failure that forces a conscious rebuild, then the finding's own pinned
hash drifts red until you re-bless the value.

Two rules make it safe:

- **Deterministic build** (stable sort, fixed float formatting) — else the output
  hash changes each rebuild and the gate false-alarms.
- **A missing raw source only warns**, never gates: raw data is gitignored /
  distributed out-of-band, so on a fresh clone or in CI (see below) the check
  verifies what it can (output hash, DR fingerprint) and reports the raw as
  "cannot verify" rather than failing.

The DR fingerprint hashes the *whole* `_decisions.py`, so altering any rule marks
every table pinning it stale — a deliberate over-trigger (a false rebuild beats a
silent false-green).

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
