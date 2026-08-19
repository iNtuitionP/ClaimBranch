---
kind: development
status: active
owners: maintainers
last_reviewed: 2026-08-20
canonical_for: repository-local validation commands and documentation enforcement
---

# Repository checks

There is no application build or test stack yet. Documentation validation and
the repository-owned Notion journal helper require Python 3.10 or newer; CI
currently uses Python 3.13.

From the repository root, run:

```powershell
python scripts/check_docs.py
```

Validate the committed partial P0 saturation source fixture and its adversarial
contract suite without network access or third-party packages:

```powershell
python scripts/check_truth_packet.py
python -m unittest discover -s tests/validation -p "test_*.py" -v
```

The first command verifies the closed artifact inventory, SHA-256 digests,
cross-file references, expected impact truth set, manuscript markers, blank
baseline, offline frozen proposal, size limits, and privacy guards. The second
command exercises both the valid packet and malformed, tampered, traversal,
link, leakage, and semantic-mismatch cases. A skipped link test on Windows
means the current account could not create a symbolic link; Linux CI exercises
that case.

Run the local-first Notion journal helper suite without contacting Notion:

```powershell
python -m unittest discover -s tests/notion_journal -p "test_*.py" -v
```

This suite uses temporary Git repositories and injected temporary state roots.
It must not use the contributor's real `LOCALAPPDATA` journal state or require
OAuth.

Validate the repository-scoped Notion journal skills:

```powershell
python -m unittest discover -s tests/skills -p "test_*.py" -v
```

This suite verifies skill discovery metadata, invocation policy, documentation
links, platform-safe encoding, adversarial safety contracts, and the record
skill's deterministic query/create/update projection. It is offline and uses
only injected temporary journal state.

The documentation checker validates repository-owned Markdown links and
headings, required agent instruction files, canonical-document front matter
and location, nearest index membership, overall reachability, ADR shape/status
index parity, and ExecPlan shape.

GitHub Actions runs the documentation, source-fixture, validation, and skill
checks on every push and pull request. The source-fixture suite runs on both
Ubuntu and Windows so Windows junction rejection is exercised continuously.
Repository administrators must configure both `Documentation / check` and
`Documentation / windows-validation` as required branch-protection checks for
CI failure to block merges. Without that external setting, the workflow
reports violations but cannot by itself prevent a merge.

Agent instructions guide semantic maintenance; static checks cannot prove that
prose matches code or user intent. Review affected canonical documents in the
same change and update `last_reviewed` only after checking their inputs.

When an application implementation stack is selected, add reproducible setup,
build, test, lint, fixture, release, and troubleshooting commands to this area
in the same change. Do not store personal shell aliases or machine-specific
paths here.
