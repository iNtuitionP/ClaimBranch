---
kind: validation-case
status: active
owners: maintainers
last_reviewed: 2026-10-16
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

The [interactive synthetic Episode Review](../../development/workflow.md#interactive-synthetic-episode-review)
now exercises undecided entry, manual and offline-AI judgment, selected closure,
human rationale reuse, contribution history and a manuscript-text candidate.
Application and local-session checks live in `tests/application/`; bounded
egress checks live in `tests/security/test_context_egress.py`. The optional real
Chrome smoke covers both desktop and narrow layouts. All results remain
unverified candidates: no native receipt, accepted append, actual manuscript
write/compile, durable restart or real-source eligibility is implied. These
checks cover part of the operator oracle below, not H0/H1 or research value.
In a plan-only selection, the omitted interpretation must not appear as a
manuscript replacement: the original bytes remain, and any conditional
manuscript work is labeled impact review. A wording candidate requires both a
selected interpretation and its selected dependency path to the anchor.

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

The bounded synthetic return-service check reopens an existing conditional
understanding item in its own project. It must retain the causal judgment,
AI/human contributions and original argument while showing current main and
corrected global evidence separately. An evidence-only correction changes the
return fingerprint even when main has not moved; episode closure or a later
merge must not resolve or replace the item. Replay restores the same context,
and each item in a multi-episode example must return its own causal view.
Two individually bounded views must remain readable together without truncating
their scientific content. Mutating a returned object cannot rewrite history. Unknown, cross-project,
manuscript and unsupported-history requests fail without mutation. This checks
readable context reconstruction only: no accepted debt, closure, artifact
verification, durable explanation draft or human comprehension is established.

The separate synthetic explanation-draft exercise selects at most three topics
bound to that item's causal claims, observations, interpretations, selected
unrun experiments or manuscript consequence. An omitted experiment must not
appear as a selected follow-up topic. The researcher can reference their existing
reason and leave partial text, including empty input, without another narrative.
Leaving/cancelling and reconstructing the candidate draft preserves its text,
reason reference, topic identity and source AI. A changed observation with the
same reasoning head leaves the draft's earlier basis visible until an explicit
current-context rebind; editing alone cannot silently refresh it. A stale rebind,
different project/item/cause/topic, unknown version or invalid snapshot fails
without changing live work. Required scientific content remains nonblank.
Serialized draft reconstruction is not protected restart evidence, a completed
answer, understanding debt creation/closure or proof of comprehension.

The separate proportional-policy exercise keeps an unfinished AI-influenced
draft quiet and reuses the completed reason for a medium-impact alternative
record. A high-impact selected merge binds one to three contextual topics only
when source or included amendment lineage carries AI. A manual edit, new manual
episode or disabled provider cannot erase inherited influence; an omitted new
AI amendment does not taint unrelated selected manual work. Required amendments
do contribute origin. An existing alternative cannot be bypassed by preparing
its record from main. Exact source revisions and Contribution chains survive
candidate round trip; broken/oversized/unknown-version lineages fail without
replacing the prior value. Human answers can explicitly reuse the existing
rationale. Empty unreferenced answers, wrong topic identities, changed scope,
origin or same-head evidence, and caller-modified policy labels invalidate
review. Not now creates no debt; deferral reports only a conditional opening.
This API exercise does not connect typed AI adoption, persist provenance, change
old replay semantics or authorize an accepted operation.

The exact-operation exercise carries that assessment into a versioned
record/merge request. Its effects contain only selected/required changes and
the actual source-plus-draft Judgment. Source contributions, amendment revisions,
topic answers/reused rationale and conditional deferral survive round trip.
Capture, Not now and a record without its matching Interpretation cannot seal.
Changed same-head evidence, lineage, manuscript, session, current review scope,
expiry, reused IDs and altered values fail before returning a candidate.
Not now, changed explanation and replacement seals revoke earlier candidacy;
invalid replacement input preserves the current valid seal.
Loading an intact older review leaves newer work current; loading bytes cannot
register their embedded origins. Individually valid sources exceeding the total
envelope limit fail without truncation. Legacy readers reject the new format.
Candidates still require authorization and leave history, debts and manuscript
unchanged. These checks do not prove trusted accepted-source loading, native
presence, file fidelity, persistence or atomic debt/receipt consumption.

The conditional commit exercise retains the full exact review while forecasting
reasoning heads and debt openings together. First/existing alternative records
leave main unchanged and open no debt. A merge retains its manuscript obligation;
explicit deferral also retains an exact-cause understanding obligation, including
when AI entered only an amendment. Answering through explicit reason reuse
retains the original topic references and adds no understanding obligation.
Changed debt kind/cause/topics, omitted obligations, changed heads, noncanonical
bytes, authority claims and unknown fields are refused on rederivation. A fresh
owner or changed selection cannot restore a current seal by loading the envelope.
Repeated calculation is byte-identical and leaves source history unchanged.
All openings remain conditional with zero accepted writes/debts; this is no proof
of native receipts, accepted replay or transaction durability.

The record-transition exercise replays only the exact reviewed interpretation
and required changes, creating the first alternative when necessary. Main,
global evidence and original owner history stay unchanged; the result preserves
full review, commands, before/after digests and the complete origin registry.
Amendment-only AI still requires contextual explanation or deferral at the next
merge, even when the judgment has only human contributions. Omitted origins stay
available without becoming recorded changes. Changed source/session/file, expiry,
unowned seals and coordinated command/digest forgery refuse continuation. A fresh
process reconstructs byte-identical candidate science from independent sources
only after explicit new assessment/seal preparation; restoration alone grants no
seal. Merge translation is refused. Zero accepted writes/debts and no persistence
or receipt are claimed. These cases are in
`tests/application/test_paper_record_transition.py`.
The seal also prechecks the complete transition budget and fixes its full origin
snapshot. Post-seal omitted-draft edits remain in current work without changing
retry bytes. Bound continuation checks the entire transition and independently
held before/after histories; missing or substituted AI origins fail even when
their outer envelope hashes are recomputed. It requires the original review
digest retained independently from that bundle: recomputing the registry and
review hashes together must also fail against that expectation. This verifies
integrity, not native authority or arbitrary caller-supplied expectations.
Bare legacy-source reopening is
unverified and cannot establish absent AI influence for this transition.

The encrypted unaccepted-work exercise saves the existing history, independent
origin registry, Judgment, exact review and partial explanation to a private
external checkpoint. A fresh process with the correct key reconstructs the
same scientific source, AI/human contributions and unfinished writing; a saved
review cannot become the fresh owner's current seal even before expiry. An
empty own-paper checkpoint invents no observation. Unknown versions, changed
project/cause, missing independent origins, malformed provenance, wrong keys,
corruption, symlinks/hardlinks/special files, public modes and competing sessions
fail without overwriting prior work. Killing the writer before/after replacement
restores the complete previous/new checkpoint. A failed post-replace directory
flush must report uncertainty and require reopen. No saved/staging file contains
known plaintext. The same store instance must recover after close/reopen;
reserved private staging files are reclaimed after lock acquisition without
deleting unrelated, linked or public files. A Mac full-sync failure before
replacement preserves the prior checkpoint without fallback. This establishes synthetic process-restart persistence, not
power-loss certification, product key custody, TUI integration, accepted debts,
trusted backups or replacement-device authority.

The source-preview work-command exercise must save a bundled candidate paper,
exit and inspect identical argument/provenance/conditional work in a fresh
process, verify its recovery key before create-only encrypted export, and
restore to a new destination without changing source bytes or resuming consent.
Run the journey from an extracted artifact as well as the checkout. Terminal
key generation requires exact hidden confirmation; absent terminal, cancellation,
malformed/oversized stdin and native failure must not expose secrets or claim
success. Existing, linked, public, oversized or truncated backup files refuse;
interrupted copies remain distinguishable from a completed export and retry
never overwrites them. A locked device failure is not permission to substitute
a software device key or skip native coverage. This exercise is independent of
TUI retention, accepted-state custody and actual replacement-device evidence.

The device-key checkpoint exercise creates an actual Secure Enclave
key-agreement identity and atomically saves wrapped-key material with encrypted
work. A fresh process reopens the same records without receiving a raw data key.
Neither plaintext data key nor recovery key appears in saved bytes. Wrong
project, either corrupted wrap/header/MAC, unknown versions and missing or
unavailable device access fail without silently recreating keys or choosing
recovery. A separate recovery-key action verifies the source, rewraps it to a
fresh device identity in a new destination and retains the original. Existing
destinations and interrupted publication cannot overwrite source work. Restored
key material spliced with the source's work ciphertext must fail authentication.
An explicitly supplied recovery secret can be checked while making a backup;
an absent secret cannot be reported as possession or a tested restore. Restored
AI provenance and unaccepted authority remain unchanged. These same-host tests
do not certify replacement hardware, native human presence or approval-key
enrollment; data-key opening cannot sign or consume a research authorization.

The versioned synthetic closure exercise supplies an explicit sealed deferred
cause separately from conditional work. Preparation and final candidate recheck
must both reject a changed cause review even with the same debt ID, or changed
evidence with the same main head. Project/episode, topic rules/set, displayed
context, operation, session and seal/expiry remain bound. Wrong debt kind/status,
manual or already-answered causes, modified sealed values, noncanonical bytes
and unknown versions fail. An intact but expired historical cause can support a
new live closure review; its former authorization is never reused. A cumulative
candidate example keeps partial explanation through an evidence correction and
stale closure refusal; explicitly rebinding the draft still cannot reuse the
old closure review. Returned values remain authority-unverified, leave the
original debt/history open and do not discharge manuscript work. These checks
prove supplied-value consistency, not protected source loading, receipt
consumption, persistence or human comprehension.

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
| Explain why the argument changed | the existing episode view connects the three observations and their conditions to the changed claim scope, selected interpretation, recorded human reason and affected sentence; interpretation remains distinguishable from observation | a changed status or graph alone hides the reason, or the UI presents the conceptual factorization as established evidence |
| Inspect AI influence after editing | the edited suggestion, its AI origin, human changes and selected disposition remain inspectable alongside the judgment | editing erases AI influence, or the researcher must reconstruct it from a chat transcript |
| Inspect the episode argument graph | selecting a node reveals its source and named relationships; two challenges and one qualification stay distinct; the next experiment is visibly an unrun plan; omitted changes remain excluded | a plan appears as supporting evidence, hidden changes look selected, stale edits keep a current-looking drawing, or loading an example overwrites a draft |
| Initialize and reopen private research | dry-run shows separate paper/workspace locations without writing; initialization defaults outside Git; reopening finds the same accepted history | private records enter a Git tree by default, or moving the paper silently creates replacement history |

The [private-workspace decision](../../architecture/decisions/0008-private-research-workspaces.md)
also requires tests for resolved path aliases, source unavailability, export
ownership, and verified restore. These are future product tests, not claims
that the current source-fixture checker proves storage safety.

The [synthetic association adapter](../../development/workflow.md#paper-and-work-association)
now exercises a bounded part of private initialization/return. Its preview must
leave paper and workspace untouched; a new paper has a thesis and no invented
evidence. Saving binds exactly the displayed source and workspace. After moving
the paper, old work remains readable; only explicit matching-source relocation
updates its association. Changed bytes, a replaced destination or a linked source
must fail without replacing prior work. Backup recovery preserves the embedded
history, AI contributions and unfinished writing even when the old paper is
missing, and restores no approval. Old readers reject the new format. These
cases in `tests/application/test_project_work.py` are backend evidence, not the
complete accepted-history, own-project UI or real-device operator oracle above.

The separate preparation tests in `tests/application/test_project_initialization.py`
require exact initial thesis/location display, zero evidence/operations/episodes,
and unchanged manuscript/workspace. Changed source/destination, changed session,
expired/replaced review, coordinated thesis/hash forgery and imported
commands/evidence/receipts must refuse. Restoring bytes can only compare against
a still-owned seal. A failed re-preparation revokes the prior seal. Results keep
the exact reviewed destination beside the candidate even if two destinations
would produce identical scientific work. Candidate calculation remains
repeatable, without receipt consumption. This is empty-candidate review evidence, not native accepted
genesis, receipt consumption or a protected canonical store.

The source-refresh extension in `tests/application/test_project_source_refresh.py`
requires an explicit exact earlier-project/new-source comparison before saving
changed bytes at the same paper/file/anchor. Retain all old association snapshots
and nested work byte-for-byte. Changed source, workspace, writing or checkpoint
after comparison refuses save; replacement failure preserves the last good file.
Encrypted restart/restore retains both source versions, contribution history and
historical reviews without current approval. Same-byte moves remain distinct
from source edits, and moving plus editing cannot silently match another paper.
Unknown/altered transitions, version downgrade and the existing snapshot/byte
bounds must fail without deleting history. Association refresh does not close
manuscript work, confirm scientific consistency or update an old review's inputs.

These interaction oracles operationalize the
[intended researcher outcome](../../product/product-spec.md#1-product-definition).
Observe them in the existing research/review flow; do not add a second
explanation form, comprehension score or AI-graded test. They establish what
the product makes inspectable, not what a researcher internally understands.

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

Before V0, an unfamiliar researcher on the supported target must complete the
documented demo, project dry run, one manual episode, deferred-review resume,
and recovery inspection without coaching or internal storage edits.

The [Mac runtime preflight](../../development/workflow.md#source-built-mac-runtime-preflight)
checks a narrower source-delivery prerequisite: a source artifact without tests
or repository scripts can explicitly build native role identities and inspect
them in a fresh process against the original retained pin. Altered binaries,
manifest replacement, role swaps, unknown schema/authority fields, missing or
linked files and incomplete builds must fail without overwriting existing work.
A passing check must still report protected acceptance unavailable, and ordinary
doctor must never trigger compilation or native authentication. The adapter's
self-identity result cannot substitute for the existing actual peer, foreground
human, accepted-state, key-custody or replacement-device oracles.

The synthetic review-delivery connection additionally requires mutual running
peer checks before sending review bytes, exact full-input matching with a fresh
exchange nonce, bounded pipe/socket I/O and cleanup. Wrong code/role, an ordinary
same-user caller, changed review or previous nonce must fail. Reopening from the
source-only artifact must work without repository scripts. The application must
recheck owned scientific scope and current context/expiry after transport; stale
work cannot report successful current delivery. Even success creates no key,
receipt, accepted operation, debt or manuscript write and keeps protected
acceptance unavailable. Caller-held build pins are not enrolled trust.

The separate synthetic key-preparation API must preview one project, exact
source-built roles and a fresh private destination before invoking a foreground
new-key review. Changed bindings and existing files fail before authentication.
Only explicit native authentication may create the new device-bound signing
candidate. Cancellation, expiry and late/duplicate callbacks cannot report
prepared or authorize research; distinguish app-review and native-authentication
cancellation. Preserve incomplete reservations rather than overwriting them.
After an observed successful preparation, a new process must verify the retained
registration pin, signed request and public identity, reconstruct the same
device key, and observe noninteractive signing denial. A valid software-key
self-signature with fake device representation must fail. Wrong project/build,
modified/linked/non-private records, missing keys and stale destinations must
not modify existing material. This prepares an unaccepted registration only;
actual foreground observations and the worker/custody/enrollment gates remain
distinct from automated lifecycle and parser tests.

Native local enrollment must remain independent of candidate/imported files.
Resolve its registry from the OS user record, mint a separate local resource
identity, and publish only after foreground confirmation and a fresh device
signature. A caller project name, copied record, self-signature or supplied
peer hash cannot stand in for enrollment. Both peers must independently reload
the same registered code/key/resource before signing, and recheck afterward.
Different directory identity, rebuilt code, changed key, unknown schema,
revocation, symlink/hardlink or non-private files must fail closed. Interrupted
prepublication work stays inert; postpublication interruption is explicitly
indeterminate until inspected, with no blind replacement or success claim.
Check actual registry/key/resource read, write-open, listing, create and rename
denial with positive controls and unchanged protected bytes. Per-attempt random
canaries cannot overwrite or delete a preexisting file. Exercise native
enrollment, restart, registered signing, cancellation and revocation separately
from parser/file tests. These are synthetic component observations; B03 atomic
acceptance, real provider protection and P0 remain separate gates.

The native serializer must match portable nested object-key ordering and exact
Unicode/control/slash bytes, including source-built worker manifest keys.
Absolute native paths must fit the generated binding schema while relative and
NUL-containing values fail. An idle polling slice must not shorten the displayed
review deadline or renew it. Show instructions before opening participation
windows, and distinguish actual OS authentication cancellation from review-window
cancellation. Revocation must deny fresh-process lookup/signing while preserving
the enrollment entry, key and protected binding.

The exact-review signing connection must reuse the same judgment, rationale,
selection, contributions and explanation disposition in its native review.
Only explicit foreground authentication may sign the complete project/key/
runtime/review/nonce-bound packet. Both native peers check running code identity,
and the gateway verifies the signature privately. No signature or reusable
receipt may reach application stdout, ordinary files or a caller-facing result.
Tampering, prior-exchange replay, expired review, wrong peer and software-key
substitution fail; cancellation and failed peers leave key/research bytes
unchanged and close their channel. Current application science, manuscript and
session bindings are rechecked after a signed result. A changed context must not
report current success; cancellation/expiry retains its terminal reason even
when that context also expires. These synthetic observations still cannot authorize
accepted science or close debt without the separate enrollment/custody/store
gates. Actual review approval and native authentication cancellation are human
observations, not inferred from software signature tests.

The origin-bound v2 record review must retain its complete registry commitment
in the exact signed packet. Python rejects malformed closed reviews or mismatched
canonical digests before reading key fields. Native parsing rejects extra/missing
top-level fields, unknown versions, invalid registry digests and v2 merge actions.
Changing the registry commitment and recomputing packet hashes cannot reuse the
original signature. Exercise both compiled peers with a missing key without
opening a foreground window, alongside native software-key signature verification.
These are parser/transport/integrity checks, not OS presence or accepted source
authentication. Keep v1 compatibility and enrolled framing; report actual v2
foreground approval/cancellation separately.

Empty-project attestation must reuse the entered title/thesis and exact source/
workspace association. Python requires the original owned current initial review
and rechecks the association/session/time before and after signing, plus current
native enrollment. Both Python and native refuse an unenrolled initial review.
Native requires a closed empty v3 seed, distinct thesis/anchor IDs, derived root,
zero evidence/operations and matching source anchor; nonempty/imported history
and authority fields cannot be added. In an explicitly synthetic enrolled parser
fixture, a valid initial signature verifies while changed thesis/root/association
cannot reuse it. Malformed fields refuse even with recomputed packet hashes.
Compiled peers separately deny absent native bindings before opening a
window; this is not a valid-enrollment parsing or OS-presence observation. Display
the enrolled target and escape newlines/control characters in paths. Actual
initial signing/cancellation, authoritative accepted-history loading and accepted
genesis publication remain separate requirements. Compile the production native
filesystem helper against disposable associations and refuse changed/replaced
bytes, links/special files, substituted Git administration paths, nested Git,
non-private/replaced workspaces, either containment direction, and workspace
ancestors in separate worktrees/bare repositories. Valid Unicode filename/root
associations retain exact bytes. A blocked repository-local Git include must
reach its bounded timeout and leave no FIFO reader. Check the complete initial
request with the actual helper in the software-signature fixture, preserving
legacy signing. Source assembly/artifact checks must include the new helper
and reject missing/linked/oversized resources. These tests do not observe native
presence, validate enrollment creation or prove atomic filesystem races.
The native initial route also requires its independently loaded enrolled target
to remain binding-only. Actual synthetic file tests refuse an existing genesis,
log, pending/foreign file, directory or dangling link; missing/changed/bad-mode/
linked/special binding; replaced or linked target; changed directory identity
or privacy mode; and state appearing between separate checks. Exact safe reserved
diagnostic scratch is preserved; unsafe scratch refuses. A complete software
initial-request fixture checks the real target helper against a synthetic holder;
it does not validate native enrollment creation. Preserve legacy review signing
and signed-only final checks; report actual initial cancellation separately.
No file is reserved or created by this precondition, and it proves no atomic
check/write exclusion or accepted genesis publication.
These candidate checks create
no project record, receipt or debt.

The source-built proposal worker must accept only the bounded existing response
format, preserve the original response trace and require an already-dispatched
request before proposal completion. Unknown tool/authority fields, duplicate
keys, broader entitlements, changed code/source, wrong pins and linked/incomplete
bundles must fail. Cancellation or an unavailable worker cannot change accepted
science or block manual judgment. Claim the first arrival before a slow check;
failure/cancellation retains that response's trace and consumes its request.
Concurrent or subsequent different-byte responses cannot replace it. A new
attempt requires fresh reviewed dispatch. Verify real OS denial against parent-owned
synthetic research/key/manuscript placeholders and live private/network listeners,
with positive controls and unchanged bytes. Exercise the same component from a
source artifact without repository scripts/tests and across process restart.
Retained OS-managed worker-container content is untrusted; it cannot be accepted
history or a trust root. These checks confine that actual component, not an
arbitrary external model server, and do not close enrolled custody on their own.

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

### Folded two-entry graph oracles (planned)

Owner-selected 2026-10-15 follow-up. Owned checks now cover folded projection,
root/control navigation, typed/status inspection and in-session writing return.
Owned checks also cover direct revision/source preservation, selected AI prefill,
validated private presentation return and large-paper rendering. Final suite
evidence belongs to the existing plan; unfamiliar-user comprehension remains
unverified, and no synthetic check establishes live scientific usefulness.
Use the large synthetic fixture specified by the
[implementation plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#foldable-two-entry-graph-implementation-plan).

1. Open `1`: recognize thesis and major claims from content-first titles. Expand
   a claim one level, inspect original wording/conditions and collapse explicitly.
   Focus/hover emphasis alone does not change group state or scientific links;
   explicit activation expands.
2. Open `2`: choose a completed experiment with multiple observations. Expand
   observations and their direct claim uses, then higher argument paths. Select
   an observation directly as another entry. An empty experiment and unrun plan
   honestly show no recorded results; neither blocks the chooser or invents data.
3. Switch `1`/`2` and back: restore root, folds, viewport and unfinished Korean
   writing in their owning context. Follow an outside connection and return to
   the original lens, not an unexplained thesis reset. Reopen retains validated
   saved presentation/writing without restoring reviews or consent.
4. A shared observation retains one source identity across groups. Distinct
   record counts, internal/boundary typed edge counts and parallel relationships
   match the source; cycles terminate. Indirect reach never appears as direct
   support. All edge labels/directions agree with the same closed vocabulary.
5. With a challenge and mandatory companion folded or filtered away, their
   indicators still lead to exact sources. Correct an observation and inspect
   all reached claims/declared anchors across folds. Structural reach never
   presents a truth score. Status and scientific relation labels stay distinct.
6. From each lens edit node title/content/kind-specific data and valid edge
   type/endpoints/rationale in the TUI. Invalid endpoints or unsafe kind changes
   preserve input and refuse acceptance. Exact comparison precedes recording;
   cancellation/stale context leaves state unchanged. Evidence corrections and
   accepted edits preserve originals and origin; notes are a separate feature.
7. Repeat with AI disabled and with an owned synthetic AI proposal. Selected
   fields remain editable, rejected changes never apply, and human revision
   retains AI origin. Fresh open/backup/restore/readable export preserve the
   recorded semantics. Folding never changes the exact AI outbound scope.
8. At 144x42, 120x32 and 80x24, controls, full titles and relation definitions
   remain reachable without color. Record large/near-capacity timings and memory
   against predeclared host-specific bounds; measure task comprehension separately.

Additional regression cases from plan cross-review: open `2` on an
experiment-only branch; inspect an observation's producing experiment and
registered anchors; edit in `2`, switch `1` -> `2` and reopen after a path/root
changes; inspect opposite-direction parallel edges and an indirect challenge
hop; convert a kind with attached edges and explicitly choose valid re-links.
Unknown authored kinds/types must fail before any append, while unsupported
imported source remains inspectable as unresolved. Corrupt/missing UI sidecars
reset only presentation. Review every recorded title edit through the same
content-edit path; no semantic-change detector is assumed.

### 10.2 Paper argument workspace oracles

These are required future checks for the
[PG-1 through PG-5 product requirements](../../product/product-spec.md#7-interaction-and-visual-character),
not claims about the current optional eight-node graph. ADR 0011 admits this
workspace during current development. The original saturation truth packet
and both original goldens remain regression inputs.

Use a separately identified synthetic paper example with a thesis, multiple
main claims, at least one subclaim path and one direct-evidence path, shared
evidence, a completed experiment and an unrun follow-up. Define the subject,
conditions, metric or categorical outcome, baseline and source for each result.
This is fixture coverage, not a frozen schema or cardinality extension. Review
and version the extended model before treating it as persistent product data.
Do not add invented damage metrics to the redacted original, which currently
provides categories rather than a measurement definition.

Implemented data-level coverage now uses the separately classified
[paper example](../../../tests/fixtures/paper-argument/manual.json) and its
recorded-AI counterpart. `test_paper_history`, `test_paper_replay` and
`test_paper_service` cover shared evidence, explicit measurement context,
optional/multiple structural parents, scientific/structural cycle rejection,
finite bounds, conflicting statuses, exact replay/review and stale/cross-context
assumptions. Scenarios preserve every candidate history byte and cannot create
accepted evidence. These are portable service tests, not passes of the visual,
accessibility, durable-resume or human-understanding oracles below.

For the next integration review, run these actions as one continuous paper
episode, with manual and recorded-AI variants over the same scientific inputs.
The researcher starts undecided, inspects a changed result and its impact,
forms a judgment once, chooses or postpones the exact change, and later resumes
the same context. Add protected acceptance, real restart and manuscript
verification/recovery only when their actual prerequisites pass. Separate
component passes do not count as a completed journey.

With AI disabled, start from a human-defined thesis and create a main claim,
subclaim, interpretation, unrun experiment plan and typed relation with chosen
endpoints/rationale through the application. Require no hand-edited JSON or
model proposal. Inspect the resulting graph and exact review without accepting
it. A draft remains unaccepted; invalid endpoints/directions fail without source
mutation. Record/confirm an observation through its evidence path and verify that
free-form authoring cannot mark an invented result as confirmed evidence. These
are required authoring oracles, not claims that the current existing-node TUI
editor already satisfies them.

`tests/application/test_paper_provider.py` and
`tests/security/test_provider_output.py` exercise split offline dispatch and
arrival. Editing/review remains available while waiting; cancelled, stale,
expired and superseded replies cannot overwrite drafts or newer proposals.
Unknown/duplicate arrivals, malformed/oversized/tool-bearing envelopes and
refusals create no adoptable proposal. Competing completions produce one trace;
pending/failed attempts consume their budget. Exact response hashes and erased
payload markers survive, as do adopted Contributions and the unchanged paper
manifest. These are volatile adapter tests, not deployment/transport evidence.
The [offline CLI exercise](../../development/workflow.md#offline-provider-exercise)
and `test_paper_provider_example` repeat five independent routes over the
bundled paper: adopt/edit, cancel, edit while pending, expire and refuse.
Inspect the measured 0.4 percentage-point loss and unrun seed-43 plan in the
selected context. Every route produces a human review; only explicit adoption
adds AI provenance. The extracted source artifact repeats the status,
continuation, erasure and unchanged-source oracles without repository tests or
scripts. It also requires the displayed research question in the selected
unfinished draft inside the actual outbound body, along with the current
Interpretation, and checks response disposition separately from adoption
status. Valid fixed text is not a live model-quality result.

At the paper-to-provider boundary, inspect the exact selected context for
subject/scope, experiment conditions, metric definition/unit/baseline, relation
rationale and source availability. Missing information stays missing; labels
or inherited UI captions cannot silently stand in for it. A useful-proposal
case names what evidence or alternative the response should help inspect and
what uncertainty must remain. Provider failure/cancellation leaves the manual
judgment available; accepted state remains unchanged until its separate review
and authorization. Frozen replies verify wiring, not model usefulness.

The offline boundary is implemented by the
[paper context/draft service](../../development/workflow.md#paper-context-and-offline-drafting).
`test_paper_context`, `test_paper_context_egress` and `test_paper_draft` check
literal measurement/source fields, unchanged original-profile bytes, bounded
explicit selection, nested secret/path denial, retained invalidation/plan status,
and source freshness even when a new run does not advance the reasoning head.
Draft checks cover AI before a complete judgment, explicit opt-in to unfinished
text, preserved AI origin after edits, replaced-text recovery, exact one-shot
review, cancellation, stale/late results, payload erasure and AI-off continuation.
The scripted CLI journey and independent source artifact exercise this connection
on the same paper. It neither creates accepted state nor completes the visual,
authorization, durable-resume or live-usefulness oracles.

Selected scientific review now has data/service coverage in
`test_paper_changes` and `test_paper_change_review`. The scripted journey narrows
the pruning claim to mask seed 42, changes its observation relation from support
to qualification, selects that relation and the new interpretation, and omits
the proposed seed-43 plan amendment. Assert the changed claim is a required
dependency, the old plan and observations stay identical, and before/after paths
identify potential reach without changing other claim statuses. Additional cases
reject invalid partial selections, stale/cross-draft reviews, changed source
with unchanged heads, retracted selected basis and loss of a retained contested
status's challenge. Source AI contribution survives a fresh human draft; adoption
invalidates review even if visible text is identical. Deferral creates only a
conditional debt description, and Not now retains the draft without accepted
writes. CLI and independently extracted source-artifact checks exercise this
connection. These do not establish a UI interaction or repeated canonical episodes.

The separate v3 cumulative-paper example now covers repeated candidate episodes
in `test_paper_episodes` under both contract and application tests. The second
episode corrects the same observation from 0.4 to 1.2 percentage points, selects
the challenge and contested status, and retains the first Interpretation and
its original contributions. Assert exact replay, unchanged first-history bytes,
one observation identity and both values, retained source AI despite a manual
new Judgment, one active episode, and explicit old/current evidence semantics.
An unmerged alternative remains browsable without entering the next main.
Reject episode/operation identity reuse, another episode's Interpretation
rewrite, invalid partial selection, stale consent and cross-episode drafts.
An Interpretation selected for AI context must carry its source episode, even
when the request itself concerns the current episode; full contribution history
is not sent implicitly.
Draft caches must use episode/ref/node identity, reuse shared-node occurrences,
retain older drafts on refresh and never silently evict at the finite limit.
The current TUI reader accepts the v3 graph shape in a service-level smoke;
episode navigation and drafting controls still need the UI integration oracle.
Both CLI variants and the independently extracted artifact exercise the frozen
two-episode history and its exact second-episode merge review. Contract and
application checks in `test_paper_merge_review` and `test_paper_merge_session`
require preserved source Judgment chains, the selected challenge/status and
required new Interpretation, unchanged evidence, inherited scientific impact
paths, and an unverified calculated graph matching the frozen example. A fresh
manual Judgment cannot hide the earlier AI contribution. Reject altered source
provenance, selection, operation/project/episode, rationale, answers, manuscript
fingerprint, expired/backwards time and source changes even with unchanged heads
and watermark. Caller-built seals must fail owned-history reconstruction.
Not now clears review without changing drafts/history or creating debt; returned
review dictionaries remain detached and cannot be receipts. These checks do not
establish manuscript source verification or a draft-to-recorded-branch UI action.
This is not protected persistence, a restart/recovery pass,
V0 eligibility or evidence that manuscript/debt work finished.

The v3 draft-to-branch checks in `tests/application/test_paper_branch.py` require
an active unmerged episode, exact source/draft scope, a complete Judgment and
matching current Interpretation. Start with a blank draft, record only selected
amendments plus required dependencies, then complete exact merge review. The CLI
and extracted artifact now exercise that path. Main and global evidence stay
unchanged during staging; omitted plans do not enter the alternative. Joining
independent drafts must preserve the recorded contribution prefix and AI original
text/trace identity without duplicating a shared prefix or truncating at the
eight-contribution bound. Refreshing two separate drafts retains both readings.
Reject historical recording, a main draft replacing an existing alternative,
incomplete reasoning, stale/foreign/tampered review and source changes with
unchanged heads/watermark. Not now keeps the buffer and creates no debt.

Context regression checks explicitly include Interpretation-to-Claim scientific
relations in v2/v3 while requiring both selected endpoints and the v3 origin
episode. Experiment/plan endpoints cannot masquerade as scientific support.
The earlier browser must retain a text-only human buffer when an AI proposal
replaces it; the disclosure must remain keyboard-accessible without horizontal
overflow at 1440 and 390 pixels, and later human edits must not erase AI influence.

The conditional-work projection in `tests/application/test_paper_work.py` must
reconstruct one manuscript review per candidate merge and understanding review
only for explicit deferral. Two closed episodes retain both sets of work; replay
and later evidence changes retain causal IDs and original contributions. A
plan-only merge opens no automatic wording, and a discarded preview creates
no work. These are conditional items, not accepted debt or a restore proof.

`tests/application/test_paper_manuscript.py` starts with blank wording and a
supplied synthetic marked source. Require a complete human reason, exact unique
markers and full current paper/draft binding. Assert byte-identical surrounding
content, including decomposed Unicode and mixed line endings, literal TeX
escaping, and exact preimage/postimage hashes. Missing/invalid source must not
produce a diff. Source AI remains explainable despite manual wording. Reject
foreign/tampered reviews, a wording draft independently refreshed to another
history, stale source/history with unchanged heads/watermark, clock reversal and
expiry. Not now preserves wording and all projected work; returning candidate
bytes cannot apply a file, verify a compiler or close debt. Both CLI/ZIP episode
routes exercise this follow-up over the same calculated merge history.
Explicit offline wording adoption must invalidate a prior review, preserve the
AI original and trace after human edits, and require explanation/deferral even
when the source graph itself was entirely manual. Supplied manuscript bytes
must not enter that AI request implicitly.

| Action | Observable pass condition | Failure |
|---|---|---|
| Read a node without opening its inspector | The visible text names the proposition, result or experimental question; relevant operations/conditions are identifiable and definitions are available in context | An ID, “three operations”, “damage” or “as expected” carries meaning absent from the visible/source context; a missing definition is fabricated |
| Read from the paper thesis to an experiment | Navigation follows thesis, main claims, optional subclaims/evidence and experiment records; the selected argument path and return context remain identifiable in the terminal projection | Run-first order hides the question, every claim is forced through a dummy subclaim, or pane/navigation order changes edge meaning |
| Follow shared evidence | One observation can be inspected from distinct claim paths with each relation and rationale preserved | Duplicated display items become independent facts, or one navigation parent hides another scientific use |
| Focus a node; optionally hover/touch in graphical views | Keyboard focus exposes typed relations and related content, with a way to follow the same node and return while retaining context | The effect is mouse-only, relies only on color, hides text, or cannot identify the emphasized relationship |
| Explore an assumed follow-up result | The graph identifies the assumed observation, possible reach, affected claims/wording and unchanged/remaining basis; actual and hypothetical states remain distinct | A planned experiment appears as observed support, a path automatically makes all ancestors false, or impact is available only in a detached prose section |
| Change the scenario, source or selection | Derived impact is recomputed or visibly stale; the researcher can return to actual state | A stale scenario or omitted change remains presented as current accepted impact |
| Form a judgment in graph context | Rationale, AI origin and human edits are inspectable at the selected argument and reused by exact review | A second mandatory narrative is needed, contribution history disappears, or visual interaction supplies authorization |
| Inspect and compare without accepting | Canonical accepted state and manuscript bytes remain identical across navigation, hover and hypothetical comparisons | Viewing a scenario confirms evidence, consumes authority, applies a patch or closes debt |
| Quit and resume the implemented product | The same own-project argument, saved judgment, provenance and pending work reopen through supported commands | Only the bundled example reopens, or accepted/saved work is lost with the browser session |

The [source-delivery gate](../../product/releases/validation-prototype.md#55-source-delivery-readiness)
additionally requires clean-source installation, independent-user operation,
CI and recovery evidence. Run graph scenarios first on synthetic data; native
authority and P0 remain prerequisites for real research. Successful automated
or browser checks make the information observable; they do not certify a
researcher's understanding or establish V0 value.

### 10.3 Terminal prototype oracle

For proposal replacement, compare the current human judgment and reason with the
complete fixed-example proposal before adoption. Opening, scrolling and cancelling
must preserve the entire session state and leave the proposal available. Explicit
replacement keeps the reason and prior text and retains AI origin after edits.
Changed writing, owner, paper context, replacement proposal or expiry invalidates
the earlier comparison. Exercise wide, 80×24, 48×18 and paused tiny screens,
complete scrolling, cancel/reopen and explicit confirmation in a real PTY.
This validates whole-judgment replacement, not selective typed adoption or live AI.
After later human edits, B must compare current and pre-adoption text/reason;
cancel preserves newer writing, and explicit restoration retains AI origin.
Unkept judgment edits remain separate through both paths.

Selected-project **Paper connection** must distinguish same-byte relocation from
changed-source refresh at the retained location. Show complete before/after paths,
fingerprints and reader compatibility, then require an explicit apply after the
preview is readable. Preview/cancel changes no association; unexpected or pasted
keys cannot apply. Queued apply input from before the first preview paint must
be discarded, including ordinary unbracketed input. Preserve exact path Unicode, nested work bytes, contribution
history, earlier source basis and graph/reader position. Changed source/work or
save refusal cannot report success or reuse the stale preview; uncertain saves
must remain unconfirmed. Missing source keeps writing usable. Test narrow/paused
screens, long paths/cursor, refreshed source status, actual encrypted restart and
a Mac PTY relocate/cancel/refresh flow with a retained Korean note. No manuscript
write, evidence confirmation or renewed review authority may occur.

For the selected synthetic project entry, dry-run and cancelled setup must create
no store, key, lock, evidence or file changes. Title, working thesis and first
question come from the person; one explicitly previewed candidate episode opens
an otherwise incomplete argument with AI off. Source changes between preview and
creation refuse without replacing work. Save/reopen retains the complete typed
project association, candidate graph, partial judgment and separate unfinished
input through the existing encrypted snapshot. Missing/changed source leaves
saved writing accessible, shows the observed-at-opening warning and preserves
the original association. Actual Mac PTY checks cover Korean judgment/note entry,
quit/restart, changed source, resize and shell restoration. Opening an existing
no-episode project must first show its retained thesis and source status, allow
human question entry/revision, and save only on explicit start. Cancel, EOF,
interruption and a refused save preserve prior checkpoint bytes. Existing keys
and associations stay unchanged, missing source permits drafting, and reopening
must not create a second episode. Exercise Korean question entry, cancel/start,
narrow graph and restart in a real Mac PTY. This synthetic connection does not
close public lifecycle, protected acceptance or real-use gates.

For opt-in [encrypted judgment recovery](../../development/workflow.md#encrypted-terminal-judgment-recovery),
a fresh process must recover independent/linked judgments, adopted AI origin,
pre-adoption text, personal notes and intentionally empty unfinished inputs
without reviving request/review authority. Source/version/owner/chain mismatches
fail before installing any projection. Creation cannot overwrite existing work;
wrong/corrupt input and failed replacement retain the last good checkpoint.
Exercise actual device reopening and PTY keep/reopen with AI disabled. The UI
must distinguish saved judgment/argument/result/explanation writing from excluded
manuscript review answers/completed reviews and name discarded session work on quit. This bounded Mac adapter does not
close full T5b, actual server/replacement-device or unfamiliar-user gates.

Checkpoint failure guidance must distinguish pre-store input/aggregate-size
refusal from storage/encryption failure and typed uncertainty/external-change
refusal. All preserve live writing and prior successful-save bookkeeping.
Input and ordinary storage causes must remain visible beside their status prefix
in a 144×42 manuscript-editor footer; complete remedies remain in the scrollable
inspector. Only input refusal suggests correcting/shortening text. A reopen-required refusal
blocks changed and unchanged retries in the same terminal recovery session;
copy newer writing before exit and inspect a freshly opened checkpoint. Inject
an actual directory flush failure after replacement and externally changed
ciphertext: report unconfirmed saving, never prior-byte retention. General
storage errors remain unconfirmed without masquerading as invalid human input.
The named save-failure action shows the complete scrollable diagnostic at 48×18
and wider; Esc returns to the same selection/writing, and resize pauses safely.
A corrected successful save clears its error. Neither inspection nor reopening
revives approval, closes work or touches the manuscript.

Exercise retained writing together in one active synthetic workspace: manual
claim/typed relationship with selected and omitted candidates, provisional result
and tentative judgment, personal note, partial original explanation and supplied-
source manuscript wording. Keep unfinished empty deletions separate throughout.
Fresh-process return with a missing manuscript file must reproduce the complete
workspace without reading that file, reviving a review or closing work. Retained
source AI remains visible with assistance off. Corruption in the last restored
layer must leave the target wholly unchanged. Injected encryption failure through the native store and
all-or-nothing oversized-save refusal must show unsuccessful saving, preserve
live text and retain the last complete ciphertext byte-for-byte. Returning from
that checkpoint restores every writing kind together and leaves science and
source-file bytes unchanged. These synthetic integration checks do not establish
protected acceptance, SSH readiness or human usability.

Exercise that mixed writing through actual terminal actions, with assistance
disabled and recorded source AI retained. Author the claim, qualified connection,
provisional result, personal note, explanation and wording through keyboard input,
not by installing prewritten drafts. Preserve kept versus intentionally empty
unfinished fields and selected versus omitted candidates. Interrupt from the
wording's scientific-basis view after narrowing the terminal; verify exact source
bytes and every independent text/owner/binding in the saved checkpoint. Remove
the supplied source before a real TUI restart, resume the unfinished wording,
keep new wording and quit normally. A fresh read must retain unrelated writing,
original context and AI history, with no restored review or work closure. Verify
shell modes after both exits. This is a Mac synthetic PTY journey, not physical
IME, Linux/SSH or protected research evidence.
The [mixed terminal test](../../../tests/application/test_tui_mixed_terminal.py)
exercises this path without replacing the separate human/host gates.

For larger collections of notes, manual judgments, fallback buffers and
unfinished note/judgment editors, one workspace validation may share source-node
membership by exact episode/ref. Compare every owner with independent source
queries; reverse row order and check each selection. Missing nodes, episodes or
refs, duplicate writing and incorrect editor shapes must refuse the complete
checkpoint even after an earlier row populated that context. Historical sessions
remain independently checked, restored mutable text remains detached, and the
next validation queries fresh sources. Measure complete native changed saves
with mixed writing as well as the internal calculation; preserve format and
all-or-nothing bounds.

The v3 envelope must additionally restore kept and unfinished candidate forms,
stable aliases/IDs, original owners, selection/omission and independent provisional
results. Reconstruct original source and contributions from verified history
prefixes, even after later source changes; never rebind on restore. Active text
and empty deletions return as unfinished input, leaving kept science unchanged.
Malformed source digests, duplicate identities, unknown fields and inconsistent
selection/aliases fail before installation. Preserve old v2 reading and the
narrower --draft-file boundary. Exercise actual device/fresh-process/PTY return,
interruption and visible oversized-save failure without truncation.

The v4 envelope additionally retains conditional explanation writing, explicit
rationale reuse, original judgment/source contributions, earlier writing basis,
selected topic and separate unfinished text. An active editor in source inspection
must also checkpoint. Reject unknown topics, duplicate works, mismatched source or
basis and invalid return positions before installation. Source changes cannot
silently rebind writing; merely browsing cannot create pending writing. Equivalent
NFC/NFD text must not block unrelated saved work. Preserve empty deletions, refuse
restoration over live explanation writing and keep old v3 checkpoints readable.
Actual Mac PTY interruption and reopen must retain Korean unfinished text and
leave explanation items open, AI origin intact and scientific history unchanged.

Checkpoint performance changes must preserve canonical explanation bytes and
the distinction between current and earlier writing bases. A forged context
digest must fail even when the bound operation is the current last operation;
an older basis still reconstructs its exact source. Report repeated changed-save
timings separately from native encryption, disk and terminal/remote latency.
When explanations share source computation, verify independent draft/cause/topic
bindings and detached mutable state, exact reconstruction of distinct prefixes,
original session ordering and refusal of a corrupt later draft without installing
partial work. Several drafts retaining the same earlier writing basis may share
its prefix replay and pending-work calculation within one batch; verify each
saved fingerprint and keep different earlier prefixes distinct. Compare batch
restoration with independent singular restoration and check that no service is
retained on a session. A following checkpoint must freshly validate its source; no shared
projection may survive as a substitute for current validation.

The v5 envelope restores unfinished scientific fields/answers with original owner,
source prefix, authored baseline or judgment/selection inputs and field position.
Sharing original-source queries within one validation must match independent
basis validation. Same-prefix/episode/ref inputs share one initial query and
editable-record lookup, while distinct prefixes and refs remain separate. Every
input still proves owner, fingerprint, original session and selected request;
a corrupt later owner or basis cannot borrow an earlier valid row's projection.
A historical session may omit a throwaway workspace lookup after owner/source
validation, but its standard constructor must still query independently and
restore_session must check its project, episode, view and adopted contributions.
Compare with workspace-based restoration; separate sessions, services and brokers
must remain independent, with no outgoing consent, adoption or live review.
Restored writing remains detached and a subsequent validation queries freshly.
The query map never survives the call or alters snapshot format/limits. An immutable
original history may also share one replay per command count across branch
groups in that call. Keep branch/episode projections separate and current
history replay-free; verify distinct earlier counts, interleaved mixed-mode
rows, independent baseline equivalence and refusal of borrowed branch/prefix
fingerprints. The next call must reconstruct the earlier prefixes again.
U names encrypted recovery; Ctrl+O exposes original/current context without editing
or losing cursor/undo. Refuse stale field application until an exact displayed
basis choice; refuse answer completion until a newly prepared scope review.
Opening that new answer editor alone preserves the original basis; changed
judgment/selection requires explicit displayed-basis choice before reuse.
Neither snapshot nor restore stages fields or resurrects a review seal. Empty
edits remain distinct, pristine browsing stays absent, canonically equal input
creates no redundant buffer, and confirmed discard removes only that input/basis.
Reject wrong source/owner/record/field shape, malformed selection and duplicate
inputs before installation. Save errors remain visible with live input retained;
old v4 files still read. Actual Mac PTY interruption in both scientific-field and
answer source views must reopen unfinished Korean text with original basis intact.

The v6 envelope also retains manuscript wording/reason, their contribution chain,
original recorded/detached scientific history, exact supplied UTF-8 bytes and
separate unfinished wording/source-path input. Preserve CRLF and NFD artifact
bytes, intentional empty edits and active field position. Restoring performs no
file access, creates no parent/child review and changes no pending work/history.
The named retained-draft picker exposes both kinds and returns to the same graph;
Tab reads retained source without a preview. Changed/missing source preserves
writing and blocks old-basis review; unchanged recorded work permits only a newly
prepared review. A detached restored parent stays historical and editable, with
new science opening separate wording. Malformed/duplicate identities, history,
source digests and editor shapes reject before installation. Pristine browsing
creates no saved draft; old v5 files still read. Save failures retain input and
previous checkpoint without truncation. Actual Mac PTY interruption/reopen covers
Korean wording in basis inspection, resize and clean shell return. Manual recovery
still excludes wording; manuscript review answers remain explicitly session-only.
Three written detached drafts sharing one 64 KiB source must retain one exact
source copy within the aggregate bound. Different oversized content must still
fail the complete save rather than dropping rows. d then Enter discards only the
chosen draft; cancelling/pasted controls preserve it and scientific work remains
unchanged. An active excluded answer must be disclosed without breaking the
checkpoint of retained wording. Authored and recorded detached parents both
retain their original owner and remain unchanged by rendering.


The v7 envelope shares exact canonical original review-writing sessions by digest.
Twelve scientific-field inputs sharing one 9,000-character judgment/reason must
fit without dropping original context or editor text. Twelve inputs sharing one
12,000-character judgment/reason must also fit:
apply the aggregate bound to the pooled representation, validating each input
independently rather than first encoding all repeated inline originals.
Different earlier judgments
at the same owner remain distinct. Reject missing/forged/duplicate/unused pool
identities and individually invalid source/record/request bindings before any
installation, even when an entry's digest is recomputed. Mutating one restored
input must not change another's historical session. Retain AI contribution chains,
intentional empty text and session-less field bases; restore no current review.
Existing v5/v6 work and v1/v2 selected-paper wrappers still read. Explicit saves
with v7 nested work use a v3 project wrapper, retaining exact relocation/refresh
history; old schemas cannot admit the new nested format. Distinct long originals
must still refuse a complete oversized save with live writing/prior checkpoint
retained. Exercise actual Mac device/fresh-process and field/answer PTY return.

[ADR 0012](../../architecture/decisions/0012-terminal-research-workspace.md)
adapts the presentation to the experiment host's terminal. The prototype's
[launch and keys](../../development/workflow.md#terminal-paper-prototype)
remain separate from production authority and the full paper-workspace gates.

| Action | Observable prototype condition |
|---|---|
| Start in a server-style terminal | `demo tui` uses stdin/stdout and opens no listener, browser, model connection or artifact |
| Write an interpretation manually | In an episode/ref with no current interpretation, AI-off entry starts blank and explicitly selects recorded observations, with current status visible. Space toggles; Enter applies; Esc cancels. Empty basis remains unlinked. An occupied source or kept/unfinished form explains its existing editing route; earlier episodes cannot be overwritten. Kept text and interprets links appear in the independent draft graph before a judgment is complete, without evidence or proposal creation. A scientific link to a claim selects its required draft interpretation at review. J on a kept new interpretation compares the owning judgment and preserved reason; Enter reuses only that text, retaining AI contributions and invalidating review/pending AI as disclosed. Unfinished candidate edits, changed comparison/work/source and existing recorded interpretations cannot bypass the reuse boundary. Tiny terminals pause controls with Escape available. Kept/unkept candidates remain excluded from manual checkpoints and quit warns. Actual PTY covers Korean, observation selection, graph, resize, judgment reuse and clean shell return; no durable or accepted transition is claimed |
| Discover manual work by name | `;` names judgment/note writing, claim/link/plan construction, connections, unfinished text and scientific/branch/merge review, retaining shortcuts. Choosing writing keeps the subject visible; cancel/return preserves graph position. Result capture names its unconfirmed, session-only boundary before entry; evidence confirmation remains unavailable. Wide, 80×24 and 48×18 views retain selection, readable availability and return controls; smaller terminals pause actions |
| Capture a result before interpreting it | With AI off, `;` → Draft a result and source permits blank/partial observation, run/source references, conditions, metric/value/unit/comparison, uncertainty and tentative judgment/reason. No source is opened and no confirmed run/observation, graph edge, proposal or review is created. Ctrl+S keeps one field in memory; Esc retains changed unfinished text separately, including an empty edit. The original subject remains visible while writing. Ctrl+O and Tab inspect result/original/current context and retained source AI without changing the buffer, cursor or undo; inspection labels the current editor text separately from kept/prior unfinished text, and paste/keep are ignored. Cancelled discard and field return retain the selected result; NFC-normalized text cannot exceed the character limit. Independent result identities and original episode/ref/node survive navigation; changed/unavailable context preserves writing and its original basis. Pristine browsing leaves no pending work; at 16 drafts capacity refuses without eviction. Resume result drafts restores the chosen capture without moving graph or other judgments; d then Enter confirms its deletion. Tiny screens pause invisible input with Escape available. Checkpoints exclude kept/unfinished/active result writing; normal quit warns even with recovery enabled. Actual PTY exercises Korean paste, real keys, resize, resume and clean shell restoration. This does not establish new-project initialization, confirmed-result integration, durable return or server support |
| Reuse one judgment explicitly | Link one observation's judgment to two existing claims through a cancellable owner/content/membership preview. Each newly linked node opens the same text, reason, AI contributions and candidate work; its own judgment and personal note remain separate. Choosing another judgment changes only the viewed node's choice, even at review-session capacity. Adding another reference preserves choices at already-linked nodes, whose different active judgment is labeled. Unlinking a node displaying that work returns to its own judgment; original ownership never moves and no scientific edge or accepted state changes. Membership changes revoke exact change/branch/child-merge reviews, retaining candidates and independent AI. Wrong endpoints, stale source/link revision and new-work capacity failures leave prior links intact; a full 16-link work is unavailable before confirmation. Other episodes/refs never borrow work. U returns to the original unfinished judgment, including separate manual work beyond review capacity. The editor names owner and viewed source at wide/narrow sizes; small terminals pause input. Actual PTY covers linking, Korean writing, resize, notes and clean exit. Manual checkpoints keep eligible text at its original owner, restore no associations, and exclude linked AI work; quit discloses session-only link loss |
| Plan a follow-up manually | With AI off and a blank judgment, choose an existing or kept draft claim and write question, conditions, metric name/definition/unit/comparison. No scientific field is prefilled. Cancelling a pristine form creates no unfinished work; partial nested measurement text remains editable. Complete kept plans have stable draft aliases, explicit unrun state and one tests relation, with unchanged evidence/history and no run execution. Reading shows the full measurement and no unavailable scenario shortcut. Omitted plan edits remain omitted; selected plans include required draft claims at exact review. Domain count/endpoint/status/blank-field failures retain input. The actual PTY covers Korean paste, all fields, resize, graph and clean exit; fields remain excluded from checkpoints |
| Construct an argument before deciding | With AI off and no complete judgment, explicitly choose a claim's level/parent and author statement/scope; connect the existing observation to it with a full type and rationale. The independent DRAFT GRAPH contains one shared observation and marked draft cards/relations. Blank/dangling/cyclic/oversized candidates cannot produce a valid graph; unfinished text remains editable. Final selected review still requires a complete judgment/reason and never changes the source manifest |
| Keep draft ownership distinct from navigation and review | Candidates remain with the original episode/ref/existing-node work after navigation, judgment edits and review expiry. Return to authored work restores that owner. Mutations/reselection invalidate exact scientific/branch/child-merge review, retaining independent proposals. Copied read values cannot mutate candidates. New candidate IDs never become Judgment/checkpoint targets; manual checkpoints exclude all candidate fields. Changed history blocks graph/review until explicit refresh; missing owner/capacity errors retain previous work |
| Separate candidate editing, omission and removal | Esc retains unfinished fields without changing kept candidates. Graph shows all valid kept candidates, even omitted ones; edits preserve omission. Unkeep retains incomplete text separately so other valid work can proceed. Kept selection remains visible beside unkept edits, and review warns that it uses kept text. Removal explicitly lists dependent kept/unfinished drafts; retaining dependents requires repair. Stable aliases survive editing/removal of other candidates. New-node impact text and comparison remain readable at final review. A real PTY covers manual form entry, Korean paste, resize, graph and clean shell return; all candidate work remains session-only |
| Refresh a changed amended source | Source changes revoke review and retain candidate/unfinished fields. A changed amended record exposes previous/current source and candidate values before explicit rebinding. Esc keeps the old binding; Enter retains the exact displayed draft against current source. A mismatched comparison cannot refresh. Rebinding grants no authority or automatic rebase, and domain validation can still reject a retained proposal |
| Launch with assistance disabled | `demo tui --ai-off` shows AI OFF before any request flow. The named AI action and Work's A key open no context picker or outbound review. Manual writing and selected-change review still work; no new Proposal, attempt or trace appears. Episode/ref navigation and comparison graphs retain the disabled capability, while recorded source AI contributions remain unchanged. Default entry still explicitly offers the fixed offline example before a complete judgment. Actual CLI/PTY checks cover menu navigation, Korean paste, resize, keep/reopen and shell restoration |
| Read a visual graph | Default navigation draws one box per record, including one shared pruning observation with lines to both claim destinations. Every argument relation key is represented, parallel types keep their direction, and lines do not pass through node boxes. Actual target arrowheads and selected-node labels remain inspectable without color; crossings add no node or edge |
| Focus a graph neighborhood | Selecting E1 keeps E1, its two directly connected claims, the producing run and interpretation bright, with exactly their four incident edges. E2, the thesis, pruning main claim, unrun plan and writing anchor remain visible but subdued, without repositioning. A selected exact edge keeps only its endpoints and that relation bright, including when another type joins the same pair; an edge outside the current lens is identified without fabricating a visible path. Text, scenario markers, navigation and source history remain intact |
| Navigate graph and read | Arrows move spatially, `j`/`k` reach every in-scope node, `Enter` opens full node content, and `r` selects an exact incident edge. `f` fits the current scope in a full-width compact map; small viewports follow selection and `HJKL` pans manually. The selected header stays visible even when a minimum-height viewport cannot fit the whole card |
| See the small paper before reading | At 144 × 42 and 120 × 32, all ten example nodes fit with T or E1 selected. Cards distinguish the two pruning claims, retain measurement values and mark the unrun plan. A note cannot displace the compact card's scientific subject/result. Changed source text cannot retain a stale authored caption; full statements stay in the reader |
| Close reading before undoing traversal | From the thesis, select another node, open reading and press Esc: the same node, graph pan and follow setting return. A second Esc may return along the previous traversal. Wide reading opens beside the map; 80-column reading uses its full pane. P pins the reader, including when used while reading, and its preference survives resizing |
| Choose explicit local scope | E1's one-hop view has five unique nodes, all fitting at 80 × 26; at 80 × 24, clipped nodes stay counted and reachable. Selecting a neighbor keeps that root and layout; changing depth is explicit. Counts distinguish clipped cards from hidden nodes/edges. Home/End stay in scope. Following an outside edge reveals its target; Esc restores the prior scope and a returns to all nodes in the current lens |
| Read shared evidence on a short screen | At 80 × 24, E1's first reader viewport exposes its recorded value/unit, conditions and both named scientific destinations before scrolling. Source, note and full relation rationale remain accessible. Compact framing does not change a relation or silently abbreviate its target identity |
| Distinguish overlaps and offscreen context | Independent route strokes never combine into a false tee or crossing X. Exact-edge selection takes drawing priority through crossings while every route remains available in the reader. Only first legs sharing an actual port may show a common fork; an unlinked node reports no connections. Incomplete cards are omitted and offscreen direct-neighbor aliases remain inspectable through the relation picker |
| Read edge types without a code key | Connected card headers show full directional phrases relative to the selected node, such as `supported by E1`, `challenged by E1` and `produced E1`. Parallel scientific/structural relations occupy separate rows; exact-edge focus shows only its own phrase. A fitting phrase shares the title line (`R1 RUN · produced E1`) in regular weight; long or parallel phrases continue directly below the title. Text stays in the reserved header band, never over source previews, notes, borders, arrowheads or route lanes. Long aliases wrap within preallocated space; changing selection leaves geometry fixed. Meaning remains readable without color. Wide 144×42 and 120×32 ten-node overviews and the 80×26 five-node local view retain complete cards |
| Tune graph presentation and retain vertical arrows | Directly stacked connected cards leave at least three route cells, including upward challenges; an actual arrowhead has a visible shaft and selection never changes geometry. A short viewport reports clipping instead of collapsing the connector. `,` opens view settings; spacing/detail/pinning preview live, Enter keeps and Esc restores the prior settings/viewport without altering notes, judgments, source or reviews. Defaults also preview until kept. Resize preserves the selected setting; below 48×18 a visible cancel hint replaces controls and changes/keep pause until resizing. A pin toggle roundtrip preserves an existing fullscreen view, manual pan/follow restores on cancel, paste/unused keys cannot invoke actions, and comparison graphs inherit spacing/detail. Spacious changes layout after caching; returning to Balanced matches a fresh scene. Visible/hidden counts and `r follows` stay readable on short screens |
| Compare graph and outline | `o` changes navigation over the same Argument/Evidence view, retaining the evidence identity, selected occurrence, draft and hypothetical state. No graph fold or placement writes a scientific relationship |
| Read the argument hierarchy | The example's sole outline root is its thesis; claims, evidence, recorded experiments, interpretation, follow-up plans and writing connections appear beneath recorded links. Unfolding covers every relation key, including parallel scientific/structural links; no implicit support is added |
| Read an inline edge | Its exact type and direction appear beside the connector: `↑` is node to parent, `↓` is parent to node. `Enter` on an outline node inspects its connecting edge, preserving complete endpoints and rationale |
| Follow shared references in outline | Evidence uses the same `E1`/`E2` label across occurrences/views with a distinct direct-claim count; `↪` marks a reference and `↔` marks another visible occurrence of the selected evidence. Other shared records retain `[shared]`/`[same]`. Selection is specific to an occurrence, `g` jumps to its primary location, and `Esc` restores the previous path. Its branch-bound draft stays identical |
| Fold and search outline paths | Left folds or goes to a parent, right unfolds, and search retains matching ancestors. The match is selected rather than its ancestor; search does not silently toggle stored fold state. Cycles terminate as references and unlinked records acquire no fabricated parent |
| Inspect shared evidence | The pruning observation has one identity and names both the comparison and pruning-detail claims with explicit relationship types. `u` selects a scientific use; parallel types keep their own rationale but count one target claim. Incoming relations and structural/experiment links do not inflate the use count; `r` still exposes all connections |
| Switch reading view | `1` selects Argument, `2` selects Evidence uses, and `[`/`]` changes the focused observation. The evidence graph shows recorded claim paths together; its outline starts with direct claims and unfolds further paths, never inventing direct support. `Esc` restores the prior view/occurrence, fold state and pane; branch-bound drafts and hypothetical state survive. No-evidence/zero-use cases remain explicit |
| Inspect a connection without repeated prose | `r` selects a relation; `Tab` reaches its complete FROM/TO statements and rationale, retaining the recorded direction for incoming as well as outgoing links; `Enter` follows the same node and `d` returns to node reading |
| Adjust reading density | `z` changes comfortable/compact spacing without losing selection, scenario or branch-bound drafts; labels, hierarchy connectors and selection markers work with `NO_COLOR`, eight colors and 256 colors |
| Explore a hypothetical result | The projection marks potentially affected claims and the comparison claim outside the path; the service's source history remains byte-identical |
| Navigate cumulative episodes and refs | `--series`, t and Tab select an explicit episode/ref. The header identifies its reasoning status and current global evidence; closed reasoning never implies historical evidence. Returning restores its selected node/viewport, and hypothetical previews clear without altering source history |
| Keep cross-episode work separate | Notes, kept/cancelled judgments, AI requests and selected reviews belong to episode/ref/node. A late reply reaches only its original session. U resumes the correct unfinished editor across episodes. Exhausting the 16 service review sessions preserves manual editing and existing reviews without crashing the Work reader |
| Read reconstructed pending work | W shows only recorded conditional work across episodes. Its reader exposes original judgment, rationale, AI influence, explanation disposition, selection and source-change flags. g selects an affected node in the originating main context; revisiting the list or closed episode resolves nothing and creates no accepted debt. Empty work remains empty |
| Return to a partial explanation | W → explanation item → e opens one to three causal topics. Original judgment/reason, original/current science, the earlier draft basis and separately identified AI contribution chains remain inspectable. r explicitly links the original rationale without copying it; blank/partial text is valid. Ctrl+O opens source while preserving text/cursor/undo; source mode ignores pasted text and keep. Ctrl+S keeps session text; Esc retains unfinished work/topic-specific input, including intentional empty edits. Returning the buffer to kept text clears only redundant unfinished input. Different topics/items do not inherit text or rationale links. Source changes retain writing and its earlier basis; s previews all affected topics and Enter requires the exact displayed current context. An unavailable source permits retained-context editing but refuses rebinding. Missing current connections are named. Character/UTF-8 limits are visible, failed keeps preserve input and successful keeps normalize NFC. Tiny terminals pause input with a retained Escape return. Leaving restores the original graph; browsing alone creates no writing. W identifies retained drafts; manual checkpoints exclude them and normal quit warns in default/manual recovery mode. Encrypted recovery retains original context, rationale links and separate unfinished writing without completing an explanation. Actual PTY covers Korean paste, Ctrl+O, resize, keep/reopen and clean terminal restoration. No answer completion, grade, provider call, accepted Debt mapping or closure occurs |
| Recover cumulative manual text | A series checkpoint retains explicit episode/ref/node for kept and unfinished manual text and selection. Invalid contexts/history reject the whole file before restoration. AI-influenced drafts and cancelled edits are excluded; the earlier manual checkpoint stays manual. Legacy single-episode files retain their format |
| Write and compare a judgment | A blank/local manual draft stays with its branch/node across layout changes; recorded AI provenance is unchanged and clearly separate |
| Write with recorded subject context | At 144×42 and 80×24, the open judgment editor shows recorded content and available conditions. A source-independent synthetic history verifies wording without caption-map entries. Ctrl+O opens complete read-only source/metric/reference/relationship context; scrolling, ignored paste/keep keys, resize and return preserve the same buffers, field, cursor and undo state. Source references are not opened; plans do not become observations. Episode/current-global-evidence and hypothetical status remain visible. Private-recovery/AI-origin state and save failures are shown even in source/tiny views. Below 48×18 input pauses and one Esc retains/leaves, with no invisible Ctrl+O transition. Kept drafts still belong to each original node. Prepared/completed review, long-field warnings and unfinished-writing indicators remain visible before long Work text. A real PTY journey covers Korean paste, source expansion, resize, keep/reopen and clean shell restoration; physical IME, SSH and human comprehension remain separate checks |
| Request optional scoped help from Work | A starts an explicit context selection; judgment inclusion is opt-in and notes/unchecked neighbors stay out. The exact fields and scientific links appear before a separate dispatch action. A fixed offline reply never changes the draft until adoption. Cancellation, expiry and intervening edits prevent stale adoption; manual work stays available |
| Retain proposal origin through editing | Explicit adoption keeps the prior buffer and ordered human/AI contributions. Later human editing or restoring the earlier text cannot erase AI influence. A new node/branch gets its own draft. Oversized Unicode drafts remain editable/kept and visibly block review rather than crashing or reviewing older text |
| Review authored scientific changes | Existing mutable scientific records are edited separately from the judgment, with explicit selection/omission. R shows exact field differences and selected/required/omitted effects through the existing service. G compares the actual before/after projections and Esc restores position; no projection mutates source history. Editing/reselection/expiry invalidates completion of the old review. AI-influenced scope requires explanation or explicit conditional deferral, and completion grants no authority |
| Review detached branches and selected merges | `--merge-example` opens the golden-verified active prefix while `--series` remains closed. Work → c → J explicitly stages the current episode Interpretation from the judgment; C previews a detached branch and Enter opens its merge selection. M opens the recorded alternative independently. Space selects exact records; R with a supplied read-only source shows required/omitted closure, literal effects and retained earlier AI origin. Tab exposes basis; G compares before/after and Esc restores graph/Work position. Enter explains/defers and v calculates an uninstalled candidate. Editing the parent, reselection, expiry, source/history change, file removal or invalid UTF-8 revokes reuse; an expired explanation editor returns to review without crashing. Cancelled source/explanation buffers survive re-preparation and adapter history refresh separately from reviewed content; refreshed history requires a new source selection/review. Escape hints name the actual return and quit warns. Neither workspace history, file bytes nor actual pending work changes |
| Leave an unaccepted review without losing origin | Not now retains judgment and staged changes while cancelling the request/review. With private recovery, AI-influenced kept/unfinished text is excluded rather than restored as human-only text; the pre-AI manual checkpoint and personal notes remain available. Adoption explains this session-only boundary, and normal quit still warns about volatile work |
| Write a personal node note | `n` edits one free-form note beside the graph; Enter inserts a newline, Ctrl+S keeps it in the session and Esc cancels only the current edit. Compact cards mark its presence with `✎`; source cards/outline show its preview and the reader exposes the full text. Search finds it. Following either use of E1 and returning, changing lenses, resizing, and switching branches preserve the correct note without replacing source or Judgment text |
| Recover uncommitted editing | Esc leaves the kept note/judgment unchanged, and cancelling unchanged text preserves older unfinished writing. N/E reopens text explicitly; U lists other nodes/branches. Undo/redo works on editor text and insertion beyond 12,000 characters produces visible feedback |
| Resume unfinished scientific review | Esc retains changed fields/explanations, including intentional empty edits, without staging/completing them; read-only browsing creates no pending work. U labels kind, original episode/ref/node and retention, then restores that exact editor. Unkept text is distinct from staged/reviewed content. Manual checkpoints exclude it and normal quit warns in default/manual mode; encrypted recovery retains it with its original basis and no review authority. Expired comparisons hide the old graph; expired explanations remain readable but completion fails without losing text. Esc → R in Work → Enter → 1 reuses the explanation under a new exact review. Below 48×18 invisible review controls pause while Escape remains available |
| Resume a shell and private checkpoint | Ctrl+Z restores canonical input/echo and stops the process; resume after resize retains the live buffer. With an explicit external draft file, abrupt process loss/restart restores unfinished Korean text separately from kept text. Another session, malformed content, history mismatch, symlink or in-Git location cannot overwrite it; failed replacement preserves the previous checkpoint |
| Exercise a larger projection | A separate connected 50-node/83-edge synthetic projection preserves cross-branch shared evidence, exact endpoint sets, local/global scope and frame bounds. The original pruning observation has six direct scientific claim uses; its one-hop scope has nine unique nodes and reports 41 hidden. The earlier disconnected 50-node/75-edge projection still checks identities and reachability. Neither establishes human legibility |
| Handle Enter and unused keys without display drift | Repeated Enter remains inside the TUI. Stale exported dimensions cannot address outside the live terminal; pane changes repaint fully, and queued unused keys do not leave a partial frame. Unknown terminal escape sequences cannot trigger ordinary navigation/quit/scenario shortcuts. Ctrl+L redraws an unchanged screen or editor without discarding its buffer |
| Handle modified keys and shell boundaries | Alt/Option bytes do not cancel then execute a shortcut. Alt+Backspace and Alt+arrow keep the note editor active; Ctrl+S still explicitly keeps writing, while standalone Esc cancels. Bracketed-paste control bytes never return remaining pasted text to the shell. No-job-control sessions refuse Ctrl+Z while retaining an editable buffer; shared graph ports account for all incident connections |
| Inspect writing context | W → Writing impact → m opens blank work-bound wording/reason; missing source is explicit. s loads a regular bounded UTF-8 file read-only; e authors wording; R shows diff/before/after/basis. Source views preserve indentation/spaces with cell-aware wrapping, while exact byte digests retain mixed line endings/decomposed Unicode. Inherited AI explanation or explicit deferral gates completed unaccepted review. File change/removal, wording edits or expiration revoke review and preserve the draft. Malformed markers never yield a diff. Esc retains item-specific unfinished editors and restores pending item/graph; normal quit warns even with graph checkpoints, which exclude this work. No source file write, compilation, acceptance or pending-item closure occurs |
| Continue selected science into wording | From a completed merge review, m opens current/retained wording for that original work. The current choice uses the exact detached candidate's manuscript consequence and supplied source, leaving workspace history and W unchanged. Wording begins blank; the judgment/reason stay readable while writing. Ctrl+R explicitly reuses the reason, confirms replacement of different text and preserves undo; Ctrl+O reads full scientific basis without losing buffers/cursor/undo or accepting pasted controls. Parent edit/link/reselection/expiry/history or source-byte changes revoke child review while preserving kept/unfinished text. A different parent creates separate wording only on explicit choice; earlier drafts remain reachable after re-preparing the same work and keep their original provenance. Other work/episode flows cannot borrow these drafts. Manual review requires no AI answer; inherited AI remains visible with its existing explanation/deferral rule. Small terminals pause invisible actions. Actual PTY exercises reason reuse, Korean paste, basis expansion, resize, exact diff and return to the original review/graph. No file bytes, accepted state, pending work or manual checkpoint are changed by candidate wording |
| Resize and type/paste Korean | Content wraps by terminal-cell width, a smaller layout retains selection/drafts, and pasted shortcuts are treated as text only |
| Return to experiments | Quit/interrupt disables paste mode and restores canonical shell input, echo and control settings; volatile nonempty drafts or notes get a discard choice on normal quit. With private recovery, q requires a successful checkpoint; a save failure stays visible and retains the buffer |
| Start without a usable terminal | Plain-text snapshot works; missing TTY or `TERM=dumb` returns an actionable error before altering the terminal |

`test_tui_interpretation` covers manual interpretation entry, observation choices,
judgment reuse, retained AI, dependency selection and stale/retention boundaries.
At 48 columns the picker keeps corrected/confirmed status visible; `r` exposes
full source conditions/measurement without changing selection. An oversized
existing reason refuses reuse and preserves the current judgment. An omitted
kept interpretation with mismatched wording gives an explicit reuse/edit/unkeep
route before review. Independent owning works remain separate exploratory drafts.
`test_tui_intake` covers provisional capture, source/episode separation, retained
writing and checkpoint exclusion; `test_tui_terminal` includes its actual key path.
`test_tui` covers projection/service and noninteractive behavior;
`test_tui_graph` covers unique boxes, recorded routes and graph navigation;
`test_tui_ports` checks endpoint type identity, visible vertical shafts, mixed ports and crossing priority;
`test_tui_view` checks reversible presentation settings and context preservation;
`test_tui_workflow` checks reading and editing outcomes; `test_tui_overview`
checks map coverage, compact content and connected local/global scope; `test_tui_recovery`
checks private checkpoints; `test_tui_review` connects manual/optional-proposal
drafting to selected review and checks provenance/freshness/recovery boundaries;
`test_tui_resume_review` checks unfinished field/explanation context, expiry,
staging separation, empty edits, minimum size, checkpoint exclusion and explicit
discard confirmation that preserves staged content. The review suite also
checks that browsing context and changing amendment scope preserve pending/ready
AI proposals while revoking scientific review;
`test_tui_context` checks cumulative context isolation, conditional work and
series recovery; `test_paper_work_links` and `test_tui_work_links` check explicit
judgment reuse, separate work/notes, provenance, freshness, capacity and retention;
`test_tui_branch` checks detached branch/merge freshness and origin;
`test_tui_manuscript` checks supplied-source wording review; `test_tui_terminal`
launches the real curses program in a Unix PTY; `test_tui_understanding` checks
conditional explanation return, rationale reuse, topic/work isolation, source
changes/failures, UTF-8 limits and session-only retention. `test_tui_wording_link`
checks exact selected-science parent binding, prior-draft access, reason reuse,
editor context, stale-source rejection and active-editor checkpoint exclusion.
It checks that pristine browsing creates no unfinished text, reason reuse
focuses the reason for immediate undo, and candidate capacity preserves written
drafts without blocking W's separate recorded-work capacity. Passing
those tests is not physical IME or assistive-technology evidence, a live
SSH/Linux result, an unfamiliar-user result, or durable acceptance/resumption.
The prototype remains synthetic, with only opt-in unaccepted UI draft recovery;
no protected server operation
or real experiment execution is admitted by this oracle.

### 10.4 Personal terminal alpha oracle

Under [ADR 0017](../../architecture/decisions/0017-personal-terminal-alpha.md),
this is the immediate first-release oracle; protected/native prototype oracles
above retain their separate future scope. The
[release checklist](../../product/releases/validation-prototype.md#55-source-delivery-readiness)
owns exit requirements, and the S ledger owns observed progress.

Start from novel human-written thesis/question with AI off and no seeded results.
Through the TUI, add claims, a provisional run/result with measurement/source,
an explicitly personally confirmed observation and a typed scientific connection
with rationale. Keep one judgment/reason and its chosen reasoning consequence.
Inspect the shared observation's other use, append a correction and confirm the
earlier value remains addressable across reasoning views. An unrun plan stays
unrun; a source reference alone never confirms an observation.

Quit/restart restores graph, notes, judgment, separate unfinished text, original
context/origin and open manuscript follow-up without source-file writes or native
keys. Cancelled review cannot record a consequence; expired comparisons are not
restored as approval. Competing opens, corrupt/newer input and interrupted save
refuse or show uncertain durability without a blind overwrite or lost live text.
Explicit backup restore targets a fresh destination and reproduces only verified
saved contents while leaving the original intact. Personal files never import
protected accepted authority or erase AI origin.

Show the local manual loop for user feedback as soon as it runs. Report the
actual host, wide/narrow PTY coverage, concrete friction and missing observations;
do not delay that feedback for unavailable SSH/IME participants or formal V0.
Clean-source startup, local rescue and applicable portable regression finish the
alpha release. This establishes recorded behavior, not scientific truth,
measured understanding or protected research readiness.

The entry/writing subset is exercised by [personal project checks](../../../tests/application/test_personal_project.py)
and the actual public init/resize/quit/reopen PTY case in
[terminal checks](../../../tests/application/test_tui_terminal.py). This does
not alone certify the result/recording, backup or source-delivery portions above.
The new-content personal result/selected reasoning/correction/later-episode
return is exercised in [personal research checks](../../../tests/application/test_personal_research.py),
[personal UI checks](../../../tests/application/test_tui_personal.py) and the
second personal terminal case. [Personal archive checks](../../../tests/application/test_personal_archive.py)
exercise complete saved-content backup, separate export, fresh restore, retained
AI origin, missing/changed source, damaged originals and interrupted replacement.
The public backup/restore terminal case creates kept and unfinished Korean
writing, exits, backs up, restores into a fresh directory and opens it in a new
80×24 terminal process. This does not establish remote host support.
[Source-artifact checks](../../../tests/application/test_source_artifact.py) and the
[standalone personal smoke](../../../scripts/personal_alpha_smoke.py) additionally
run public new-content authoring, correction, later question, wide/narrow actual
PTY return and saved-work rescue from the extracted runtime without importing
repository tests/scripts. They check complete restored saved contents and unchanged
source bytes. Remote CI and independent comprehension remain separate observations.
Recording checks also cover repeat-confirmation refusal, consumed correction
drafts, exact limitations/unchanged-run previews, later-episode reasoning,
cancelled/failed next-question input and uncertain post-replace saving. The
public PTY journey manually creates a claim and two distinct scientific uses
from one observation before recording and reopening; it uses no internal JSON
edits. These tests establish retained behavior, not unfamiliar-user usability.

#### Co-reported reading acceptance

On a personal paper profile, select primary and reversed sensitivity readings
with separate definitions/basis and one human reason. Review mandatory companion
closure and omitted candidates, then explicitly record one disposition: both
Interpretations reach main; global evidence/value and claim status do not change.
Group links cannot be mutual scientific support. Missing membership, inactive
basis, changed context/source/input or omitted required companion refuses before
append. A separate independent AI candidate can remain omitted without adopted
influence. Known AI/unknown original influence cannot disappear through editing
or a human-only merge judgment. A later revision uses new identities referring
to originals; prior-episode reading edits refuse. Original scopes, reason,
explanation choice and unfinished notes survive fresh process/backup. The episode
outcome is co-reported, not a fabricated legacy merge. Check actual PTY record/
open/quit, old-reader refusal and combined 128-reading replay/query/backup. No
operation certifies understanding, closes debt or modifies the manuscript.

#### Human reporting restriction acceptance

For personal paper profiles, keep a supported claim while recording "direction
only, appendix only" restrictions. Inspect the before/after, existing reason and
AI/unknown source references, explicitly record, and verify that support and
evidence remain unchanged. Reopen and backup/restore: policy, reporting companion
and unfinished writing must survive without resumed consent.

A registered abstract block with a prohibited phrase and missing declared
companion must show independent lexical, placement and companion warnings.
"Share" must not match "shares" or a TeX comment. An unclassified/stale source
or paragraph cannot receive a clean semantic certification; re-registration or
same-text relocation must invalidate earlier placement context. Declared
paragraph companions must use registered associations. A changed policy must
revoke a previous scientific comparison without losing its reason. Invalid
endpoint/identity/schema or a 257th companion refuses before append; cancellation
and older-reader refusal preserve the original. A historical view without a
reporting endpoint discloses coverage and does not crash. Check actual terminal
record/open/quit independently. No lint writes the manuscript, changes support,
creates confirmed evidence or closes manuscript/understanding work.

#### Personal paper migration and revision acceptance (planned)

The original-ledger follow-up currently adds an executable I01 preview boundary:
four exact maintained Markdown originals totaling 1,468,006 bytes, 430 records,
100 tables/5,400 cells, mixed defaults and ten human overrides. Required checks
include deterministic preview, exact/normalized cell extraction, declared rewrites
remaining unresolved, duplicate-locator and digest/Unicode failures, explicit
multi-source origin conflicts and prohibited ancestry clearing, source-link/path
refusal, create-only private preparation and independent source-artifact CLI
preview. I02 adds a table-only 54-cell historical import, first append-only cell
correction, condition query, private source/writing return, snapshot corruption/stream
refusal, changed/cancelled/interrupted/duplicate registration and frame mismatch
cases. Wide/narrow graph rendering and actual terminal reopen/exit are checked.
Full-paper fresh-process registration/open/backup/restore compares manifest hashes.
I03 adds compound AI/unknown and unknown-only scoped review, reason reuse,
fresh review after correction, more than 128 source dependencies in one choice,
128 saved partial causes and a lossless 129th refusal. Recorded choices/current
partial writing remain independent; shared causes count once. Older formats keep
their bounds. Actual terminal review/resize and fresh-process private return must
pass; 40+ unaccepted comparisons are not claimed as 40 merged judgments in a
32-episode model. I04 checks label-only initial setup/actual terminal return, section hierarchy,
figure/table captions, CRLF fidelity, kind/span binding and refreshed private
associations. Fake labels in comments/literal code, spaced duplicate labels,
invalid literal closers, missing/duplicate/changed labels and byte overflow must
refuse or remain unresolved with manuscript bytes unchanged. I05 additionally
checks explicit shared-audit opt-in: full logical audit equality, unchanged old
prefixes, source-checked replay, reference/forged-view rejection and expansion
refusal before repeated allocation. Actual terminal conversion requires `convert`;
cancel and dry-run preserve saved bytes. Existing partial writing and its original
cause must survive conversion, further editing and backup return, with no restored
review authority. The frozen combined fixture must still meet its original cold
operation budgets; a codec pass alone is insufficient. A faster retained-cause
reader must reproduce full-review selection/amendments/provenance and exact topic
IDs, including co-report/companion and manuscript paths. Borrowed projection
payloads must not mutate sources or escape as a review. A size-only validator
must match the real canonical encoder's byte count and refusals, including NFC,
escaping, aliases and all depth/collection/string/integer limits; the entire
original preview ceiling still applies. Integrated source
delivery remains I05; the private real-paper import remains unrun. See the
[implementation ledger](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#original-ledger-migration-implementation-plan).


These are next-version acceptance oracles for the owner's issue planning and
[ADR 0023](../../architecture/decisions/0023-personal-argument-import-and-sharing.md).
The [prior-argument import](../../development/workflow.md#prior-argument-mapping-preview)
now supplies exact-reviewed registration, source-aware personal reasoning and
private read/save/backup return. Owned tests distinguish imported AI/mixed/unknown
ancestry from new human Contributions, refuse altered source references, retain
unknown authorship and exclude independent omitted candidates. These are
behavior checks, not original-source fidelity or human-use evidence.
Named read-only anchor registration/impact/private return now has owned CLI/PTY,
origin-return, stale-source, capacity and old-reader checks. This certifies no
private source fidelity or graphic correctness.
Typed measurements now have owned exact-value, append-only correction, declared
condition query and private-return checks. Registered-rule original/amended
assessment paths, private sourced questions and selected canonical sharing now
have owned checks; these checks do not revise F0 or count as V0
evidence. The
[issue implementation plan](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#real-paper-migration-implementation-plan)
owns sequencing/tests; the
[domain proposal](../../designs/2026-08-03-domain-model.md#personal-paper-lifecycle-extension-planned)
owns engineering ceilings and versioning. Use separately identified synthetic
fixtures until a person explicitly supplies and checks their private source.

| Case | Observable pass condition |
|---|---|
| Whole-paper capacity | New profile accepts the declared combined fixture, reports actual per-type/byte capacity and meets measured host budgets; exact-overflow input refuses before publication. Legacy six histories/goldens remain byte-identical; actual old readers refuse small and large new frames without changing canonical data. |
| Existing argument import | Dry-run changes nothing; exact confirmation registers only selected/dependency-closed mapped personal records once, retaining source dates/reasons/origins separately from local import. It invents no prior receipt or new experiment. Invalid/stale/import-interrupted cases leave source and destination science unchanged. |
| Partial meaning | Unsupported fields remain retained with source pointers and visible unresolved markers after restart/backup. Complete independent records remain usable; an operation needing unimplemented typed meaning refuses while preserving work. Later mapping appends and never silently replaces current writing. |
| Multiple manuscript uses | One changed claim or corrected observation reaches every explicitly associated text/figure/table/caption with deterministic before/after witness paths; unrelated and outside-coverage locations remain distinct. Source stays read-only and old single-anchor meaning is preserved. |
| Wording and co-report | Supported yet direction-only/appendix-only status retains its limitation. Lint names a literal forbidden phrase and a missing declared companion without certifying semantic correctness. Two definition-specific readings remain separate, share the same reviewed reporting obligation and retain original reason/origin through return. |
| Typed measurement and registered rules | Stable table cells/conditions can be queried and corrected append-only. A post-result rule/reference/tolerance amendment retains the original values, registered rule and failed result; confirmatory claims and unknown/source-claimed chronology are explicitly distinguished from app-observed ordering. Coverage never overwrites claim scope. |
| Private critique | A raw original and human question survive private save/backup but are not empirical evidence. Known private originals/identities and direct quotes are excluded from default export/provider projections, including origin/label/diagnostic paths; neutral wording is human-reviewed and not automatically certified anonymous. |
| Selected share projection | Only selected science plus disclosed allowed dependencies appears; reasons require their own selection. Private source references use redacted stable IDs. Identical source/policy/selection reproduces bytes; changed source/output/selection/policy fails verification. Existing edited destination is retained and export neither commits Git nor restores private history. |
| Entry and manual continuity | Unsupported runtime has a concrete documented setup route. Supported source extraction provides actual terminal authoring/read/return without a provider, native key or internal JSON editing. Failed AI/new-schema compatibility leaves manual work and retained origin intact. |

Judge the first useful checkpoint by whether a person can bring their existing
argument and reasons, inspect what remains unresolved and return after exit.
Do not require the whole future roadmap before showing that checkpoint or
substitute synthetic/model checks for actual private-source fidelity or benefit.

#### Metadata registration acceptance

Declare new AI/mixed/unknown input separately from a human confirming actor and
source-claimed authorship. An undeclared new input cannot become human because a
protocol source claims human origin. Old commands/envelopes/goldens stay unchanged;
new frames refuse old readers. Declared/source AI survives revisions, node read,
sharing, save/reopen and private backup return. New co-report AI/unknown input
cannot use a not-required explanation disposition.

Batch independent wording/companion, structured measurement, protocol/gate,
anchor and critique requests through existing validators. Complete selected/omitted
scope and graph effects precede one confirmation/save. Invalid late entry, missing
prerequisite, malformed selection, changed source/input/private project and cancelled
review create no partial registered prefix. Retained raw input is exact and
private; repeated identical input refuses. No original ledger or newer judgment
is overwritten and unsupported pointers remain unresolved.

Use the graph action, Unicode private path, resize, all-page reading, literal
confirmation and Esc return with original selection/writing intact. Saved-source
failure must retain live writing and prevent blind retry. Critique originals and
omitted raw requests cannot enter default sharing/full-readable export or provider
context. Verify candidate reconstruction and one saved-write boundary including
interruptions. Focused synthetic tests and an actual Mac terminal rehearsal cover
the implemented origin/batch/graph paths; the existing plan records release
regression, review evidence and remaining unobserved cases.

#### Selected canonical sharing acceptance

Select owned science whose internal ID contains a confidential marker; repeated
exports map it through saved opaque IDs and allocate/write no private state.
Explicit reasons appear only when separately selected. Incoming scientific basis,
mandatory companions, co-reported scopes and protocol failures/amendments remain
in the disclosed required closure, including an experiment selected by itself.
Registered anchors contain structure without manuscript bytes/path/digest. Typed
tables retain exact cells/units/semantic condition labels with local coordinate
joins. AI/unknown origin and unresolved counts remain honest about source coverage.
Unmerged or omitted AI claim-status alternatives cannot alter main-claim origin;
a separately recorded branch-context flag remains distinct.

Known private critique text/identity/path copies in questions/reasons stay omitted
in resolvable placeholders; known literals copied into selected science refuse.
Source chunks/hashes, private IDs, origin payloads, notes and unselected writing
never enter public bytes. Omission coverage and anonymity/source fidelity limits
remain visible. Existing files/symlinks, stale selection/private source/reviewed
parent and failed writes cannot overwrite or publish a partial projection. First
file reads do not fail because access time changed; terminal control/bidi characters
are shown as JSON escapes without losing the complete reviewed meaning.

An actual owned PTY export into a paper Git directory and fresh-process
`verify-export` preserve private saved bytes. Changed output, policy, selection or
saved private revision fails verification. A large-paper projection reproduces
bytes with resolved references; measured limits belong to the execution plan.
Legacy private export/backup, old schemas/goldens and source extraction remain
unchanged in meaning. No Git commit, research egress, restore authority,
scientific correctness, anonymity or user understanding follows from these checks.

#### Private critique acceptance

Use owned private-original, identity and path markers with a separately authored
question. Capture changes no observation or claim status. Questioning a claim,
referencing a plan/completed record and linking an exact reviewed claim/wording
consequence form an inspectable path; none is empirical support or resolution.
An unchanged merge dependency cannot be labeled a claim change. A prior consequence
may be explicitly referenced as recorded before app capture, with outside
chronology unverified. Origin and every question revision/reason survive return.

Exact raw capture bytes are retained privately; scientific history, graph, default
TUI/neutral CLI and capture preview exclude originals, identities and private
labels/hash/handles. Explicit local original reading restores them. Normalized
reformatted duplicates refuse, source omission/tampering/orphans refuse and the
128-question/32-revision/512-link budgets fail before append. Default reference
projection excludes all question/reason/source prose, even deliberate known-secret
copies, and maps all references to saved opaque IDs. Missing mapping refuses with
a generic redacted error. This is not proof of anonymity or the full share export.

Actual PTY capture/fresh open/quit and private backup/fresh restore preserve source
bytes and writing; old shipped readers refuse new frames. Input/source changes and
cancel cannot persist a partial original. Full JSON export refuses before file
creation, while explicitly private backup retains originals. Provider attachment
and context compilation refuse before credentials/egress. No automatic source
interpretation, scientific approval, manuscript write or resolved critique is
inferred from these owned checks.

#### Protocol and gate acceptance

Use five owned result shapes: failed prediction; consistent but non-discriminating
result with required limitation; registered cross-run identity failure followed by
an explicit changed reference; tolerance widened after the result; primary and
reversed sensitivity readings retained together. Original rules/failures and human
reasons remain beside later assessments, while measurement cells and claim status
stay unchanged. Exact observation/event, association and per-gate rule versions
bind each assessment; gate basis is set-like and order cannot change its identity.

A commit/unseen claim is source-claimed or unknown, never verified outside timing.
Preexisting app observations at association and contradictory before-result
amendments remain visible. Prediction consistency cannot certify gate validity:
failed/incomplete/unknown/no-declared-gate coverage is separately displayed.
Changed source/input/plan/head/evidence refuses stale review before saving;
correction/retraction leaves old assessments visible and marks their basis stale.
Superseded rules cannot gain a fresh association/amendment; original registered
assessments remain inspectable. Imported plan view annotations do not change the
scientific digest, and AI/unknown origin cannot be erased by a human judgment.

Dependent claim/observation/Interpretation/plan reading shows original/current
protocols through scientific paths, excluding structural containment. Global
registries in historical reasoning views are labeled as such; an absent plan is
unavailable for comparison rather than changed. Exact prefix replay
still omits later records. Actual PTY review/record/open/quit, origin/writing return,
backup/fresh restoration and shipped old-reader refusal preserve saved bytes.
Provider access still refuses for this profile before credentials/dispatch. Owned
checks establish no outside chronology, scientific fidelity, understanding or
real-user benefit.

#### Structured measurement acceptance

Use owned 18×3 decimal cells, declared leg/dose/model/seed conditions and explicit
missingness. Exact integers/text/decimal precision replay without floats. A
single-cell correction retains every other cell and prior revision; stale input,
unknown cells/conditions/type, duplicated IDs and capacity refuse before saving.
Changed units/estimand/conditions require an explicit new measurement identity,
and altered cell meaning cannot reuse an ID from any retained table. Generic
text corrections cannot erase a table. Invalidated/retracted observations keep
history and are disclosed as inactive query basis.

Transform an imported text observation: source digest, original origin, historical
content and unresolved source remain unchanged. A supporting-evidence query through
a direct edge or Interpretation returns one global observation identity, exact
units and matching rows. `dose=max` uses the explicitly declared ascending group;
no inferred scope/claim status or scientific strength is written. Local query
graphs disclose unstructured, inactive and hidden basis.

Explicit artifact checks match a claimed file hash and one JSON pointer/cell,
report mismatch/unavailable/symlink/changed input, and change no source or science.
A successful check is not unit/estimand/fidelity verification. Complete preview,
cancel, exact input/source/project changes, literal recording and actual PTY
fresh open preserve writing, original source, table and older cells. Backup/fresh
return reproduces saved bytes; old checkpoint/frame readers refuse the new format.
Existing legacy goldens remain unchanged. Paper profiles continue refusing
provider use before credentials/dispatch. Synthetic verification does not establish
actual private-source conversion fidelity or user benefit.

#### Personal-alpha feedback tasks

These tasks apply to the current AI-off personal workspace, not the deferred
protected/native or live-AI workflow. They are a proposed human feedback exercise,
not completed usability evidence, a comprehension exam or a V0 protocol. Use one
disposable project and the [public personal setup and keys](../../development/workflow.md#personal-project-writing-in-the-terminal).
The following Korean content is invented for this exercise; it does not extend
or replace the original saturation fixture. No source artifact is opened or
experiment run by the app. Keep the local version/artifact identifiable when
reporting a problem.

**먼저 볼 것.** ① 그래프가 논문의 주장과 근거를 설명하는가,
② 판단하는 동안 도움이 되는가와 같은 이유를 다시 쓰게 하는가,
③ 다시 열었을 때 판단 이유와 미완성 생각을 이어 갈 수 있는가.
UC-1–UC-3을 먼저 해 보고, 이후 UC-4–UC-6으로 영향·정정·복귀를 확인한다.

**시작 화면의 전환 조건.** UC 번호와 키보드 `1`/`2`는 별개다. 새 프로젝트에서는
우선 Argument에서 작성한다. UC-2에서 결과를 직접 확인해 기록한 후에 `2`를
시험하고, UC-3에서 연결을 포함한 추론을 기록한 후 공유 근거의 사용처를 본다.
메뉴·편집기에서 Esc로 그래프로 돌아온 뒤 누른다. 관찰이 없는 상태, 결과 초안,
기록된 관찰과 아직 초안인 연결의 차이는 [전환 안내](../../development/workflow.md#terminal-paper-prototype)에
설명되어 있다. 단축키가 작동하지 않는다고 연구 결과를 만들어 채워서는 안 된다.

**하나의 합성 연구 주제.** 아래 T/C/E/P는 이 설명에서만 쓰는 이름이다.
앱의 ID·별칭은 자동으로 정해지므로 입력할 필요가 없다.

| 입력 | 복사하거나 바꾸어 쓸 예시 |
|---|---|
| 프로젝트 제목 | 반복 요청에서 캐시가 응답 지연에 미치는 영향 |
| T: 논제 | 응답 캐시는 동일 키의 반복 요청 지연을 줄인다. |
| 첫 연구 질문 | CPU-A와 2 MiB 캐시에서 반복 요청의 평균 지연이 줄어드는가? |
| C1: 주요 주장, 부모 T | CPU-A·2 MiB 캐시에서 동일 키의 반복 요청 평균 지연은 캐시 사용 시 더 낮다. |
| C1의 범위 | CPU-A, 동일 키, 각 조건 100회 요청, 외부 네트워크 없음. 다른 CPU와 최초 조회는 미확인. |
| C1a: 하위 주장, 부모 C1 | 이번 측정에서 평균 지연 감소량은 9 ms다. |
| C1a의 범위 | 이 실험의 15 ms − 6 ms 비교에 한정한다. |
| C2: 주요 주장, 부모 T | CPU-B에서도 같은 지연 감소가 재현된다. |
| C2의 범위 | 아직 측정하지 않은 가설이다. CPU-A 결과만으로 확인하지 않는다. |
| 판단 | 측정한 CPU-A 조건에서는 캐시가 반복 요청의 평균 지연을 줄였지만, CPU-B와 최초 조회에 대한 결론은 보류한다. |
| 판단 이유 | CPU와 키를 고정한 비교에서 15 ms가 6 ms로 줄었다. 다른 CPU와 최초 요청은 확인하지 않았으므로 일반화하지 않는다. |

E1의 **결과 초안**에 아래 값을 입력한다. 판단/이유는 UC-3에서 원래 논제의
작업에 한 번 작성하므로 이 결과 입력에서는 비워 둔다.

| 결과 입력 항목 | 예시 |
|---|---|
| 관찰 내용 | CPU-A에서 동일 키 100회 요청의 평균 지연은 캐시 사용 시 6 ms, 미사용 시 15 ms였다. |
| 실행·방법 참조 | feedback-run-01: 각 조건 100회 요청, 요청별 지연의 산술 평균. 합성 실행. |
| 출처 참조 | feedback-cache-01.csv — 이 사례를 위한 가상의 출처 이름. 실제 파일은 제공하지 않으며 앱이 열지 않는다. |
| 조건 | CPU-A, 2 MiB 캐시, 동일 키, 외부 네트워크 없음. |
| 측정 이름 | mean response latency |
| 측정 정의 | 요청 시작부터 응답 완료까지 시간을 100회 측정한 산술 평균. |
| 값 / 단위 | 6 / ms |
| 비교 대상 | 캐시 미사용: 15 ms |
| 한계·불확실성 | CPU-B와 처음 조회하는 키는 측정하지 않았다. |

**UC-1 — 결론을 모르더라도 논증을 만들 수 있는가.**

- 행동: 새 프로젝트에 제목·논제·질문을 입력한다. 논제에서 `;` →
  **Add a claim or subclaim**으로 C1, C1a, C2를 만든다. 아직 판단·이유는
  작성하지 않는다. 필드 편집 후 Ctrl+S로 돌아오고, 양식에서도 Ctrl+S로
  초안을 유지한다. **Open argument drafts** 목록에서 `g`로 초안 그래프를
  열어 긴 주장과 부모·하위 주장을 읽는다. Esc는 목록, 다시 Esc는 원래
  기록된 그래프로 돌아온다. UC-3 기록 전의 초안 그래프와 기록된 그래프를 구별한다.
- 기대: 빈 상태에서 사람의 내용만으로 초안 그래프를 만들 수 있다.
  논제·주요 주장·하위 주장·미측정 가설이 구별되고, 전체 문장과 범위를
  읽을 수 있다. 결과가 없다는 이유로 창작을 막거나 근거를 만들어 내지 않는다.
- 중점: 화면만 보아 무엇을 주장하는지 이해되는가? 작은 카드의 요약 때문에
  조건·핵심 비교가 사라지는가? 첫 행동을 찾는 데 내부 용어나 단축키 암기가 필요한가?

**UC-2 — 결과 초안과 근거가 구별되고, 공유 근거가 연결되는가.**

- 행동: 원래 논제로 돌아가 **Draft a result and source**에 E1을 입력한다.
  `c`로 확인 미리보기를 열고 한 번 Esc로 취소한다. 다시 열어 전체를 읽고
  명시적으로 기록한다. 원래 논제의 작업으로 돌아와 **Open argument drafts**를
  연다. 출처 변경 안내가 있으면 `s`로 이전 초안과 현재 출처를 확인·갱신한 뒤,
  **Connect research records**로 아래 연결과 각각의 이유를 만든다.

  | 연결 | 사람이 입력할 이유 |
  |---|---|
  | E1 → C1, supports | 고정한 CPU·키·요청 수에서 캐시 사용 평균 6 ms가 미사용 15 ms보다 낮다. |
  | E1 → C1a, supports | 이 측정의 평균 차이는 15 − 6 = 9 ms다. |
  | E1 → T, qualifies | CPU-A의 반복 요청만 측정했으므로 논제의 적용 범위를 제한한다. |
  | C1 → T, supports | 시험한 반복 요청 조건에서 논제를 뒷받침한다. 다른 CPU로의 일반화는 미확인이다. |

- 기대: 취소 시 근거는 생기지 않고, 직접 확인한 뒤 하나의 E1이 생긴다.
  여러 주장에 연결해도 같은 관찰이며 출처·측정 정의·단위·조건은 보존된다.
  부모 관계는 논증 구조이고, supports/qualifies는 별도의 과학적 관계다.
  C2는 측정하지 않았으므로 확인된 주장처럼 표시하지 않는다.
- 전환 확인: 결과 확인 직후 Esc로 그래프에 돌아와 `2` → Evidence uses,
  `1` → Argument를 시험한다. 이 시점에서 연결이 아직 초안이면 Evidence uses의
  사용처는 0일 수 있다. 초안 연결은 **Open argument drafts**의 그래프에서 보고,
  UC-3의 추론 기록 후에 기록된 공유 근거 경로를 확인한다.
- 중점: 관찰과 해석을 혼동하는가? 그래프에서 E1의 여러 용도와 방향을
  찾을 수 있는가? 카드·연결 선택·reader를 왕복하면 원래 위치로 돌아오는가?

**UC-3 — 한 번 만든 판단을 그 결과까지 이어 갈 수 있는가.**

- 행동: 계속 원래 논제의 같은 작업에서 **Plan a follow-up experiment**를
  만든다. P1의 대상은 C1, 질문은 “같은 조건의 새 100회 측정에서도 지연
  감소가 재현되는가?”, 조건은 같은 CPU-A·2 MiB·동일 키다. 측정은 E1과 같은
  평균 지연 정의·ms·캐시 미사용 비교를 쓴다. 아직 실행하지 않은 계획으로 둔다.
  **Write an interpretation**에서 위 판단과 E1의 명시적 관찰 연결을 작성한다.
  **Open argument drafts**에서 그 해석을 선택해 `J`로 비교 후 판단 문구로
  재사용한다. `e`에서는 판단 이유를 한 번 작성하고 Ctrl+S로 유지한다.
  **Record selected reasoning personally**에서 선택·필수·제외 내용과 원래 이유를
  읽고 `G`로 전후 그래프를 본다. 한 번 취소한 뒤 새 미리보기에서 기록한다.
- 기대: 판단·이유를 새 결정 양식에 다시 전사하지 않는다. 선택한 주장·연결·P1이
  기록되고 대안과 원래 이유가 남는다. 취소는 기록하지 않는다. 계획은 실행 결과가
  아니며, 원고 후속 작업은 열려 있고 원고 파일은 변경되지 않는다.
- 전환 확인: 기록 후 그래프에서 `2`로 E1의 기록된 supports/qualifies 사용처를
  따라가고, `1`로 논제 중심 화면에 돌아온다. 같은 E1과 원래 이유가 유지되어야 한다.
- 중점: “지금 무엇을 왜 선택하는가”를 그래프와 같은 판단에서 따라갈 수 있는가?
  양식 사이 이동·중복 입력이 생각을 끊는가? 기록과 원고 완료가 혼동되는가?

**UC-4 — 후속 실험의 가능한 영향을 그래프에서 읽을 수 있는가.**

- 행동: UC-3에서 기록한 미실행 P1을 선택하고 `s`로 supports, challenges,
  inconclusive 가정을 번갈아 본다. 연결과 원문을 읽고 전체 그래프로 돌아온다.
  큰 터미널과 80×24 정도의 작은 창에서 비교한다.
- 기대: 가정은 실제 E1이나 새 측정값이 되지 않는다. 명시적인 과학적 연결을
  따라 C1과 T의 검토 경로를 볼 수 있고, C2는 이 경로 밖이다. C1a의 부모 관계만으로
  과학적 영향이 전파되지는 않는다. 경로 밖은 “참/거짓이 확정됨”이 아니라
  “이번 계산 경로에 포함되지 않음”이다. 화면 밖 노드·연결도 읽을 경로가 남는다.
- 중점: 별도 장문 설명 없이 영향 범위와 한계를 알 수 있는가? 카드가 잘리거나
  화살표가 겹쳐 어떤 주장으로 이어지는지 놓치는가? 가정을 실제 결과로 오해하는가?

**UC-5 — 결과를 정정해도 당시 판단 이유를 잃지 않는가.**

- 행동: E1에서 새 결과 초안을 연다. 정정 내용은 “CPU-A에서 동일 키 100회
  요청의 평균 지연은 캐시 사용 시 8 ms, 미사용 시 15 ms였다.”,
  값은 `8`, 이유는 “타이머 보정 누락을 수정했다.”만 입력한다. 다른 결과 필드는
  비워 둔 채 `a`로 정정 미리보기를 읽고 기록한다. 과거 6 ms와 당시 판단 이유,
  C1a의 “9 ms”를 최신 관찰과 비교한다. 이후 **Start the next research question**에서
  “보정 후 결과로 주장 범위를 어떻게 바꿀까?”를 시작해 새 판단을 이어 간다.
- 기대: 정정은 원래 기록을 삭제하지 않는다. 새 값의 차이는 15 − 8 = 7 ms이므로
  예전 “9 ms” 주장과 이유를 사람이 재검토할 수 있다. 앱이 과학적 결론이나
  이전 주장을 자동 수정하지 않는다. 이전 에피소드의 판단·대안·후속 작업은 남는다.
- 중점: 최신 값과 당시 값·판단을 혼동하는가? 다시 읽었을 때 어떤 이유로
  그 결론을 냈는지 복원되는가? 정정 이후 바꿀 주장과 남길 주장을 판단하기 쉬운가?

**UC-6 — 중단·재시작·복원 후 생각을 계속할 수 있는가.**

- 행동: 노드 메모를 Ctrl+S로 유지한다. 판단 편집기에 “CPU-B는 별도 실험이 필요…”를
  쓰다가 Esc로 나와 미완성 입력을 남긴다. `q`로 저장·종료하고 같은 프로젝트를 다시
  연다. 유지된 판단/이유와 `U`의 미완성 입력을 각각 확인한다. 다시 종료한 뒤
  [기존 백업·내보내기·새 폴더 복원 절차](../../development/workflow.md#personal-project-writing-in-the-terminal)를
  수행하고 복원본을 연다. 살아 있는 터미널 세션 대신 저장된 작업을 백업한다.
- 기대: 유지된 내용과 취소한 미완성 내용이 구별되어 돌아온다. 원래 판단 이유,
  정정 전후 근거, 메모, 연구 질문·대안과 열린 후속 작업을 찾을 수 있다.
  복원본은 백업 시점의 저장된 작업이며 원본을 덮어쓰지 않는다. 내보낸 JSON은
  복원용 백업과 다르다. 외부 실험 파일·원고 파일은 백업에 포함되지 않는다.
- 중점: 재시작 후 같은 내용을 다시 입력해야 하는가? “무엇을 하려던 중인지”
  회복되는가? 작은 터미널에서도 미완성 작업과 원래 출처를 오갈 수 있는가?

**진행 한계와 피드백.** 하나의 에피소드에서는 선택한 해석·추론 기록이 한 번이다.
UC-3 전에 원하는 주장·연결·P1을 함께 준비한다. 다음 질문을 시작하면 이전 결과
초안은 읽을 수 있지만 확인할 수 없으므로 미확인 결과를 먼저 마무리한다.
새 질문 이후에는 새 작업에 판단을 쓰며, 이전 작업을 덮어쓰지 않는다.
이 사례는 일상적인 판단·이유 재사용과 복귀를 본다. 실제 AI 품질과 보호된 이해
부채 생성·종결은 현재 알파의 수행 사례가 아니다.

피드백은 “어느 화면·동작 → 기대한 동작 → 실제로 생각/작업이 끊긴 지점”처럼
간단히 전하면 된다. 별도 판단 일지나 점수표를 작성할 필요가 없다. 사실·출처·
개인 정보가 담긴 전체 연구 자료나 대화 기록을 공유할 필요도 없다. 사용자 관찰
결과가 나오기 전에는 위 기대가 인간 사용성 검증을 통과했다고 기록하지 않는다.

## 11. Prospective use

The first personal GitHub alpha is checked by the
[personal terminal oracle](#104-personal-terminal-alpha-oracle) and the
[source-delivery contract](../../product/releases/validation-prototype.md#55-source-delivery-readiness)
under [ADR 0017](../../architecture/decisions/0017-personal-terminal-alpha.md).
Its manual own-project feedback requires no native key or protected authorization.

The following table retains the deferred protected own-project contract from
[ADR 0016](../../architecture/decisions/0016-own-project-source-release.md).
ADR 0017 supersedes its first-release timing, while preserving these requirements
for protected capabilities. This table is not the personal-alpha completion
checklist; none of its actual authority or independent-user observations is
established by the bundled demo.

| Case | Protected-workflow pass condition |
|---|---|
| Clean source to own paper | Declared checkout/artifact and prerequisites reach public setup/doctor and an empty compatible project; only the human-entered thesis appears, with no invented result/evidence or maintainer-local file dependency. |
| Manual authoring and confirmation | With AI disabled, author claims, typed rationale-bearing connections and unrun plans; reference/capture/explicitly confirm a result and form one judgment without a completed external decision log or internal JSON edits. |
| Exact acceptance and restart | Actual foreground authorization and private single-use consumption commit the selected scientific effects; a new process recovers the same graph, evidence, reason, signatures and unfinished writing. |
| Failure and same-device rescue | Cancel/stale/replay/cross-project/two-process/interrupted-write cases preserve originals. With the original approval key/enrollment intact, restore an independently verified backup to a fresh destination; a separately reviewed same-key resource transition precedes resumed accepted writing. Key/enrollment loss or unverifiable checkpoint grants no write authority; verified readable recovery/export stays distinct. Public actions require no internal editing. |
| Source or version changes | Changed/unavailable manuscript retains prior writing and source. A compatible newer build provides read-only status/export and names the build mismatch; unsupported format/build/key transitions refuse accepted mutation without replacing history or performing an implicit migration. |
| Deferred capabilities stay unavailable | Live AI/AI-influenced acceptance, automatic manuscript write, accepted debt closure and replacement-device continuation cannot invoke a mutation; existing provenance and unresolved work remain intact and inspectable. |
| Independent supported user | An unfamiliar researcher/second profile completes declared setup, own-project writing, save/restart and recovery on the supported host, without coaching or a hardware/software fixture being relabeled as actual authority. |

P0 still passes before the protected H0/H1/V0 real-research program. Personal-alpha
feedback uses the person's supplied and checked sources under ADR 0017 and does
not close that historical mapping. Alpha completion does not pass the full
H0-recorded/manuscript workflow, H1 live provider gate or V0 below.

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

### 13.1 Optional AI follow-up acceptance proposal

**Contextual discussion amendment (2026-10-12).** Under
[ADR 0022](../../architecture/decisions/0022-contextual-advice-and-explicit-edits.md),
first read plain-text advice on selected science without requiring graph items.
Use a Korean question, include no earlier messages by default, then explicitly
choose a retained reply for a follow-up. Check original question/model/context
and selected-message integrity, three-attempt continuity, cancellation, stale
input, unsafe/oversized text refusal and manual continuation. An invalid later
typed edit must leave the earlier advice readable. Advice cannot enter existing
item staging or become an evidence record. Save/restart and fresh-directory
backup restore must retain the answer with AI disabled and no send capability.
Unsent questions have an explicit session-only/quit-loss boundary.

The [owned controller checks](../../../tests/application/test_provider_proposal_work.py)
and [actual terminal checks](../../../tests/application/test_tui_proposals_terminal.py)
exercise this discussion slice. Actual live discussion remains a separate
observation. The subsequent selected passage/action origin and human recording
checks remain required by the [current L04 order](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#l04-contextual-assistance-implementation-order).
Do not apply the legacy fixture's two-item requirement to a discussion-only
answer, or count readable advice as completion of the selected-edit journey.

For the local edit path, select a canonical answer span into each supported
form; no request or graph acceptance occurs. Cancel comparison and verify no
draft; explicitly prepare once and refuse replay. Retain missing fields and
original AI text through editing, unkeep/reopen and ordinary backup. Invalid
span, source mutation, expiry and full checkpoint must preserve previous work.
Unfinished passage input must coexist with independent valid typed staging;
retain its source once and refuse erasure/eviction while origin references it.
Clarification text must be fully readable, with explicit follow-up and selected
prior-message inclusion; a session-only unavailable source offers no local edit.
An unrun plan cannot supply scientific support. For an explicit instruction,
check the separate exact input binding, selected previous messages, four-item
bound, clarification-only response, selected dependency closure, graph preview
and atomic failure. Existing typed validators continue rejecting unknown or
unselected endpoints, cycles and fabricated evidence. Reading either mode never
restores send or staging consent.

The connected local recording cases now exercise three selected/required passage
origins (claim, connection and unrun plan), an omitted independent suggestion,
the original human reason, explicit explanation choice and separate partial
writing. Correct a measured value, retain the original cause/AI text, save,
open in a fresh AI-off process and restore a backup into a new directory. A later
human-authored subclaim inherits its recorded parent's AI origin. A direct edit
retains explicitly included advice and its original instruction, including after
eligible typed-payload erasure. Inspect the question, requested/reported model,
original answer/context and passage alongside human edits. Refused erasure of
required or copied source text must leave restored work unchanged; cancellation,
expiry, changed writing, failed save and origin tampering preserve prior data.
The [provider return cases](../../../tests/application/test_provider_proposal_work.py)
and actual PTY case above exercise this C outcome. PTY starts with saved edited
candidates, records through real terminal input with Korean partial explanation,
resizes, quits and reads origin/explanation from a restored project with AI off.
Actual connected usefulness remains D acceptance, not inferred from these local
checks or from a stored explanation choice.

Proposed 2026-10-08 for the
[four-unit AI follow-up](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#optional-ai-follow-up-implementation-plan).
These are future end-to-end checks, not whole-flow observed passes. The next
personal-AI scope is selected under [ADR 0018](../../architecture/decisions/0018-optional-personal-ai.md);
the current public personal app remains AI-off. On 2026-10-10 the owner selected
these existing live checks as a prerequisite for the next
[GitHub publication](../../product/releases/validation-prototype.md#ai-connected-github-publication-milestone).
This does not convert the current internal/frozen observations into public
live passes. The L01 selected-input and typed-
ingress subset is exercised in [portable checks](../../../tests/application/test_paper_proposals.py)
and the [offline example](../../development/workflow.md#typed-proposal-ingress-exercise).
The [L02 offline backend cases](../../../tests/application/test_paper_proposal_work.py)
add atomic selective staging, retained human/item origin, explicit personal
explanation, original partial context, correction, fresh-process and ordinary
backup/restore checks. They cover a manual judgment with an AI relationship,
independent siblings, mapped dependencies and quota/save/reader failures.
The [offline terminal checks](../../../tests/application/test_tui_proposals_terminal.py)
exercise L03 contextual selection, editing, explicit explanation and ordinary
restart/backup return. Actual provider protection and useful human assistance
remain unobserved. Use the invented cache-study inputs from the
[personal feedback tasks](#personal-alpha-feedback-tasks), with a separately
identified context-matched frozen response before any live provider. New source
references remain unopened; all invented runs are fixture data.

**Assistance fixture.** Before the original judgment is complete, request a
critique of generalizing CPU-A results to CPU-B. A useful candidate keeps the
6 ms versus 15 ms measurement and its conditions, flags the unmeasured CPU-B
claim, suggests a narrower claim/qualification with explicit source references,
and optionally proposes a same-condition repeat or a CPU-B discriminating
experiment. The latter remains planned with no invented result. The response
may suggest an interpretation, but cannot confirm evidence or grade the person.
Create at least two independently selectable suggestions so selective adoption
is observable; do not count whole-judgment replacement as that behavior.

The L04 [BYO preparation checks](../../../tests/application/test_provider_profile.py)
exercise private create-only configuration, no inline secrets/key lookup/network,
exact selected-science wire preview and typed API response decoding. Check that
an own-project preview leaves saved history/manuscript bytes unchanged and
creates no attempt/consent; configuration and keys remain absent from backup.
Changed endpoint/model/secret-reference/output settings/context or expiry refuse
reuse. Symlink/hardlink/nonprivate/in-Git configuration and malformed/tool-bearing/
truncated responses refuse. `dispatch_available: false` remains visible even for
localhost. These are preparation observations, not actual endpoint qualification,
live return or novel-task usefulness passes.

The separate Codex-profile preparation cases use the same private configuration
store, explicit model and existing graph picker without an API-key requirement.
Check complete selected application input/optional draft, honest service-origin
and unverified CLI wrapper/destination labels, candidate-versus-observed client
version, bounded bytes, expiry, changed profile/context/draft and independent
cancel revocation. Public saved-project preview and actual wide/narrow PTY
manual quit/restart preserve writing/source and create no client, attempt, trace
or consent. The API qualification test hook cannot activate Codex or fall through
to API transport. Old API profile/wire/history formats remain unchanged. These
checks do not qualify the actual Codex runtime or observe a live reply.

The separate [actual Codex boundary probe](../../development/workflow.md#personal-llm-configuration-and-unsent-preview)
uses an empty client home and an owned scripted peer without inference or login.
Check actual shell/question dispatcher refusal and an unchanged owned canary;
remaining advertised tools cannot be called executable merely by name.
Absent/malformed/duplicate tool metadata, control characters, credentials,
timeouts or missing refusal observations cannot pass. A successful observation
still reports `dispatch_supported: false`: custom-provider fallback metadata is
not the selected authenticated model, and that route's resource access, exact
egress and checked return remain required. No test flag or saved observation
can activate public Codex dispatch.

The separate `--file-access` observation must reproduce the original loader
abort, then start the same pinned CLI with only literal `/` read access added.
Require positive permitted-file read/write controls outside cwd, successful
permitted CLI spawning/version exit and actual outside-file
direct/symlink read/write, directory-read and shell-spawn permission refusals.
An unchanged outside canary/directory, complete cleanup and strict Boolean observations
are required. No credential or model turn is supplied. A literal root lookup
is not a recursive filesystem allowance. This file/exec observation is distinct
from authenticated account controls and cannot certify Mach IPC, HTTP content,
retention, request counts or public support.

The internal compiler now denies Mach lookup except four exact observed OS
global service names and denies authorization-right acquisition. No local-name,
prefix or wildcard service exception is permitted. Actual login controls
under that policy reach the checked ephemeral thread and close network tunnels
before any model input can leave. The routing failure reappears without the
required service exceptions. This is an authentication observation, not proof
that the permitted services expose no key/human-operation API or additional
keychain credential access beyond the named file. Preserve that
missing qualification and generated HTTP/retention/request-count evidence;
no observed-control record or configurable allowlist enables public AI.

The [internal Codex stdio cases](../../../tests/application/test_codex_app_server.py)
check exact current input before launch, client-advertised model/effort/text
capabilities before any thread or turn, ephemeral thread/model/version/policy,
disabled remote control, owned request/turn identity and bounded typed final
return. Missing login, tool/approval requests, executable items, ambient
instructions, changed model/version, duplicate JSON, unselected references,
partial/failed/cross-thread output and byte/deadline limits refuse. Cancellation
and timeout terminate/reap the owned client without returning adoptable text.
Pinned terminal `itemsView` may be full, summary or notLoaded (omitted means full).
Accept completed content only from owned item/completed events, never terminal-
only text. Summary can omit earlier items; notLoaded must be empty, while full
must list every owned completed ID. Any supplied terminal items must exactly
match with JSON type distinctions retained; unknown views, duplicates, changed/
foreign items, nonempty notLoaded and incomplete full views refuse. The terminal
status/acknowledgement, final-message uniqueness and unchanged typed scientific
validation still apply. Actual local CLI/SSE observations do not turn a remote
protocol failure into a qualified live response.
Missing/duplicate/aliased model rows, unsupported effort/modality or an unread
catalog page refuse before thread/turn creation; malformed catalogs, missing
required top-level fields and extra fields refuse too. A valid older catalog
without `inputModalities` still permits the checked scoped return through the
documented compatibility default. The catalog is not inference entitlement or actual
served-model evidence. Unexpected warnings still fail closed, and no automatic
model or effort substitution is permitted.
These are synthetic protocol cases, not actual authenticated access/egress,
origin-retention or useful human-assistance passes. Authenticated account updates
must remain ChatGPT during account/read, discard identity/plan data and still
require the account reply. Observed thread-setting notifications must preserve
exact model/provider/effort, context, approval, sandbox and null instruction override;
foreign threads, unknown fields or expanded permissions refuse. An internal
custom-provider echo cannot be silently rewritten as built-in. Anonymous actual
CLI observations reach account refusal; separate existing-login controls now
reach a checked ephemeral thread. Network closure before a synthetic turn
observes settings without model egress. These controls do not establish complete
file/IPC or generated HTTP qualification. An approved live diagnostic can reach
turn start and still fail without a checked response. Preserve that failure and
spent outbound attempt rather than pass live usefulness or infer an unrecorded
HTTP/authentication/schema cause. Any future diagnostic must retain only a
bounded error category/status projection, excluding raw messages, instructions,
paths and credentials; that projection remains an untrusted client observation.
The internal adapter now exposes that projection as ephemeral `result.failure`.
Check exact owned thread/turn identity, allowlisted installed-schema categories,
optional integer HTTP status 100–599 (never Boolean), exact Boolean retry
observation and standard matching RPC codes. Unknown detail remains unclassified;
raw error text and continuation instructions cannot survive the projection.
Failed turns supply no proposal, foreign notifications supply no owned diagnostic,
and scientific result metadata/checkpoint formats exclude the projection.
The pinned client may encode a service JSON envelope in `message` while its
category is `other`. Check bounded duplicate-free object parsing and only the
five known `service_error_code` values described in the
[adapter contract](../../development/workflow.md#internal-codex-app-server-adapter).
Arbitrary code/text/params, duplicate keys, non-object/oversized/nested-invalid
JSON and invalid Unicode must neither leak nor authorize a retry. Earlier exact
approved live diagnostics remain failed/spent with no known direct cause.
Codex generation uses the supported schema subset independently from unchanged
scientific validation. The exact preview/digest binds that projected schema;
changed generation must invalidate the old body, review and consent. Check
closed required fields, all four disjoint item kinds, nullable types and unknown-
keyword refusal. Removing generation-only limits cannot permit invalid IDs,
oversized text, duplicate references, unselected context or invalid dependencies
through typed ingress. Local actual-CLI HTTP controls may exercise a synthetic
strict-schema refusal and completion, but cannot prove remote service acceptance,
access/egress qualification or researcher benefit.
Owned failure fixtures cannot establish the cause of the earlier live failure.
Public Codex dispatch and existing saved formats remain unchanged by that adapter.
An identical, separately authorized synthetic diagnostic now completes a checked
typed reply under the repaired adapter. It remains a standalone input, not a
request owned by a personal project or a provider qualification. Changing its
context/digest to import that reply elsewhere must not be allowed.
Actual local HTTP controls observe nested `additional_tools`, developer/environment
messages and client metadata despite an empty top-level tool list. Check the
whole transmitted body; a top-level tool count cannot prove scoped egress.
The separate [offline HTTP compiler cases](../../../tests/application/test_codex_egress.py)
check selected-only input/instructions/schema, explicit no-tools/no-encrypted-
reasoning request, exact bytes/hash and independent current profile/context/time.
Expired/future/noninteger clocks, changed current inputs and an added field with
a recomputed binding digest refuse. Compilation/preview opens no socket or
credential and creates no consent; a future live owner must enforce ownership,
one-shot choice and controlled actual transmission separately. No relay, exact
endpoint acceptance, retention or novel-task benefit is established by these cases.
The separate [exact relay cases](../../../tests/application/test_codex_relay.py)
now check frozen body/header replacement, fixed upstream path, one counted
attempt, framing/size/compression/redirect refusal and no credential echo.
Check no-authentication version preflight before a login alias, dead/blocked
worker cancellation, exact matching wire outcome before typed incorporation,
visible retained scratch on uncertain cleanup and refusal of later starts.
The [contextual TUI cases](../../../tests/application/test_tui_proposals.py)
check complete HTTP read/confirmation, stale body/context/draft refusal,
independent Codex qualification before login/attempt, owned typed origin return
and unclosed-owner retention with one shutdown deadline. Also check a bounded
44-header service reply through the actual stdlib worker, with local request
count/line/aggregate bounds still refusing before upstream access. Separate
service count/line/aggregate failures must remain visible, bounded and
non-adoptable. The ephemeral failure projection accepts only known phase/category
values, discards secret-bearing error text and extra retry/message fields, and
never survives into scientific history or a reopened checkpoint. Response-header
refusal must identify status, framing, media type or encoding without raw values.
Duplicate content-type/encoding refusal, mixed-case identity headers and actual
stdlib chunk decoding are checked; trailing whitespace on the transfer token
cannot cause raw chunk framing to be reported as a relayed SSE response.
Missing, blank or JSON-labeled media headers accept only an actual bounded SSE
prefix. Check fragmented BOM/field prefixes, exact byte replay/counting, HTML,
actual JSON, empty/unknown content, the 2 KiB prefix and total body limits, and
credential echo split across inspected and remaining bytes. Real HTTP parser
and worker cases must cover missing media headers and a fully consumed body.
Real socket cases bound chunk-metadata dribbling by the absolute sniff deadline
and preserve the later body idle timeout after a slowly arriving valid prefix.
HTTP 200 without checked content cannot pass live qualification. These owned
controls do not establish service acceptance or human scientific judgment.
For an owned completed Codex message rejected by typed ingress, check distinct
canonical-JSON, schema and unselected-reference diagnostics. Unknown validator
text must map to a fixed category, never appear in diagnostics. Current-session
terminal history exposes the category without retaining it in personal saves or
reopened research, and the malformed response supplies no adoptable proposal.
Retained proposals may enter a new explicit local review under
[ADR 0020](../../architecture/decisions/0020-retained-proposal-review.md).
Check original/current reading before selection, no new request or attempt,
unchanged historical disposition and origin, refused expiry/erasure/context or
owner changes, and preserved IDs/human edits on repeated selection. Personal
recording, fresh-process return and backup/restore retain the original AI lineage;
reopening cannot restore an active review. Separate operator diagnostic files
must not be mislabeled as complete historical application attempts.
Actual target-specific CLI and native API positive/negative observations belong
in the existing L04 plan and must name their scope. Required OS cache channels
cannot be widened to arbitrary preference, IPC or key services. Refer to
[ADR 0019](../../architecture/decisions/0019-reviewed-codex-http-relay.md).
The separate checked Codex-origin cases in
[proposal retention tests](../../../tests/application/test_provider_proposal_work.py)
connect owned returns through dependency selection, human edits, explicit
personal consequence and fresh-process/backup return. Check shared offline/API/
Codex attempt accounting, unsent-preview preservation, current-input/capacity
preflight, cancellation/stale/expired non-incorporation, malformed metadata and
failed-save preservation. Distinct workspace v9/work v10/project v6 retain
bounded input/outcome commitments, without HTTP status, account/login data or a
client capability. Old formats remain closed and byte-identical; trace rewrites
refuse even with recomputed hashes. Raw-payload erasure/quota must preserve
adopted origin, original reason and independent explanation choice. Restored
responses are historical and cannot stage new items without an explicit new
local review under ADR 0020. These owned checks still
do not qualify actual authenticated access/egress or demonstrate useful live AI.

The [internal wire tests](../../../tests/application/test_provider_transport.py)
add owned disposable HTTP/TLS round trips, unchanged exact body/headers,
review-change/expiry/replay refusal, credentials isolated from argv/environment,
content and decoded endpoint paths, frozen DNS/connect/header/body-idle/total
waits despite later policy changes, redirects/errors/framing/body
limits, cancellation during spawn/validation and child reaping. Escaped secret
echoes in model or typed text refuse. Default trust rejects an untrusted TLS
certificate without importing a private CA override. Pre-header disconnect is
distinguished from malformed output. These component checks
enable no public app request and cannot pass actual provider qualification,
durable live origin/return or the novel human task below.

The [checked API retention cases](../../../tests/application/test_provider_proposal_work.py)
now connect owned wire returns to selective item origin, personal recording,
fresh-process and backup/restore. Check namespace model names, separate raw and
normalized hashes, frozen request-policy replay, pending/failure/cancelled/stale
history, mixed offline/wire three-attempt limits, preflight capacity refusal,
payload quota/erasure and immutable saved metadata. Restore no live capability;
preserve the original reason and explanation choice with AI off. These are
internal synthetic observations, not public live connectivity or qualification.

The [contextual provider UI cases](../../../tests/application/test_tui_proposals.py)
and [actual terminal cases](../../../tests/application/test_tui_proposals_terminal.py)
now exercise explicit public profile attachment/complete unsent preview, task
selection, tiny/narrow resize, read-before-confirmation and unqualified refusal
before key lookup/I/O. Owned peers with a test-only qualification replacement
exercise asynchronous polling, wrong-owner focus preservation, cancellation/
shutdown reaping before checkpoint, selective editing/recording, origin and
fresh-process/backup return. Default init/open and reopening without the profile
stay AI-off. Invalid/changed profiles and included-draft changes refuse without
dispatch; disabling retains earlier staged origin and manual writing. No actual
provider, service retention or useful researcher task passes from these cases.
Continue-writing leaves an omitted-draft request pending without stealing the
active editor on arrival. New unsent previews cannot revoke a pending request
or a completed current item batch without explicit decline/disable. Failure
projecting a completed history/item view preserves its owned trace and proposal
for reopening; a missing projected entry cannot crash polling.
Fault-injected polling/cleanup errors cannot skip the
final writing checkpoint or leave AI enabled; unavailable traces stay missing,
attempts remain spent and unconfirmed reaping is disclosed.

| Case | Observable pass condition |
|---|---|
| Ask before finishing the judgment | Blank/partial judgment and missing reason remain valid input for optional assistance. Manual authoring stays reachable before, during and after the attempt. |
| Select exact model context | Preview retains selected recorded science's measurement definition/unit/baseline, conditions, status and link rationale. Unselected neighbors, candidate graph, notes, raw artifacts, provisional results, secrets, absolute paths, backup contents and unselected manuscript text are absent. Optional unfinished judgment inclusion is explicit; changed selected context invalidates the preview. Relation endpoint context is explicitly selected, never fetched secretly. |
| Validate typed output | Closed typed v2 and text v1 stay distinct, with purpose/kind/create/edit mappings explicit. Unselected, forged or cross-project targets, unknown fields/kinds, commands/tools/approval claims, evidence mutations, cycles and resource excess cannot become valid staged or recorded changes. Selected context/local-item references are checked; new IDs are allocated locally and existing edit targets retain their identity. Invalid suggestions do not replace human writing or execute terminal controls. |
| Route the reviewed response contract | Typed review binds its expected v2 schema while legacy text review bytes remain unchanged. A wrong local completion reader neither consumes the pending dispatch nor records provider malformation; its correct reader can finish. Model output with the wrong envelope under the correct route remains malformed and requires a fresh request. |
| Choose one suggestion | Compare full current/suggested content and required dependencies. Stage only the chosen dependency-closed batch after explicit action, validating all capacity/identity/origin inputs before publishing any item. Failure leaves the prior candidates and writing intact. Graph projection is unrecorded and shares existing evidence identity; nothing records or confirms on arrival. |
| Choose a second independent suggestion | Staging or omitting the first item from one response leaves an independent sibling inspectable/selectable. A changed referenced proposed dependency revokes its dependent comparison, not unrelated items. Re-selection revokes the scientific consequence review; it is not blanket cancellation of independent provider work. |
| Edit an AI relationship under a manual judgment | Preserve owned proposal/item/context identity through edits, selection, omission/reselection, consequence preview and explicit personal recording. Include selected/required amendment origins and inherited/current judgment origins. Fresh open, history refresh and later correction retain the AI relationship under that manual judgment. Omitted items are not recorded as selected changes. |
| Reject or cancel | Merely opening/comparing, Esc/Not now, refusal or invalid output changes no kept candidate or recorded science. Explicitly staged work remains distinct from a later cancelled review. Existing writing and manual continuation stay usable. |
| Change state while waiting | Owner/judgment identity, recorded view or included draft changes revoke affected adoption. If the draft was omitted from input, continued typing keeps independently valid typed items readable; staging requires a fresh comparison with current writing. Whole-judgment replacement keeps its stricter revision binding. Dependency/selection changes revoke dependent comparisons/reviews without blanket sibling cancellation. Late/duplicate arrivals cannot overwrite work or revive consent. |
| Save, reopen and restore | Save/quit/fresh open and backup/fresh restore retain item origins, human edits/reason, kept/unfinished writing and original context within one versioned workspace. One response's multiple items must not be miscounted as multiple dispatched requests. No request, consent, current adoption/review or protected authority is restored. Changed source remains explicit; failed/corrupt/newer/conflicting saves preserve available work. |
| Return to an unstaged response | Retained available suggestions reopen as read-only historical material with their original basis. Opening cannot stage them or resurrect consent; an explicit new local review of identical original/current context precedes further incorporation. Changed context requires a new proposal. Previously staged candidates remain editable/reviewable with origin without another model call. Erased/not-retained payload status stays honest. |
| Reach an edit or total-storage bound | Keeps, complete dependency batches and checkpoints obey all bounds, including 256 KiB. Refusal retains buffers and last valid origin without partial staging, truncation or revision merging. Optional newly received unstaged payloads may be explicitly marked not-retained under the declared quota, preserving digest/disposition and session reading; they cannot block an otherwise valid human save or evict previous saved/adopted material silently. |
| Leave an explanation unfinished | Help/staging stays quiet. Personal explanation state defaults to not-reviewed separately from AI origin; partial text, explicit reviewed choice or leave-for-later choice retain original reason/context. Consequential AI recording requests that explicit choice through existing contextual review. AI alone cannot manufacture deferral, comprehension or accepted debt. Legacy deferred encoding requires compatible human choice; no personal enum is inserted into protected/F0 records. |
| AI off after earlier adoption | Provider removal/disabling preserves prior AI origin and the same manual episode/review/return. No model request occurs, and earlier influence is never relabeled manual. |
| Inspect retained traces | Request/response/destination/model identity and disposition remain separate from human adoption and recorded science. Credentials are excluded from saved research, outbound scientific content and diagnostics. Eligible raw-payload erasure retains unavailable markers/digests and required contribution history. No automatic transmission or transcript log is created. |

**Partial-return failure cases.** Write the first partial explanation after its
consequence preview expires; checkpoint and Esc must retain the text on the
original cause without permitting stale recording. Edit a retained explanation,
return to the list and reopen it: the latest text remains, one editable row is
shown per cause, and recorded review choice is immutable. A malformed/expired
response reached while waiting must return to an up-to-date, read-only history
without crashing or installing proposal capability.

**Terminal checkpoint.** Through the existing graph/work reader, exercise
request preview, item inspection, editing, dependency scope, rejection and
before/after consequence review at a wide viewport and 80×24. Verify full
scientific text is reachable, focus/return survives resize, Korean input is
retained, unfinished text remains separate and exit restores shell modes.
Repeat the existing personal manual loop unchanged. L01–L03 do not enable
bundled AI replies on public personal projects; their offline rehearsal remains
explicitly synthetic and does not close the live check below.

**Live checkpoint, only after its scope and deployment choice.** Exercise one
user-selected endpoint with exact one-shot outbound review, bounded timeout and
cancellation, malformed/refused output and delayed arrival. Verify the actual
provider's research-file/key/IPC/API access boundary under section 13; compatible
JSON, localhost or a connector sandbox is insufficient. Repeat selective human
incorporation and a fresh-process restore without automatic scientific writes.
The proposed personal route records only personal intent; protected accepted
effects remain unavailable without their separate authorization/log gates.

For critique, alternative interpretation and a proposed experiment, have the
person identify a concrete claim limit, comparison or uncertainty the response
helped inspect, or record that it did not help. Preserve missing-field/source
limitations. Valid JSON and frozen expected wording prove no live usefulness;
neither observed adoption nor a human answer certifies understanding. No AI
score, mandatory second decision log, formal debt closure or V0 success is
inferred. Check the affected extracted-source journey before claiming this new
capability distributable; license/publication remains a separate action.

After the frozen-study wiring check, observe one researcher-authored new
project/task through the same permitted personal route. The person supplies
their chosen sources and explicitly reviews outbound content; disposable novel
content is sufficient and private research is not automatically required.
Report a concrete benefit or absence of benefit instead of counting known
fixture wording as usefulness. Reuse the prior manual-loop regression and run
affected checks; do not repeat all six unchanged human tasks at each AI unit.


### External proposal import checks

A private typed external response is previewed before exact local confirmation.
Dry-run and cancellation leave the checkpoint unchanged; importing contacts no
provider and creates no research judgment or evidence. Display external/unverified
source identity during history and selection. Preserve its declared original
hashes separately from computed normalized/import hashes through restart and
backup. Reject changed source bindings, duplicate judgment imports, foreign
references and insufficient retention capacity. An exhausted three-request budget
stays exhausted. Long reading remains possible; expired comparisons require
refresh. Failure to open a replacement review preserves the previous review.
These checks implement [ADR 0021](../../architecture/decisions/0021-external-proposal-import.md).


### Public Codex connection release checks

On the pinned Mac Codex route, exact HTTP review reaches the real connection
without replacing qualification in tests of the public entry. Missing runtime,
unsupported model, changed content, expired input and cancelled review cannot
launch. An owned returned proposal supports item comparison/staging and ordinary
save/reopen with no restored connection. Generic API/unsupported Codex profiles
remain preview-only. Actual service validation uses separately consented input;
unit peers do not establish account access. Record final alpha and extracted
source checks, actual service outcome, human use and release status separately.

### Personal runtime prerequisite guidance

The source entry refuses non-3.13 Python with exit 3 before importing application
or domain modules. Its JSON states replay not-run and provides version-matched
manual setup alternatives. Python 3.8 bootstrap syntax parsing is not application
support. Actual Mac Python 3.9.6 checks the refusal path; its target-runtime curses status
is not checked (`null`). On supported Python,
missing/broken curses or absent system Git yields exit 3 with guidance naming
curses/_curses, `/usr/bin/git` and PATH; no installer runs. A simulated macOS
Git shim without developer tools refuses readiness without invoking the shim.
Fresh extracted subprocesses exercise unsupported-runtime and actual missing
curses imports; malformed member paths are tested within the ZIP member budget. The supported fresh
source artifact still passes doctor/help and its manual init/open/save/return
journey. See [runtime setup](../../development/workflow.md#personal-terminal-alpha-source).

### Personal paper capacity and return

01 uses a combined synthetic lifecycle with 64 claims, 256 observations,
256 experiments, 512 scientific edges, 64 plans, 32 episodes/Interpretations,
1,024 events and 1,439 commands; a separate case reaches 2,048 commands.
The same history replays deterministically, keeps corrections and reports exact
headroom. Count/aggregate overflow refuses without append or truncation; unknown
versions/profiles/caller caps refuse. Legacy six histories/goldens stay unchanged.
Source bytes round-trip non-NFC and originals larger than a scientific text field,
including encoded overhead and aggregate refusal. Tiny and near-budget frame-v2
files/backups are rejected by the actual shipped old readers with canonical bytes
intact and advisory locks released; an empty persistent `work.lock` sentinel may
remain, as those readers normally retain it.

Fresh-process and extracted real PTY journeys exercise manual authoring, notes,
judgment/reason, correction, quit/reopen, backup and new-folder restore for both
profiles. Save failures, external changes and conflicting sessions retain source
bytes and live writing. Compatible conversion previews preserve science, original
checkpoint bytes and known AI Contributions, require a fresh destination/exact
confirmation, and cancel/refuse unsupported source-bound work without publication.
Derived manifests are not duplicated in saved work. Scoped context remains narrow,
excludes retained sources and grants no provider or protected merge authority.
Measured performance and completed cross-review live in the
[execution record](../../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#real-paper-migration-implementation-plan);
[usage](../../development/workflow.md#personal-paper-lifecycle-capacity) declares
which profile/operations are available. Later import/revision types remain planned.
