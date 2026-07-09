# analysis-kit user guide

This is the long-form guide. If you just want to start a project right now, see the [quick start](#quick-start) below.

## Contents

1. [What is analysis-kit?](#what-is-analysis-kit)
2. [Distribution model](#distribution-model)
3. [Why use it?](#why-use-it)
4. [Prerequisites](#prerequisites)
5. [Quick start](#quick-start)
6. [Tour of a scaffolded project](#tour-of-a-scaffolded-project)
7. [The trust contract, explained](#the-trust-contract-explained)
8. [Working with findings](#working-with-findings)
9. [Working with decisions (DR-NNN)](#working-with-decisions-dr-nnn)
10. [Working with the analysis backlog (A-NNN)](#working-with-the-analysis-backlog-a-nnn)
11. [Working with memory and caveats](#working-with-memory-and-caveats)
12. [The live documents](#the-live-documents)
13. [Hooks: what they do, when they fire](#hooks-what-they-do-when-they-fire)
14. [`validate.py` — running and extending](#validatepy--running-and-extending)
15. [The two tiers: `--minimum` and `--full`](#the-two-tiers-minimum-and-full)
16. [Vignettes — publishing for non-technical readers](#vignettes--publishing-for-non-technical-readers)
17. [Common workflows (cookbook)](#common-workflows-cookbook)
18. [Counterfactual tagging discipline](#counterfactual-tagging-discipline)
19. [Troubleshooting](#troubleshooting)
20. [When NOT to use analysis-kit](#when-not-to-use-analysis-kit)
21. [Upgrading the framework](#upgrading-the-framework)
22. [Glossary](#glossary)

---

## What is analysis-kit?

analysis-kit is essentially a lightweight reproducibility and provenance framework for pandas-style analysis projects, designed for situations where you are producing memos, reports, or stakeholder-facing findings, not building production data pipelines. Its whole purpose is to stop AI-assisted analysis from producing numbers that look credible but cannot be traced, reproduced, or trusted and sits somewhere between “plain Jupyter chaos” and “full enterprise-grade data governance.” The sweet spot is consulting-style or nonprofit/public-sector analysis where you need to move quickly but cannot afford to have numbers become untraceable. In other words, it's for making AI-assisted data analysis auditable enough that you can safely put numbers in front of real people.

analysis-kit is a **scaffolding framework** for data-analysis projects where [Claude Code](https://code.claude.com) (or another agentic AI) is doing some of the work. It gives you a starting layout — a folder structure, a few template files, a small Python harness, and some Claude Code hooks — that enforces a particular discipline:

- Every quantitative claim you make to a stakeholder is backed by a code path that reproduces it.
- That code path is verifiable by running one command (`python analysis/validate.py`).
- Data-quality caveats live next to the data, not in your head.
- Decisions about how to clean the data are recorded, named, and applied consistently.

You don't have to use Claude Code with it — the framework is just Python, bash, markdown, and JSON. But it's designed assuming an agent is part of your workflow, and the hooks are Claude Code-specific.

It is **not** a pipeline runner, a notebook framework, or a BI tool. See [When NOT to use analysis-kit](#when-not-to-use-analysis-kit) for what it isn't.

## Distribution model

analysis-kit is a **scaffolding tool**, not a runtime dependency. Closer to cookiecutter than to dbt. It's worth being explicit about this because the model has real consequences for how teammates use it and how upgrades work.

### The lifecycle

```
   ┌───────────────────────────────┐
   │  ~/dev/analysis-kit/          │  ← cloned once per machine
   │  (this repo)                  │     contains templates + bootstrap
   └───────────────────────────────┘
                │
                │  bootstrap/new-project.sh ./my-analysis
                │  (copies templates, runs git init, makes a fresh repo)
                ▼
   ┌───────────────────────────────┐
   │  ~/work/my-analysis/          │  ← brand new git repo, fully self-contained
   │  (your project)               │     owns its CLAUDE.md, validate.py, hooks…
   │                               │     has no runtime dep on analysis-kit
   └───────────────────────────────┘
```

After bootstrap, the new project is a **complete artefact**. You can delete `~/dev/analysis-kit/` and the project still runs. There's no `pip install analysis-kit`. Nothing in your project imports `analysis_kit`. The `validate.py` in your project is *your* `validate.py` — fully readable, fully editable.

### What this means in practice

- **For you (the project author):** clone analysis-kit once on your laptop, then use the bootstrap script every time you start a new project.
- **For teammates joining a scaffolded project:** they clone the *project repo*, not analysis-kit. They only need analysis-kit if they want to scaffold their own new project.
- **For upgrades:** when analysis-kit ships a new version, your existing projects don't change automatically. To pull in new check_types or hooks, manually copy the new `validate.py` over and run any migration script. The scaffolded project is a snapshot, pinned via `analysis-kit.json`'s `framework_version`.

## Why use it?

A few specific problems analysis-kit is designed to prevent:

1. **Stat in a memo, no idea where it came from.** You write "median session rating is 4.2" in a memo three weeks ago, then someone asks "where does that come from?" and you spend an hour trying to find which script produced it. analysis-kit gives every numeric claim an `F-NNN` id and a function path, so the answer is always "run `python analysis/validate.py`".

2. **Stale findings.** You computed something on raw data, then later applied a cleanup rule that changed it, but the memo still cites the old number. The replay harness catches this — every claim's value is recomputed from the data through the declared filters and compared to what's stored.

3. **Caveats that live in your head.** "Don't aggregate column X without masking the zero-sentinel" is a rule that lives in `memory/data_quality_caveats.md` so the next session of Claude (or your colleague) reads it before computing anything.

4. **Drift from a data refresh.** When the data owner sends a new file, will any of your existing findings silently become wrong? validate.py catches it via the `row_count_after_filter` field and value replay.

5. **AI hallucinations.** When an agent writes a memo claiming a statistic, you want a deterministic check that the number is real. analysis-kit's check is: "does running validate.py exit 0?". No LLM judgement involved.

If those problems are theoretical for you, you might not need this. If two or more have happened to you, you probably do.

## Prerequisites

- **Python 3.11 or later.** The harness uses modern type hints.
- **bash** (any modern Unix shell). Bootstrap and hooks are bash scripts.
- **`jq`.** The hooks use it to parse Claude Code's tool input. Install with `apt install jq` (Linux), `brew install jq` (macOS), or your package manager of choice.
- **`git`.** The bootstrap initializes a repo and the hooks check git state.
- **pandas + Pandera.** Listed in `templates/requirements.txt`. Install per project.
- **Claude Code** (optional but assumed). The hooks fire from Claude Code; they're inert without it. You can still use `validate.py` standalone.
- **Quarto** (optional, only for `--full` tier vignettes). Install from [quarto.org](https://quarto.org).
- **Datasette** (optional, only for `--full` tier exploration UI). Install with `pipx install datasette`.

## Quick start

This gets you from nothing to a scaffolded project (5 minutes). Everything *after* the scaffold — data in, markers filled, first finding registered — is covered by the `QUICKSTART.md` that ships inside every project, so it isn't repeated here.

```bash
# 1. Get analysis-kit
git clone https://github.com/<your-fork>/analysis-kit ~/dev/analysis-kit

# 2. Create your first project
~/dev/analysis-kit/bootstrap/new-project.sh ~/work/my-first-analysis \
    --minimum \
    --name "My first analysis" \
    --github-user yourusername

# 3. Go look at what got created
cd ~/work/my-first-analysis
ls -la

# 4. Install Python deps
pip install -r requirements.txt

# 5. Run the validator (it should pass on the empty project)
python analysis/validate.py --fast

# 6. (If using Claude Code) open the project — Claude reads CLAUDE.md and follows the discipline
claude
```

That's it. You now have a project that:
- Has a CLAUDE.md telling Claude what discipline to follow
- Has six live documents waiting to be filled in
- Has a `validate.py` that already passes
- Has Claude Code hooks pre-wired in `.claude/settings.json`
- Has a `memory/` directory of preconditions for the agent
- Is a fresh git repo with one initial commit

**Next steps — continue inside the project.** From here the interface is two things: add your files (raw data → `reference/raw-data/`, project context → `reference/`), then open Claude Code and type `/akit-next` — it detects where the project is and walks you through the rest one approved step at a time (filling markers, inspecting data, registering findings, validating, committing). Your scaffold's `QUICKSTART.md` is the two-minute version of what to expect. The rest of this guide is the depth behind those steps, not a substitute for them.

## Tour of a scaffolded project

Here's every file you get and what it's for. Open one of these in a real scaffolded project to follow along.

```
my-first-analysis/
├── CLAUDE.md                          # Instructions for Claude — keep tight
├── README.md                          # Human-facing project description
├── analysis-kit.json                  # Project manifest — pins framework version
├── requirements.txt                   # Python deps
├── .gitignore
├── .claude/
│   ├── settings.json                  # Claude Code hook configuration
│   └── hooks/
│       ├── validate-on-stop.sh        # Runs validate.py --fast at end of each turn
│       ├── block-unvalidated-commit.sh # Blocks `git commit` if validate is red
│       └── findings-coverage-on-edit.sh # Soft warning when analysis/ edited
├── analysis/
│   ├── validate.py                    # The trust contract — exit code is truth
│   ├── _findings.py                   # Helper: register/update findings
│   ├── _decisions.py                  # DR-NNN filter functions
│   ├── schemas.py                     # Pandera schemas (column-level validation)
│   ├── 01_inspect_raw.py              # First-pass inspection
│   ├── 02_profile.py                  # Profile + first findings
│   └── output/
│       └── findings.json              # The claims ledger (starts empty)
├── live-docs/
│   ├── TRUST_MEMO.md                  # What's reliable / noisy / unassessable
│   ├── DATA_PROFILE.md                # Per-column descriptive profile
│   ├── DECISIONS.md                   # DR-NNN cleanup decisions
│   ├── ANALYSIS_BACKLOG.md            # A-NNN ideas to investigate
│   ├── TOOLING.md                     # T-NNN tool/library choices
│   └── METHODOLOGY_LOG.md             # Methodology narrative (optional)
├── memory/
│   ├── MEMORY.md                      # Index of memory entries
│   ├── project_overview.md            # Goal, audience, deliverable
│   ├── data_quality_caveats.md        # Preconditions before aggregation
│   ├── analysis_framework.md          # The trust contract restated
│   └── stakeholder_stance.md          # How the audience views the work
└── reference/
    ├── README.md                      # The reference/ vs raw-data/ split, format guidance
    ├── raw-data/                      # Raw data files (gitignored by default)
    │   └── README.md                  # What does/doesn't belong; on data refreshes
    └── (your project's briefs, dictionaries, prior art — see reference/README.md)
```

The `reference/` directory has two purposes split across two layers:

- **`reference/`** itself holds *project-context materials* that are committed to git: the project brief, the data dictionary, stakeholder correspondence, prior art. These are usually small, often shareable, and you want them visible immediately on `git clone` so a new analyst joining the project has context.
- **`reference/raw-data/`** holds the *actual data files* (CSV, Excel, etc.). These are gitignored by default — typically large, often sensitive, and refreshed externally. Don't put briefs or dictionaries in here.

Format guidance: prefer markdown for anything you might edit or reference programmatically. PDFs are fine for *fixed* source documents (signed contracts, vendor briefs) but a poor fit for living documents like data dictionaries — they bloat the repo, can't be diffed, and can't be cross-referenced from `live-docs/` or vignettes. If you have a vendor PDF that's a source of truth, keep the PDF for provenance and maintain a markdown shadow next to it.

See `reference/README.md` in any scaffolded project for the full convention.

If you scaffolded `--full` you also get:

```
├── _quarto.yml                        # Quarto site config
└── vignettes/
    └── 00_template.qmd                # Vignette template (Quarto)
```

### What you'll edit, when

| File | Frequency | Owner |
|---|---|---|
| `CLAUDE.md` | Once at start, then rarely | You |
| `live-docs/*.md` | Continuously | You + Claude |
| `analysis/_decisions.py` | When a new DR-NNN is agreed | You + Claude |
| `analysis/02_profile.py` and friends | When profiling changes | You + Claude |
| `analysis/output/findings.json` | Continuously, via `_findings.py` | Claude (mostly) |
| `memory/*.md` | When a new caveat or stakeholder note emerges | You |
| `analysis/validate.py` core dispatcher | Never (fix in framework upstream) | Framework maintainer |
| `analysis/validate.py` `project_specific_checks` | When a project-specific check is needed | You |

## The trust contract, explained

The "trust contract" is the central concept. Plain English:

> A **claim** is anything quantitative you'd put in a memo, vignette, or stakeholder communication: a number, a statistic, a distribution, a correlation, an assertion that something is true or false.
>
> Every claim must be **reproducible** from the data by running code. Not "I remember computing this", not "look at this notebook", not "trust me". Run a script, get the number.
>
> If you can't reproduce a claim, either the claim is wrong, the data changed, or your code changed. All three are important to know about, and the system should fail loudly when any of them happens.

This is implemented as five rules:

1. **Every claim has an `F-NNN` id** in `analysis/output/findings.json`. The id is what you cite — in memos, in vignettes, in conversations.
2. **Every finding has a `code_path`** that points to a function. Running the function reproduces the claim's value.
3. **Every finding has an `input` block** (which source files + columns) and a **`reproducibility` block** (which DR-NNN filters, and how many rows after filtering). This makes the inputs to the function explicit.
4. **`validate.py` replays every finding** by reading the source, applying the filters, calling the function, and comparing the result to the stored value.
5. **Exit code is the truth.** If `python analysis/validate.py` exits 0, all claims are reproducible. If it exits non-zero, something is broken and you don't ship the memo.

Importantly, **the LLM is not part of the trust check**. The replay harness is plain Python comparing numbers. An LLM can't talk it into passing.

## How validation works (with diagrams)

This is the deep dive. If you've read the trust contract section, you know *what* validation does. This section explains *how*, layer by layer, with diagrams.

### The big picture

When you run `python analysis/validate.py`, here's what happens:

```
                    python analysis/validate.py
                              │
                              ▼
                 ┌──────────────────────┐
                 │  Read findings.json  │
                 └──────────────────────┘
                              │
                              ▼
       ┌──────────────────────────────────────────┐
       │  STRUCTURAL CHECKS  (always — fast)      │
       │  ──────────────────────────────────      │
       │  • Every finding has an F-NNN id         │
       │  • Required fields present               │
       │  • check_type is in the valid enum       │
       │  • code_path resolves to a real file     │
       │  • OBSERVED tags have measurement_ref    │
       │  • TRUST_MEMO citations exist            │
       │  • revision_history non-empty            │
       └──────────────────────────────────────────┘
                              │
                              │  any failure → exit 1
                              ▼
                  ┌──────────────────────┐
                  │   --fast flag set?   │
                  └──────────────────────┘
                       │              │
                  yes  │              │  no
                       ▼              ▼
                  ┌─────────┐  ┌─────────────────────────┐
                  │ exit 0  │  │  REPLAY each finding    │
                  └─────────┘  │  (see next diagram)     │
                                └─────────────────────────┘
                                          │
                                          ▼
                                ┌──────────────────────┐
                                │  any replay failed?  │
                                └──────────────────────┘
                                     │            │
                                yes  │            │  no
                                     ▼            ▼
                                ┌─────────┐  ┌─────────┐
                                │ exit 1  │  │ exit 0  │
                                └─────────┘  └─────────┘
```

Two modes: `--fast` skips replay (use in hooks; ~1 second). The default is full replay (~tens of seconds depending on data size; use at commit time and in CI).

### What "replay" actually does

Replay is the heart of the trust contract. For each finding, it reads the source data, re-runs the analysis, and compares the result to what's stored. Here's the flow for one finding:

```
                    finding F (from findings.json)
                              │
                              ▼
     ┌────────────────────────────────────────────┐
     │  input + reproducibility blocks:           │
     │  ─────────────────────                     │
     │  input.sources: [{path: "…/sessions.csv"}] │
     │  input.columns: ["session_rating"]         │
     │  reproducibility.filters: ["DR-001","DR-003"]│
     │  reproducibility.row_count_after_filter: 312│
     └────────────────────────────────────────────┘
                              │
                              ▼
     ┌────────────────────────────────────────────┐
     │  STEP 1 — Read the file                    │
     │  pd.read_csv(source)  →  raw_df            │
     │  (e.g. 1125 rows)                          │
     └────────────────────────────────────────────┘
                              │
                              ▼
     ┌────────────────────────────────────────────┐
     │  STEP 2 — Apply filters in order           │
     │  for each DR-NNN in filters:               │
     │    df = _decisions.DR_NNN(df)              │
     │  (e.g. DR-001 drops 34 rows → 1091,        │
     │   DR-003 drops 12 more  → 1079, etc.)      │
     └────────────────────────────────────────────┘
                              │
                              ▼
     ┌────────────────────────────────────────────┐
     │  STEP 3 — Check the row count              │
     │  if len(df) != row_count_after_filter:     │
     │     ✗ FAIL  "row count X != contract Y     │
     │              (data drift?)"                │
     │  ✓ counts match → continue                  │
     └────────────────────────────────────────────┘
                              │
                              ▼
     ┌────────────────────────────────────────────┐
     │  STEP 4 — Run the function                 │
     │  fn = import_callable(code_path)           │
     │  result = fn(df)                           │
     │  (e.g. median_session_rating(df) → 4.2)    │
     └────────────────────────────────────────────┘
                              │
                              ▼
     ┌────────────────────────────────────────────┐
     │  STEP 5 — Compare to stored value           │
     │  stored = F.value  (or .distribution,       │
     │                     .matrix, etc.)         │
     │  match = compare(stored, result)           │
     │  ✓ match → REPLAY OK                        │
     │  ✗ mismatch → FAIL with both values shown  │
     └────────────────────────────────────────────┘
```

Notice the split: **the function does NOT apply filters — validate.py does**. This is on purpose. If the function applied its own filters, you could change a filter rule and the function would just compute the same answer. The framework would never know. By separating "what data" (the contract) from "what computation" (the function), changes to either get caught.

### The five layers of trust

Validation is layered. Each layer catches a different class of problem. Here's the onion:

```
        ╭──────────────────────────────────────────────────────╮
        │           5. CROSS-REFERENCE LAYER                   │
        │  catches: orphan F-NNN refs in TRUST_MEMO,           │
        │           live-doc abandonment, > 60% OBSERVED       │
        │  ╭────────────────────────────────────────────────╮  │
        │  │           4. REPLAY LAYER                      │  │
        │  │  catches: stale findings, value drift,         │  │
        │  │           filter logic changes                 │  │
        │  │  ╭──────────────────────────────────────────╮  │  │
        │  │  │       3. DATA CONTRACT LAYER             │  │  │
        │  │  │  catches: schema drift, row count        │  │  │
        │  │  │           changes, missing source files  │  │  │
        │  │  │  ╭────────────────────────────────────╮  │  │  │
        │  │  │  │    2. PROVENANCE LAYER             │  │  │  │
        │  │  │  │  catches: missing code paths,      │  │  │  │
        │  │  │  │           OBSERVED without ref     │  │  │  │
        │  │  │  │  ╭──────────────────────────────╮  │  │  │  │
        │  │  │  │  │  1. STRUCTURAL LAYER         │  │  │  │  │
        │  │  │  │  │  catches: missing fields,    │  │  │  │  │
        │  │  │  │  │           bad enums,         │  │  │  │  │
        │  │  │  │  │           duplicate ids      │  │  │  │  │
        │  │  │  │  ╰──────────────────────────────╯  │  │  │  │
        │  │  │  ╰────────────────────────────────────╯  │  │  │
        │  │  ╰──────────────────────────────────────────╯  │  │
        │  ╰────────────────────────────────────────────────╯  │
        ╰──────────────────────────────────────────────────────╯
```

Outer layers depend on inner layers. If structural checks fail, replay won't even attempt. This is on purpose — there's no point replaying a finding that's structurally malformed.

#### Layer 1 — Structural

The basics. Without these, nothing else means anything.

| Check | What it protects against |
|---|---|
| Every finding has `id`, `claim`, `check_type`, `code_path`, `input`, `reproducibility`, `caveats`, `counterfactual_tag`, `revision_history` | Missing data prevents downstream layers from running |
| `id` matches `F-NNN[a-z]?` | Inconsistent referencing across documents |
| Every `id` is unique | Two findings with the same id silently overwrite each other |
| `check_type` is in the valid set | Typos that prevent dispatch |
| `counterfactual_tag` is in `{OBSERVED, PLAUSIBLE, WEAK}` | Free-form tags that defeat the discipline |
| `revision_history` is non-empty | Findings without history can't be audited |

#### Layer 2 — Provenance

The "where does this number come from?" layer.

| Check | What it protects against |
|---|---|
| `code_path` points to a file that exists | Renamed/moved files breaking citations |
| `OBSERVED` findings have a `measurement_ref` | "OBSERVED" being used as a credibility marker without evidence |
| The function named in `code_path` exists and is callable | Renamed functions silently breaking replay |

#### Layer 3 — Data contract

The "what data was this computed from?" layer. Most of the silent-drift protection lives here.

| Check | What it protects against |
|---|---|
| `input.sources` exist on disk | Data files moved or deleted |
| Each `DR-NNN` in `filters` resolves to a function in `_decisions.py` | Renamed or deleted decision functions |
| `len(df_after_filters) == row_count_after_filter` | **Silent data drift — the most important check.** A new data refresh changes the row count? Caught. A filter logic change includes/excludes different rows? Caught. |

#### Layer 4 — Replay

The "is the stored answer still the right answer?" layer.

| Check | What it protects against |
|---|---|
| Function output matches stored value (within tolerance) | Stored claim diverged from what the data + code now produces |
| `OBSERVED` boolean matches recomputed boolean | Stale yes/no assertions (e.g., "data lacks X" still true?) |
| Matrix entries match element-wise | Correlation drift, off-diagonal changes |
| Quote text appears verbatim in source_locator | Hallucinated or paraphrased quotes |

#### Layer 5 — Cross-reference

The "is the project healthy?" layer.

| Check | What it protects against |
|---|---|
| Every `F-NNN` cited in TRUST_MEMO.md exists in findings.json | Memo cites a finding you renamed or removed |
| `max(F-NNN) in findings - max(F-NNN) cited in TRUST_MEMO < threshold` | Live-doc abandonment (warns) |
| < 60% of findings tagged `OBSERVED` | Counterfactual discipline decay (warns) |

### Worked example: catching silent drift

Concrete walkthrough. Imagine this sequence:

**Day 1.** You register F-001:

```python
register(
    id="F-001",
    claim="median session rating is 4.2 (n=312)",
    check_type="scalar",
    code_path="analysis/02_profile.py:median_session_rating",
    value=4.2,
    n=312,
    input={
        "sources": [{"path": "reference/raw-data/sessions.csv"}],
        "columns": ["session_rating"],
    },
    reproducibility={
        "filters": ["DR-001"],
        "row_count_after_filter": 312,
    },
    ...
)
```

DR-001 in `_decisions.py` is "exclude rows where any BPN score is 0":

```python
def DR_001(df):
    return df[(df[BPN_COLS] > 0).all(axis=1)].copy()
```

`validate.py` runs. All five layers pass. Exit 0.

**Day 14.** Someone (you, a colleague, an agent) refactors DR_001. They mean to clean up the code. They change `.all(axis=1)` to `.any(axis=1)`:

```python
def DR_001(df):
    return df[(df[BPN_COLS] > 0).any(axis=1)].copy()  # subtly different
```

This is now a *different rule*. It excludes rows where *all* BPNs are 0 (much rarer), instead of where *any* BPN is 0. The function still runs. The function name is still `DR_001`. The DECISIONS.md entry still says the same thing.

**`validate.py` runs.** Layer by layer:

```
Layer 1 — Structural        ✓ findings.json well-formed
Layer 2 — Provenance        ✓ code_path resolves, function exists
Layer 3 — Data contract     ┐
                            │   reads source: 1125 rows
                            │   applies DR_001:    1119 rows (was 1091)
                            │   row_count_after_filter: 312
                            │
                            ✗ FAIL: row count 1119 != contract 312
```

The finding is rejected at **layer 3 — data contract**. Validate exits 1. The commit hook blocks `git commit`. You see the diagnostic message and investigate. You find the refactor. You either revert it or update findings explicitly.

**Why this is the most important diagnostic.** Without `row_count_after_filter`, layer 3 wouldn't catch this. Validate would proceed to layer 4 (replay), call `median_session_rating` on the new 1119-row dataframe, get a different median, and fail with `value mismatch: stored=4.2 computed=4.18`. Same outcome (validate fails), but the *diagnosis* is much weaker — you'd think the data values changed when actually a *filter rule* changed. The row count tells you "the SHAPE of the data going into your function changed" before you even get to the values. Different cause, different fix.

### What the hooks do — the chain

Three hooks compose to enforce validation at three different moments. Diagram:

```
  Claude Code session lifecycle
  ─────────────────────────────

   you talk to Claude
        │
        ▼
   Claude reasons / plans
        │
        ▼
   ┌────────────────────────────────────┐
   │ Claude calls Edit/Write tool       │
   └────────────────────────────────────┘
        │
        │   PostToolUse hook fires (after the edit)
        ├──► findings-coverage-on-edit.sh
        │    if file is analysis/NN_*.py
        │    AND findings.json untouched in last 3 commits
        │    → print soft nudge ("did you forget to register?")
        │    NEVER blocks. NEVER fails.
        │
        ▼
   ┌────────────────────────────────────┐
   │ Claude calls Bash tool             │
   │ (e.g., git commit -m "...")        │
   └────────────────────────────────────┘
        │
        │   PreToolUse hook fires BEFORE the command runs
        ├──► block-unvalidated-commit.sh
        │    if command contains "git commit":
        │      run validate.py  (FULL replay)
        │      if validation fails:
        │        BLOCK the commit
        │        return reason to Claude
        │      else allow
        │
        ▼
   command runs (or was blocked)
        │
        ▼
   Claude continues or finishes the turn
        │
        │   Stop hook fires when turn ends
        ├──► validate-on-stop.sh
        │    run validate.py --fast
        │    if validation fails:
        │      surface to Claude in-turn
        │      (does NOT hard-block — community evidence
        │       shows aggressive Stop-blocking causes
        │       false-positive premature ends)
        │
        ▼
   turn ends, you see the response
```

**Why three hooks instead of one?** Different moments need different aggressiveness:

- **Stop (every turn): fast.** Cheap check, runs constantly, can't be slow.
- **PreToolUse (commits only): full + blocking.** Commits are durable. The cost of a one-time 30-second wait is much less than the cost of committing wrong findings.
- **PostToolUse (edits only): soft warn.** Editing analysis code without registering a finding isn't always wrong (you might be in the middle of refactoring). A nudge is the right intensity.

### What validation does NOT catch

Be honest about edges. Validation catches *whether stored claims still reproduce*. It does **not** catch:

- **Wrong analytical question.** If you computed the mean when you should have computed the median, validate just checks the mean. It can't know the median was the right call.
- **Wrong interpretation.** A correlation of 0.6 between X and Y replays fine. Whether you should describe it as "strong", "moderate", or "weak" in prose is a human judgement.
- **Missing findings.** Validate checks the findings you registered, not the ones you didn't think to register. If you forgot to look at gender stratification, validate has nothing to say.
- **Overconfident prose.** A finding tagged `PLAUSIBLE` correctly might still be cited in a memo as if it were measured. The tagging discipline only helps if you actually use it.
- **A hallucinated quote that happens to exist verbatim in the source.** `quote_provenance` checks the quote text appears in the cited file. If a long quote is hallucinated but the file genuinely contains those exact words elsewhere, validate passes. (Mitigation: keep `source_locator` line-precise so the verification is narrow.)
- **Filter functions that lie about what they do.** `DR_001` is supposed to mask a zero-sentinel; if it actually drops half the data instead, validate has no oracle for "what should DR_001 do?" — it only checks consistency between contract, function, and stored value. The DECISIONS.md prose is the source of truth for *intent*, and humans verify intent against the function.
- **Data quality issues you didn't think to caveat.** If your data has a hidden ceiling effect that nobody noticed, validate runs green while the analysis is misleading. (Mitigation: `memory/data_quality_caveats.md` and the `caveats` field push you to record these as you find them.)

The framework's job is to make a class of failures **impossible to ship silently**. It doesn't substitute for thinking. It frees you to think about the harder parts — what to measure, how to interpret it, what to caveat — by making "did the number reproduce?" a deterministic question you don't have to ask manually.

### Summary

| Validation question | Layer | When | Speed |
|---|---|---|---|
| Is the schema right? | Structural | Every fast run | <100ms |
| Is the code path real? | Provenance | Every fast run | <100ms |
| Is the data still the same shape? | Data contract | Replay only | depends on file size |
| Is the answer still the same? | Replay | Replay only | depends on function cost |
| Are cross-references intact? | Cross-reference | Every fast run | <500ms |

If you remember nothing else: **`row_count_after_filter` is the highest-value field** in the whole schema. It's what catches silent filter changes, silent data drift, and silent column drops — three of the most common ways analyses go wrong.

## Working with findings

A finding is one entry in `analysis/output/findings.json`. Don't edit that file by hand — use the helper:

```python
from analysis._findings import register_computed, next_id

register_computed(  # runs the function and stamps value, row count, and source hash
    id=next_id(),
    claim="median session rating is 4.2 (n=312)",
    check_type="scalar",
    code_path="analysis/02_profile.py:median_session_rating",
    n=312,
    input={
        "sources": [{"path": "reference/raw-data/sessions.csv"}],
        "columns": ["session_rating"],
    },
    reproducibility={
        "filters": ["DR-001"],
    },
    caveats=["zero_sentinel_masked"],
    counterfactual_tag="OBSERVED",
    measurement_ref="analysis/02_profile.py:median_session_rating",
    reason="initial entry from descriptive profile",
)
```

(`register()` is the lower-level form — you pass `value=` yourself. Prefer
`register_computed()`: it runs `code_path` and stores the *returned* value, so
the number can't drift from the code that produced it.)

The function `median_session_rating` lives in `analysis/02_profile.py` and looks like this:

```python
def median_session_rating(df: pd.DataFrame) -> float:
    """Median of session_rating after filters declared in reproducibility.

    NOTE: this function does NOT apply filters. validate.py applies the
    filters declared in reproducibility.filters before calling.
    """
    return float(df["session_rating"].median())
```

The shape is important: **the function takes a pre-filtered DataFrame and returns a value**. It does *not* know about DR-NNN filters or read the source file. validate.py handles that. Why this split? Because if the function applied its own filters, you couldn't change a filter rule and have the framework catch the drift — the function would just compute the same answer either way.

### `check_type` — pick the right one

| `check_type` | Use when | What `register()` needs |
|---|---|---|
| `scalar` | Single number (count, mean, ratio) | `value=4.2`, `n=312` |
| `proportion` | A ratio specifically (0.0–1.0) | `value=0.32`, `n=312` |
| `rate` | A rate (per unit time, per session, etc.) | `value=4.91`, `n=229` |
| `boolean` | A yes/no assertion | `value=True` |
| `distribution` | A summary distribution (mean+std+quantiles) | `distribution={"mean": ..., "min": ..., "q25": ..., "median": ..., "q75": ..., "max": ...}` |
| `matrix` | A 2D matrix (correlations, confusion) | `matrix=[[1.0, 0.5], [0.5, 1.0]]` |
| `quote_provenance` | A verbatim quote from source data | `quote="..."`, `source_locator="path:Lstart-Lend"` |
| `manual` | Documented but not auto-replayable (heterogeneous structures) | No replay; structural checks only |

When in doubt, pick the most specific type that fits. `manual` is the escape hatch — use it when you can't naturally express the claim as one of the typed shapes, but plan to promote it later as a pattern emerges.

### `counterfactual_tag` — three values, picked carefully

- `OBSERVED` — measured directly. Requires `measurement_ref` (a `path/to/file.py:fn_or_lines` reference). Default for findings computed from data.
- `PLAUSIBLE` — informed estimate. Use when the supporting pattern (commit, finding id, log entry) is named but the specific claim isn't directly measured.
- `WEAK` — vibes. **Never publish a `WEAK`-tagged claim externally.** They exist as a category to mark removal candidates.

See [`COUNTERFACTUAL_TAGGING.md`](COUNTERFACTUAL_TAGGING.md) for the full rules.

### `input` and `reproducibility` — the two most important blocks

A finding declares its data dependency in two blocks: `input` (what the claim
is *about*) and `reproducibility` (how to re-derive it).

```json
"input": {
  "sources": [{"path": "reference/raw-data/sessions.csv", "sha256": "9f86d08..."}],
  "columns": ["session_rating"]
},
"reproducibility": {
  "filters": ["DR-001"],
  "row_count_after_filter": 312
}
```

| Field | What it does |
|---|---|
| `input.sources` | List of `{path, sha256}` input files. `register()` stamps the hash; validate fails if a file's bytes change since the finding was recorded, and all findings on a path must agree on its hash. A replayable finding has exactly one source (multi-source → `manual`). |
| `input.columns` | The columns this finding depends on. Documentary; lock a Pandera schema with `schemas.snapshot()` for real shape/type/range drift detection. |
| `reproducibility.filters` | Ordered list of DR-NNN ids. Each must have a function in `analysis/_decisions.py`. validate.py applies them in order. |
| `reproducibility.row_count_after_filter` | Integer. validate.py computes `len(df)` after applying filters and fails if it doesn't match. **An early-warning system for silent data drift, alongside the source hash.** |

`row_count_after_filter` and `input.sources[].sha256` are the live drift signals. Example: if someone changes a DR-NNN function from "exclude rows where any BPN is zero" to "exclude rows where all BPNs are zero" without updating the documentation, validate.py catches it because the row count after filter changes; and if the raw file itself is swapped, the source hash catches it immediately.

### `caveats` — references to memory entries

```json
"caveats": ["zero_sentinel_masked", "ceiling_effect_present"]
```

Each string is a free-form name. The convention: use it as a key into `memory/data_quality_caveats.md`. validate.py doesn't (yet) check that the names resolve, but it warns if a finding's `caveats` array is empty (since most findings should have at least one — even "n is small" or "self-reported").

## Working with decisions (DR-NNN)

A "decision" (DR-NNN) is a durable cleanup or analysis rule. Examples: "exclude rows where the rating is 0", "drop the first three months as pilot data", "treat gender as Male/Female/null per ethics policy".

### Adding a new DR-NNN

Step 1: Add an entry to `live-docs/DECISIONS.md`:

```markdown
### DR-001

- **Status:** active
- **Rule:** Mask zero-sentinel values in `session_rating` to NaN before aggregation.
- **Why:** `session_rating` uses 0 to mean "not collected". Means/medians silently understated when zeros are included.
- **Implementation:** `analysis/_decisions.py:DR_001`
- **Mandatory:** true
```

Step 2: Add the function to `analysis/_decisions.py`:

```python
import pandas as pd

def DR_001(df: pd.DataFrame) -> pd.DataFrame:
    """Mask zero-sentinel in session_rating (DECISIONS.md DR-001)."""
    return df.assign(session_rating=df["session_rating"].where(df["session_rating"] != 0))
```

Step 3: Reference in `reproducibility.filters` for any finding that depends on it:

```python
reproducibility={
    "filters": ["DR-001"],
    ...
}
```

### Rules for DR-NNN functions

- **Pure**: same input → same output, no side effects
- **Idempotent**: applying twice gives the same result as once
- **Naming**: `DR_NNN(df)` — function name matches the id with hyphens replaced by underscores
- **Document**: every function should have a docstring referencing the DECISIONS.md entry

### Don't delete or rename DR-NNN entries

If a decision is superseded, mark it `superseded` and add a new DR-NNN. If a decision is dropped, mark it `dropped` and explain why. Never delete — the trail is more important than the cleanliness of the file.

## Working with the analysis backlog (A-NNN)

The backlog (`live-docs/ANALYSIS_BACKLOG.md`) captures questions worth investigating. Add an A-NNN whenever an idea emerges — from a finding, a conversation, a brief.

```markdown
### A-001

- **Status:** open
- **Question:** Do session ratings drift over time within a coach-participant pair?
- **Source:** Initial profile suggested non-stationarity in early sessions.
- **Notes:** Requires session_number column; check presence before scoping.
```

Statuses:

- `open` — new, not yet picked up
- `in-progress` — actively being worked
- `done` — answered (link to finding ids in the closing notes)
- `dropped` — abandoned (always say why)
- `superseded` — replaced by a different A-NNN (always link to the replacement)

## Working with memory and caveats

The `memory/` directory is **preconditions Claude reads before doing work**. Different from auto-memory (which Claude writes itself); these are intentional, in-repo, version-controlled.

The most important file is `memory/data_quality_caveats.md`. Whenever you discover a data-quality issue that affects how aggregates should be computed, add it here. Example:

```markdown
### Zero-sentinel in session_rating

- **Rule:** Mask 0 to NaN before mean/median.
- **Why:** 0 means "not collected" in this column, not "absent" — aggregations otherwise silently understate.
- **How to apply:** Use `DR-001` from `analysis/_decisions.py`. Declare in `reproducibility.filters`.
- **Severity:** mandatory
- **Discovery:** F-007 found 26 rows of all-zero records, all with empty qual content; verified as analysis-failure sentinel by audit.
```

Other memory templates:

- `project_overview.md` — what this analysis is for, who reads it, what success looks like
- `analysis_framework.md` — the trust contract restated in this project's context
- `stakeholder_stance.md` — how the data owner / audience views the work; what to emphasise vs soften

You can add more memory files as needed. Keep each focused.

## The live documents

These are the six markdown files in `live-docs/`. They're called "live" because they're amendable peers — meant to be updated continuously, not append-only.

### `TRUST_MEMO.md`

The trust memo is for the human reader. It says, in plain language, what's reliable, what's noisy, and what's unassessable. Cite finding ids (`F-NNN`) for every claim.

Update when: a new finding changes a recommendation, a limitation gets resolved, a caveat changes.

### `DATA_PROFILE.md`

A self-contained, dictionary-aligned profile of every column in every file. Self-contained means: no cross-references to internal documents — this is what you'd send to an external collaborator. Per-column: type, range, null count, treatment, caveats.

Update when: raw data or dictionary changes. Often regenerated from `02_profile.py`.

### `DECISIONS.md`

DR-NNN cleanup decisions. See [Working with decisions](#working-with-decisions-dr-nnn) above.

### `ANALYSIS_BACKLOG.md`

A-NNN questions to investigate. See [Working with the analysis backlog](#working-with-the-analysis-backlog-a-nnn) above.

### `TOOLING.md`

T-NNN tool/library/framework choices. Records what was picked and why. Includes alternatives considered.

```markdown
### T-007 — Observable Plot for visualisation

- **Status:** active
- **Why:** programmatic, AI-friendly, low API surface, escape hatches to D3.
- **Alternatives considered:** D3 (verbose), Plotly (looks generic), Vega-Lite (storytelling ceiling), Recharts (React-bound).
- **Date:** 2026-04-26
```

### `METHODOLOGY_LOG.md`

Narrative record of methodology moments. Discoveries, framework decisions, AI mistakes caught, limitations surfaced. Failures count as much as wins. Use counterfactual tagging (`[OBSERVED]`, `[PLAUSIBLE]`, `[WEAK]`).

This is optional — if you're not preparing a talk or write-up about *how* you did the work, you might not need it. If you are, this log is the source material.

## Hooks: what they do, when they fire

Three hooks ship by default, configured in `.claude/settings.json`. They only fire when Claude Code is the one running commands. They're inert if you're working manually.

### `validate-on-stop.sh`

- **Fires:** at the end of every Claude Code turn (Stop event)
- **Mode:** fast
- **What it does:** runs `python analysis/validate.py --fast`. Fast mode does structural checks only (schema, code paths resolve, no orphan refs in TRUST_MEMO) — no replay. Should complete in under 2 seconds.
- **What happens on failure:** Claude sees the validation output and reports it. Does not hard-block the turn — community evidence shows aggressive Stop-blocking causes premature-end behaviour.

### `block-unvalidated-commit.sh`

- **Fires:** before every Claude Code Bash tool call that contains `git commit` (PreToolUse)
- **Mode:** full
- **What it does:** runs `python analysis/validate.py` (full replay — reads source, applies filters, compares values).
- **What happens on failure:** **the commit is blocked**, with a reason string Claude shows you. You can override by running `git commit` manually outside Claude — that's a deliberate hatch.

### `findings-coverage-on-edit.sh`

- **Fires:** after Edit/Write to any file under `analysis/` (PostToolUse)
- **Mode:** soft
- **What it does:** if you edited a numbered analysis script (e.g., `analysis/02_profile.py`) but `findings.json` hasn't been touched in the last 3 commits, prints a nudge.
- **What happens on failure:** never fails. It's a reminder, not a gate.

### Disabling a hook

If a hook is wrong, fix it or remove it. **Don't add a `--no-verify`-style shortcut.** The right way is to edit `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [],   // disabled
    ...
  }
}
```

This change is visible in git, reviewable in PRs. That's the point.

If Claude is autonomously setting `disableAllHooks: true`, file an issue — the framework should not normalize that.

## `validate.py` — running and extending

### How to run

```bash
# Fast mode — schema + structural checks (~1s). Run frequently.
python analysis/validate.py --fast

# Full mode — fast checks plus replay (reads source, applies filters, compares values).
python analysis/validate.py

# Strict mode — treat warnings as failures. Useful in CI.
python analysis/validate.py --strict
```

### What gets checked (fast mode)

- `findings.json` parses as JSON and is an array of objects (malformed input fails gracefully, never with a traceback)
- Every finding has the required fields (`id`, `claim`, `check_type`, `code_path`, `input`, `reproducibility`, `caveats`, `counterfactual_tag`, `revision_history`)
- Every `id` matches `F-NNN` or `F-NNNa` (alpha suffix optional, for corroborating variants)
- Every `id` is unique
- Every `check_type` is in the valid enum
- The conditional payload is present for the check_type (`value` for scalar/proportion/rate/boolean, non-empty `distribution`, non-empty `matrix`, `quote`+`source_locator`) — so no finding can replay vacuously
- Every `counterfactual_tag` is in `{OBSERVED, PLAUSIBLE, WEAK}`
- Every `OBSERVED` finding has a non-empty `measurement_ref`
- Every `code_path` resolves; replayable check_types must name a runnable function (a line reference can't verify a value)
- Every `caveats` field is a list (warns if empty)
- `input` has a non-empty `sources` list and `columns`; a replayable finding has exactly one source
- `reproducibility` has `filters` (and `row_count_after_filter` for replayable types)
- Any custom `tolerance` is within the cap (abs ≤ 1.0, rel ≤ 0.1) and warns
- Findings sharing a source agree on its `sha256`; unpinned sources warn (and fail under `--strict`)
- Every F-NNN cited in `TRUST_MEMO.md` exists in findings.json (no orphans)
- `revision_history` is non-empty for every finding
- (Warning) If more than 60% of findings are `OBSERVED`, the discipline may be decaying

### What gets checked (full mode adds replay)

If `analysis/output/schema-lock.json` exists, each locked source is re-validated against its Pandera schema (shape/type/range drift). Then, for every finding (except `manual` and `quote_provenance` which have their own paths):

1. Read the single `input.sources[0]`; if its `sha256` is pinned, verify the file still matches (catches mutated/reordered data)
2. Apply `reproducibility.filters` (each is a function in `analysis/_decisions.py`)
3. Verify `len(df) == reproducibility.row_count_after_filter` (catches row-count drift)
4. Import the function at `code_path`
5. Call it with the filtered DataFrame
6. Compare the result to the stored `value` / `distribution` / `matrix`

Float comparison uses `math.isclose(rel_tol=1e-9, abs_tol=1e-6)`. A finding can override this with a `tolerance: {abs, rel}` block (capped at abs ≤ 1.0, rel ≤ 0.1, and surfaced as a warning); for a project-wide change, override `_TOL_ABS` and `_TOL_REL` in your project's `validate.py`.

### Adding project-specific checks

`validate.py` has a hook for project-specific checks at the bottom:

```python
def project_specific_checks(findings: list[dict]) -> None:
    """Override per project. Default: no-op."""
    pass
```

Replace the body with whatever invariants your project cares about. Example:

```python
def project_specific_checks(findings: list[dict]) -> None:
    # Every BPN finding should reference DR-001
    for f in findings:
        if "bpn" in f.get("claim", "").lower():
            if "DR-001" not in f.get("reproducibility", {}).get("filters", []):
                fail("project:bpn_must_use_DR_001",
                     f"{f['id']} mentions BPN but doesn't apply DR-001")
```

Use the `fail(name, msg)` and `warn(name, msg)` helpers from the file. Don't modify the dispatcher logic above the marker — that's framework code; fix bugs upstream and migrate.

## The two tiers: `--minimum` and `--full`

**`--minimum`** is the default. You get:

- CLAUDE.md, README.md, analysis-kit.json, requirements.txt
- `analysis/` (validate.py, _findings.py, _decisions.py, schemas.py, 01/02 scripts, output dir)
- `live-docs/` (six documents)
- `memory/` (four entries)
- `.claude/` (settings + three hooks)
- `reference/raw-data/` (gitignored)

About 25 files. Suitable for any analysis project — small to medium, sprint-style, consultancy work, internal investigations.

**`--full`** adds:

- `_quarto.yml` — Quarto site configuration
- `vignettes/00_template.qmd` — vignette template

Vignettes are HTML/PDF reports for non-technical readers. Use `--full` when:

- You'll produce stakeholder-readable artefacts (memos, reports) and want them generated from data, not hand-written
- You want cross-references between findings and prose
- You want a publication pipeline that can produce HTML and PDF from the same source

If you're not sure, start with `--minimum`. You can always add Quarto later by hand.

## Vignettes — publishing for non-technical readers

(Only relevant for `--full` projects.)

A "vignette" is a self-contained, accessible-language summary of one analytical finding or theme. The template (`vignettes/00_template.qmd`) gives you:

- A title, author, date front matter
- An executive summary at the top
- A plot (Python or R code embedded)
- An "implications" section
- A "caveats" section
- A "follow-up questions" section
- A "reproducibility" footer with finding ids

To render a vignette:

```bash
quarto render vignettes/01_my_topic.qmd
```

This produces both HTML and PDF (configured in `_quarto.yml`). The HTML is `embed-resources: true` by default — single-file, no external assets — so you can email or Slack it without breaking links.

### Vignette discipline

- **Cite finding ids** for every numeric claim. Reviewers can click through to validate.
- **Use counterfactual tags** in prose. "This refactor saved roughly 4 hours [PLAUSIBLE — see commit a13b2c]."
- **Never publish a `WEAK`-tagged claim.** Either measure or rephrase.

## Common workflows (cookbook)

### "I just got new raw data — what do I do?"

1. Drop the file in `reference/raw-data/`.
2. Run `python analysis/01_inspect_raw.py` to print shape, dtypes, nulls, head/tail.
3. Open Claude Code (or your editor) and update `live-docs/DATA_PROFILE.md` with the new column information.
4. Run `python analysis/validate.py` in full mode. **Any finding whose `reproducibility.row_count_after_filter` (or pinned source `sha256`) no longer matches is a real signal** — either the data shape changed unexpectedly, or your filters need updating.
5. If validate fails on row counts: investigate (don't just update the field). Maybe the new data is missing a column you assumed was there. Maybe rows got duplicated. The framework's job is to make this visible.
6. Once you understand the change, update `findings.json` (via `_findings.update()`) with the new values and a `reason` explaining why.

### "I need to ship a memo with stats — what's the discipline?"

1. Every numeric claim in the memo should reference an `F-NNN` id. If a number doesn't have one yet, register it before adding the claim.
2. Run `python analysis/validate.py` (full mode). It must exit 0.
3. Every counterfactual claim ("without X this would have been Y") gets a tag. Use `[OBSERVED]` only if you have a measurement; use `[PLAUSIBLE]` with a named pattern; do not publish `[WEAK]`.
4. Cite the relevant DR-NNN decisions in any methodology section.
5. Cross-reference `TRUST_MEMO.md`'s "noisy" and "unassessable" sections — anything in those is a candidate caveat for the memo.

### "I want to add a new finding — what's the procedure?"

1. Decide the `check_type` (see the [check_type table](#check_type--pick-the-right-one)).
2. Write a function in `analysis/02_profile.py` (or a new `analysis/NN_*.py` file) that takes a filtered DataFrame and returns the value.
3. Decide the `input` (source file(s) + columns) and `reproducibility` (filter DR-NNN ids; the row count is filled in for you).
4. Use `_findings.register_computed()` from a script to add the entry — it runs the function and stamps the value, row count, and source hash. Don't hand-edit `findings.json`.
5. Run `python analysis/validate.py`. The new finding should replay green.

### "I want to update an existing finding"

```python
from analysis._findings import update

update("F-001", reason="recomputed after DR-003 was applied", value=4.31)
```

`update()` appends to `revision_history` automatically. Always pass a `reason` — it lives forever.

### "Validate.py is failing and I don't understand why"

Read the failure messages from the top — the structural failures often cause cascade. Common causes:

- `code_path: not found` — you renamed a function or moved a file. Update `code_path`.
- `value mismatch` — either the data changed, the function changed, or the filter changed. Run the function manually and compare to the stored value.
- `row count X != contract Y` — silent data drift. **This is not a "fix the field" situation.** Investigate the actual data first; only update the contract once you understand why the count changed.
- `OBSERVED requires measurement_ref` — fill in the field, or downgrade the tag to `PLAUSIBLE`.
- `unknown check_type` — typo, or framework version mismatch.

### "I'm preparing for a webinar/talk and need a methodology log"

Add entries to `live-docs/METHODOLOGY_LOG.md` after meaningful methodology moments:

- A discovery cascade (one finding led to a dozen)
- A framework decision (chose tool X over Y, with rationale)
- An AI mistake the human caught
- A limitation surfaced
- A stakeholder communication

Each entry is brief (2–6 sentences) with theme tags and counterfactual tags. The log is the source material — don't try to write the deck directly.

## Counterfactual tagging discipline

Three tags for any claim about "what would have happened without X":

- `[OBSERVED]` — measured. Test: a critic could reproduce this from the repo state. Requires a `measurement_ref` for findings.
- `[PLAUSIBLE]` — informed estimate. Test: the supporting pattern is named (commit, finding id, log entry).
- `[WEAK]` — vibes. Action: rephrase or measure.

Why this matters: agentic AI's reputation for hallucination is the audience's primary objection. Overclaiming the agent's contribution loses credibility faster than underclaiming. The discipline is asymmetric on purpose.

Common failure modes:

1. **OBSERVED becomes the dominant tag.** If >60% of your tags are OBSERVED on an early-stage project, the discipline has decayed. Real analytical work has plenty of plausible inferences.
2. **WEAK never appears.** If you never produce a WEAK claim, you're not noticing the soft ones — they're getting smuggled in as PLAUSIBLE or OBSERVED.

When in doubt, soften.

See [`COUNTERFACTUAL_TAGGING.md`](COUNTERFACTUAL_TAGGING.md) for the full rules.

## Troubleshooting

### "Bootstrap failed: target X exists and is non-empty"

The bootstrap refuses to overwrite a non-empty directory by design. Either delete the target first or pick a different path.

### "validate.py: import of analysis/02_profile.py raised: No module named 'analysis'"

Your `analysis/02_profile.py` does `from analysis._decisions import ...`. validate.py adds the project root to `sys.path` automatically (since v0.1 patch). If you're hitting this, you may have an older copy of `validate.py` — re-scaffold or copy the latest from `templates/analysis/validate.py`.

### "Hook X failed but I don't see why"

Hooks output to stderr. Run them manually:

```bash
echo '{"tool_input":{"command":"git commit -m foo"}}' | .claude/hooks/block-unvalidated-commit.sh
```

You'll see the actual stdout/stderr.

### "validate.py is taking too long"

Full-mode validate scales with the number of findings × cost of replay. If it's >60s, you have several options:

1. Use `--fast` in your hook, full only at commit time. (This is the default.)
2. Split your findings into multiple files (not yet supported; on the roadmap).
3. Cache filter results between findings that share a contract (not yet supported).

### "I changed a filter and now half my findings fail"

Working as designed. The findings stored their value when the filter was different. Decide:

- Was the old filter wrong? Update the findings with `update()` and a `reason`. The old values are preserved in `revision_history`.
- Was the new filter wrong? Revert the filter change.
- Is this a temporary diagnostic? Don't commit; check what you wanted to check; revert.

### "I need to delete a finding"

Don't. Mark it superseded or change its `claim` to "REVOKED — see F-NNN". The revision history is more valuable than tidiness.

### "The agent ignored a memory entry"

Two checks:

1. Is the memory file in `memory/` and indexed in `MEMORY.md`?
2. Did the agent's session start with a fresh context? Memory entries are read at session start. Mid-session changes don't take effect until next session.

If both are yes and it still happened, this is a real failure mode worth recording in `METHODOLOGY_LOG.md`.

## When NOT to use analysis-kit

Be honest about edges. Don't use analysis-kit if:

- **You're doing exploratory data analysis where every claim is provisional.** The framework's overhead pays off when claims will be cited externally. For private exploration, plain Jupyter is fine.
- **Your data fits in a warehouse and your project is BI-shaped.** Use dbt + dbt-mcp instead. analysis-kit is pandas-shaped.
- **You're shipping a model, not a memo.** Use MLflow / Metaflow / similar. analysis-kit is descriptive/explanatory.
- **You're doing genuine notebook-first work** (interactive plotting, narrative-driven). Use Ploomber or Quarto stand-alone.
- **You don't have repeating findings.** A one-off "let's count X" doesn't need a claims ledger.
- **You're working in a regulated environment with formal change-control.** The framework is opinionated about velocity; if you need formal audit trails for every finding revision, build something heavier.

If you'd describe your work as "I run analyses, write memos with numbers in them, and stakeholders cite those numbers" — analysis-kit fits.

## Upgrading the framework

The framework version is pinned in `analysis-kit.json`:

```json
{
  "framework_version": "1.0.0",
  ...
}
```

When the framework releases a new version:

1. Pull analysis-kit (`git pull`).
2. Read the changelog in `docs/PROVENANCE_CONTRACT.md` for breaking changes.
3. If a migration script exists, run it: `python ~/dev/analysis-kit/bootstrap/migrations/0.2_to_0.3.py .`
4. Copy the new `validate.py` if it changed: `cp ~/dev/analysis-kit/templates/analysis/validate.py analysis/validate.py`
5. Update `analysis-kit.json`'s `framework_version`.
6. Run `python analysis/validate.py`. Any failures are the migration's responsibility to surface.

The framework promises: minor version bumps are backwards-compatible (new features, new optional fields, new check_types). Major version bumps may require migration. Migrations always have a script.

## Glossary

- **Agentic AI / agent** — an AI system with the ability to take actions (run code, edit files), not just generate text. Claude Code is one.
- **Bootstrap** — `bootstrap/new-project.sh`. Scaffolds a new project from templates.
- **Caveat carrier** — a memory entry that documents a precondition the agent must consult before doing related work.
- **Claim** — any quantitative or factual assertion ("median X is 4.2", "the data lacks Y"). The unit of trust in analysis-kit.
- **Counterfactual tag** — `OBSERVED` / `PLAUSIBLE` / `WEAK`. Used on any claim about "what would have happened without X".
- **DR-NNN** — Decision Record. A durable cleanup or analysis rule, with a function in `_decisions.py` and a markdown entry in `DECISIONS.md`.
- **A-NNN** — Analysis backlog item. A question worth investigating.
- **T-NNN** — Tooling decision. A library, framework, or tool choice with rationale.
- **F-NNN** — Finding id. The unit identifier in `findings.json`. Optionally suffixed with a letter for corroborating variants (`F-040`, `F-040b`).
- **Replay** — the process where validate.py re-runs every finding's compute function against current data and compares the result.
- **`check_type`** — the kind of value a finding produces (`scalar`, `distribution`, `matrix`, `boolean`, `manual`, etc.). Tells validate how to compare.
- **`input`** — what a finding is about: its source files (`sources: [{path, sha256}]`) and the columns it depends on.
- **`reproducibility`** — how to re-derive a finding: the DR-NNN filters applied and the post-filter row count.
- **Live document** — one of the six markdown files in `live-docs/`. Amendable peers, updated continuously.
- **Manual finding** — a finding whose value is too heterogeneous for typed replay; structural checks apply but no value comparison.
- **Memo** — any stakeholder-facing write-up where you state numbers (a report, summary, message, or PR description). Not generated by the framework — it's your deliverable; every number in it should cite an `F-NNN` finding.
- **Vignette** — a memo in publishable form: a Quarto-rendered report (`vignettes/NN_*.qmd`, `--full` tier) that cites `F-NNN` ids the same way.
- **Tier** — `--minimum` or `--full`. The latter adds Quarto vignettes.
- **Trust contract** — the discipline: every claim has a code path that reproduces it, validate.py is the gate, exit code is the truth.

---

For deeper reading:

- [`PHILOSOPHY.md`](PHILOSOPHY.md) — the principles
- [`PROVENANCE_CONTRACT.md`](PROVENANCE_CONTRACT.md) — the findings.json schema in detail
- [`COUNTERFACTUAL_TAGGING.md`](COUNTERFACTUAL_TAGGING.md) — the tagging rules
- [`HOOKS_GUIDE.md`](HOOKS_GUIDE.md) — hook contracts and failure modes

Found a gap? File an issue or a PR.
