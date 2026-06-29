# Quickstart

From an empty scaffold to your first verified, committed finding — entirely
through conversation with Claude Code. Budget ~20 minutes.

> **The one idea:** analysis-kit's unit of trust is the **finding** — a number a
> machine can re-derive from your raw data on demand. You drive and decide;
> Claude drafts; a validator replays every number so it can't silently drift.

## Before you start

- You've scaffolded a project (via `/akit-start` or `bootstrap/new-project.sh`).
- The skills are installed. If you scaffolded with `/akit-start`, they are. If
  not, install them once: `bash <analysis-kit>/bootstrap/install-skills.sh`.
- Open Claude Code in the project directory: `cd <project> && claude`.
- **Lost at any point? Type `/akit-next`** — it detects where you are and tells
  you the single next step. It's the safety net for everything below.

---

## 1. Drop in your data and context

Two different places — the split matters:

- **Raw data files** (CSV/Excel/Parquet) → `reference/raw-data/`
- **Project context** (brief, data dictionary, prior art, scope note) →
  `reference/` directly (*not* inside `raw-data/`)

Why context matters: the next step drafts your project's text *from* these
materials. With no brief or dictionary, Claude would write generic filler —
exactly what the scaffold's markers exist to prevent.

## 2. Fill the placeholders — `/akit-fill`

```
/akit-fill
```

Claude scans every `{{MUST_CUSTOMIZE}}` marker (project goal, data caveats, data
profile, stakeholder stance, …), reads your reference materials, and for **each**
marker drafts content and shows it to you. For each one you **accept / edit /
skip**.

- Don't batch-accept. This text propagates into every downstream decision.
- If `reference/` has no real context yet, Claude will stop and ask for it.

Done when no markers remain (Claude confirms; or check yourself:
`grep -rlE '\{\{MUST_CUSTOMIZE' .` returns nothing).

## 3. Inspect the data

Ask Claude:

```
inspect the raw data
```

(or run `python analysis/01_inspect_raw.py`). Read the shape, dtypes, and null
counts together. This is where the data's quirks surface — zero-sentinels,
status codes, weird columns, sparse fields.

## 4. Record cleanup decisions as they emerge (`DR-NNN`)

When you spot a quirk that must be cleaned *before* aggregating, say so:

```
that's a decision — exclude the DNF/DNS rows before any finisher count
```

Claude writes a pure `DR_NNN(df)` filter in `analysis/_decisions.py`, documents
it in `live-docs/DECISIONS.md`, and notes a caveat in `memory/`. Findings cite
these by id, so the cleanup becomes part of the reproducible recipe. You don't
pre-plan them — they emerge from the data, and you approve each one.

## 5. Register your first finding — `/akit-finding`

Give it a one-line hypothesis:

```
/akit-finding "median field size is ~108 finishers per race after excluding non-finishers"
```

Claude drafts the whole record — the compute function, the `input` +
`reproducibility` blocks (source file, columns, which `DR-NNN` filters), the
caveats, and a counterfactual tag (`OBSERVED` / `PLAUSIBLE` / `WEAK`) — shows you
the proposed JSON, and asks you to confirm. The value is **computed by running
the code**, so the stored number can't be divorced from what produced it.

Repeat this for every claim worth keeping. It's the workhorse of the whole
workflow.

## 6. Verify — `validate.py`

```
run validate
```

(`python analysis/validate.py`). Exit 0 means **every** finding re-derived from
the raw data and matched its stored value. This also runs automatically when
Claude finishes a turn (fast check) and — in full — before any commit.

## 7. Commit

```
commit this
```

The commit hook re-runs the full replay first and **blocks the commit if
anything is red**. (Claude will branch first if you're on the default branch.)

## 8. Communicate *(full tier only)*

```
make render
```

Rebuilds your vignettes from the verified findings (gated on `validate`). Any
number you state in a vignette or memo must cite an `F-NNN` — state it *via* the
finding, never hand-typed.

---

## Then: repeat

You're in the steady-state loop. Each new claim → `/akit-finding`. Each new
cleanup rule → tell Claude. Keep the live-docs current. Forgotten where you are?
`/akit-next`.

## Command cheat-sheet

| You want to… | Do this |
|---|---|
| Find out the next step | `/akit-next` |
| Fill the scaffold placeholders | `/akit-fill` |
| Inspect the raw data | "inspect the raw data" |
| Record a cleanup rule | tell Claude (becomes a `DR-NNN`) |
| Register a claim | `/akit-finding "<hypothesis>"` |
| Verify everything replays | `python analysis/validate.py` |
| Rebuild vignettes *(full)* | `make render` |
| See the skill index | `/akit` |

## The four rules that keep you honest

1. Every quantitative claim has an `F-NNN` that replays from raw data.
2. Don't hand-type numbers into memos/vignettes — cite the finding.
3. Don't aggregate a column before applying its relevant `DR-NNN` filter.
4. Don't bypass the validator — a red `validate.py` means stop, not ship.

More depth: `CLAUDE.md` (the project's discipline), and in analysis-kit
`docs/USER_GUIDE.md`, `docs/CONCEPTS.md`, `docs/PHILOSOPHY.md`.
