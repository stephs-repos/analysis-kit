# Synthetic fixture

Tiny dataset used by self-tests. Properties are deterministic so checks can replay against known values.

`sessions.csv`:
- 10 rows, 4 columns.
- `session_rating` includes one zero-sentinel (S006) used to test the DR-001 masking pattern.
- After masking S006: n=9, mean=4.17, median=4.0.
- Without masking: n=10, mean=3.75, median=4.0.

The difference between masked and unmasked aggregates is what makes this fixture useful — it lets tests verify that `reproducibility.filters` is actually applied during replay.
