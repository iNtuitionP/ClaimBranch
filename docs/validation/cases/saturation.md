---
kind: validation-case
status: active
owners: maintainers
last_reviewed: 2026-09-21
canonical_for: saturation workflow acceptance criteria
---

# Canonical acceptance case: saturation and operator damage

This anonymized retrospective case is ClaimBranch's finite contract fixture. It
is not a scientific conclusion and cannot establish product value by itself.
Its purpose is to make evidence, reasoning, AI contribution, human authority,
understanding debt, manuscript consequence, replay, and recovery observable in
one bounded episode.

The exact logical schema is in the
[domain model](../../designs/2026-08-03-domain-model.md). The
[validation prototype](../../product/releases/validation-prototype.md) owns the
H0/H1/V0 release gates.

## 1. Truth packet

The redacted fixture contains:

- the pre-result Claim and marked manuscript source;
- one result ArtifactRef and content digest;
- one completed Run and its code/method reference;
- three direct Observations;
- the unaided human interpretation and rationale from the real case;
- one optional discriminating ExperimentPlan;
- one frozen normalized AI Proposal and trace for the recorded variant;
- the expected scientific-edge and impact closure;
- the exact before/after marked block and compile configuration; and
- deterministic clocks, IDs, entropy, signing key, rule/schema versions, and
  compiler fingerprint for replay.

Private source artifacts remain outside version control. The committed truth
packet uses redacted substitutions with a local-only manifest connecting them
to the real episode.

The repository now commits a partial P0 source fixture—deliberately not the
complete F0 truth packet specified above—through its [integrity
manifest](../../../tests/fixtures/saturation/truth-packet/manifest.json) and
validates it with:

```powershell
python scripts/check_truth_packet.py
python -m unittest discover -s tests/validation -p "test_*.py" -v
```

