# Build graph for an analysis-kit project.
#
# The load-bearing rule: `render` depends on `validate`, so a vignette/memo can
# never be built off a red ledger. The pipeline AUTOMATES THE DERIVATION
# (compute -> validate -> render) but NOT THE JUDGMENT: refreshing findings.json
# values is a deliberate human step (`make findings`, then review the git diff),
# precisely so data drift surfaces to a person instead of being silently
# overwritten with a new "truth". See docs/REBUILD_PIPELINE.md in analysis-kit.

PY ?= python3
export PYTHONPATH := $(CURDIR)

.PHONY: help findings validate validate-fast report render all clean

help:
	@echo "make findings       run analysis/NN_*.py -> refresh findings.json (then REVIEW THE DIFF)"
	@echo "make validate       full replay; non-zero exit on any drift"
	@echo "make validate-fast  structural checks only (~1s, no replay, no data needed)"
	@echo "make report         regenerate analysis/output/report.html (status + drift view)"
	@echo "make render         render vignettes (full tier; gated on validate)"
	@echo "make all            validate + render"
	@echo "make clean          remove Quarto caches"

# Human-driven: run after a data refresh, then `git diff analysis/output/findings.json`
# and bless the value changes before committing. Runs each numbered analysis step
# in sequence. The `analysis/[0-9][0-9]_*.py` guard is so an empty match (a project
# with no numbered scripts yet) is a clean no-op rather than an error.
findings:
	@for s in analysis/[0-9][0-9]_*.py; do [ -e "$$s" ] || continue; echo "→ $$s"; $(PY) "$$s"; done

validate:
	$(PY) analysis/validate.py

validate-fast:
	$(PY) analysis/validate.py --fast

# A human-facing STATUS VIEW, not a gate: it re-runs the checks in-process and
# writes a self-contained analysis/output/report.html — per finding, what it's
# built from, its trust status, and what's out of sync (with plain-English fixes).
# Deliberately NOT gated on `validate` (unlike `render`): its whole job is to
# surface drift, so it must render even on a red ledger. The output is a derived
# view (gitignored) — regenerate to trust it. `--artifact PATH` emits a body-only
# fragment for publishing as a shareable Artifact.
report:
	$(PY) analysis/report.py

# render CANNOT run unless validate is green (the prerequisite enforces it).
# It clears the Quarto freeze cache first: `freeze: auto` re-executes a chunk only
# when the .qmd SOURCE changes, so without clearing it a render after a data
# refresh serves stale cached numbers (there is no `--no-freeze` flag). On the
# --minimum tier there is no _quarto.yml, so this is a clean no-op.
render: validate
	@if [ -f _quarto.yml ]; then \
	  rm -rf _freeze vignettes/_freeze .quarto; \
	  quarto render --to html; \
	else \
	  echo "no _quarto.yml (minimum tier) — nothing to render"; \
	fi

all: validate render

clean:
	rm -rf _freeze vignettes/_freeze .quarto vignettes/.quarto
