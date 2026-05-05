# Counterfactual tagging

Every claim about model behaviour, agent contribution, or "what would have happened without X" must carry one of three tags. The tags are part of `findings.json` and appear in prose (memos, vignettes, methodology logs).

## The three tags

### `[OBSERVED]`

Measured directly. **Requires `measurement_ref`** — a path:line citation to the code or script that produced the measurement.

Test: a critic could reproduce this from the repo state.

Examples:
- "Median session rating is 4.2" with `measurement_ref: analysis/02_profile.py:L120-L145`.
- "Validate.py exits 0 in 22 of 22 cases" with `measurement_ref: tests/test_validate.py`.

### `[PLAUSIBLE]`

Informed estimate. The supporting pattern is named (commit, finding ID, log entry, prior literature) but the specific claim was not measured directly.

Test: the supporting pattern is named, and a reader could verify the inference is reasonable.

Examples:
- "Without the caveat carrier, the agent would have reported the un-masked mean (≈3.1 instead of 4.2)" — supporting pattern: `F-007` shows the un-masked aggregate when DR-001 is not applied.
- "The agent saved ~30 minutes of cleanup time on this analysis" — supporting pattern: prior similar analyses logged in METHODOLOGY_LOG took 35–45 minutes; this one logged 5–15.

### `[WEAK]`

Vibes. No supporting pattern, no measurement.

Action: rephrase to remove the claim, or downgrade what's being asserted, or do the measurement and re-tag.

Never publish a `[WEAK]`-tagged claim externally. They exist as a category to **mark removal candidates**, not to flag soft claims as acceptable.

## Where tags appear

- In `findings.json`, every finding has `counterfactual_tag: OBSERVED | PLAUSIBLE | WEAK`.
- In prose (memos, vignettes, methodology log entries), claims about agent behaviour or savings are inline-tagged: `"This refactor saved roughly 4 hours [PLAUSIBLE — see commit a13b2c]."`
- In webinar / talk content, the tags should appear in slide notes if not on the slide itself.

## Why this exists

Agentic AI's reputation for hallucination is the audience's primary objection. Overclaiming the agent's contribution loses credibility faster than underclaiming. The tagging discipline is asymmetric on purpose: the cost of an exaggerated `OBSERVED` is much higher than the cost of a soft `PLAUSIBLE`.

## Common failure modes

1. **OBSERVED becomes the dominant tag.** If >60% of your tags are OBSERVED on an early-stage project, the discipline has decayed. Real analytical work has plenty of plausible inferences.
2. **WEAK never appears.** If you never produce a WEAK claim, you're not noticing the soft ones — they're getting smuggled in as PLAUSIBLE or OBSERVED.
3. **`measurement_ref` points to a non-existent line.** Validate.py checks the file exists; it does not check the line range is meaningful. Reviewers should spot-check.
4. **The pattern named for PLAUSIBLE is hand-wavy.** "Best practice" is not a pattern. "Commit a13b2c" is a pattern. "F-007" is a pattern.

## When in doubt, soften

If you can't decide between OBSERVED and PLAUSIBLE, choose PLAUSIBLE. Between PLAUSIBLE and WEAK, choose WEAK and then either measure or rephrase.
