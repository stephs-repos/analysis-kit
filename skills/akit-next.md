---
name: akit-next
description: Resumable conductor for the analysis-kit workflow. Detects the project's current phase (setup / fill / first-finding / validate / commit / render / steady-state) and guides the user to the single next action, delegating to /akit-fill, /akit-finding, etc. Never auto-advances past a human-judgment step. Invoked as /akit-next, or whenever the user asks "what now?" / is unsure of the next step.
---

# /akit-next

The workflow conductor. Work out where the project sits in the analysis-kit
lifecycle, tell the user the **one** next action, offer to do the part that's
safe to automate, and **stop** at every step that needs their judgment.

This skill is **resumable and stateless**: it remembers nothing of its own.
Every invocation recomputes the phase from the project itself, so the user can
run it anytime — after a break, when lost, or to confirm they're on track. It's
a GPS, not a map.

Guiding rule (the analysis-kit philosophy — see `docs/PHILOSOPHY.md`): **never
auto-advance past a human-judgment step.** Dropping data, accepting a marker,
deciding a DR-NNN rule, blessing a finding's value, committing — each is the
user's call. This skill routes and offers; it never decides.

## Pre-flight: is this a project?

1. Confirm the cwd (or a parent) contains `analysis-kit.json`. If not, stop:
   "This isn't an analysis-kit project. Run `/akit-start <name>` to scaffold one,
   or `cd` into a project root."

2. Read `analysis-kit.json` and note `tier` (`minimum` or `full`). The render
   phase (step 5 below) applies only to `full`.

## Read the project's state

Compute these signals — they're cheap and read-only. Run the commands; don't
guess from memory.

- **markers** — unfilled scaffold placeholders:
  ```bash
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
  SCAN="$ROOT/.claude/akit/check-must-customize.sh"      # ships in the scaffold
  [ -f "$SCAN" ] || SCAN="__AKIT_ROOT__/bootstrap/check-must-customize.sh"
  bash "$SCAN" "$ROOT"
  ```
  (Prefers the project's own copy of the scanner; falls back to the kit clone —
  `__AKIT_ROOT__` is substituted at install time. Exit 1 + a file list = markers
  remain; exit 0 = none.)
- **data** — does `reference/raw-data/` hold anything beyond `README.md` / `.gitkeep`?
- **reference** — does `reference/` hold any context file besides its README
  (a brief, data dictionary, scope note)?
- **findings** — number of entries in `analysis/output/findings.json` (a JSON array).
- **health** — `python analysis/validate.py --fast` (structural). If findings
  exist *and* data is present, also run full `python analysis/validate.py`
  (replay) to catch drift.
- **committed** — `git status --short` (working tree dirty?) and
  `git log --oneline` (any commit past the scaffold?).
- **rendered** (full tier only) — do any `vignettes/*.html` exist?

## Route to the single next action

Evaluate **in order** and act on the first phase that matches. Always show the
user a one-line "you are here" before the recommendation.

### 1. Setup — markers remain
- **No data/reference yet** → STOP (human step):
  "Setup, step 1: drop your raw data into `reference/raw-data/` and your project
  context (brief, data dictionary, prior art) into `reference/` (see
  `reference/README.md`). Re-run `/akit-next` when they're in place."
- **Data/reference present, markers remain** → offer to delegate:
  "You have data and N unfilled markers. Next: `/akit-fill` walks each one,
  drafting from your reference materials — you accept/edit/skip every one. Want
  me to start it?" Invoke `/akit-fill` only on confirmation; it runs its own
  per-marker pauses.

### 2. First finding — markers clear, zero findings
"Setup is done (0 markers). Now turn the data into checked claims."
- Offer to run inspection (safe, read-only): `python analysis/01_inspect_raw.py`,
  and read the output together.
- Flag the judgment step: "As you read the data, note any cleanup rules
  (zero-sentinels, status codes, unattributable rows). Those become DR-NNN
  decisions in `_decisions.py` / `DECISIONS.md`, recorded *before* you aggregate
  over the affected column. Tell me when you spot one."
- Then: "When you have a concrete claim, run
  `/akit-finding \"<one-line hypothesis>\"` to register it."

### 3. Red ledger — findings exist, validate fails
"`validate.py` is red — stop and fix this before anything else." Show the
failing `FAIL …` lines. Diagnose: drift (value mismatch / sha256 / row-count →
data or code changed) vs structural (schema / orphan citation). Do not advance
until it's green.

### 4. Bank it — green but uncommitted
"Findings replay green and the tree has uncommitted work. Commit it — the commit
hook re-runs the full replay before allowing it." Offer to branch (if on the
default branch) + stage + commit; let the user confirm the message. Never
auto-commit silently.

### 5. Communicate (full tier) — green, committed, vignette missing/stale
"Your ledger is solid. To communicate it: `make render` rebuilds vignettes from
the verified findings (gated on validate), or draft a vignette/memo that cites
your `F-NNN` ids. State numbers *via* the finding — don't hand-type them."

### 6. Steady state — green, committed, findings exist
"You're in the analysis loop. From here:
- new claim → `/akit-finding \"<hypothesis>\"`
- new cleanup rule → surface a DR-NNN (tell me)
- keep the live-docs current (TRUST_MEMO, ANALYSIS_BACKLOG, METHODOLOGY_LOG)
- communicate → `make render` / a vignette."
Offer the single most likely next step (usually another finding).

## Critical rules

- **Resumable & stateless.** Recompute the phase every run. Never assume a
  remembered position.
- **One next action.** Recommend a single primary step; mention others briefly.
  Don't dump the whole workflow.
- **Stop at human pauses.** Dropping data, filling a marker, deciding a DR-NNN,
  blessing a finding, committing — offer, then wait for explicit confirmation.
- **Delegate, don't reimplement.** Hand markers to `/akit-fill` and claims to
  `/akit-finding`; never inline their logic here.
- **Safe to run unprompted:** read-only inspection (`01_inspect_raw.py`) and
  `validate.py`. Anything that writes or commits needs an explicit yes.
