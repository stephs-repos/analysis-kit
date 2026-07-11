# Quickstart

Two things to do, one command to remember. Claude Code guides the rest.

> **The one idea:** analysis-kit's unit of trust is the **finding** — a number a
> machine can re-derive from your raw data on demand. You drive and decide;
> Claude drafts; a validator replays every number so it can't silently drift.

## 1. Add your files

- **Raw data** (CSV/Excel/Parquet) → `reference/raw-data/`
- **Project context** (brief, data dictionary, prior art — anything that says
  what the project is *for*) → `reference/` directly

The context files matter: Claude drafts your project's framing *from* them.
Without a brief or dictionary it can only write generic filler.

## 2. Open Claude Code and type `/akit-next`

```
cd <project> && claude
```

then:

```
/akit-next
```

That's the whole interface. `/akit-next` reads the project's actual state,
tells you where you are, and offers the single next step — then stops at every
decision that's yours to make. Type it again whenever a step completes, when
you're unsure, or when you come back after a break. It never loses your place,
because it recomputes it from the project each time.

*(The workflow skills ship inside this project at `.claude/skills/`, so
`/akit-next` works for anyone who clones it — no install. If it isn't
recognized, check you opened Claude Code at the project root; for an older
scaffold without embedded skills, install them globally once:
`bash <analysis-kit>/bootstrap/install-skills.sh`.)*

## What it will walk you through

These phases, one step at a time — you approve each; nothing is decided for you:

1. **Fill the scaffold** — `/akit-fill` drafts the six `MUST_CUSTOMIZE`
   placeholders from your reference materials (`memory/project_overview.md`
   first — it's the source the others distill from); you accept/edit/skip
   each one.
2. **Inspect the data** — read shape, dtypes, and nulls together; quirks that
   need cleanup become named `DR-NNN` decision rules you approve.
3. **Register findings** — for each claim, `/akit-finding "<one-line
   hypothesis>"` drafts the code, provenance, and caveats; the value is
   computed by running the code, never typed in.
4. **Validate and commit** — `validate.py` replays every finding from raw
   data; the commit hook blocks anything red.

From there you're in the steady-state loop: new claim → `/akit-finding`; new
cleanup rule → tell Claude; a status overview (every finding, its lineage, and
anything out of sync) → `make report`; unsure → `/akit-next`.

## The four rules that keep you honest

1. Every quantitative claim has an `F-NNN` that replays from raw data.
2. Don't hand-type numbers into memos/vignettes — cite the finding.
3. Don't aggregate a column before applying its relevant `DR-NNN` filter.
4. Don't bypass the validator — a red `validate.py` means stop, not ship.

Need a specific command later? [`CHEAT_SHEET.md`](CHEAT_SHEET.md) is the
task → command lookup. More depth: `CLAUDE.md` (this project's discipline),
and in analysis-kit `docs/USER_GUIDE.md` and `docs/CONCEPTS.md`.
