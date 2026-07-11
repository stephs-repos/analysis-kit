# Contributing to analysis-kit

Thanks for your interest. analysis-kit is **scaffolding** — the code here is
copied into new projects and then runs independently, so changes ripple out to
every future project. That makes small, well-tested, deliberate changes the norm.

## Development setup

```bash
git clone https://github.com/stephs-repos/analysis-kit
cd analysis-kit
pip install -e ".[dev]"     # pytest, pandas, pandera, numpy, openpyxl
pytest tests/ -q            # ~130 tests; must be green
```

CI runs `pytest tests/ -q` on Python **3.11, 3.12, and 3.13** — please make sure
all three would pass (the code targets 3.11+ syntax).

## How the repo is laid out

| Path | What it is |
|---|---|
| `templates/` | The scaffold copied into every new project — **this is the framework**. `templates/analysis/*.py` (esp. `validate.py`, `_findings.py`, `_provenance.py`, `report.py`) is the trust machinery. |
| `bootstrap/` | Project creation + skill install + the marker scanner (shell). |
| `skills/` | The `/akit-*` Claude Code skills. |
| `docs/` | Concepts, the provenance contract, philosophy, guides. |
| `tests/` | Pytest suite that scaffolds throwaway projects and exercises the machinery end-to-end. |

## The rules that keep the framework trustworthy

- **Fix it here, not downstream.** A created project is told *never* to edit its
  own `validate.py` core dispatcher — "fix it upstream and migrate." You are
  upstream. Framework changes belong in `templates/`.
- **Every behavior change ships with a test.** The suite scaffolds a real project
  (`scaffolded_project` fixture) and drives the CLI; add cases there.
- **Keep template code deterministic.** Replay compares floats to a tight
  tolerance, so nondeterminism (unseeded randomness, dict-order reliance, unpinned
  numeric behavior) turns findings red for no real reason.
- **Never write the literal scaffold marker in a shipped file.** The string
  `{{` + `MUST_CUSTOMIZE` is what `bootstrap/check-must-customize.sh` greps for;
  `test_bootstrap.py` asserts an exact marker count. If code needs that sentinel
  (e.g. a guard), build it by concatenation so the contiguous literal never
  appears in source. (Yes, this has bitten us.)
- **Schema changes are a contract change.** If you alter the `findings.json`
  shape, update the changelog in [`docs/PROVENANCE_CONTRACT.md`](docs/PROVENANCE_CONTRACT.md)
  and bump `framework_version`.

## Submitting a change

1. Branch from `main`; keep the change focused (one logical thing).
2. `pytest tests/ -q` green locally; run the **whole** suite, not just the file
   you touched (`test_bootstrap.py` guards marker counts and scaffold integrity).
3. Open a PR describing the *why*; CI must pass on all three Python versions.
4. For anything touching `validate.py`'s guarantees, say in the PR how you
   verified it can't false-green or spuriously fail.

## Reporting bugs / ideas

Open an issue with a minimal reproduction (a tiny scaffolded project + the
command that misbehaves is ideal). Security issues → see [`SECURITY.md`](SECURITY.md),
report privately. Conduct → [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
