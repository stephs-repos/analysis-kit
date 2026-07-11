# Security

## The trust model — read this before running someone else's project

analysis-kit's validator is **not a sandbox**. `analysis/validate.py` works by
**importing and executing** a project's own Python — the `code_path` functions it
cites and `analysis/_decisions.py` — in order to *replay* each finding from its
declared data. Running `validate.py` (or the commit hook, or `make findings`) on a
project therefore runs that project's code with your privileges.

This is intentional and unavoidable: replaying a claim means re-running the code
that produced it. It's the same trust you extend to any repository with executable
code — `pip install`, a `Makefile`, a test suite. The containment guard only stops
`code_path`/quote sources from pointing **outside** the project directory; it does
**not** and cannot restrain what in-project code does (filesystem, network, etc.).

**Practical guidance:**

- Treat cloning-and-validating an untrusted analysis-kit project exactly like
  cloning and running any untrusted repo. Read the `analysis/*.py` before you run
  it, or run it in a container/VM you don't mind exposing.
- **CI:** the shipped workflow runs `validate.py` on `pull_request` (unprivileged,
  read-only token, no secrets) — correct for running fork PR code. Do **not**
  switch it to `pull_request_target`, and if your project fetches raw data in CI,
  don't expose write-scoped credentials to the validate job.

## What a green ledger does — and does not — mean

A passing `validate.py` proves each stored value **is what its `code_path` produces
from the pinned data**. It does **not** prove the code computes what the claim
says: a function that ignores its input and returns a constant replays green.
`register_computed()` mitigates this at authoring time, but `findings.json` can be
hand-edited. Trust a green ledger on a project you authored or reviewed; otherwise,
read the code. (More in [`docs/CONCEPTS.md`](docs/CONCEPTS.md) → "What it deliberately is *not*".)

## Supported versions

analysis-kit is scaffolding: a created project has **no runtime dependency** on
this repo, so there are no patched artifacts to pull. Fixes land on `main` and are
adopted by deliberately re-copying updated templates. The current framework schema
version is pinned in each project's `analysis-kit.json` (`framework_version`).

| Version | Supported |
|---|---|
| latest `main` | ✅ |
| older tags | best-effort |

## Reporting a vulnerability

Please report suspected vulnerabilities **privately**, not via a public issue:

- Preferred: GitHub → the repo's **Security** tab → **Report a vulnerability**
  (private advisory).
- Or contact the maintainer (**@stephs-repos**).

Include a description, affected files, and a reproduction if possible. We'll
acknowledge within a reasonable window and coordinate a fix and disclosure.