This executable source fixture freezes the bounded P0 source facts, cross-file
references, expected impact, marked before/after text, offline frozen proposal,
and blank V0 baseline. It is a validation fixture rather than an implemented
product import schema. It does not yet freeze the optional ExperimentPlan, the
proposal trace manifest, deterministic replay clocks/entropy/signing inputs,
the compiler fingerprint, or the expected compile-output digest. These
implementation-dependent F0 inputs are frozen at P1 exit, after the schema,
authority, and toolchain decisions; they are not prerequisites for entering P1.
P0 still requires the private human-confirmed mapping to the real episode and
source-level manuscript/compile evidence, which the repository checker cannot
prove. Passing this checker alone therefore cannot close P0. The
[scope-lock gate](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#scope-lock-gate)
owns the complete P0 exit criteria.

Private-source verification remains unchecked and mandatory before any real
research use, including real workspace writes, adoption, manuscript edits, or
a real-use pilot. It no longer blocks explicitly synthetic development; the
[release gate](../../product/releases/validation-prototype.md#11-development-and-real-use-gates)
keeps the unchanged P1/H0 safety and trust requirements separate. Augmented
synthetic cases below do not change this source fixture or assert private-case
fidelity.

## 2. Initial accepted state

### Claim C-01

    Saturation-based sensitivity determines the damage caused by pruning,
    quantization, and compression.

Initial branch-local status:

    lifecycle = active
    scientific_maturity = supported

The working expectation is:

| Operator | Expected result |
|---|---|
| Pruning | saturated path has greater damage |
| Quantization | saturated path has greater damage |
| Compression | saturated path has greater damage |

### Marked manuscript block A-01

The F0 fixture has exactly one source file and one marker pair:

    % claimbranch:start id=anchor-central-claim
    Across pruning, quantization, and compression, saturation-based
    sensitivity determines operator damage.
    % claimbranch:end id=anchor-central-claim

Its initial file hash, marker identity, exact text, surrounding fingerprint,
compile argument vector, compiler fingerprint, and expected output digest are
part of the truth packet.

## 3. Accepted evidence

One completed Run R-01 references the result artifact and produces:

| Observation | Operator | Expected? | Reviewed relationship to C-01 |
|---|---|---:|---|
| O-01 | Pruning | no | challenges |
| O-02 | Quantization | no | challenges |
| O-03 | Compression | yes | qualifies/supports under the compression condition |

Each Observation becomes accepted only through its own human-confirmed
EvidenceEvent. The artifact, Run, Observations, and events are global and
append-only. The reasoning branch cannot copy, hide, edit, or delete them.

The relationship records retain rationale and scope. Rendering only three
colored lines without the pruning, quantization, and compression conditions is
an acceptance failure.

## 4. One competing interpretation

The episode creates one non-nested branch named
joint-distortion-sensitivity and one Interpretation I-01:

> Sensitivity is real but insufficient by itself. Operator damage also depends
> on the magnitude, direction, structure, correlation, and ranking effect of
> the operator-induced logit distortion.

The interpretation references all three Observations at the episode's evidence
watermark. It may challenge or qualify the scope of C-01.

“Jointly determined” is a conceptual factorization. ClaimBranch must not
serialize, display, or teach it as a proven multiplicative equation. Existing
controlled-noise evidence, if shown as context, can support only the sensitivity
component and cannot create an additional accepted record in F0.

The optional ExperimentPlan EP-01 asks for the smallest discriminating test
between distortion magnitude and rank-preserving explanations. It has one tests
edge to C-01 and one human rationale. The broader historical list of possible
experiments remains context, not six F0 plan records.

## 5. Expected impact and selected merge

The deterministic impact closure contains:

- C-01 and its branch-local contested status;
- I-01 and its Observation references;
- the three reviewed scientific relationships;
- EP-01 when present;
- one Decision and SelectedMerge;
- A-01; and
- one ManuscriptDebt.

The single selected merge from the branch into main adopts:

    [x] C-01 becomes contested
    [x] the reviewed challenge/qualification relationships
    [x] I-01 as the selected competing interpretation
    [x] EP-01 when present
    [x] one manuscript debt for A-01
    [ ] any stronger replacement central claim
    [ ] any unreviewed manuscript wording

No second Claim exists in F0. A stronger joint-distortion Claim may remain in
the original case notes or Proposal, but accepting it requires a later contract.

The merge is one explicit dependency-closed copy, not a general three-way merge.
It records source, target, expected heads, selected IDs, closure IDs, evidence
watermark, omissions, and the human rationale. The source branch remains
addressable.

## 6. Human decision and understanding

The high-impact review asks at most three context-specific questions selected
from:

- Which scope of C-01 is challenged?
- Why does compression support not erase the pruning and quantization mismatch?
- Which part of I-01 is supported and which part remains an interpretation?
- What result would distinguish magnitude from ranking explanations?
- What exact manuscript sentence must change?

The sealed ReviewBundle includes the exact operation, heads, evidence watermark,
impact, Contributions, rationale, answer or deferral, and manuscript state.

Allowed outcomes:

- answer, authorize, and store the human Decision;
- edit the operation/rationale, reseal, and authorize;
- choose Not now, leaving accepted state unchanged; or
- authorize the exact merge while deferring explanation review, atomically
  opening one UnderstandingDebt.

AI may suggest a question or point out inconsistency. It cannot grade the
answer, issue the receipt, perform the merge, or close the debt. The recorded
variant later requires a separate exact human closure.

## 7. Manuscript consequence

The one PatchIntent proposes wording that preserves the observed mixed result
without asserting the unproven factorization. The truth packet freezes the
exact replacement digest; one acceptable semantic form is:

    Across the tested operators, saturation-based sensitivity alone did not
    determine damage: pruning and quantization challenged the expected pattern,
    while compression remained consistent with it.

The researcher sees the exact source diff, marker, expected file hash, plain-
language consequence, compile plan, and affected ManuscriptDebt before
authorizing patch work.

Visible phases remain distinct:

    selected reasoning accepted
      -> manuscript debt open
      -> patch prepared
      -> applied but unverified
      -> compiling
      -> verified or exact restore/recovery required
      -> separate human manuscript-debt closure

Only a closure receipt bound to the exact debt, PatchIntent, PatchAttempt,
source/output/compiler digests, graph head, and non-restored saga state may
close the debt.

## 8. Two H0 histories

### H0-manual

- contains no Proposal, ExecutionTraceManifest, AI Contribution, or
  UnderstandingDebt;
- makes zero provider and network calls;
- completes the entire accepted and manuscript path through human input; and
- replays to its own full-audit golden.

### H0-recorded

- starts with exactly one frozen root Proposal and one trace manifest;
- makes zero live provider and network calls;
- retains the Proposal through human edits and selected materialization;
- records ordered AI and human Contributions;
- opens and later human-closes exactly one UnderstandingDebt; and
- replays to a different full-audit golden.

Comparing these audit manifests for equality is a failure because it would erase
the provenance difference. A separate scientific-state projection may be
compared only with documented exclusions.

## 9. Failure and denial oracles

The case fails if any of these occur:

- a reasoning branch hides accepted evidence;
- an evidence record is edited rather than superseded or invalidated;
- a free-form or out-of-contract edge/record/operation is accepted;
- an AI/model process confirms evidence or gains accepted-store, human-export,
  signing-key, receipt, merge, patch, or debt-closure authority;
- a caller-supplied human actor value changes authorization;
- Not now changes accepted state;
- high-impact deferral accepts without opening UnderstandingDebt;
- AI influence disappears after a human edit;
- the selected merge has a dangling or implicit dependency;
- projection deletion changes the accepted manifest;
- remote-capable egress occurs without an exact matching preview digest;
- untrusted imported history becomes local accepted authority;
- graph acceptance is displayed as manuscript verification;
- stale, forged, replayed, or cross-project closure succeeds;
- patch failure loses or overwrites manuscript bytes;
- exact state cannot be proved but normal mutation remains available; or
- H0 replay calls a live provider.

Crash and concurrency fixtures cover every accepted append, journal, snapshot,
temporary write, replace/flush, compile, finalization, cleanup, and restore
boundary plus external edits, competing writers, supersession, missing key, and
disk full.

## 10. Operator experience oracle

The primary-workspace contract adds these observable cases to the existing
foundation and H1 checks. They test interaction behavior, not scientific truth
or live-study timing:

| Case | Pass condition | Failure |
|---|---|---|
| Start before deciding, AI off | source evidence and the existing claim open the manual path; the researcher forms an interpretation inside it | a final interpretation, external completed log, or AI Proposal is required at entry |
| Review an entered judgment | the same episode context and human rationale are available for inspection/editing | the researcher must rewrite unchanged meaning into a second journal or retrospective form |
| Context changes during review | changed evidence, meaning, selection, or manuscript state invalidates the applicable authorization | reused text silently reuses consent or accepts stale scope |
| Defer and return | the episode shows what was decided and what remains open, with the existing distinct Not now and debt-opening paths | the researcher must reconstruct the situation from raw audit events or AI silently closes debt |
| Inspect without an audit dump | situation, evidence basis, decision, and manuscript consequence are legible; detailed provenance is available on demand | internal IDs, provider traces, or a mandatory Notion record are needed to understand the decision |
| Initialize and reopen private research | dry-run shows separate paper/workspace locations without writing; initialization defaults outside Git; reopening finds the same accepted history | private records enter a Git tree by default, or moving the paper silently creates replacement history |

The [private-workspace decision](../../architecture/decisions/0008-private-research-workspaces.md)
also requires tests for resolved path aliases, source unavailability, export
ownership, and verified restore. These are future product tests, not claims
that the current source-fixture checker proves storage safety.

The user reviews whether the proposed context and questions are sufficient
before H1 surface implementation. AI cannot certify human understanding from
these tests. A known-answer demonstration remains distinct from prospective use.

The disposable demo renders the same lineage without a provider, LaTeX
installation, browser requirement, or real-project write:

    3 confirmed observations -> 1 interpretation -> 1 contested claim
      -> 1 selected merge -> 1 marked manuscript consequence

It labels any frozen AI text Not accepted, verifies the manifest, and states
that the user's project and manuscript were not changed.

From the declared clean-checkout state, bootstrap, doctor, and demo complete in
at most 300 seconds wall time and 90 seconds active time across three cold
trials. The demo takes at most 60 seconds after bootstrap. The full
compiler-installed H0 case has a separate ten-minute budget.

Before V0, an unfamiliar supported-Windows researcher must complete the
documented demo, project dry run, one manual episode, deferred-review resume,
and recovery inspection without coaching or internal storage edits.

### 10.1 Early read-only graph inspection

The executable [graph walkthrough](../../development/workflow.md#read-only-graph-walkthrough)
exposes a smaller, synthetic inspection path before the full demo above.
It checks two challenge relationships and one compression-qualified
relationship, each with its condition and original rationale; main and
candidate retain identical observations. Its five computed differences are
the claim status, existing fixture interpretation, and three relationships.
Selection is explicit and empty by default. Preview retains omissions,
references existing dependencies, rejects missing dependencies, and follows
only displayed links toward the manuscript anchor. It creates no accepted
state, manuscript debt, approval, or manuscript edit.

`tests/contract/test_graph_demo.py` covers these projection and subprocess
contracts. The views are not real refs; interpretation-to-observation paths
are references, not new scientific inference. Passing this suite does not
implement SelectedMerge, validate the original private research, establish
user comprehension, or meet the full demo's time and onboarding gates.

## 11. Prospective use

The saturation fixture is retrospective and known-answer. V0 applies the same
finite shape and authority rules to the first three qualifying unexpected
result episodes on the next real paper. Scientific content may differ; the
episode must still fit the closed record and manuscript bounds or count as
out-of-F0.

The [validation prototype](../../product/releases/validation-prototype.md)
defines eligibility, baseline, timing, replacement limits, recorded fields, and
the ordered outcome rule. Its first-pass comparison design requires user
approval before prospective use: the committed baseline's instruction to
finish Markdown first is historical, not the primary-workspace workflow.
This retrospective fixture cannot establish first-pass timing. It also cannot
be cited as market evidence or as
proof that ClaimBranch prevented an omission.

## 12. Augmented synthetic contract oracles

These five hypothetical scenarios extend test coverage only. They are not
new facts about the original saturation episode, additional accepted F0
records, or scientific findings. The fixture is
[augmented-cases.json](../../../tests/fixtures/saturation/augmented-cases.json); contract and disposable-store
tests live in `tests/contract/test_augmented_cases.py` and
`tests/probes/test_augmented_storage.py`. The original truth-packet files and
integrity manifest remain unchanged.

| Hypothetical case | Observable pass condition |
|---|---|
| Observation correction | a new immutable synthetic revision supersedes the old value without deleting or mutating it; reasoning drafts do not own evidence; the earlier evidence-bound review is stale |
| Competing interpretations | two model proposals coexist as unaccepted alternatives; neither rewrites the draft nor selects, merges, or accepts the other |
| Compression-only support | a proposal asserting general support remains unaccepted; model confirmation is denied through the generic proposal-only boundary, irrespective of persuasive wording |
| Review basis changes | changing the evidence snapshot or manuscript anchor/content hash invalidates the old review even when draft text and rationale are unchanged |
| Storage crash and retry | actual subprocess exits immediately before and after SQLite commit leave either no judgment or the exact completed judgment; reopening and identical retry leave exactly one record, and changed retries cannot overwrite it |

The compression case tests authority, not an automated inference that decides
which scientific claims the observations entail. Synthetic observation
revisions and review digests are non-authoritative reference values, not
human-confirmed evidence or consent receipts. Manuscript target versions are
caller-supplied; the model neither reads files nor detects external edits.
The storage case uses disposable
roots and tests process termination, not power-loss durability, OS isolation,
or manuscript-saga recovery. Passing these cases alone cannot satisfy P0, P1,
H0, or a real-use gate. Execution steps and actual results belong in the
[active plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#augmented-synthetic-contract-cases).

## 13. Provider authority and support oracle

These planned product checks implement
[ADR 0009](../../architecture/decisions/0009-external-inference-and-local-authority.md).
They are not capabilities established by the current helper or source fixture.

| Case | Observable pass condition |
|---|---|
| AI off or provider lost | the same episode, rationale, review, and manual path remain usable; no provider request or duplicate explanation is required |
| Compatible but unverified server | compatibility is reported separately from protection; live protected use remains unavailable, with manual continuation and no accepted change |
| Same-user server behind an isolated connector | direct file/approval-channel access is tested from the actual server context; connector denial alone cannot earn a supported verdict |
| Separately hosted or isolated server | verify no accepted-store/key/manuscript write route through mounts, credentials, IPC, or exposed APIs; topology names alone cannot pass |
| Hostile provider output | commands, forged human labels, approval fields, oversized/malformed responses, and markup cannot authorize or execute writes; accepted state stays unchanged |
| Changed outbound destination or content | prior consent is invalidated before transmission; localhost is not local-only without external-network denial evidence |
| Cancelled, stale, late, or repeated response | no automatic adoption, tool execution, debt closure, or duplicate accepted operation occurs; any later human review uses current state |
| Exact human authorization | broker independently reloads the sealed review; cancellation, expiry, replay, changed scope, and direct model-originated requests fail without mutation |

H0 exercises offline/manual and frozen malicious inputs. H1 additionally needs
observed actual-runtime topology and egress evidence. A pure synthetic receipt
or binding test cannot close the foreground-presence, key-custody, IPC, or
durability gate. Execution order and test ownership belong to the active plan.
