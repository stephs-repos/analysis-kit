# Cheat sheet

Task → command lookup for this project. If you're new, read
[`QUICKSTART.md`](QUICKSTART.md) first — the whole workflow is: add your files,
type `/akit-next`, approve each step. This page is for when you know *what* you
want to do and need the exact command.

## The daily loop

| You want to… | Do this |
|---|---|
| Find out the next step | `/akit-next` — recomputes your position from the project every run; safe anytime |
| Inspect the raw data | `python analysis/01_inspect_raw.py` (or ask Claude: "inspect the raw data") |
| Register a claim | `/akit-finding "median field size is ~108 after excluding non-finishers"` |
| Record a cleanup rule | tell Claude: *"that's a decision — exclude DNF rows before any finisher count"* → becomes a `DR-NNN` |
| Verify everything replays | `python analysis/validate.py` — exit 0 is the trust gate |
| Quick structural check | `python analysis/validate.py --fast` (~1s, no replay, no data needed) |
| Commit | ask Claude to commit — the commit hook re-runs the full replay and blocks on red |

## Findings (`F-NNN`) — the unit of trust

- **Register interactively:** `/akit-finding "<one-line hypothesis with a value>"` — drafts the compute function, `input` + `reproducibility` blocks, caveats, and tag; you confirm before it's written.
- **Register from code:** `register_computed(...)` in `analysis/_findings.py` — the value is computed by *running* the function, so the stored number can't be divorced from the code that produced it.
- **Amend:** `update("F-012", reason="...", ...)` in `analysis/_findings.py`. Never hand-edit values in `findings.json`.
- **The ledger:** `analysis/output/findings.json`.
- **Evidence tags:** `OBSERVED` (measured — requires `measurement_ref`) · `PLAUSIBLE` (informed estimate — name the supporting pattern) · `WEAK` (rephrase or remove).

## Decisions (`DR-NNN`) — named cleanup rules

- **Enter one:** surface it in conversation; Claude writes a pure `DR_NNN(df) -> df` function in `analysis/_decisions.py`, documents it in `live-docs/DECISIONS.md`, and notes the caveat in `memory/`.
- **Apply:** findings cite the filters they use in their `reproducibility` block — never aggregate a column before applying its relevant `DR-NNN`.
- **Retire:** mark `superseded` or `dropped` in `DECISIONS.md` — never delete or renumber.

## Validation & rebuild

| Command | What it does |
|---|---|
| `python analysis/validate.py` | Full replay: re-derives every finding from raw data; non-zero exit on any drift |
| `python analysis/validate.py --fast` | Structural checks only (schema, orphan citations) |
| `python analysis/validate.py --strict` | Treat warnings as failures |
| `make findings` | Re-run all `analysis/NN_*.py` to refresh the ledger — then **review the diff** before committing; drift must surface to a person |
| `make validate` / `make validate-fast` | Same as above, via make |
| `make render` | Rebuild vignettes, gated on green validate (*full tier*; clean no-op on minimum) |

Hooks that run these for you:

| When | What fires | On red |
|---|---|---|
| Claude finishes a turn | `validate.py --fast` | blocks the turn |
| `git commit` | full replay | blocks the commit (fails closed — even without `jq`) |
| `findings.json` edited | coverage nudge | warns |

## Scaffold & setup

| You want to… | Do this |
|---|---|
| List unfilled placeholders | `grep -rlE '\{\{MUST_CUSTOMIZE' . --exclude-dir=.claude` |
| Fill them | `/akit-fill` — drafts each from `reference/`; you accept/edit/skip |
| Install the `/akit-*` skills | already embedded in this project (`.claude/skills/`); the global install — `bash <analysis-kit>/bootstrap/install-skills.sh` — mainly adds `/akit-start` |
| Start another project | `/akit-start <name>` |

## Where things live

| What | Where |
|---|---|
| Raw data (gitignored) | `reference/raw-data/` |
| Project context: brief, dictionary, prior art | `reference/` |
| Numbered analysis scripts | `analysis/NN_*.py` |
| Cleanup filters | `analysis/_decisions.py` |
| Data schemas (Pandera) | `analysis/schemas.py` |
| Findings ledger | `analysis/output/findings.json` |
| Caveats the agent reads before aggregating | `memory/` |
| Live documents | `live-docs/` |

## The live documents & ID registry

| ID | Lives in | Records |
|---|---|---|
| `F-NNN` | `analysis/output/findings.json` | one verified claim |
| `DR-NNN` | `live-docs/DECISIONS.md` | one cleanup rule |
| `A-NNN` | `live-docs/ANALYSIS_BACKLOG.md` | one analytical question worth investigating |
| `T-NNN` | `live-docs/TOOLING.md` | one durable tool/library choice |

Plus: `TRUST_MEMO.md` (what's reliable vs. noisy), `DATA_PROFILE.md` (column-level profile), `METHODOLOGY_LOG.md` (the narrative — discoveries, decisions, AI mistakes caught).

## The don'ts

1. Don't hand-type numbers into memos/vignettes — cite the `F-NNN`.
2. Don't aggregate before applying the relevant `DR-NNN` filters.
3. Don't add an `OBSERVED` claim without a `measurement_ref`.
4. Don't delete or renumber `DR-NNN`/`A-NNN` entries — mark `superseded` or `dropped`.
5. Don't bypass a red validator — it means stop, not ship.
