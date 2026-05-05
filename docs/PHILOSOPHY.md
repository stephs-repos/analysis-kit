# Philosophy

## The bet

Agentic data analysis fails in production not because models are bad at code, but because they're confidently wrong about claims. They invent statistics, misread units, ignore caveats, and report aggregates over uncleaned data. The fix is not better prompts or smarter validators — it's making **claims first-class objects** that a deterministic harness can replay.

analysis-kit is built on the bet that *constraining the agent's improvisational surface* produces more trustworthy work than *expanding the agent's capabilities*.

## Five tenets

### 1. Exit code is the trust contract

`validate.py` exits 0 or non-zero. There is no third option. No "warning". No "soft block". An LLM-generated trust score is not a substitute for a deterministic check. If the check is wrong, fix the check; don't downgrade it.

### 2. Every claim has provenance

A claim with no F-NNN id, no `code_path`, no `data_contract`, and no `counterfactual_tag` is not a claim — it's a vibe. The claims ledger (`findings.json`) is the unit of trust, not the prose around it. Memos cite ids; vignettes cite ids; PR descriptions cite ids.

### 3. Caveats travel with the data, not with the human

Data quality issues (zero sentinels, scale mismatches, ceiling effects, masked rows) are preconditions the operator must satisfy *before* aggregating. They live in `memory/` so the agent reads them at session start, and in `findings.json` so checks can verify they were applied. A caveat that lives only in a human's head is a caveat that will be ignored.

### 4. Templates declare shape, projects fill content

The framework ships skeletons with `{{MUST_CUSTOMIZE}}` tokens. Bootstrap refuses to scaffold if any tokens remain unfilled. This stops the failure mode where an LLM completes a template with generic placeholder text that passes structural checks but says nothing.

### 5. Counterfactual claims must be defensible

Every claim about model behaviour, agent contribution, or "what would have happened without X" gets tagged `[OBSERVED]`, `[PLAUSIBLE]`, or `[WEAK]`. `OBSERVED` requires a `measurement_ref`. The system is designed assuming AI's reputation for hallucination — overclaiming the agent's contribution loses the audience. When in doubt, soften.

## What we delegate to other tools

- Schema/column validation → **Pandera**
- Vignette publishing → **Quarto**
- Optional exploration UI → **Datasette**
- Data versioning → **DVC** (opt-in)
- Warehouse-resident projects → **dbt + dbt-mcp**
- Project structure conventions → **Cookiecutter Data Science** layout

We don't reimplement these. Where analysis-kit fits is the layer above: claims, caveats, replay, and agent-shaped guardrails.

## What we deliberately don't do

- **No subagent swarms by default.** Community evidence is they're mostly demoware in analytics; expensive failure mode is research-subagent hallucinations being trusted by the main agent. Add subagents per-project when there's a clearly-bounded read-heavy task.
- **No MCP-first integration by default.** Pandas-in-script wins for analytical correctness because it produces auditable artefacts. MCP earns its keep for databases and docs, nothing else.
- **No hallucination scoring (THS, semantic entropy).** The claims ledger + replay harness is the deterministic version of the same idea.
- **No "validator agent checks executor agent".** If the validator hallucinates, you have no recourse. Use deterministic checks.

## How to know if the framework is working

Six months into a project:

- `findings.json` has 50+ entries, all replay green.
- TRUST_MEMO.md cites finding IDs that exist in findings.json (no orphans).
- Memory entries have been amended at least once each.
- No entries in git log show `--no-verify`.
- A new analyst can reproduce any cited claim by running `python analysis/validate.py`.

Six months in, if those things are not true, the framework is not working — investigate before adding features.
