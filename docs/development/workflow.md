---
kind: development
status: active
owners: maintainers
last_reviewed: 2026-08-03
canonical_for: repository-local validation commands and documentation enforcement
---

# Repository checks

There is no application build or test stack yet. Documentation validation
requires Python 3.10 or newer; CI currently uses Python 3.13.

From the repository root, run:

```powershell
python scripts/check_docs.py
```

The checker validates repository-owned Markdown links and headings, required
agent instruction files, canonical-document front matter and location, nearest
index membership, overall reachability, ADR shape/status index parity, and
ExecPlan shape.

GitHub Actions runs the same command on every push and pull request. Repository
administrators must configure the `Documentation / check` status as a required
branch-protection check for CI failure to block merges. Without that external
setting, the workflow reports violations but cannot by itself prevent a merge.

Agent instructions guide semantic maintenance; static checks cannot prove that
prose matches code or user intent. Review affected canonical documents in the
same change and update `last_reviewed` only after checking their inputs.

When an implementation stack is selected, add reproducible setup, build, test,
lint, fixture, release, and troubleshooting commands to this area in the same
change. Do not store personal shell aliases or machine-specific paths here.
