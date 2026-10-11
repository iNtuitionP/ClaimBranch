---
kind: development
status: active
owners: maintainers
last_reviewed: 2026-10-11
canonical_for: repository-local validation commands and documentation enforcement
---

# Repository checks

For the user-selected native execution loop and grouped verification commands,
see the [implementation harness](implementation-harness.md). The individual
commands below remain supported; the harness delegates to these same checkers.

The personal alpha, synthetic examples and source packaging use Python 3.13
and the standard library. Documentation validation and the repository-owned
Notion journal helper require Python 3.10 or newer; CI uses Python 3.13.
Production native packaging and the protected application stack remain open.

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

Run the non-authoritative first-pass contract model:

```powershell
python -m unittest discover -s tests/contract -p "test_*.py" -v
```

This synthetic, in-memory model checks undecided entry, exact rationale reuse,
append-only observation corrections, evidence/manuscript-bound review freshness,
and the proposal-only model ingress. The
[five hypothetical cases](../validation/cases/saturation.md#12-augmented-synthetic-contract-oracles)
extend software-contract coverage, not the original research findings.
Manuscript anchors, hashes, and monotonic revisions are supplied by the caller;
the model does not read files or detect external edits. A draft is not a
canonical ResearchEpisode or accepted judgment; a review digest is not a
human authorization receipt. There is no accepted-write or persistence API.
Passing these tests does not prove user understanding, OS process isolation,
or P1 completion. The [early-slice plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#p1-early-slice-first-pass-and-placement-contracts)
owns the scope. The portable runtime CI job now includes this suite, along with
application/security tests and source-artifact checks on Linux and macOS.

The same contract suite now includes `review_binding.py`: a pure synthetic
binding of the complete review to an action digest, session, and expiry. It
reuses the entered rationale and rejects changed or expired context. It reads
no files or clock, writes no state, and issues no human authorization. Callers
must provide a freshly prepared current review; the public digest is forgeable
and repeated matching does not consume a receipt. Run this slice alone with
`python -m unittest tests.contract.test_review_binding -v`.
The [A1 plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#a1-bind-one-exact-review-to-one-proposed-action)
owns its enforcement limits and the separate real-authorization work.

### Authorization attempt lifecycle checks

Run `python -m unittest discover -s tests/contract -p test_authorization_attempt.py -v`
for the A2.1 reference model in `scripts/contracts/authorization_attempt.py`.
It reuses A1 binding, derives an attempt challenge, reloads the current review
after a matching synthetic response, and rejects cancellation, expiry, stale
context, dependency failure, and repeated completion. Its injected clock also
rejects backwards observations. Terminal results cannot resume on that object.

This is an in-memory, serialized event-order experiment. Tests supply a fake
response verifier; `matched` always has `authorization_verified: false` and
issues no receipt. Neither the module nor its tests prove OS authentication,
protected reads, thread safety, or durable replay rejection after restart.
Native key/cancellation/cleanup and private IPC remain Windows experiments;
atomic stored receipt consumption belongs to A3. The
[A2 plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#a2-demonstrate-a-real-foreground-authorization-boundary)
owns the detailed contracts and completion gates. `core` and `all` include
these tests automatically.

### WebAuthn assertion verification checks

Run `python -m unittest discover -s tests/probes -p test_webauthn_assertion.py -v`
for `scripts/probes/webauthn_assertion.py`. The shared validator checks a narrow
ES256 assertion profile against caller-pinned public-key and credential context,
then passes the original signed bytes to a mandatory native signature verifier.
Its [public synthetic fixture](../../tests/fixtures/webauthn/assertion-es256.json)
contains an OpenSSL-created signature and public keys, never a private key or
an enrolled Windows credential. A2.1 integration still reports authorization
false, including for a cryptographically matching synthetic response.

Most tests need only the standard library. The native signature tests use an
already-installed `openssl` on PATH, or an explicit executable absolute path
in `CLAIMBRANCH_TEST_OPENSSL`. No executable is installed automatically.
Missing default OpenSSL skips only the native-test class; an invalid explicit
override, launch failure, timeout, or exit other than 0/1 is a test error.
The test oracle treats exit 1 as verification mismatch; OpenSSL can also use
that exit for an unusable key. The fixed fixture's positive verification is
therefore essential. More precise oracle failure classification remains a
documented follow-up, not a production-backend guarantee. The harness reports
skipped coverage rather than success.
Temporary public-key/signature files use the existing non-Git temporary-root
check, including when this suite is run directly. All native commands have a
10-second test timeout and no network or account access.

The [A2.2 plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#a22-verify-the-actual-windows-presence-adapter)
defines the deliberately restricted assertion profile and the separate Windows
registration, foreground-presence, protected-key, and private-delivery gates.
The test-only OpenSSL oracle does not select a Windows or product dependency.

## R1 offline research-screen design

Open the [Episode Review storyboard](../designs/assets/episode-review.html) in
a browser to compare 14 synthetic states and two reading styles. Product
actions are disabled. The [design proposal](../designs/2026-09-22-episode-review.md)
owns the intended experience and review questions.

```sh
python -B -m scripts.render_episode_review
python -B -m scripts.render_episode_review --check
python -m unittest tests.contract.test_episode_review_design -v
```

The standard-library renderer uses the source checker's verified fixture bytes,
the committed view examples and a local HTML template. Regenerate the HTML
after editing those inputs; do not hand-edit it. The semantic tests run in the
existing contract/core/all suites. They verify design consistency and inert
rendering, not user understanding, native approval or a working product UI.

## macOS R2 authority and isolation experiments

The [Mac-first decision](../architecture/decisions/0010-macos-first-platform-adapters.md)
keeps Windows checks separate. These commands use the installed Swift/macOS SDK,
AppKit, LocalAuthentication, Security and CryptoKit without installing packages:

```sh
python3.13 -B -m scripts.probes.macos_authorization --check
python3.13 -B -m scripts.probes.macos_authorization --review
python3.13 -m unittest tests.probes.test_macos_authorization tests.probes.test_macos_isolation -v
```

`--check` does not prompt or create keys. `--review` opens a fixed synthetic
review; only the person at the Mac can complete the native authentication.
It signs an exact challenge with a fresh non-persistent Secure Enclave key,
checks the signature and private-export denial, rejects late results and never
reports product authorization. The review expires after 90 seconds. No durable
key, research history or manuscript is created. Closing/cancelling the dialog
does not issue a signature result. Native authentication cancellation is
classified by its error domain as well as its code.

The separate `python3.13 -B -m scripts.probes.macos_isolation --check` command
compares baseline and sandboxed access to owned synthetic resources. It creates
an ad-hoc signed worker and an OS application container; it is deliberately not
part of automated tests. Cleanup can be denied by macOS. A remaining probe
container or application-scripts directory returns `blocked_cleanup` (exit 3)
before compilation or further resource creation. An incomplete cleanup is
reported separately from observations, never hidden as a successful run.
Do not repeat the experiment until the existing owned resource is resolved.
The [plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#mac-authority-and-isolation-increment)
records the current blocker and exact owned identifier. These probes prove
neither provider confinement nor production private IPC or durable key custody.

Independent key-reconstruction measurement, without a sandbox container:

```sh
python3.13 -B -m scripts.probes.macos_key_reopen --check
python3.13 -B -m scripts.probes.macos_key_reopen --exercise
python3.13 -B -m scripts.probes.macos_key_reopen --review
python3.13 -m unittest tests.probes.test_macos_key_reopen tests.probes.test_macos_key_reopen_review -v
```

`--check` compiles and reads capability only. Explicit `--exercise` creates one
synthetic Secure Enclave key with user-presence access control, stores its
encrypted representation in an owned temporary directory outside Git, and
reconstructs it in new processes. Interaction stays disabled, including a fixed
synthetic signing attempt that must be denied. It changes one representation
byte, observes reconstruction, restores the original bytes, and checks the
valid control. Only bounded status, public identity digests and error codes
are printed; the owned temporary files are removed. No existing key, explicit
Keychain item, research source or product receipt is used. Automated tests
create no Secure Enclave credential and request no human authentication. The
independent public-signature test uses a disposable software test key with
installed OpenSSL; this is never a runtime fallback for the protected key.

Capability availability returns 0. The exercise currently reports `incomplete`
(exit 3), retaining the valid continuity and signing-denial observations while
leaving `tamper_integrity_verified` false. Reconstructing changed bytes proves
no integrity; a constructor error could be an authentication failure or another
unclassified cause. No native integrity-error classifier is established yet.
Unavailable or unsupported capability also returns 3; errors return 1. The
[R2 evidence](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#r2-preparation-tied-to-durable-research-use)
records the observed result. Product signing after restart, private delivery,
worker isolation and validated recovery under the selected
[ADR 0014 policy](../architecture/decisions/0014-device-replacement-recovery.md)
remain separate gates.

`--review` is an explicit two-step foreground experiment. First, a preparation
window lets the person choose `테스트 키 만들기` to create a new synthetic
Secure Enclave key. Merely opening the window creates no key and enables no
authentication interaction. A timely, uncancelled result stores its encrypted
representation; that process exits before reconstruction. Cancelling or expiring
preparation stops the flow with `phase: prepare`, no key identity or signature.
The driver then checks reconstruction and noninteractive signing denial before
opening the separate fixed review. Its `승인 검증` button explicitly evaluates
device-owner authentication on a fresh context. Only a successful callback
before cancellation/expiry starts signing; the same context must satisfy the
key's user-presence access control with further implicit interaction disabled.
The noninteractive `--exercise` never switches into this flow
after an error; it keeps its original failure behavior.
The displayed text, pinned key/representation and a fresh request value are
bound into the signed message. A second native process verifies the public
signature; a fresh process must still deny noninteractive signing afterward.
The 90-second deadline advances during system sleep. Cancel/window close or
expiry invalidates the context and discards any late signature. A preflight
failure stops before the window; it never switches to a software key.

Successful observation reports `review_observed` (exit 0), with product custody
and authorization still false. Cancellation/expiry returns 3 with no signature
in the result; `cancel_source` distinguishes the review window from native
authentication cancellation. Errors return 1. `explicit_authentication_succeeded`
and `signing_started` describe the accepted callback and signing dispatch; they
do not certify that macOS displayed a dialog. Human observation is required for
that distinction. Cancellation also retains the exact `cancel_trigger` and
nullable native error domain/code. `cancel_source` gives an explicit native
user-cancel precedence over a racing app-close, but cannot establish which UI
the person saw from terminal state alone. Final output contains only bounded
digests/status and error identifiers; owned temporary material is cleaned on normal
return or handled failure. This does not prove application identity, private
IPC, a durable project or device-loss recovery. The
[R2 plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#r2-preparation-tied-to-durable-research-use)
distinguishes automated checks from actual human observations.

Independent native peer/delivery measurement, without authentication or Sandbox:

```sh
python3.13 -B -m scripts.probes.macos_delivery --check
python3.13 -B -m scripts.probes.macos_delivery --exercise
python3.13 -m unittest tests.probes.test_macos_delivery -v
```

`--check` builds three disposable ad-hoc signed roles and returns incomplete
evidence (exit 3); it does not test delivery. `--exercise` uses an owned 0700
temporary directory and a local Unix socket. Both endpoints obtain the peer's
audit token from the kernel, check its dynamic code against an exact identifier
and CDHash, and require signed and running hardened-runtime flags. The sender
releases the fixed synthetic binding only after checking the receiver; the
receiver rejects the wrong sender before reading its binding.

Seven case groups cover wrong peers, changed/cross-project/stale bindings,
one delivery followed by replay, terminal cancellation, expiry and malformed
frames. Unit tests also pin an unhardened peer's exact code to prove that a
matching hash alone is insufficient. Frames are bounded, deadlines advance
through sleep, existing destinations are preserved, and normal/handled-failure
cleanup removes only owned temporary resources. An observed run returns 0 with
`peer_delivery_verified`; errors return 1 and unsupported hosts return 3.

This is not deployment or receipt delivery. The same user can launch the test
binaries, their pins are supplied by the experiment driver, and consumption
state is volatile. No signing credential, human receipt, accepted-state handle,
production identity, constrained model worker or protected store is involved.
Those product fields stay false; production launch policy, peer pins and durable
replay rejection remain R2/R4 integration work.

Independent encrypted recovery experiment, with no authentication window:

```sh
python3.13 -B -m scripts.probes.macos_recovery --check
python3.13 -B -m scripts.probes.macos_recovery --exercise
python3.13 -m unittest tests.contract.test_recovery_archive tests.probes.test_macos_recovery -v
```

`--check` compiles the CryptoKit helper and checks fixed AES-256-GCM/HKDF-SHA256
known answers. `--exercise` uses the bundled synthetic candidate history,
throwaway recovery/local keys and an owned temporary directory outside Git.
Separate processes encrypt, decrypt, replay the exact seed/command bytes and
reencrypt the restored candidate under the new local key. Only ciphertext is
written. Key/payload transport uses internal pipes, never command arguments;
the public command accepts no research paths, keys or provider input. It reports
bounded observations and deletes its owned temporary directory.

Wrong keys, altered authentication data, another project or a mismatched/missing
expected manifest cannot publish a restored file. Publication creates a new file
without overwriting an existing destination, including one created during the
operation. Handled interruption before publication removes staging ciphertext;
a hard crash can leave staging or a published-but-incomplete filesystem state,
which is not an application power-loss guarantee. No plaintext is staged.

The portable `claimbranch/core/recovery.py` archive holds only finite candidate
history, not accepted signatures/receipts, external artifacts, terminal drafts or
active review/provider state. Its embedded digest checks consistency; it does
not prove origin or recency. The experiment's restore API separately requires
an expected project and manifest digest from the caller. No production backup
format, runtime stack or complete backup boundary is selected by this probe.
In-memory secrets and pipes are not protected from the current user or privileged
processes and have no zeroization guarantee. Native custody/isolation and actual
replacement-device enrollment remain required under ADR 0014.

An observed same-host recovery returns `recovery_observed` / exit 0 while
`authorization_verified`, `product_custody_verified` and `cross_device_verified`
stay false. Capability returns 0, unsupported hosts return 3 without native work,
and errors return 1 with a fixed diagnostic that contains no input/output.
The [R2 recovery evidence](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#r2-preparation-tied-to-durable-research-use)
owns actual measurements; source checkout and this exercise are not private
research backup products.

Signed candidate recovery adds an explicit profile to the same experiment:

```sh
python3.13 -B -m scripts.probes.macos_signed_recovery --check
python3.13 -B -m scripts.probes.macos_signed_recovery --exercise
python3.13 -m unittest tests.contract.test_recovery_checkpoint tests.probes.test_macos_signed_recovery -v
```

`claimbranch/core/recovery_checkpoint.py` binds the exact candidate archive,
project, replay manifest, operation count and checkpoint ID in canonical bytes.
Parsing checks those bindings but does not verify the signature. The signed
restore API separately requires the expected project, SHA-256 of the original
uncompressed P-256 public key, and SHA-256 of the checkpoint message. Obtain
both digest expectations outside the archive; deriving them from its contents
does not establish trust or freshness. Native P-256/SHA-256 verification must
succeed before any destination is written. Restore preserves the exact original
public key, signature and candidate bytes while encrypting under a new local key.
Unsigned archives are rejected by this API; the unsigned experiment stays separate.

The demonstration generates a disposable software signing fixture in native
process memory. It neither exports nor reconstructs a device private key, opens
an authentication window, enrolls a device, nor verifies historical accepted
receipts. Output labels the signer `disposable-software-fixture` and keeps all
product authority/custody/cross-device claims false. `--check` checks compilation
and symmetric known answers only; `--exercise` additionally verifies the fixture
signature and signed restore. The successful exercise status is
`signed_recovery_observed` (exit 0); unsupported hosts return 3 and errors return
1 without input/output diagnostics. Temporary cleanup and the previous
interruption/filesystem limits also apply.

The signed frame is bounded at 263621 bytes; the shared native plaintext pipe
limit is 270336 bytes. These bounds describe an experimental candidate profile,
not a production format or complete project backup. The signature test also
uses the system `openssl dgst -sha256` verifier with only public key/signature
files; `CLAIMBRANCH_TEST_OPENSSL` can select an already installed executable.
No test needs a private signing key file, OS credential or provider.

## Portable R3 review and debt contracts

```sh
python3.13 -m unittest tests.contract.test_research_review tests.contract.test_debt_closure -v
python3.13 -m unittest tests.contract.test_research_history tests.contract.test_research_replay -v
python3.13 -B -m scripts.replay_research_history
python3.13 -B -m scripts.export_research_schema --check
```

`claimbranch/core/` implements finite serialization, immutable judgment and AI
contribution history, selected dependency closure, exact review freshness, and
candidate acceptance/debt closure. It has no OS, storage, provider, filesystem
or ambient-clock dependency. A candidate describes an effect that still
requires real authorization; it cannot write accepted state. The
[domain design](../designs/2026-08-03-domain-model.md#context-and-current-state)
records the implemented subset and remaining full-F0 work.

`replay_research_history` checks the separate frozen manual and recorded-AI
candidate histories and their audit goldens under `tests/fixtures/saturation/`.
Both preserve the three mixed observations, selected reasoning dependencies,
omitted experiment and evidence-to-manuscript paths. The recorded history also
retains the original AI text, human edit and explanation deferral. This command
creates no workspace, key, provider request or OS container; it is a contributor
check, not the public H0 CLI or a trusted restore tool. Review-bound candidate
acceptance uses the same provenance and debt rules as the review core.

The [research command schema](../../schemas/research-command-v1.json) is generated
from `claimbranch/core/research_schema.py`; rerun the export command without
`--check` after changing that source. Do not hand-edit the generated file. It
uses the [JSON Schema 2020-12 validation vocabulary](https://json-schema.org/draft/2020-12/json-schema-validation),
with additional runtime UTF-8 and cross-record checks. The complete canonical
record/receipt/saga schema is still pending. Candidate history and manifest
size is limited to 256 KiB before a transition returns; invalid input cannot
leave an unexportable new history.

## Paper argument candidate service

```sh
python3.13 -m claimbranch demo paper --json
python3.13 -m claimbranch demo paper --variant recorded --scenario challenges --json
python3.13 -m unittest tests.contract.test_paper_history tests.contract.test_paper_replay tests.application.test_paper_service -v
python3.13 -m scripts.export_research_schema --check
```

The separate synthetic example supplies a thesis, main/subclaims, shared
observations, defined accuracy measurements and an unrun replication plan.
`--scenario supports|challenges|inconclusive` computes hypothetical reach;
it records no result and changes no claim status. Both manual and recorded-AI
examples replay to their own golden manifests. The
[domain extension](../designs/2026-08-03-domain-model.md#paper-argument-extension-under-review)
owns semantics, finite bounds and remaining persistence limitations.

UI adapters can use `PaperService(history).query(ref, at_operation=...)` for
`claimbranch.paper-view/v1`, and `.scenario(request)` for
`claimbranch.paper-impact/v1`. Pass the complete current view digest with the
project, episode and ref; never reconstruct it from layout or node selection.
The request contract is [generated](../../schemas/paper-scenario-v1.json).
Relations distinguish structural grouping from scientific support/challenge/
qualification. Nodes include source-bound metric/conditions and original
provenance remains in the judgment. The service returns detached values and
owns no store, HTTP endpoint, provider or layout state. The existing web demo
has not yet been converted to this paper model.

### Paper context and offline drafting

```sh
python3.13 -m claimbranch demo paper --context --json
python3.13 -m claimbranch demo paper --workflow --variant manual
python3.13 -m claimbranch demo paper --workflow --variant recorded --json
python3.13 -m unittest tests.application.test_paper_context tests.application.test_paper_draft tests.security.test_paper_context_egress -v
python3.13 -m unittest tests.contract.test_paper_changes tests.application.test_paper_change_review tests.application.test_cli -v
```

`PaperService.compile_context(request)` reads only its own validated paper history.
Supply project/episode/ref, the complete current view digest, purpose, explicit
node/field selections and scientific edge IDs using the generated
[request contract](../../schemas/paper-context-request-v1.json). The generated
[field catalog](../../schemas/paper-context-fields-v2.json) describes reader
projections; the runtime validates selected subsets. No graph neighborhood is
automatically added. A scientific edge requires both selected endpoints and
its complete rationale/type; a structural parent never becomes support.

The version-two context profile admits up to 16 non-relation records (including
an optional draft), 32 scientific relations, 10 fields per record and 65,536
UTF-8 payload bytes. Exceeding a bound rejects the request without truncation.
Observations/plans must explicitly select status; omitting it fails. Nested
metric/source text receives the same supplementary secret/path screening as
prose. Candidate records default to `private`, have no caller-supplied trust
classification, and carry no accepted authority. Source availability is
`unverified`: this service never opens the referenced artifact. A manuscript
anchor supplies no excerpt; raw artifact/history/export fields are unavailable.
Version-one context bytes remain unchanged for the original Episode Review.

`PaperDraftSession(service, ref=..., episode_id=..., frozen_response=..., clock=...)` is an
in-process adapter service, with a new blank edit buffer over that source view.
Omit `frozen_response` for AI off; no live sender or configurable destination
exists. `edit(text, rationale)` permits incomplete drafts. `prepare_request`
takes the paper selection and returns exact outbound bytes/digest without
dispatching. Set `include_draft=True` explicitly to also include current text,
nullable rationale and its AI-origin/contribution digest; unselected draft
text is excluded. `begin_proposal(request_id, review_digest)` consumes that
exact offline request once; `complete_proposal(request_id)` separately delivers
the constructor-owned response. The adapter can edit, review manually or cancel
between those calls. There is no worker, network or blocking wait in either
method. `request_proposal(request_id, review_digest)` remains the synchronous
convenience route. The session permits three dispatched examples, including
unfinished/failed/cancelled ones, using the existing 120-second review lifetime.

`state().attempts` retains dispatched request identity, context binding, start
and expiry and current adoption status. Replacing a request invalidates the
older result without deleting that attempt. Completion of an older request
cannot replace a newer proposal or consume its pending outbound review.
`traces` distinguishes response disposition (`proposed`, `refused`, `failed`,
`malformed`) from attempt freshness (`cancelled`, `stale`, `expired`): a valid
late response is traceable but not adoptable. State exposes hashes and payload
availability, never the raw response envelope.

For offline failure exercises, supply `frozen_result=bytes` instead of
`frozen_response`. The closed `claimbranch.provider-result/v1` envelope has
exactly `schema`, `status` (`ok`, `refused`, `failed`) and `text`; non-`ok` results
require null text. Responses are bounded to 64 KiB and proposal text to 16 KiB,
without truncation. Duplicate keys, unsupported fields such as tools/authority,
bad Unicode or invalid shape produce no proposal. The response hash binds the
exact supplied envelope bytes; invalid non-byte/oversized input has an
unavailable hash. No response can select a destination or invoke code. This
remains a volatile offline adapter, not an implementation of live transport or
durable execution traces.

`use_proposal(proposal_id)` retains the AI original and preserves the replaced
edit buffer in `before_proposal`, including incomplete human text. Human edits
retain that AI contribution. `review_draft()` materializes a complete candidate
Judgment using the same text and rationale, with the existing eight-contribution
bound; it is not a scientific change selection, authorization or merge.
`update_source(new_service)` must name the same project/episode and invalidates
pending requests/results when its paper digest changes. Draft edits, cancellation
and expiry also prevent dispatch/adoption. `not_now()` retains the local draft
without creating debt; `erase_trace(request_id)` erases eligible raw response
payload while preserving its digest and adopted contribution. Returned state is
detached. Sessions have no HTTP port, durable storage, native helper or UI layout.

`prepare_changes(request)` connects a complete draft to scientific review.
Use the generated [change request contract](../../schemas/paper-changes-request-v1.json):
the current state's paper identity/view digest, `draft_id` and `revision`,
explicit typed amendments and nonempty selected IDs. Amendments reuse the v2
claim, interpretation, scientific-edge, claim-status and unrun-plan records.
The history owner validates the whole proposal and the selected result, including
dependency closure, cycles, status basis and active evidence. The response
distinguishes selected amendments, required amended dependencies, unchanged
references and omitted amendments. It contains detached before/after graphs,
directly changed and unchanged claims, potential scientific reach from both
graphs, witness paths and unchanged evidence. Structural parents do not imply
scientific impact; planned experiments do not become observations. Potential
manuscript-anchor impact has no verified source, wording patch or write action.

The preview expires after 300 seconds. `finish_changes_review(preview_digest,
disposition=..., answers=[...])` revalidates its exact scope and reuses the draft
rationale. Manual review uses `not-required`; AI-influenced review requires one
to three nonempty answers (`answered`) or explicit `deferred`. Original source
and working-draft contributions remain separate. Because v2 has branch-level
Judgment provenance, any AI influence in the source is conservatively retained
even when the new draft is manual. Deferral describes understanding debt **if
later accepted**; finishing this review creates neither debt nor authority.
Inspect detached results through `get_changes_preview()` and
`get_changes_review()`. Editing, AI adoption, changed source, reselection,
expiry, clock reversal or Not now invalidates the prior review. Re-preparing
even identical scope replaces its review identity; an old digest cannot finish it.

This is a disposable projection, including over an already merged candidate.
It adds no history command, canonical episode, record deletion, thesis rewrite,
evidence mutation or completed-run edit. Existing v1/v2 bytes and finite limits
remain unchanged; oversized requests/results fail without truncation. The review
is explicitly unaccepted and cannot be consumed as a sealed merge or approval
receipt. Durable repeated episodes and protected acceptance remain separate work.

The workflow command scripts both variants over the same bundled paper, starting
with a blank draft, selecting scientific context, optionally using the recorded
AI example, narrowing a pruning claim to its measured mask, and inspecting
selected changes before Not now. It selects the interpretation and qualifying
relation, includes the changed claim as a required dependency, and omits the
proposed plan amendment. JSON exposes the exact request, contributions, graph
comparison, review and unchanged-source check. The AI route explicitly defers
explanation in this scripted example; no debt is recorded. The response comes
from the existing recorded paper fixture, not a model. This verifies wiring,
not useful AI, first-pass human understanding, protected acceptance or
restart/resume. The separate UI adapter still has to connect these services
to the researcher-facing experience.

### Typed proposal ingress exercise

Run the portable L01 input/response exercise on a new invented cache study:

```sh
python3.13 -m claimbranch.application.paper_proposal_example
python3.13 -B -m unittest tests.application.test_paper_proposals -v
python3.13 -m scripts.export_research_schema --check
```

This contributor exercise is independent of personal project open: it shows
exact selected input, an optional unfinished judgment, a context-matched frozen
response, broker-owned identity and a trace. It keeps the original manual
writing/science unchanged. It performs no network request, allocation, staging,
personal recording, native approval or persistence. Live AI remains unavailable
in the public personal app; [ADR 0018](../architecture/decisions/0018-optional-personal-ai.md)
selects its later scope rather than claiming those connections are implemented.

`PaperDraftSession.compile_proposal_context(request, include_draft=False)` reuses
the existing checked reader and owner/view binding. Explicit draft inclusion
may contain blank/partial text and a missing reason. Reading this context does
not replace a request, enable AI or grant consent. Source references remain
unopened/unverified and no candidate graph or provisional result enters input.

`provider_typed_result(raw, compiled_context)` validates the separate generated
[v2 response schema](../../schemas/provider-result-v2.json). The exact keys are
`schema`, `status`, `critique` and `items`. Successful output supplies critique
or items; refused/failed output supplies null critique and no items. The existing
text v1 decoder and manuscript-text route remain unchanged. All three scientific
purposes permit claim, interpretation, scientific-edge and unrun-plan suggestions.

An item has `id`, `action` (create/edit), `kind`, `target_id` and complete `body`.
`id` belongs only to the response; creation requires null `target_id` and later
application allocation. Editing preserves one selected matching target ID;
thesis edits are unavailable, and interpretation edits require the selected
current `episode_id`. Context `scientific-relation` maps to `scientific-edge`.
Body references use `{domain: context|item, id: ...}` to distinguish exact selected
records from local dependencies; parent roles must be explicitly selected.
No unselected reference is resolved by fetching a neighbor. Runs, observations,
source/measurement edits, claim-status changes and manuscript mutations are excluded.

The response is bounded to 65,536 raw/normalized UTF-8 bytes and at most 64 items,
with at most 15 claims, one interpretation, 32 relationships and 8 plans. Unknown
fields, forged authority/origin, duplicate edits/IDs, wrong reference kinds,
terminal controls, incompatible roles and known dependency/structural/scientific
cycles or depth beyond 8 refuse the complete response. This validates proposals
against the selected input only: the owning selective-staging service below
rechecks its entire current candidate graph, capacity and dependency batch.
If an item edits a selected target, other suggestions reference that edit using
its item-domain ID, never the target's old context-domain identity. This prevents
hidden dependencies or two apparent parents collapsing into one edited record.
Display direction/line-separator controls are rejected without banning ordinary
joined-script text. An interpretation may explicitly have no linked basis; that
does not verify evidence or turn its statement into an observation.

`OfflineBroker.complete_typed(request_id, raw)` consumes one previously reviewed
offline dispatch, checks its retained exact context and records the original
response hash/disposition. It returns an immutable `TypedProposal` payload with
broker-owned project/episode/request/context/trace metadata. These values are
not an adoption capability. Invalid input creates no proposal; a retry needs
fresh consent. The text completion route continues to reject typed v2. Returned
typed proposals cannot go through whole-judgment text adoption. The selective
origin/return service below supplies L02; the offline TUI rehearsal supplies L03.
Actual provider integration remains L04.
Prepare and dispatch typed work with `review_outbound(..., result_format="typed")`
and `broker.begin(..., result_format="typed")`. Its displayed review binds
`result_schema=claimbranch.provider-result/v2`; text review bytes stay unchanged.
Wrong-route completion refuses before consuming the pending dispatch or adding
a misleading malformed-response trace, so the correct reader can still finish.

### Selective proposal staging and origin return

The L02 backend reuses the existing terminal workspace and private checkpoint.
It accepts only a constructor-owned frozen response for an offline rehearsal;
public personal init/open still starts AI-off. It adds no live endpoint, native
key, new editor, evidence confirmation or manuscript write. Run its checks:

```sh
python3.13 -B -m unittest tests.application.test_paper_proposal_work -v
```

`PaperProposalWork(app.paper, app.context_key(), frozen_result=raw, clock=clock)`
owns one response's incorporation. `prepare(request, include_draft=False)`
returns the exact typed outbound review. Explicit `begin(review)` reserves
minimal checkpoint space before spending one of the owning judgment's three
requests; `complete(review.request_id)` records arrival and its trace.
`compare(item_ids)` displays mapped candidates, existing kept content,
dependencies and the prospective graph; `stage(comparison)` incorporates only
that current dependency batch atomically. Independent siblings remain selectable.
Included draft edits, source changes, replacement requests, expiry and changed
dependencies revoke the relevant comparison. Failed identity allocation leaves
no poisoned mapping. New requests allocate independent create IDs; edits preserve
selected target IDs. An AI edit over a kept human candidate retains that writing
as the earlier revision, rather than losing it beneath an AI-only root.

The generated [amendment lineage v2](../../schemas/paper-amendment-lineage-v2.json)
retains each original item and request/context/response/trace digests, its local
item-to-record mapping and ordered human keeps. `PaperCandidates.put(record)`
preserves that lineage through edits; eight revisions is a hard bound. Failure
preserves prior kept content/origin, while the existing editor retains unfinished
text. Omission and deletion remain separate. Origin never manufactures a source
Judgment. Retained item/body mappings and personal cause/reason/selection are
checked against their original response and replayed history when reopened.

`PersonalResearch.prepare("reasoning")` exposes complete selected/required item
origins plus inherited/current judgment origin. An AI relationship under a manual
judgment remains AI-influenced. Quiet staging requires no explanation. For an
AI-influenced personal consequence, the default `not-reviewed` comparison cannot
record until the person explicitly chooses `reviewed` or `leave-for-later`.
Use `explanation_entries` with the displayed topic IDs and explicit original-
reason reuse or human text. `keep_explanation(preview, entries=...)` retains
partial writing with its original causal context; a different judgment/selection
keeps separate earlier writing. `explanation_contexts()` shows original/current
science without grading or closing work. These choices attest personal intent,
not comprehension or protected UnderstandingDebt. The existing reason is reused.
The legacy scientific command's disposition reflects its judgment history;
item-only AI and its explicit personal explanation remain in companion metadata.

The new explicit version mapping is workspace v7 →
[paper-work v8](../../schemas/paper-work-v8.json) →
[project-work v4](../../schemas/project-work-v4.json). Older formats remain
readable, manual snapshots retain their existing version and unknown versions
refuse without conversion. Selected/inherited origins, explanation and minimal
attempt traces share that one checkpoint, correction/history-refresh and ordinary
backup/restore path. There is no separate provider store. Eight recorded personal
origin/explanation consequences and sixteen partial causal contexts are bounded;
earlier history is not truncated to fit.

Historical unstaged suggestions are read-only. Restore never installs consent,
an outstanding broker request or staging authority; new incorporation requires
a fresh request. Payload availability is `available`, `not-retained` or `erased`.
The whole project, including writing/origin/source association, obeys 256 KiB.
Never-saved optional raw payloads yield to valid human writing and required
origin, remaining session-readable with a notice; already saved payloads cannot
be silently evicted. Saving refusal retains live writing and the prior checkpoint.
Explicit `erase_proposal_payload(request_id)` removes raw response reading but
retains trace digests and the adopted item material needed to explain research.
Raw retention duration and live provider qualification remain L04 decisions.
The example compares the live service query and complete draft state before/after
the exercise; its science/writing preservation fields are observations rather
than a comparison with an unused original immutable history.

### Selective AI items in the terminal

The explicit L03 rehearsal uses an invented cache study, with a context-matched
fixed response and ordinary private storage. It supplies no live inference or
real measurements. Public `project init/open` remains AI-off. No native key,
new editor or manuscript write is involved. From the checkout or source artifact:

```sh
mkdir -m 700 /path/to/new-disposable-study
python3.13 -m claimbranch demo proposals --directory /path/to/new-disposable-study --create
python3.13 -m claimbranch demo proposals --directory /path/to/new-disposable-study
python3.13 -m claimbranch demo proposals --snapshot
```

Creation previews separate `paper/` and `work/` children before typing `create`.
The paper is an invented Git paper; work is unencrypted private personal data.
Existing children are never replaced. The rehearsal may ask for suggestions only
while its original recorded cache context matches; recording/correction changes
that context and leaves manual work and history available. It never attaches a
seed-paper response to an ordinary own-project entry.
EOF at the creation prompt cancels before writing. Interrupted/failed setup may
retain incomplete disposable children: preserve them and retry in a fresh private
folder with working Git. The command does not delete or overwrite those children.

Use `;` → **Ask AI about this context**, or `A`. Space selects recorded nodes and
scientific relations, `r` reads full context, and `d` explicitly includes an
unfinished judgment. Relation endpoints must be selected. Enter previews the
exact task, destination, scientific fields, redactions, draft and digest. Read
through End before Enter requests the offline example. Esc cancels. There are
at most three dispatched attempts per owning judgment, shared with earlier
assistance; no retry occurs automatically. This fixed response offers no graph
items when its required thesis/CPU-A observation are not both selected.

Read an item with Enter, select individual items with Space and use `c` to compare.
The comparison names chosen, required and omitted items and shows complete before/
after content. `G` opens both draft graphs; Tab switches them and Esc returns.
Read to End before Enter stages the batch. Arrival, reading and cancellation
change no judgment or recorded science. Independent siblings remain selectable.
`x` declines further incorporation while retaining prior staged work and history.
`e` opens the same argument-draft editor: edit the staged wording/connection,
keep it explicitly, and include/omit it through the existing selection controls.
Human keeps preserve the original AI item. Staging requires no explanation.

Write the judgment and reason once through the existing editor, then use
**Record selected reasoning personally**. Inspect the exact consequence and
before/after graph first. Item-level AI remains visible under a manual judgment.
At End, `1` opens contextual explanation topics, while `2` explicitly leaves
explanation review for later. Enter records only after that explicit choice and
a complete refreshed consequence preview. AI influence alone never asserts
human deferral, understanding or accepted debt.

Explanation topics permit unfinished human text and `r` explicitly reuses the
original reason without copying it. Enter edits a topic; Ctrl+S/Esc retain partial
writing, and the existing private checkpoint also retains active unfinished
partial text. Ctrl+O inspects original/current science while preserving editor,
cursor and undo. `v` records an explicit reviewed choice only when each topic has
human text or explicit reason reuse; it does not grade understanding. Partial
writing cannot record science. Changed scope keeps the original explanation
separate and requires another consequence comparison.
Review expiry likewise preserves partial writing on its original cause, while
recording requires a fresh comparison. Returning to the topic list reloads the
latest partial text; one cause has one editable row, with the immutable recorded
review choice shown separately. Reopening cannot restore an older copy over newer
human writing.

After restart, `;` → **Read AI response history**, **Inspect AI item origins** or
**Return to personal explanations** restores original input, full original item,
kept edits, original judgment/reason, partial text and recorded review choice.
Historical replies have no staging capability. Historical explanation edits stay
partial on the original cause and cannot overwrite a recorded review choice or
close work. Already staged candidates remain editable with AI disabled.

Ordinary `project open --directory /path/to/new-disposable-study/work` resumes
with AI off. Existing `project backup/restore` operates on that work directory;
backups include only its verified saved checkpoint. Restored work likewise opens
AI-off. Raw payload availability and whole-checkpoint bounds follow the L02
contract above; retained input/origin is not protected authority or proof of
useful live assistance. Human usefulness and actual provider/egress remain L04.

```sh
python3.13 -m unittest tests.application.test_tui_proposals tests.application.test_tui_proposals_terminal -v
```

### Personal LLM configuration and unsent preview

L04 now prepares a user's own API or Codex-login connection instead of choosing a fixed
provider/model for everyone. The public app remains AI-off: these commands
save connection settings and inspect an **unsent** request. They do not read
API keys, probe a server, authorize transmission or make a proposal attempt.
Public personal init/open can now attach an explicitly chosen profile for
contextual unsent previews. Actual provider qualification and live enablement
remain unfinished in the [L04 ledger](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#optional-ai-follow-up-implementation-plan).
The [reference review](../references/research-agent-runtime-and-graph.md#personal-provider-configuration)
records the OpenClaw pattern and official API sources.

Use a separate existing owner-private directory outside Git. A configuration
stores API format, the **complete POST URL**, model ID, optional environment
variable **name**, output limit and JSON compatibility mode. It contains no
credential value and is not included in project storage, export or backup.
The initial formats are OpenAI-compatible Chat Completions and Anthropic
Messages. A separate Codex ChatGPT-login profile below prepares application
input only. Responses API, live subscription dispatch, model discovery, tools,
server management and automatic fallback are not implemented. Replace example URLs
and model IDs with your server's documented values; example URLs are not live.

```sh
mkdir -m 700 /path/to/private-llm-config
python3.13 -m claimbranch provider configure --directory /path/to/private-llm-config --api openai-chat --endpoint https://llm.example/v1/chat/completions --model your-model-id --credential-env MY_LLM_KEY --dry-run
python3.13 -m claimbranch provider configure --directory /path/to/private-llm-config --api openai-chat --endpoint https://llm.example/v1/chat/completions --model your-model-id --credential-env MY_LLM_KEY
python3.13 -m claimbranch provider inspect --directory /path/to/private-llm-config
```

For Anthropic use `--api anthropic-messages` and the complete `/v1/messages`
endpoint; the adapter uses `max_tokens` and prompt-only JSON. OpenAI chat uses
`max_completion_tokens` and `response_format: json_object` by default. A custom
server may require `--output-limit-field max_tokens --json-mode prompt-only`.
No format compatibility is inferred from its URL. The file `provider.json` is
create-only: to change settings, configure a fresh directory. Interrupted
creation preserves any incomplete file; inspect or retry in a fresh directory.
Never put a key value on the command line or in a public issue. No other app's
configuration or credentials are imported automatically.

Close the project's TUI, then preview selected recorded science:

```sh
python3.13 -m claimbranch provider preview --directory /path/to/private-llm-config --project-directory /path/to/private-work --node thesis --record thesis
```

Repeat `--record` for each selected node and `--relation` for each scientific
connection; explicitly select its endpoints too. `--episode`/`--ref` choose
another retained context. `--include-draft` explicitly includes the owning kept
judgment/reason, which may be incomplete; unkept editor text, provisional
results and candidate graph records are excluded. Source references are not
opened. Preview preserves project bytes and manuscript and creates no saved
attempt. Its terminal output contains selected private research; do not share
it as a diagnostic bundle.

The API preview exposes the exact complete provider body, including system
instruction, closed result schema, selected science, model and output settings;
it also names authentication reference, redactions, profile/context/body/request
digests and retention limits. Changing any of these inputs revokes reuse; the
preview expires after 120 seconds and itself supplies no consent capability.
The complete wire body is bounded to 65,536 bytes, not just its scientific
context. The pure response decoder requires one complete text response and the
existing typed contract; truncation, tools, malformed JSON and unselected
references refuse without staging or scientific changes.
Null tool fields or an empty tool-call list are absence, not invocation;
nonempty calls and invalid shapes still refuse.

Connection preparation fixes proposed connect/read/total budgets at 5/15/60
seconds, three attempts per judgment, no streaming, retry, redirects, environment
proxies or model fallback. These are preparation settings, **not observed live
application guarantees**; the internal transport below exercises these limits.
Local history uses the existing bounded workspace;
credentials stay separate. A service's retention is unknown until the actual
service/account is checked; `store: false` is not a zero-retention promise.
Configuration, localhost, HTTPS and compatible JSON do not qualify a deployment.

**Using an existing Codex login.** Codex supports ChatGPT sign-in as well as
API-key sign-in; subscription access does not require creating an API key.
Check `codex login status` locally. If signed out, `codex login` opens its normal
browser sign-in. Do not paste credentials here or copy its login cache into
ClaimBranch. A client running on this Mac can still use external inference;
its local tool/file access is a separate boundary. See the official
[authentication guide](https://learn.chatgpt.com/docs/auth).

Use a separate new private configuration directory for Codex preparation:

```sh
mkdir -m 700 /path/to/private-codex-config
python3.13 -m claimbranch provider configure-codex --directory /path/to/private-codex-config --model gpt-6.1-sol --dry-run
python3.13 -m claimbranch provider configure-codex --directory /path/to/private-codex-config --model gpt-6.1-sol
python3.13 -m claimbranch provider inspect --directory /path/to/private-codex-config
python3.13 -m claimbranch project open --directory /path/to/private-work --provider-directory /path/to/private-codex-config
```

Use your explicitly selected model; this example does not discover or choose
one. `--reasoning-effort` defaults to `medium`. The separate closed
`codex-profile/v1` stores model/effort, ChatGPT-login intent and candidate client
version 0.158.0, with no executable path, login cache, token or credential name.
It uses the same private create-only `provider.json` boundary and stays outside
research/backup. Configure/inspect never invokes Codex or checks login/version.

`provider preview` and the contextual TUI accept this profile. They show the
complete selected **application input**, instructions and typed response schema,
optional kept judgment/reason, model/effort and input/profile/context digests.
The complete input is limited to 65,536 bytes and its preview expires in 120
seconds. Changed profile/context/included writing or cancellation revokes reuse.
They explicitly label the remote service **origin**, unverified transport
destinations and CLI-generated wrapper. This is **not** an exact HTTP wire
preview or one-shot send consent. No client, credential read, attempt or trace
is created, and no live capability/profile restores with research.

Actual Codex application dispatch remains unavailable. Enter reports
**Actual Codex client not qualified** before any client or API transport; Esc
returns to the same manual writing. Reusing the login still requires restricted
tool/file/mount/credential/IPC/API access, bounded runtime/return and exact
outbound review within L04. A login token is not an API key for `provider configure`.
`codex exec` supports scripted invocation and structured output, but its
read-only default alone does not establish this application boundary. See official
[non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

**Actual-client boundary probe (maintainers, macOS only).** Run the bounded
offline observation with an explicit installed Codex 0.158.0 executable:

```sh
python3.13 -B -m scripts.probes.codex_boundary --client /path/to/installed/codex
```

The probe creates disposable private scratch and an empty client home, supplies
only synthetic input, skips user config/rules, disables execution/connectors/
hooks/plugins, and uses `sandbox-exec` to deny real-home access except the
executable, other process execution and network except its owned loopback peer.
It does not install, log in, read/copy the user's login cache, contact an
inference service or alter research. The peer returns scripted tool calls,
observes actual refusals, then terminates the request with HTTP 400. Diagnostics
show bounded metadata, not request text, paths, credentials or raw CLI logs;
scratch is removed on normal or handled interruption exits. SIGTERM/SIGHUP and
Ctrl+C trigger bounded child cleanup; abrupt process death cannot guarantee it.
Handlers record cancellation without raising during process creation or cleanup.
The client wait polls that flag at most every 0.1 second and cleanup uses SIGKILL
on its owned process group. The child inherits the normal signal mask; these
observations still do not prove cancellation of a production authenticated request.
Exit 0 means the two observed calls were refused
and the owned canary remained unchanged; the expected client exit is 1.
Exit 1 reports a failed gate: incomplete observation or an observed boundary
violation or cleanup failure; inspect the JSON. Missing/changed canary and failed
scratch cleanup retain available observations. Exit 2 reports failed startup/
observation execution; handled cancellation uses the conventional signal exit.
Neither result grants provider support.

On the available Mac, shell and `request_user_input` calls were refused by
the actual dispatcher. The remaining advertised question tool is unavailable
in Default mode; its name alone does not establish an executable capability.
This custom-provider run uses fallback model metadata, not the selected
ChatGPT-login model. It proves neither that route's complete tool set nor
authenticated file/key/IPC/API denial, exact outbound wrapper/destinations,
or a valid live proposal return. Do not enable dispatch from this result or
rerun it as a substitute for that missing evidence. Continue L04 only with a
supported authenticated access/egress boundary; API-key purchase is not assumed.

A separate file-access observation now reproduces and repairs the stricter
startup failure, without login, a model turn or a network exception:

```sh
python3.13 -B -m scripts.probes.codex_boundary --client /path/to/codex --file-access
```

The internal `mac_codex_policy` compiler denies file contents globally, permits
the exact executable, owned temporary tree and bounded OS-library paths, and
allows the macOS loader to read `/` as a **literal**, never its descendants.
Removing that one rule reproduces SIGABRT before initialization on this Mac.
Global file metadata remains readable; this is a content restriction, not hiding
arbitrary paths' existence/size/times. With the rule, actual host-file APIs can
read/write a permitted owned file outside cwd and spawn the permitted CLI to
successful version exit, while direct and symbolic-link reads/writes of an outside synthetic file,
outside directory listing and `/bin/sh` spawning fail with permission errors.
Exit 0 requires all three positive controls, all six denials, unchanged outside
bytes/directory entries and completed scratch cleanup; integers cannot masquerade
as Boolean evidence. Malformed reply shapes produce structured failure. The two
version controls each have a five-second deadline and check cancellation between
calls; host-API polling uses a separate 20-second bound and cooperative cancellation.
Uncertain ordinary kill/wait/pipe-close failures mark cleanup incomplete and
cannot skip the remaining cleanup steps or report a passing observation.
The result always reports `dispatch_supported: false`. The pure compiler checks
path/port bounds but does not inspect filesystem ownership, canonical identity
or proxy integrity; its trusted owner must do those checks before use.

The compiler now also denies Mach service lookup except exact
`com.apple.cfprefsd.daemon`, `com.apple.cfprefsd.agent`,
`com.apple.SecurityServer` and `com.apple.trustd.agent`, and denies
`authorization-right-obtain`. These four exact global-name services are fixed internal
exceptions, not a user-editable permission list. The file/network/exec rules
remain intact. Global file metadata and other default operations remain allowed;
this is not a whole-IPC or credential-API protection claim.

Disposable existing-login controls reach a checked ephemeral thread under that
policy, closing every proxy tunnel before the synthetic turn. They perform no
inference. Owned-process sandbox logs identify SecurityServer denial in the
earlier routing failure; narrowly allowing the observed services resolves
authentication only, without inference.
Removing trustd.agent from the smaller policy reproduces failed authentication.
Successful authentication does not qualify the permitted services' key or
human-operation APIs. SecurityServer may expose keychain items beyond the exact
credential-file exception; preference-service APIs may also reach other domains.
These service APIs remain unqualified. Generated HTTP
contents/destinations, retention, request
counts and a checked live response remain open; public AI stays unavailable.
See the [Mach lookup result](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#2026-10-10-l04-codex-mach-lookup-result-review).

To inspect a request while forming a judgment in the graph:

```sh
python3.13 -m claimbranch project open --directory /path/to/private-work --provider-directory /path/to/private-llm-config
```

`project init` accepts the same optional flag. Without it, personal projects
remain AI-off. With it, the header says **AI preview**: `A` or **Ask AI about this
context** opens the existing recorded-context picker. Space selects records;
`r` reads complete fields, `d` explicitly includes the kept unfinished judgment/
reason and `p` cycles critique, planned-experiment and evidence-comparison tasks.
Enter prepares the complete unsent API request or explicitly labeled Codex
application input; End/PgDn reads it. The API's 120-second review shows the exact endpoint/model/API/body, safe headers, environment-name
reference, redactions, digest, deadline, request budget and retention expectation.
The public live check reports **Actual provider not qualified** before reading
a key or creating transport. Esc returns to writing without an attempt.
No CLI flag or configuration trust label bypasses this check. The actual
deployment still needs ADR 0018's path/mount/credential/IPC/API evidence before
enablement; this build sends no research through the public entry.

Named **Disable personal AI connection** revokes pending/item capabilities while
preserving manual work, staged origins and history. **Enable personal AI previews**
rechecks the selected configuration but sends nothing and grants no qualification.
Changing configuration requires reopening with the intended profile and a new
exact review. Setup fails before project creation for invalid configuration.
The connection lasts only for that session and survives in-session personal
recording/correction/next-question refresh. Reopen without the flag stays AI-off;
research storage/backups contain neither profile nor credential reference.

Owned synthetic peers exercise the downstream asynchronous response path:
`m` returns from waiting to manual writing without cancelling. A pending request
or completed current item batch cannot be silently replaced by a new unsent
preview. Reopen the batch and explicitly decline with `x`, or disable AI, before
preparing another; staged drafts and origin remain. Waiting does not
consume the pending poll or overwrite human writing, a response
cannot move focus to another judgment, explicit item selection reuses existing
comparison/editors, and cancel/normal exit cancels and reaps before the final
writing checkpoint. Poll/cleanup failure still revokes capability and reaches
the final writing checkpoint. Item/history projection failure after a trace is
recorded preserves that completed response for reopening; an unavailable terminal trace stays explicitly
unavailable and the dispatched attempt remains spent. Unconfirmed child cleanup
is reported rather than claimed successful. Trace metadata and edited origins return as historical
material with AI off. These tests replace the qualification check only inside
the test process; they establish wiring, not actual deployment safety/usefulness.

#### Internal asynchronous transport

`application/provider_transport.py` now supplies the internal post-review I/O
component for L04. The connected TUI reaches it only after its qualification
check; that public check currently refuses. Passing a digest to this
library does not establish foreground human intent or qualify a deployment.
Public configure/inspect/preview still read no key and send nothing; public
personal init/open remains AI-off. The actual deployment, credential/account
and retention choice must be verified before application use under ADR 0018.

The component rechecks the exact profile/context/body/header/policy digest and
120-second expiry against the trusted caller's current review-clock epoch,
before resolving the selected environment credential. Synthetic tests inject
their fixed epoch; a serialized or model-supplied time is not an application
clock or human consent. Changed
or replayed request IDs/nonces refuse; credentials missing, containing controls
or present in selected science/request content (including model and decoded
endpoint path) refuse before sending. The safe HTTP headers are
included in preparation and passed unchanged. A cancellable background thread
feeds only frozen wire data and the selected credential through stdin to a
short-lived Python `-I` child with empty environment and closed inherited file
descriptors. Keys never appear in argv, errors, returned metadata or saved work.
This same-user child enables cancellation; it is **not a sandbox** or proof that
the external inference server lacks research access.

Direct HTTP uses an explicitly configured literal loopback URL; HTTPS verifies
against Python's default roots. Environment proxies, `SSL_CERT_FILE`/
`SSL_CERT_DIR` imports, private-CA configuration and certificate bypass are
unsupported in this initial component. An untrusted certificate returns
`tls_verification_failed`; there is no retry with weaker verification. Neither
HTTP nor HTTPS is classified local-only or qualified from its address.

Parent deadlines cover connect/DNS (5 s), header wait within the whole-job limit,
body idle reads (15 s) and the whole job (60 s). Non-streaming generation can
precede headers; body-idle timing starts after headers. Header/body progress and
expiry checks share the same lock; a late frame cannot renew an elapsed interval.
Headers and body reads report progress without extending
the total deadline. Each job freezes its limits; later configuration changes
cannot prolong it or change its session's attempt ceiling.
Cancellation/polling do not wait for sockets or child exit;
shutdown cancels outstanding work and explicit cleanup can await reaping.
Redirects, HTTP errors and malformed/tool/truncated output are terminal, with
no automatic retry or fallback. Disconnect before headers is a connection
failure, distinct from malformed returned content. Responses have a 65,536-byte body limit;
ambiguous/compressed framing refuses. A valid body passes the existing typed
decoder without staging. Credential echoes, including JSON-escaped model/text
metadata, refuse. Any reported model is self-reported, not identity verification.

The ephemeral owner permits three I/O starts and rejects replay, but does not
replace the workspace's durable per-judgment budget. Results contain request/
response digests, elapsed milliseconds, disposition and valid typed bytes;
they contain no raw wire body. The separate checked controller below now
connects owned returns to existing history and selective incorporation. Public
live enablement and actual provider qualification remain open.

The owned HTTP/TLS peers below use invented science and public synthetic test
certificates. They exercise transport only, never an actual provider's access
boundary, account retention, scientific usefulness or protected authority:

```sh
python3.13 -B -m unittest tests.application.test_provider_transport tests.application.test_provider_profile
```
Inspect honestly reports `dispatch_available: false`; unrestricted same-user
servers remain unsupported under ADRs 0009/0018. Continue manual work normally.

#### Internal Codex app-server adapter

`application/codex_app_server.py` implements the installed 0.158.0 stdio
protocol separately from HTTP APIs. Its internal trusted caller supplies an
explicit command, isolated working directory and environment; no private
profile, saved research, public option or test flag qualifies that command.
The public Codex gate still refuses before construction. The adapter never
reads/copies login files, installs a CLI or treats an input digest as foreground
consent or an exact CLI-generated HTTP preview.

Before launch, it rechecks selected application input, profile, context and
120-second expiry, and refuses repeated request IDs/nonces. It initializes
JSON-RPC, requests account state without refresh and requires ChatGPT login
before requesting `model/list`. The bounded complete catalog must advertise
exactly one matching model ID/slug, the explicitly selected reasoning effort
and text input before a thread or turn is created. Missing, aliased, duplicate,
incompatible or paginated metadata refuses; malformed catalog frames, including
missing `data`/`nextCursor`, also
refuse. Older catalogs without input modalities use the official text/image
compatibility default. Nothing silently changes the selected model or effort.
This checks client-advertised metadata, not account entitlement or actual
served identity. It then creates a new ephemeral thread with the exact selected model,
instructions/input/output schema, empty environment/dynamic-tool/capability
roots and no approval. It checks returned model, CLI version, working directory,
ephemeral state, read-only policy with `networkAccess: false` and instruction
sources. That network value is a tool-policy setting, not denial of client HTTP.
Unexpected executable items, server tool/approval requests or active remote
control terminate the job. These checks are not actual file/tool/HTTP confinement:
installed readOnly has no restricted read-root field, and thread overrides do
not prove that all startup settings are excluded. Official protocol documentation
is [here](https://learn.chatgpt.com/docs/app-server); the installed generated
schema, rather than a newer documented field, defines this adapter's version.

Authenticated `account/updated` is checked only during account/read; it cannot
replace the account reply or change to another authentication mode. Identity
and plan values are discarded. Observed `thread/settings/updated` must retain
the exact owned thread, model/provider/effort, cwd, no approval, read-only/no-tool-
network policy and the observed null developer-instruction override. Null is
not proof that CLI-generated default instructions are absent. Additional permissions,
delegation or unknown fields refuse. The explicit thread settings suppress their
own unstable-feature notice; other unexpected warnings remain fail-closed.
The trusted internal constructor may name `claimbranch-chatgpt` separately from
the default `openai`. It checks that exact provider echo, rather than relabeling
a custom return as built-in. This alias does not create a provider configuration,
disable CLI retries by itself or qualify a deployment. Actual 0.158.0 refuses
overriding the reserved built-in `openai` provider; an owned custom configuration
can pin request/stream retry counts to zero without changing the existing login.

Only one completed final assistant message from the owned thread/turn is decoded
through the existing scoped typed ingress. A completed turn, valid JSON and
selected references are required; partial/different-context/tool-bearing output
cannot supply a proposal. The result carries distinct Codex disposition, request/
response hashes, timing and bounded runtime IDs, without fictional HTTP status,
account identity, raw diagnostics or automatic scientific incorporation. No
served-model identity is proven: the configured model is checked against the
thread's echo, separately from any future actual inference evidence. The internal
Codex origin controller below now connects owned returns to selective staging
and saved history. Real authenticated dispatch still depends on the actual
provider gate. No live capability restores.

Nonblocking stdio and a background job keep polling/cancel separate from manual
work. The request deadline is at most 60 seconds, including protocol startup;
up to two seconds of leader reaping follows termination. Owned tests may shorten
the request deadline. Per-token delta notifications are opted out without
disabling completed-item/tool events. RPC framing is bounded to 256 KiB per line,
1 MiB total stdout, 64 KiB discarded stderr and 8,192 messages; final proposal text is
at most 65,536 bytes. Duplicate keys, malformed or excessively nested JSON
refuse. There is no adapter retry/model fallback. Three ephemeral starts limit
the transport, not the workspace's durable per-judgment count. Every exit kills
the owned process group and waits for its leader; unknown cleanup cannot supply
a successful return. `close` cancels; `wait_closed` separately awaits cleanup.
Normal interpreter exit performs both, and uncertain cleanup remains explicit
in result metadata and cannot report successful `wait_closed`.

```sh
python3.13 -B -m unittest tests.application.test_codex_app_server
```

These tests execute owned protocol peers, not inference. Anonymous actual CLI
controls still observe `auth_required` before a thread. Authenticated disposable
controls now reach account/read and a checked ephemeral thread with the existing
ChatGPT login, an empty configuration/state home and a temporary credential-file
alias consumed by the CLI. ClaimBranch never opens or extracts token values;
the CLI needs scratch state writes, and absence of transient CLI-created token
copies has not been established. Original-home content except that credential
file is denied, with directory metadata separately allowed. A domain-filtered
opaque CONNECT proxy permits only the selected service origins; it does not
inspect HTTP paths/body or count requests inside a reused TLS connection.
The later [file-access observation](#personal-llm-configuration-and-unsent-preview)
now repairs the stronger global-read startup failure and checks outside-file
denial through actual host-file APIs. It does not qualify Mach IPC or generated HTTP.
Closing all proxy tunnels before a synthetic turn observes the settings event
without model egress. The latest approved diagnostic reaches a checked turn
acknowledgement/start with matching model metadata, then fails with a client
error and no typed response. Its detailed error was not retained; no specific
HTTP/authentication/schema cause is established. That attempt is spent and
must not be silently resent. Neither controls nor a started turn prove useful assistance.
See the [model preflight and diagnostic result](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#2026-10-11-l04-codex-model-preflight-and-diagnostic-result-review).
See the [authenticated diagnostic result](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#2026-10-10-l04-authenticated-codex-diagnostic-result-review)
for the preserved failures and dependent stop. Public launch remains unavailable.

#### Checked Codex proposal retention

`application/paper_proposal_work.py::CodexProposalWork` connects checked owned
app-server returns to the existing item comparison, dependency selection, human
editing, personal explanation choice and explicit personal recording. It is an
internal integration seam, not a public launcher. Public configure/init/open still
use the unsent-only Codex preview and refuse before client construction. A real
caller must first qualify authenticated resource/egress access and obtain exact
one-shot foreground consent; the input digest alone grants neither.

Unsent previews create no attempt or trace and preserve earlier live comparisons.
Begin rechecks current profile/context/optional draft, 120-second expiry, the
shared three-request judgment budget and complete checkpoint capacity before
starting the owned client. A successful start consumes and tracks one attempt,
including when replacement cancellation raises. Cancellation, changed input, expiry, malformed scientific content
and failed cleanup prevent incorporation while preserving writing and minimal
historical disposition. An owned inconsistent return becomes a sanitized terminal
protocol failure; it cannot remain indefinitely pending or stage content. Foreign
request identity/digest is refused without claiming its response. No retry, fallback or automatic scientific recording is
introduced.

Workspace v9/work v10/project v6 retain a distinct `codex` input commitment and
bounded outcome: disposition, elapsed time, selected/echoed model, observed client
version, thread/turn IDs and cleanup status. The destination is a service origin,
not a claim about exact HTTP endpoints. There is no fabricated HTTP status, login
token, account identity, raw CLI diagnostic or launch environment in research
history. The original input/profile hashes remain opaque commitments; reading
old history does not recompile today's prompt or create consent. Older offline
and API schemas remain byte-identical and readable.

Existing ordinary personal save, append-only record/correction and local backup
retain complete selected/required origins, human edits, original reason and
explanation choice. Saved request/outcome/trace metadata cannot be rewritten even
with a new hash. Optional new raw responses may yield to the writing quota;
selected item origin and saved history cannot. Explicit payload erasure keeps
the minimal trace and adopted origin. Fresh-process return restores historical
reading/editing only, without a client, active request or incorporation capability.

```sh
python3.13 -B -m unittest tests.application.test_provider_proposal_work
python3.13 -m scripts.export_research_schema --check
```

These cases use owned scripted stdio peers and synthetic personal projects.
They establish the internal return path, not actual authenticated provider
protection, a live response or useful assistance. Manual work remains available.

#### Checked API proposal retention

`application/paper_proposal_work.py::ProviderProposalWork` is an internal
post-review controller, now attached by the contextual personal TUI. Its trusted
caller must qualify the actual deployment and establish exact foreground
outbound intent before `begin`; passing a profile/digest proves neither.
Contributor tests use only owned synthetic peers or owned transport results.
This supplies no bypass for the actual provider gate.

Preparation compiles the same selected science and optional unfinished judgment.
Before I/O, the complete pending checkpoint and exact current request are
checked. Wire, offline typed and whole-judgment requests share the existing
three-dispatch limit per judgment, including after restart and across provider
switches. Missing/invalid credentials or preflight refusal start no attempt;
a dispatched failure consumes one. Polling and cancellation use the bounded
transport while human writing remains separate. Included-draft edits, source
changes, expiry, cancellation and replacement revoke incorporation; late returns
stay historical. No response changes science or writing automatically.

Successful typed returns reuse existing item comparison, dependency staging,
candidate editors and personal consequence review. Workspace v8 / paper work v9 /
project work v5 retain API/output settings, an opaque profile commitment, exact
context/wire request hashes, safe headers and frozen version-one policy in
`provider-wire-binding/v1`. They also retain
raw-response and normalized-result hashes, terminal transport disposition,
elapsed milliseconds, HTTP status and bounded model self-report. The requested
model and its self-report remain separate; neither verifies the served model.
The opaque profile/wire digests cannot independently reconstruct or verify
omitted configuration or wire bytes. Reading verifies stored bindings and
replayed selected science without rebuilding today's prompt/schema/headers.
The v1 policy, API/output settings, model and URL schemas are literal historical
contracts, independent of running defaults, connection profiles and claim-text
fields. Preparation validates that version before returning a request; its
preview and retained metadata keep the same frozen policy/headers and manifest
digest. Changing those running defaults cannot strand v1 writing. A changed
historical contract, including destination scheme/loopback rules or source
semantics, requires an explicit versioned reader/migration; this is not a promise
of arbitrary schema compatibility. No credential value, environment reference, full
configuration, raw API wrapper or transport job is stored in research/backup.
Scientific source and selected input are replayed from the existing history.
Older workspace/work/project formats remain readable and unchanged; unsupported
versions and inconsistent hashes/outcomes refuse without conversion.

Fresh open and ordinary backup/restore retain edited item origin and the original
human reason/explanation choice. Retained suggestions are read-only historical
material: no request, consent, job, staging capability or protected authority
restores. Previously staged candidates remain editable with AI off. Required
origin and minimal traces survive optional response quota refusal or explicit
payload erasure; saved metadata cannot be rewritten or unavailable payloads
silently revived. The existing 256 KiB checkpoint and atomic-save rules apply;
there is no second research store. API schema data is separated into the
I/O-free `provider_contract.py` to avoid storage/profile import cycles.

```sh
python3.13 -B -m unittest tests.application.test_provider_proposal_work tests.application.test_paper_proposal_work
```

These checks cover owned wire return and personal retention. They do not
establish actual provider access protection, public TUI connectivity, useful
critique or human understanding. Public own-project init/open stays AI-off.

### Offline provider exercise

```sh
python3.13 -m claimbranch demo paper --provider
python3.13 -m claimbranch demo paper --provider --variant recorded --json
python3.13 -m unittest tests.application.test_paper_provider_example tests.application.test_paper_provider tests.security.test_provider_output -v
```

`paper_provider_example.workflow` runs five independent, fresh sessions over
the selected bundled paper: explicit adoption followed by a human edit,
cancellation, editing before arrival, expiry, and refusal. Each asks whether
Model A's 0.4 percentage-point accuracy loss at 20% pruning with mask seed 42
supports the same claim for the unmeasured seed 43. The request explicitly
selects the claim, current interpretation, observation, experiment definition
and still-unrun plan. Each session explicitly writes the question as an
unfinished draft with an empty rationale, then requests `include_draft=True`.
The question therefore passes the same field/byte/privacy checks and is part
of the exact reviewed request digest; it is not an accepted interpretation.
The fixed response names that evidence and preserves the uncertainty.

JSON includes the exact outbound review, arrival status, human Judgment,
retained contributions and unchanged source digest. All five routes permit a
manual review; only the explicit adoption route records an AI contribution.
Eligible raw result payloads are erased without breaking trace identity or
adopted provenance. The five sessions do not share an attempt budget and do
not represent five requests permitted in one session. Both `manual` and
`recorded` choose the source paper variant; the explicit adoption exercise uses
a frozen response in either variant.

This command is included and checked in the source ZIP. It has no endpoint,
file input, worker, TUI control or live request. Its scripted human actions and
fixed response verify continuation and provenance, not scientific understanding
or model usefulness. The runtime implementation remains unavailable for private
research and protected acceptance.

### Cumulative paper episodes

```sh
python3.13 -m claimbranch demo paper --episodes --variant manual
python3.13 -m claimbranch demo paper --episodes --variant recorded --json
python3.13 -m unittest tests.contract.test_paper_episodes tests.application.test_paper_episodes -v
```

This separately identified v3 example replays two episodes over one synthetic
paper. The second corrects the existing pruning observation from 0.4 to 1.2
percentage points, then records a different Interpretation and an explicit
challenge/status candidate. The first observation value and both contribution
chains remain. The recorded variant retains the first episode's AI influence
even though the second Judgment is manual. Both histories replay to their own
goldens. `merged` means a candidate scientific transition, not approval,
durable storage, manuscript completion or a successful V0 episode.

The [domain contract](../designs/2026-08-03-domain-model.md#cumulative-paper-episodes)
owns episode semantics and finite limits. `ResearchHistory.start_paper_series`
starts the explicit v3 profile; `append` takes the generated command envelope,
including exact heads/watermark, project/episode and supplied UTC clock. There
is no automatic conversion of an existing v1/v2 history. The original v2
constructors, commands, query shape and examples remain available.

For the TUI adapter:

- `PaperService(history).episodes()` returns `claimbranch.paper-episodes/v1`
  with active identity and detached episode metadata. It is available for v3.
- `query(ref, episode_id=...)` returns `claimbranch.paper-view/v2` for v3, using
  the same node/relation shape as the existing TUI. It adds the selected episode,
  all retained `judgments`, and an episode ID on Interpretation node content.
  The existing singular `judgment` is the latest decision on that reasoning ref;
  do not use it as a substitute for the complete contribution history.
  If an Interpretation enters a v3 paper AI context request, explicitly select
  its `episode_id` alongside the wanted scientific fields; omitting that origin
  fails. This prevents an earlier reading from being presented as the current
  episode's interpretation, without sending the full provenance history.
- An omitted episode selector chooses the active or latest closed episode.
  A closed episode's reasoning is frozen, but its evidence is current and global.
  Supply `at_operation` for a historical snapshot of both. The full source
  digest binds the selection; an old/as-of query is not fresh request consent.
- `PaperWorkspace(history).draft(episode_id, ref, node_id)` returns the same
  `PaperDraftSession` for that exact context. Repeated shared-node occurrences
  reuse it; another episode, ref or node starts a separate blank draft. A new
  workspace is volatile and permits 16 draft sessions. Reaching its limit
  retains existing drafts and rejects allocation instead of evicting work.
- `workspace.update_history(later_history)` requires an append-only extension
  of the same seed and validates every stored context before updating it.
  Existing drafts survive and remain in their original episode; changed source
  invalidates their prepared request/scientific/branch review. An explicitly
  calculated [branch candidate](#draft-to-branch-candidate) may be supplied here
  for volatile continuation; there is no accepted-write API on this adapter.

The current TUI's graph reader is exercised with v3 nodes and relations by the
service tests. Its presentation, episode selector and replacement of the current
local draft dictionary with `PaperWorkspace` remain the UI session's integration
work. These services select no keys, pane arrangement or styling. The CLI/ZIP
journey checks draft separation and retained history without opening a terminal
UI or provider. Nothing persists after process exit. The example now begins the
second reading with a blank draft, constructs its selected branch, and exercises
the [exact merge review](#exact-cumulative-merge-review) before comparing the
calculated graph/provenance to the frozen example and discarding the review.

### Draft to branch candidate

`PaperDraftSession.prepare_branch(request)` accepts the same closed amendment
request as `prepare_changes`: exact draft ID/revision and paper view binding,
explicit amendments and selected IDs. It requires a complete interpretation and
human rationale in the active v3 episode. On `main`, it can create an alternative
when none exists. If an alternative exists, use a draft bound to that ref;
recording cannot replace it or continue an already merged episode. Closed-episode
drafts still support hypothetical `prepare_changes`, not branch recording.

The detached `prepared-paper-branch/v1` response contains before/after graphs,
selected/required/omitted amendments, the combined provenance, exact proposed
commands and candidate-history digest. Only the selected amendments and required
dependencies enter the branch; a matching current-episode Interpretation must
be present. An omitted plan is not recorded and a missing Interpretation is not
invented. Preparation neither changes evidence/main nor saves a project.

An independent draft is joined to the recorded current-episode Judgment before
review. The existing Contribution prefix stays exact; new contributions retain
author, original text, human rationale and proposal/trace identity while their
parent links are rebound. Shared prefixes appear once. This prepared combined
chain becomes the working draft's provenance, so re-review and later continuation
do not duplicate it. Other episode Judgments remain separate. Eight-contribution
overflow fails without truncation. If a superseded draft cannot be joined while
keeping its stated rationale, refine it before preparing again; its buffer stays.

After inspecting that response, `branch_candidate(prepared["digest"])`
independently recomputes the exact candidate from owned source and draft state.
It returns a new immutable `ResearchHistory`; neither the session nor workspace
is updated automatically. For an explicit in-memory continuation, supply it to
`workspace.update_history(candidate)`, then construct `PaperMergeSession` over
that same candidate. Further recordings use the alternative-bound draft; the
original main-bound buffer stays in its original context. Merge selection and
AI explanation remain a separate review, and conditional debt is not opened by
staging. No returned value authorizes protected persistence.

`get_branch_preview()` returns a detached current response. Five-minute expiry,
backwards clock, edit, AI adoption, source refresh, new preparation (including
`prepare_changes`) and `not_now()` invalidate it. Invalid input preserves the
last valid preparation and draft. The UI owner can render the existing graph
shape and wire these calls without changing scientific rules or copying a
rationale into another form. The [terminal controls](#terminal-paper-prototype)
now expose this detached continuation; durable candidate restart remains unavailable.

```sh
python3.13 -m unittest tests.application.test_paper_branch -v
python3.13 -m claimbranch demo paper --episodes --variant recorded --json
```

### Exact cumulative merge review

`PaperService(history).preview_merge(selected_ids, episode_id=...)` reads the
explicit active v3 episode's recorded alternative. Its `paper-merge/v1` response
uses the same before/after node/relation and impact shapes as `preview_changes`.
It separates selected/required/omitted amendments, inherited record references
and global evidence references. Scientific reach includes the existing graph's
explicit paths; it does not invent changed claim statuses or evidence.

Use `PaperMergeSession(history, episode_id=..., manuscript_digest=..., clock=...)`
from `claimbranch.application.paper_merge` for a volatile exact review:

1. `prepare(selected_ids)` returns a detached preview with a fresh operation
   identity, manuscript fingerprint and at most 300 seconds of validity. Inspect
   its graphs and original/current contribution chains. The fingerprint is
   supplied context, explicitly unverified; the adapter never reads a file.
2. `finish(preview_digest, disposition=..., answers=[...])` reuses the recorded
   Judgment/rationale and constructs the exact merge command internally. A
   manual current Judgment still requires explanation or deferral when inherited
   source Judgments contain AI. The response includes the sealed review payload,
   exact command and conditional obligations; it is not a receipt.
3. `candidate(review_digest)` recomputes the binding and returns a new immutable
   `(ResearchHistory, AcceptanceCandidate)` value with authorization unverified.
   It neither replaces the session's source nor saves/accepts the result.
   `not_now()` clears this review without altering history or cached drafts.
4. `update_source(later_history, manuscript_digest=...)` accepts only an append-only
   extension of the same seed. Any source or manuscript change clears the review;
   it never switches episode. Expiry, clock reversal, reselection and a changed
   explanation likewise prevent reuse of the old review. Use `get_preview()`
   and `get_review()` for detached current values.

The core `prepare_merge_review` / `append_reviewed_merge` support v3 with retained
source Judgments and independent history reconstruction. A caller can hash its
own data; only an owned-source reconstruction establishes the scientific binding,
and even that supplies no native approval. The v1/v2 seal payloads, commands and
frozen manifests retain their existing format. The
[domain contract](../designs/2026-08-03-domain-model.md#cumulative-paper-episodes)
owns the invariant and candidate limits.

The TUI owner can render these graph/provenance values without adopting new
keys or layout. [Draft staging](#draft-to-branch-candidate) now constructs the
recorded alternative; connecting the controls remains UI integration work. A
draft review dictionary cannot substitute for a sealed merge. R2/R4 still own native
authorization, protected persistence, restart and recovery.

```sh
python3.13 -m unittest tests.contract.test_paper_merge_review tests.application.test_paper_merge_session -v
python3.13 -m claimbranch demo paper --episodes --variant recorded --json
```

### Conditional work and manuscript review

`PaperService(history).pending_work(episode_id=...)` reconstructs outstanding
consequences from recorded v3 candidate merges; omit the episode selector to
see the whole paper. Each merge retains a manuscript-impact review item, even
when a selected plan supplies no new wording. Explicit explanation deferral
adds an understanding-review item. A draft, preview or Not now does not create
one. Closing an episode never resolves these items, and another episode preserves
their stable causal IDs, original Judgment and source contributions. Changed
main/evidence is reported separately. These `paper-work/v1` values are
`pending-if-accepted`: the candidate history contains no native acceptance or
closure receipts, so they are not accepted Debt records. A disposable canonical
cache belongs to the immutable service revision; returned objects are detached.

`PaperService(history).understanding_return(work_id, project_id=...)` reopens one
understanding item from that list. It returns `claimbranch.paper-understanding-return/v1`:

- `work` retains the original Judgment, source Contributions, selected/required/
  omitted references, affected claim/anchor references and explanation deferral.
- `original` is the main argument immediately after the causal merge, rebuilt
  from its exact history prefix. Its `at_operation` names that merge. Later
  evidence corrections leave this view and its fingerprint unchanged.
- `current` is the latest main argument, including current global evidence and
  its episode. It may belong to a later episode than the cause.
- The work item's independent head/evidence flags and
  `history_changed_since_merge` expose changes. The latter includes episode
  closure or other recorded history; it does not assert a scientific change.

The explicit project and owned item lookup reject unknown IDs, manuscript items,
other projects and unsupported history versions. The projection digest binds
both views, so even evidence-only changes produce a different context
fingerprint. To verify it, first recompute each view's digest over that view
without its `digest` field and require a match with its embedded digest. Then
hash the response without its top-level `digest`, replacing `work` with its
canonical digest and `original`/`current` with those verified view digests.
This preserves each component's 256 KiB canonical limit without truncating
their full content when the combined read response exceeds one record's limit.
The combined response is a read envelope, not a canonical storage record or
sealed review/consent. The response retains
`conditional-on-acceptance`, zero accepted writes/debts and unavailable
acceptance/closure; `accepted-cause-review-unavailable` explains the missing
accepted binding. Reading performs no artifact access, provider call, state
mutation or explanation closure. The [partial-explanation adapter](#partial-understanding-explanation)
now retains unfinished text in memory; protected persistence and the TUI return
action remain separate implementation work.

For an explicitly synthetic service rehearsal:

```python
from claimbranch.application.paper_service import PaperService
from claimbranch.fixtures import replay_example

service = PaperService(replay_example("recorded", series=True))
pending = service.pending_work()
item = next(item for item in pending["items"] if item["kind"] == "understanding")
context = service.understanding_return(item["id"], project_id=pending["project_id"])
```

`PaperManuscriptSession(history, work_id=..., source=..., frozen_response=..., clock=...)`, from
`claimbranch.application.paper_manuscript`, connects one such manuscript item
to a wording review. It starts with a blank `session.draft`, using the existing
`PaperDraftSession` edit/rationale contract. Wording is never copied automatically
from the selected graph or from an omitted Interpretation. The cause episode
and Judgment remain visible while the review binds the current paper context.
AI is off unless the constructor supplies a frozen response. The existing
`session.draft.prepare_request`/dispatch/adoption flow then supports an explicit
offline wording request using selected scientific fields and optional draft
text; it does not send the supplied manuscript bytes implicitly. Adoption
revokes any prepared manuscript review and retains the AI original after human
editing. No live endpoint is added.

1. Supply `source` as UTF-8 bytes, at most 64 KiB, with exactly one ordered LF
   `% claimbranch:start id=<anchor>` / `% claimbranch:end id=<anchor>` pair for
   the history's anchor. `None` means unavailable source and produces no diff.
   The adapter does not read paths or verify a filesystem identity. Even a
   valid supplied fingerprint leaves `source_verified` false.
2. Call `session.draft.edit(text, rationale)` with complete human wording/reason,
   then `prepare()`. The returned `prepared-paper-manuscript/v1` contains exact
   before/after text, a source diff, byte fingerprints, current history/head/
   evidence, work identity, draft binding and all current source Judgments.
   Literal TeX metacharacters are escaped; source bytes outside the block remain
   exact, including mixed line endings and decomposed Unicode. Artifact text is
   rendered from its original bytes outside canonical JSON normalization; the
   canonical review binds the exact source/postimage hashes. The postimage must
   also fit 64 KiB; an oversized candidate fails rather than truncating it.
3. After inspecting that response, call `finish(preview["digest"],
   disposition=..., answers=[...])`. It reuses the wording's rationale and
   independently reconstructs the owned preview. Current source AI requires an
   explanation or explicit deferral even when the new wording is manual.
   `postimage(review["digest"])` then returns candidate bytes only. It performs
   no write/compile/restore, opens no accepted debt and resolves no work item.
4. `get_preview()` and `get_review()` are detached current views. Draft changes,
   five-minute expiry, backwards time, new preparation and `not_now()` revoke
   the review; Not now retains wording. `update_source(later_history, source=...)`
   requires an append-only extension of the same seed, invalidates changed
   history or source (including a new run with unchanged heads/watermark), and
   retains the draft. Missing source stays unavailable. A later episode requires
   a new review session; the old wording remains in its original draft context.

The native writer, file/fencing identity, durable intent/encrypted preimage,
pinned compiler and actual recovery/closure belong to the unfinished R2/R4/R5
boundary. This session cannot be supplied as an authorization receipt. TUI
control integration is separate and is not part of these APIs.

```sh
python3.13 -m claimbranch demo paper --pending --variant recorded --json
python3.13 -m claimbranch demo paper --episodes --variant recorded --json
python3.13 -m unittest tests.application.test_paper_work tests.application.test_paper_manuscript -v
```

The episode journey's `followup` object uses the calculated merge candidate as
its source. Its `current`, `pending_work` and manuscript `preview` share that
history digest. It reconstructs the same work through replay, supplies a labeled
synthetic marked-text illustration based on the earlier fixture Judgment, and
explicitly scripts new human wording from the current fixture Judgment. After
reviewing the postimage it chooses Not now: wording remains, conditional work is
unchanged and no file was opened or saved. Both manual and inherited-AI routes
run through the source ZIP. This tests connections, not a restart of a protected
store, an original manuscript or a human comprehension outcome.

### Partial understanding explanation

`PaperUnderstandingSession` from `claimbranch.application.paper_understanding`
adds unfinished explanation to an existing conditional understanding item.
Construct it with the immutable v3 `history`, explicit `project_id` and `work_id`.
It never calls a provider, opens a file or constructs an accepted Debt. Its
`state()` combines the return service's original/current context, the draft's
bound `draft_basis`, deterministic `topics` and detached `draft` values. Known
source AI remains visible even while writing manually; there is no comprehension
score or completion action.

The versioned topic catalog selects one to three contextual issues: affected
claim scope, referenced evidence/interpretation, and a selected unrun experiment
or otherwise an applicable manuscript consequence. Each includes exact causal
node/relation references and the causal view digest. Read those references in
`context.original`; current source values are separately in `context.current`.
Recorded plans remain unrun, references do not verify artifacts, and manuscript
anchors do not supply exact manuscript wording. A plan omitted from the merge
cannot become a follow-up explanation topic. This catalog handles existing
conditional deferrals; it is not the future acceptance-impact classifier.

- `edit(topic_id, text, reuse_rationale=None)` records incomplete text, including
  empty/whitespace content. It normalizes text to NFC; synchronize an editor
  with the returned text rather than comparing it with decomposed input.
  `reuse_rationale=True` references
  `context.work.judgment.rationale`; it does not copy that reason into the text
  or mark an answer complete. Later edits preserve this reference unless it is
  explicitly set to `False`. The surrounding editor owns keep, cancel and undo;
  this API records only edits passed to it.
- `snapshot()` or `leave_open()` returns identical canonical draft bytes.
  An adapter can retain them on cancel/leave and pass them as `draft=...` to a
  new session with the same history or its append-only extension.
  This exercises serialization/reconstruction in memory. It neither saves to
  disk nor extends the private TUI checkpoint format. Normal process exit loses
  these bytes unless a future approved custody adapter retains them.
- `update_source(history)` accepts the same append-only lineage. Existing text,
  rationale references, topics and `draft_basis` remain intact. Changed evidence,
  reasoning or other history makes `context_current` false. Editing stale text
  does not silently rebind it. A rollback or changed causal history is rejected.
- After inspecting the displayed context, call
  `rebind_context(state["context"]["digest"])` to retain the text while explicitly
  changing its basis. A stale fingerprint fails without mutation. Rebinding
  supplies no review, consent, completed answer or closure capability.

The generated [draft schema](../../schemas/paper-understanding-draft-v1.json)
defines `claimbranch.paper-understanding-draft/v1`. It binds the project, work,
cause, topic rule/set and exact historical context; texts allow at most 16 KiB
UTF-8 each and the complete draft at most 64 KiB. Restore rejects unknown fields
or versions, wrong owners/topics, changed causes and missing/mismatched context.
The 64 KiB limit counts canonical JSON escaping and metadata: several long
newline-heavy entries can exceed it even when each text fits its own limit.
Such an edit fails atomically, retaining the prior draft; the editor must keep
its unsaved buffer. JSON Schema validates shape, while runtime also checks
canonical bytes, unique topic IDs in owned order and the reconstructed context.
All source bindings are reconstructed from history; serialized text is still
untrusted and unaccepted. The two views and the old draft basis are a read
envelope, not another canonical research record. Accepted answers/deferral,
native authorization, durable custody and actual human closure remain separate.

The [terminal return workflow](#terminal-paper-prototype) connects this service
to a topic reader/editor through `W`. It retains drafts and cancelled input in
memory, separately from graph-note recovery; it does not serialize these
snapshots into `--draft-file`.

This synthetic rehearsal keeps its snapshot only in a Python variable:

```python
from claimbranch.application.paper_service import PaperService
from claimbranch.application.paper_understanding import PaperUnderstandingSession
from claimbranch.fixtures import replay_example

history = replay_example("recorded", series=True)
pending = PaperService(history).pending_work()
item = next(item for item in pending["items"] if item["kind"] == "understanding")
session = PaperUnderstandingSession(history, project_id=pending["project_id"], work_id=item["id"])
topic_id = session.state()["topics"][0]["id"]
session.edit(topic_id, "Still checking which conditions limit this judgment.", reuse_rationale=True)
unfinished = session.leave_open()
resumed = PaperUnderstandingSession(history, project_id=pending["project_id"], work_id=item["id"], draft=unfinished)
```

```sh
python3.13 -m unittest tests.application.test_paper_understanding tests.application.test_paper_work -v
python3.13 -m scripts.export_research_schema --check
```

### Proportional paper review

`claimbranch.application.paper_review_policy.PaperReviewPolicy(history,
episode_id=...)` supplies an in-memory candidate assessment for an active v3
paper episode. The [finite policy and lineage contract](../designs/2026-08-03-domain-model.md#finite-review-policy-and-amendment-lineage)
owns the action/impact table and bounds. This service has no TUI command, model
client, accepted writer or private storage; it does not change the legacy sealed
review policy used by existing candidates.

- `revise_amendment(record, sources=(judgment, ...))` registers a typed record
  and retains its earlier revisions/sources through subsequent manual edits.
  It returns immutable `AmendmentLineage` bytes/digest. Sources may be unfinished
  judgments, so AI help is usable before a complete reason exists. The adapter
  retains known origin by record ID; callers cannot replace it with a manual
  label. `AmendmentLineage.restore(raw)` checks a separate candidate snapshot's
  closed shape and chains; there is no restore-to-session or accepted-origin
  import in this increment. A new session cannot claim durable provenance from
  old v3 commands, which lack these per-record references.
- `capture(ref, amendment_ids, judgment=None)` projects registered drafts,
  including an empty set. No completed judgment or explanation is required.
- `record(ref, amendment_ids, selected_ids, judgment)` reviews selected/required
  changes with a complete existing reason. Use alternative when it exists,
  otherwise main as the base for a future alternative. This calculates a
  medium-impact assessment, not a branch append or implicit merge.
  Its judgment uses the same source-prefix/suffix join as `branch_candidate`;
  the existing reason is reused, without rewriting a second account.
- `merge(selected_ids)` reloads the recorded alternative and its inherited
  judgments. A high-impact AI assessment supplies deterministic contextual
  topics; a manual history has no AI explanation requirement. Registered origin
  for an included record must exactly match that recorded revision.
- `finish(assessment, disposition=..., entries=...)` recomputes the last owned
  assessment. Entries for `answered` name every topic in order with `topic_id`,
  `text` and Boolean `reuse_rationale`. Blank text is valid with an explicit
  reference to the existing reason; otherwise an answer is required, without
  grading. `deferred`, `not-now` and `not-required` take no entries and must
  match the finite policy. Preserve unfinished explanation separately rather
  than passing it as a completed answer or silently erasing it on deferral.
  Not now or a changed explanation decision revokes a prepared operation seal;
  repeating the identical decision preserves it.
- `update_source(history)` permits only an extension of the exact owned seed
  and commands. It retains registered origin but invalidates a prepared review
  when history changes, including an evidence correction with unchanged heads.

Failed scope preparation preserves the previous valid assessment and seal;
it does not install the invalid selection. Callers must display the scope
actually returned, and use `finish(..., disposition='not-now')` to cancel it.
An earlier human rationale can accompany later AI wording without a fabricated
human edit. Only future exact foreground authorization can adopt that displayed
pair; this service neither confirms its meaning nor grades understanding.

The eight-revision limit is explicit: an additional edit fails and retains the
last good lineage. There is no reset that erases known AI origin. If a recorded
record subsequently differs and no revision capacity remains, this session
cannot assess that record for merge; it must report the bound rather than
silently dropping provenance. Capture has no acceptance selection; its authored
IDs are carried by `lineages` and the scientific draft fingerprint.

An assessment's immutable `payload` and `digest` bind source context, scientific
scope, contributions, origins and topic rules. The returned decision adds its
own digest and reports `none` or `opens-if-accepted` understanding debt, always
with acceptance/authorization unavailable. These are contextual assessments,
not expiring authorization reviews; no time, session nonce, native approval or
receipt is supplied by assessment/finish. Repeated calculation creates no
record or debt. The [exact operation API](#exact-paper-operation-review) adds
the versioned request and expiring seal. Future R2/R4 integration must reload
authoritative sources and bind that review to a matching receipt. Do not feed the new
decision into a legacy seal as though contextual topic identity were retained.

The existing text-only Proposal still cannot supply typed AI graph amendments.
The new source references preserve stated contribution influence; they do not
prove which structured provider fields were adopted. T6 must connect explicit
adoption and owned traces before making that claim. Both manual and frozen-AI
tests run without a provider:

```sh
python3.13 -B -m unittest tests.contract.test_amendment_lineage tests.application.test_paper_review_policy -v
python3.13 -B -m scripts.export_research_schema --check
```

### Exact paper operation review

`PaperReviewPolicy` connects its current record/merge assessment to the
[versioned operation contract](../designs/2026-08-03-domain-model.md#exact-versioned-paper-operation-review).
It remains an in-memory candidate API, independent of TUI, native signing and
private storage:

- `prepare_operation(assessment, disposition=..., entries=..., operation_id=...,
  manuscript_digest=..., session_nonce=..., sealed_at=..., expires_at=..., now=...,
  parent_review_digest=None)` returns immutable `PaperOperationReview` bytes
  and digest. Supply integer epoch seconds and at most a 300-second lifetime.
  Reuse `finish`'s explanation format. The assessment must still be current;
  capture/Not now, ID collisions, backwards time and illegal branch effects fail.
  A record's Interpretation must match its joined Judgment, even if an earlier
  draft preview was legal. No omitted amendment becomes an operation effect.
  A successful preparation replaces this owner's current seal; failed input
  leaves the last valid seal intact.
- `restore_operation(raw, manuscript_digest=..., session_nonce=..., now=...)`
  checks canonical shape, freshness and exact recomputation from independently
  owned history/origins. It does not import those sources or select the loaded
  scope as current. Missing origins cannot be recovered by trusting embedded
  snapshots. Supplied manuscript/session values must match.
- `operation_candidate(review, manuscript_digest=..., session_nonce=..., now=...)`
  rechecks the review and current owned preparation/seal. Restoring an older review
  cannot bypass newer selection/draft work. A fresh owner must independently
  reconstruct and explicitly prepare the assessment and seal before requesting
  a candidate. Restore alone cannot reinstate a revoked seal. The result contains exact operation bytes/digest and review
  digest, with `requires_authorization=True`, `authorization_verified=False`.

The seal includes complete source contributions, included amendment revisions,
topics, rationale references and the conditional deferral decision. Bounds
reject oversized envelopes without trimming sources. The optional parent
digest proves no accepted relationship. These APIs supply no receipt, debt
transition, accepted reducer, project save/reopen or original-file verification.
Do not append the raw operation to legacy `ResearchHistory` or flatten its
merge explanation into an old review. Protected integration must retain and verify
the exact review as well as its operation.

`commit_candidate(review, manuscript_digest=..., session_nonce=..., now=...)`
now prepares one bounded, conditional transaction-effect envelope using that
same current seal. It keeps the complete review and its digest, forecasts the
resulting reasoning heads and includes deterministic, exact-cause debt openings.
Recording changes only alternative and opens no debt. A selected merge retains
the existing single-anchor manuscript obligation; explicit contextual deferral
also includes an understanding obligation bound to the original topics. No
legacy command is appended, so amendment-only AI and rationale references remain
intact. `restore_commit_candidate(raw, review, ...)` rederives the envelope from
current owned sources and seal; loading cannot install a seal or recover consent.
The [generated candidate schema](../../schemas/paper-commit-candidate-v1.json)
keeps the 256 KiB limit, rejecting rather than trimming provenance. These are
forecasts with zero accepted writes/debts, not accepted state or a receipt.
Native source loading, receipt consumption and atomic encrypted persistence
remain unfinished. This API is independent of TUI and opens no authentication UI.

`record_transition(review, manuscript_digest=..., session_nonce=..., now=...)`
now replays the exact **record-interpretation** effect into a new unaccepted
`ResearchHistory`. First recording creates the alternative and records the
interpretation as one returned transition; subsequent recording appends only
the exact record command. The existing reducer checks scientific dependencies,
matching interpretation/judgment, contribution retention, identities and bounds.
Prepare this review with `prepare_operation(..., bind_origins=True)`. Its
[v2 format](../../schemas/paper-operation-review-v2.json) binds the complete
origin-registry snapshot digest, including omitted drafts. Default preparation
retains v1 compatibility; v1 cannot supply this transition. The native signing
adapter now accepts closed v2 record reviews and signs the
exact packet including the whole-registry commitment. This remains synthetic
unaccepted attestation, not independent origin/source authentication or accepted
recording. Native parsing refuses v2 merge, missing/invalid registry digests,
unknown versions and extra review fields; Python additionally checks the complete
closed review and canonical digest before reading key fields. Actual foreground
v2 approval/cancellation has not been observed. Old v1 reviews remain readable; old readers reject v2 rather than
silently drop the registry commitment.
Main and global evidence stay unchanged. The result retains full review bytes,
before/after manifest digests, derived commands and the complete independent
origin registry in the [bounded transition schema](../../schemas/paper-record-transition-v1.json).
`PaperReviewPolicy.from_record_transition(result, expected_review_digest=...)`
requires a digest retained independently from the original reviewed source,
not one read out of an untrusted transition. It verifies the full review,
source/result histories and complete registry before preparing further candidate
work, with no inherited current seal. Missing or substituted origins refuse
continuation. Do not pass its bare legacy history to `from_work_sources`: that
unverified legacy factory cannot establish AI absence after provenance was
discarded. Omitted draft origins stay available without entering recorded science. Keep the whole
transition; bare legacy commands cannot replace its review/provenance envelope.

`restore_record_transition(raw, review, ...)` rederives against the current
owner's independently held sources and seal, never adopting embedded origins.
A fresh process can inspect/rederive the old review but must explicitly prepare
its own assessment/seal before calculating a transition. Replay is repeatable
and byte-stable, not receipt consumption or accepted history. Merge requests
are refused: their full contextual explanation/debt policy must not be flattened
into a legacy merge command. This API installs no history in the original owner,
changes no manuscript, creates no accepted debt and persists nothing. Native
source loading, accepted genesis and atomic log remain unfinished; TUI and work
checkpoint formats are unchanged.
Keeping all origins is an explicit bounded policy: up to 64 origins and a total
256 KiB transition. Even a small selected change may exceed the aggregate because
of omitted drafts. Refuse it without pruning origins or losing current writing;
this is not an automatic expansion or migration. A digest check proves integrity
relative to the independently held expectation, not native authority.
Record preparation checks the complete transition budget before installing the
seal and freezes its registry snapshot. Later omitted-draft edits stay in the
original owner but do not change that sealed transition or its retry bytes.
The bound continuation API checks historical science at the original sealed time;
it supplies no current approval and cannot make an imported bundle authoritative.

```sh
python3.13 -B -m unittest tests.application.test_paper_commit tests.application.test_paper_operation tests.application.test_paper_review_policy -v
python3.13 -B -m scripts.export_research_schema --check
```

### Encrypted unaccepted work checkpoint

`claimbranch.application.paper_work_store` supplies a real disk checkpoint for
the existing candidate services, independent of TUI integration. Its generated
[work schema](../../schemas/paper-work-v1.json) retains cumulative source
history, independent amendment lineages, an optional Judgment and exact review,
and conditional partial-explanation drafts. The aggregate canonical envelope is
at most 256 KiB; individually valid maxima need not fit together. Oversized work
fails visibly without truncating provenance or replacing the previous file.

This raw-key path remains a synthetic developer API. It does not initialize a protected
research project or replace the TUI's manual checkpoint. Product key custody,
accepted writes, recovery-key enrollment, original-source verification and
cross-device backup remain unavailable. This path creates no device key; the
optional [device work-key adapter](#device-work-key-reopening-and-recovery) below
adds local data-key reopening separately from approval authority.

- `PaperWork.from_policy(policy, judgment=None, review=None, explanations=())`
  takes immutable history/origins from the owner. Explanations are the bytes
  returned by `PaperUnderstandingSession.snapshot()`. Alternatively,
  `PaperWork.create(history, episode_id=None, ...)` admits a legitimate empty
  paper without fabricating evidence. An active episode is required for origins,
  Judgment or review. An AI-only Judgment may still have no human reason.
- `PaperWork(payload)` validates all source replay, lineage, project/cause and
  review bindings before installing anything. A review is checked at its
  original seal time for historical inspection, including after expiry. It
  cannot become a current request on return. `new_policy()` starts without an
  assessment or seal; explicitly prepare a fresh review before candidacy.
  Saving a review against changed sources fails; preserve its earlier complete
  checkpoint or explicitly prepare the intended new work rather than silently
  dropping its source. Imported v3 history remains authorization-unverified.
- Use `with MacWorkCipher() as cipher` and
  `with PaperWorkStore(directory, cipher=cipher, key=key, project_id=...) as store`.
  The directory must already exist, be owned mode 700 and outside Git. The key
  is a caller-owned random 32-byte value; it is never an argv argument or file.
  `load()` returns `None` for a new store or fully reconstructed work; `save(work)`
  encrypts before writing a private staging file. The exclusive session lock,
  source-file comparison and atomic replacement prevent cooperative concurrent
  writes and detected external replacement. Existing work must decrypt and
  validate before replacement. Symbolic links, hard links, special files and
  non-private files are refused. Reserve `work.cbw`, `work.lock` and
  `.work-` followed by 32 lowercase hexadecimal characters for this store.
  After taking the lock, reopen reclaims private, owned, unlinked regular
  staging files within the byte limit. Other names, links and public files
  remain untouched. A directory scan exceeding 128 entries fails before cleanup.
- `work.cbw` contains `CBWK`, version 1, random 32-byte salt and AES-256-GCM
  combined nonce/ciphertext/tag. CryptoKit derives the encryption key with
  HKDF-SHA256 and the purpose `ClaimBranch unaccepted paper work v1`; it
  authenticates the format/version/salt header. The helper is packaged with
  the source preview and built explicitly in a private temporary directory
  using installed Xcode command-line tools. AES-GCM and HKDF known answers run
  before use. Windows/Linux have no encryption adapter in this increment.

A failed write before replacement preserves the last checkpoint. On Mac both
the staged file and replaced directory request `F_FULLFSYNC` after `fsync`,
following [Apple's synchronization contract](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fcntl.2.html).
Unsupported flushes fail rather than silently weakening the requested barrier.
A directory
flush failure after replacement reports an uncertain outcome and requires
closing/reopening before continuing, including reusing the same store object.
Process death can leave an encrypted staging file until the next exclusive
open; it cannot install partial plaintext. This is process-interruption
evidence, not a power-loss/filesystem durability certification. Keys/plaintext
still exist in caller/helper memory; this component supplies no hostile
same-user isolation or rollback-resistant accepted authority. Loading a saved
explanation creates a new in-memory editor; later edits need another explicit
checkpoint. Ciphertext plus a lost key is not recoverable through this API.

```sh
python3.13 -B -m unittest tests.application.test_paper_work_store -v
python3.13 -B -m scripts.export_research_schema --check
```

### Source-built Mac runtime preflight

`python3.13 -m claimbranch runtime build/check` provides an explicit developer
build and identity preflight for the pending Mac approval integration. It needs
Apple Silicon macOS and installed Swift command-line tools. No publisher account,
profile, credential, installation, authentication prompt or research data is
used. `doctor` remains nonexecuting and continues to report protected acceptance
unavailable. These commands do not implement the broker/gateway's scientific
operations. Separate native modes serve the bounded synthetic APIs below;
ordinary build/check never invokes them.

```sh
mkdir -m 700 "$HOME/claimbranch-native-example"
python3.13 -m claimbranch runtime build --directory "$HOME/claimbranch-native-example" --json
# Retain build_pin from the successful result separately; it is not a secret.
python3.13 -m claimbranch runtime check --directory "$HOME/claimbranch-native-example" --expected-build <retained-build-pin> --json
```

Replace `<retained-build-pin>` before running the last command. The directory
must already exist, be private and outside Git; build requires it to be empty.
Ancestors must be root/user-owned without group/world write, except root-owned
sticky temporary roots. These mode checks are not an ACL or hostile same-user
isolation proof. New files receive their exact private modes despite umask.
The package includes `native/RuntimeIdentity.swift`. Compilation fixes separate
broker/gateway roles, signs each locally with ad-hoc hardened signatures, and
records source/binary SHA-256 and role-specific code hashes in a closed
[`runtime.json` format](../../schemas/mac-runtime-build-v1.json). This is an exact-build identity, not a publisher signature or
proof that an arbitrary supplied binary was built from claimed source. Rebuilding
may change the pin; an old pin is never silently updated. Changed packaged
Swift source requires a fresh build, even when the earlier pin still matches
the old executables.

`check` requires the separately retained pin. It does not trust a replacement
manifest beside its own executable. Before launch it validates the complete
inventory, private single-link files, exact bytes and static signature, then
compares the helper's dynamic self identity and running hardening. Its tools
receive a minimal environment with no inherited provider/credential, DYLD,
Python-path or developer-tool overrides. Build intermediates use the owned
temporary directory; both roles share its one module cache. Commands use bounded
output and deadlines; process groups are cleaned before reaping their leader. There is
no arbitrary-program launch method in the command or native helper.

Build never replaces existing files. An interrupted/failed build may leave
incomplete files, including an empty manifest reservation; check refuses them.
Keep them for inspection and retry in a fresh empty destination. There is no
automatic deletion, update or repair. Exit 0 means only build/preflight succeeded,
1 is failure, 2 is invalid command syntax, and 130 is interruption. Fixed
`runtime-*` diagnostics distinguish pin/source mismatch, unsafe placement,
incomplete builds, tool failure and timeout without echoing private paths. Output failure
after completion reports that the completed build remains; if its pin was lost,
rebuild in a new destination rather than accepting a pin read from an untrusted
adjacent manifest. Read-only checks change no runtime or research files.

The Python APIs are `build_runtime(directory) -> build_pin` and
`check_runtime(directory, expected_build) -> report`. A caller-supplied pin is
not human authority or enrolled trust. The build/check APIs supply source-build
and observed self-identity evidence only. They do not establish peer delivery,
signing-key custody, accepted-source loading, atomic receipt consumption,
protection against an unrestricted same-user process racing filesystem changes,
production updates or SSH/Linux support. Those remain the R2/R4 integration
requirements. No saved candidate or operation becomes accepted through this API.

```sh
python3.13 -B -m unittest tests.application.test_mac_runtime -v
```

The separate synthetic `application.mac_review_delivery.deliver_operation_review`
API now connects a current owned `PaperOperationReview` to the packaged native
roles. Supply the runtime directory/build pin, owning `PaperReviewPolicy`, review,
and a `current_context` callback that reloads `manuscript_digest`, `session_nonce`
and `now`. The application rederives the exact candidate before and after
transport; changed scope, context or expiry refuses application success without
changing research. The callback's values are not independent source-fidelity or
accepted-store evidence.

Both native roles identify the connected peer through the kernel audit token,
same-user check, opposite fixed role's identifier/CDHash and running hardening.
Only after mutual verification does the broker send the complete review and a
fresh 32-byte exchange nonce over a private temporary Unix socket beneath the
OS-reported per-user temporary root, independent of shared `/tmp` or `TMPDIR`. The gateway
compares them byte-for-byte with its expected input. Bounds cover the 256 KiB
review, framing, input/output and an eight-second native continuous-time deadline.
The sender retries only not-yet-bound/listening connections within that deadline;
expensive preflight runs before either peer starts and again after delivery.
Native stdin requires a pipe and restores its status flags. The one-connection
receiver exits and removes its own socket; the Python owner
cleans bounded child process groups and the temporary directory. Results expose
digests/counts and `delivered-unaccepted-review`, never review prose or a receipt.
Review bytes go through pipes, not command-line arguments or persistent files.

This closes a transport connection within B01, not B01 itself. The build pins
remain caller-held rather than enrolled authority. No key, prompt, accepted
write, TUI connection, supported-provider confinement or product custody follows.
An unrestricted same-user process can launch these binaries; that does not make
its input trusted science. Future approval and storage must independently load
accepted sources, enroll trust, obtain human presence and consume receipts.

```sh
python3.13 -B -m unittest tests.application.test_mac_review_delivery -v
```

The separate `application.mac_key_registration` API prepares a **new synthetic
device-key candidate**, not trusted enrollment. Its concrete sequence is:

1. `preview_key_preparation(runtime, expected_build, directory, project_id=...)`
   checks an existing empty private directory outside Git and the source-built
   roles. `KeyPreparation.display()` exposes the project, exact build and role
   hashes, directory device/inode and fresh nonce. Preview writes nothing.
2. `prepare_key(runtime, expected_build, directory, preparation)` rechecks that
   preview before starting the pinned broker. The foreground review displays
   project/build/destination and requires **새 키 준비** followed by explicit
   macOS authentication. Only that authenticated context can create a new
   user-presence-protected Secure Enclave signing key and sign the registration.
   It never accesses an existing credential or changes research/manuscript state.
3. Retain `registration_digest` from a successful `prepared` result separately.
   `reopen_key(runtime, expected_build, directory, expected_registration,
   project_id=...)` checks the exact record/request/signature, reconstructs the
   same device key and requires observed noninteractive signing denial in a
   fresh native process. It opens no authentication window.

The closed [registration format](../../schemas/key-registration-v1.json) binds
the public identity and opaque, device-bound representation to the complete
request through a domain-separated signature. Python validates structure,
private files and digests; the pinned native helper verifies the signature and
device key. A self-signed imported record is not enrolled authority. Neither
the private key plaintext nor the opaque representation is printed in results.
The latter remains sensitive even though it is not a portable private key.

The broker reserves `key-registration.json` create-only before displaying review.
Cancelled, expired, failed or interrupted attempts can retain an empty or
incomplete reservation; expiry during final persistence is a failure and can
leave an unaccepted candidate without a successful result. Ordinary cancelled
or expired results require an empty private reservation or no file. Preserve
these files and retry in a
fresh directory. Never infer completion from file presence or obtain a lost
registration pin by trusting the adjacent file. The 90-second native deadline,
one-shot authentication/generation and terminal cancellation gate discard late
callbacks. Cancellation reports `review-window` or `os-authentication`; expiry
reports `deadline`. A brief bounded callback wait distinguishes simultaneous
native user cancellation and app termination without permitting generation.

These are synthetic contributor APIs, not public own-project setup or a TUI
connection. Build changes, directory replacement/relocation, another project,
wrong pins, malformed/changed files or unavailable keys are refused. There is
no fallback software key, overwrite, automatic re-enrollment or migration.
Every result keeps `authorization_verified` and `product_custody_verified`
false. Code-private custody, actual worker denial, trusted enrollment, approved
research receipts and replacement-device authority remain B01/B05 work. Actual
foreground approval/cancellation and positive device reopening require separate
human observations; automated negative tests do not establish them.

```sh
python3.13 -B -m unittest tests.application.test_mac_key_registration tests.application.test_mac_runtime -v
```

The next synthetic connection is
`application.mac_review_signing.sign_operation_review(runtime, expected_build,
key_directory, expected_registration, policy, review, current_context=...)`.
It uses the owning `PaperReviewPolicy` and complete operation review, reusing the
researcher's existing judgment, reason, selected effects, contribution history
and explanation disposition. The context callback has the same exact shape as
review delivery. This is an unaccepted signing observation, not an enrolled
research approval or accepted operation.

Before the native window, the adapter verifies the current owned review, runtime
and project-bound key, including fresh-process key reopening/noninteractive
denial. The bounded [signing request header](../../schemas/review-signing-request-v1.json)
is length-prefixed, followed by the complete exact review bytes. It binds the
key registration, project/build/roles, public identity, review and operation
digests and a fresh 32-byte nonce. Review prose and key representation never
enter command-line arguments; opaque key material stays out of the channel.

Both native roles verify the connected peer before proceeding. The foreground
window reuses judgment/reason, identifies the action and explanation disposition,
and exposes the entire immutable review. Direction-control characters are shown
explicitly, including invisible formatting/control characters. An explicit gesture plus fresh native authentication signs only a
domain-separated digest of that exact packet. The existing device key and
registration are read-only. Native signing and gateway verification enforce
review lifetime, with a bounded continuous-time interaction deadline. The
gateway verifies the public-key signature and acknowledges the exact private
reply; signatures are neither printed nor written to a file. Python receives
only matching digest/status observations, then rechecks key/runtime identity
and, for a signed result, current owned review context. A changed or expired
context cannot report current signing success, even if signing already happened.
Cancellation/expiry retains its terminal reason when the scientific context
also expires; it makes no claim of a current review or authorization.

`signed-unaccepted-review`, `cancelled` and `expired` remain distinct;
cancellation names the review window or native authentication. All results keep
protected acceptance and authorization verification false. Invalid/replayed or
changed packets, wrong roles/code, unknown result fields and inconsistent peers
fail closed. A failed sender or receiver cancels its waiting peer, rather than
leaving it for the entire authentication timeout. No TUI,
provider, research-store or manuscript operation is connected by this API.
Trusted source loading, enrolled key custody/worker denial and atomic receipt
consumption remain B01/B03 prerequisites for real approval. A successful
synthetic signature does not bypass those gates or create understanding debt.

```sh
python3.13 -B -m unittest tests.application.test_mac_review_signing -v
```

The separate `application.mac_worker` component processes bounded proposal
responses under App Sandbox. It is source-built and independent of the approval
roles; it cannot perform research operations or launch a model/tool command.
Use `build_worker(directory)` with a fresh private external directory and retain
the returned pin. Build creates no container; explicit `check_worker(directory,
pin)` or response handling launches the component. Source/bundle replacement,
extra files, links, broader entitlements and a wrong pin are refused. The
[generated build format](../../schemas/proposal-worker-build-v1.json) records
integrity, not enrolled authority.

The signed bundle uses exactly the App Sandbox entitlement, hardened execution,
no network/file exceptions, sanitized environment and bounded pipe input/output.
Its stable identifier is `org.claimbranch.local-proposal-worker`. First execution
creates the OS-managed container for that identity, and later executions reuse
it. The identifier-only designated requirement supports that lifecycle, but
does not authenticate the worker: the parent additionally pins exact source,
bundle bytes and code hash. The returned self-report is a liveness/parity check,
not independent authentication of a running peer. Arbitrary hostile same-user
path replacement remains outside this measurement. Treat the container as untrusted, never as a place
for research, keys or trust metadata. The app does not delete it or ask for
broader system access; this is one application container, not another sequence
of disposable probe containers. Uninstalling that container remains an explicit
OS/user action. No signing credential, publisher account or profile is used.

`inspect_result(directory, pin, raw, cancel_event=...)` checks the closed existing
provider-result format in the parent, passes its canonical bytes through the
confined worker and requires exact matching output bytes/digest with authority
false. This is confined processing/parity checking of already-normalized input,
not isolation of the parent's original JSON parse. Model prose is
data; it cannot add tools or accepted operations. `complete_proposal(directory,
pin, broker, request_id, raw, cancel_event=...)` connects this processing to an
already-dispatched `OfflineBroker` request. It retains the original response
bytes/digest in the existing trace and claims the first arrival before worker
execution. Malformed arrivals are recorded without launching the worker;
cancellation or worker failure records that original response as failed and
consumes the attempt. Retrying requires a new explicitly reviewed request;
another response cannot replace the first while checking is in progress.
Raw and normalized response limits agree; output reserves space for its envelope.
Python owns canonical Unicode normalization, and the worker preserves those
bytes rather than imposing the OS's potentially different Unicode version.
Completion does not adopt text into a judgment. Manual work is unchanged.

`verify_boundary(directory, pin)` creates only fresh synthetic research/key/
manuscript placeholders and private/local listeners. Positive controls establish
access before the pinned worker must receive OS permission denial for
those three files, that AF_UNIX socket and IPv4 TCP loopback connection. Results
name that scope; they do not generalize to all filesystem/IPC/network operations.
It verifies unchanged bytes
and removes its temporary resources. This observation covers this component
and those placements; it cannot establish external inference confinement,
accepted-store custody, trusted enrollment, or protected SSH/Linux use. The
source-only artifact includes the component. There is no TUI connection or live
provider dispatch in this increment.

```sh
python3.13 -B -m unittest tests.application.test_mac_worker -v
```

The synthetic `claimbranch.application.mac_enrollment` connection adds native
local enrollment independently of candidate/imported records. It is not ready
for real research or protected acceptance; its current verification and human
observations are tracked in the [B01 ledger](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#remaining-non-ui-implementation-ledger).

`enroll_project(runtime, build_pin, key_directory, registration_digest,
worker_directory, worker_pin, project_id=...)` opens a native foreground review
and requests per-attempt authentication. It uses only a deliberately selected
synthetic candidate key. The broker derives current code identities, creates a
random local identity and empty protected resource, and publishes a signed
enrollment after authentication. The fixed registry is resolved through the OS
user record under `~/Library/Application Support/ClaimBranch/enrollments-v1`,
outside Git; environment, working directory and request paths cannot relocate
it. Only this native foreground path writes entries. Trust derives from that
restricted application path and namespace, not a self-signature or imported hash.
Unrestricted same-user programs, administrator/OS compromise and external
provider topology are outside this measured component boundary.

The selected key's encrypted representation is copied unchanged into the new
native-owned `keys` directory; the original candidate is retained unchanged.
The durable trust choice and limits are recorded in
[ADR 0015](../architecture/decisions/0015-native-local-enrollment.md).

`enrollment_status(runtime, build_pin, local_id)` reloads native registration
without accepting a project name, registry path or key pin as authority. Both
native roles check the registered code, key and protected directory's device,
inode and birth time. The application measures the exact registry/key/resource
paths with `verify_resource_custody`: read/write-open, directory listing, and
create/rename attempts must be denied to the pinned worker. Positive controls
use random disposable canaries; actual protected file bytes are never renamed
or written. The native entry is checked again after the measurement. This does
not promise denial for other programs or other files/operations.

`sign_enrolled_operation_review(..., local_id, policy, review,
current_context=...)` reuses the existing scientific judgment and exact review.
The native broker and gateway each load their expected peer/key from the fixed
registry, authenticate peers and verify the domain-separated signature. They
do not derive authority from argv peer hashes. The original unregistered
signing exercise remains distinct. Changed science, code, key, resource or
registration prevents success. Neither path accepts a scientific operation;
B03 must separately bind the registered resource to atomic receipt consumption
and accepted history.

`revoke_enrollment(runtime, build_pin, local_id)` requires a separate native
foreground confirmation and records revocation without deleting keys or
history. Revoked or unexpected entries refuse further enrolled signing. There
is no automatic re-enrollment, source upgrade, import, relocation or recovery
conversion. Candidate keys from earlier builds require explicit new enrollment
before use with the new code. An enrollment key cannot be silently reused for
another local enrollment. Cancellation before reservation writes no entry;
interruption after reservation may leave inert files, and interruption after
publication can leave a committed entry without a success response. Inspect
the native status rather than blindly retrying or editing registry files.

Publication uses an exclusive atomic rename, leaving incomplete reservations
inert. Status housekeeping removes only strictly named private diagnostic
canaries under the same writer lock used by custody measurement. Concurrent
scratch cleanup cannot invalidate an entry merely because that scratch file
has disappeared. Foreign names in the registry root are retained and ignored;
unsafe identity-shaped entries still fail closed. Revocation verifies the
enrolled key and protected identity without requiring the old runtime or worker
files to remain available. Normal signing still requires those exact files.
Already registered keys, including revoked keys, cannot be enrolled again by
this initial API. Upgrade transitions remain B05 work; public enumeration and
diagnosis after an indeterminate publication remain B08 work.

All three native source files (`RuntimeIdentity.swift`, `Enrollment.swift` and
`InitialSource.swift`) are bound by the runtime build hash and included in the
source artifact. Each retains its 64 KiB resource limit; support files require
exactly one assembly marker. Existing runtime builds become stale when any
changes. Public doctor remains
read-only and never launches these dialogs or builds a runtime automatically.

Actual synthetic enrollment, fresh-process status/resource denial, registered
review signing, separate macOS authentication cancellation and explicit
revocation have been observed. They retain the same judgment, contributions
and original candidate bytes. Native JSON uses portable byte-key order, including
worker manifest names, Unicode/control escapes and nested objects. Private
channel polling retains its absolute deadline across idle polling slices; the
native review keeps its separate approximately 90-second gate. System sleep can
delay socket teardown by a polling slice, without extending signing authority.
These observations do not enable accepted science or qualify a real provider.

### Paper and work association

The synthetic backend `claimbranch.application.project_work` associates a
selected Git paper root and its exact marked manuscript with encrypted candidate
work. The [synthetic terminal connection](#selected-synthetic-project-in-the-terminal)
uses this API; the public own-project lifecycle remains incomplete. Real
research remains behind P0 and protected-write gates.
It changes no manuscript, confirms no evidence and restores no authorization.

- `preview_association(paper_root, manuscript, anchor_id, workspace)` checks an
  actual Git working-tree root, one relative UTF-8 `.tex` file of at most 64 KiB
  with exact unique LF markers, and an existing private external workspace.
  `display()` names the resolved paper and workspace separately. Preview creates
  no workspace, lock, key or metadata. This narrow association check does not
  report compiler, dirty-worktree, provider or authorization readiness for the
  complete future initialization flow. Absolute/escaping manuscript paths,
  intermediate/final manuscript symlinks, hard links and special files fail.
- `initialize_project(preview, project_id=..., title=..., thesis_id=..., thesis=...)`
  rechecks the preview and returns a legitimate empty candidate paper with its
  thesis. It does not invent observations, runs, judgments or completed reasons.
  For existing work, `ProjectWork.create(paper_work, preview)` retains the entire
  validated PaperWork payload, including AI contributions and unfinished text.
- `ProjectInitialization` in `claimbranch.application.project_initialization`
  adds a transient exact review of that empty candidate. Construct it with the
  same preview and title/thesis fields, call `prepare_review(session_nonce=...,
  sealed_at=..., expires_at=...)`, then `display(review, session_nonce=..., now=...)`
  and `candidate(review, session_nonce=..., now=...)`. The review retains the
  seed, initial main head, exact association, zero evidence/operations and a
  lifetime of at most 300 seconds. A changed association, session, expired or
  replaced seal refuses continuation. `restore_review` compares bytes to a
  still-live owned seal; it cannot install an imported review or revive consent.
  The [generated review schema](../../schemas/project-initialization-review-v1.json)
  has no imported history, evidence or receipt field. The result retains
  `project` (the same unaccepted `ProjectWork`), `association` and `review`
  together. When explicitly saving this candidate checkpoint, pass
  `result.association` as the store's `preview`; the existing save checks that
  destination. No write, source-fidelity or native-approval claim is made.
  Re-preparing invalidates the old seal even if the new attempt fails. Candidate
  calculation is repeatable, not single-use receipt consumption. This backend
  API does not connect to the TUI or initialize an accepted native log; the
  original advisory candidate initialization API remains compatible and does
  not require this transient review.
- `claimbranch.application.mac_initialization_signing.sign_enrolled_initialization_review(
  runtime, expected_build, local_id, owner, review, current_context=...)` now
  carries that owned empty review through the existing private signing channel.
  The context reader returns exactly `session_nonce` and `now`. The owner
  rechecks the full association before and after a signed result; the native
  enrollment is independently reloaded before and after transport. Native
  parsing requires an enrolled binding, the closed v3 empty seed, its derived
  initial root, zero evidence/operations, distinct thesis/anchor IDs and the
  matching source anchor. The internal attested effect comprises action
  `initialize-project`, project, seed, association and initial head; it is not
  an accepted operation or a store format. The initial review shows the already
  entered title/thesis, paper/manuscript/workspace locations and enrolled
  protected target. Path newlines/control characters are escaped separately
  from scientific prose. The whole framed packet is signed privately; no
  portable signature/receipt is returned. Cancellation/expiry remains distinct
  from success and cannot recover approval. Actual initial foreground signing
  and cancellation have not been observed; parser/software-signature and absent
  enrollment checks do not substitute for them. Both native roles independently
  discover the exact Git root/admin paths and directory identities, open the
  manuscript relative to the root without following links, and check its single
  link, identity, size/timestamps, UTF-8 bytes, SHA-256 and unique ordered LF
  markers. The external workspace must be owned/private and neither contain
  nor lie within the recorded paper/admin paths; Git and bare-repository
  ancestors are refused. Descriptor ancestry checks reject containment through
  byte-distinct macOS firmlink aliases. The broker repeats source checks before
  review, around key use and before signature delivery. Signed results recheck sources and
  expiry before success; cancellation/expiry bypass these final reads.
  Initial signing also requires the enrolled native protected target to retain
  its exact directory identity and private single-link `binding` containing the
  local ID, with no other non-diagnostic entry. Existing genesis/log files,
  unknown entries or pending publication refuse initialization without changing
  them. Safe reserved custody canaries remain untouched; unsafe canaries refuse.
  Each source check brackets its reads with this empty-target precondition.
  The target comes from independently loaded native enrollment, separately from
  the association's advisory candidate-work location. This is a read-only
  precondition, not a reservation, atomic empty check/write or receipt use.
  Git discovery uses fixed arguments, at most 12 KiB output and a five-second
  deadline per invocation, with repository-local includes still honored.
  Initial review reserves 11 seconds from the remaining peer deadline and 21
  from review expiry for signed-path verification; insufficient time refuses
  before opening the window. This is a fail-closed allowance, not a guarantee
  that completing OS authentication produces success near a deadline. Git
  root arguments require UTF-8; relative manuscript paths retain their exact
  bytes. Other filesystem I/O has no independent deadline; network/synced roots
  remain unsupported. These are repeated read-only filesystem snapshots, not
  atomic compare-and-swap, scientific source fidelity or authoritative research
  history loading. No project
  genesis, accepted log, receipt consumption, key enrollment or TUI connection
  is performed by this API.
- `ProjectWorkStore.create(directory, cipher=..., project_id=..., recovery_key=...)`
  uses the existing device encryption and private atomic checkpoint. Within its
  context, `save(project_work, preview=preview)` rechecks new/changed associations
  against the exact store destination. Reopen through `ProjectWorkStore(...)`
  and `load()`. The [project-work schema](../../schemas/project-work-v1.json)
  contains PaperWork v1/v2/v3/v4/v5/v6 and up to 16 association snapshots within 256 KiB
  total; it is distinct from the legacy work format. Neither reader silently
  migrates the other. Physical paths use filesystem-byte hex inside ciphertext,
  preserving decomposed Unicode names without treating them as normalized prose.
- `with_work(paper_work)` retains project identity and the recorded history
  prefix. Save can update unaccepted writing even if the paper is unavailable;
  it cannot silently replace the retained history or association chain.
  `source_status()` distinguishes unchanged bytes (including metadata-only edits),
  source changes requiring explicit association refresh, identity relocation and
  unavailable-or-unsupported sources. These are read observations, not scientific source
  verification or future manuscript write authorization.
- After a move, explicitly preview the new root/destination, call
  `relocate(preview)` and save with that preview. The manuscript bytes and anchor
  must match the earlier snapshot exactly. Original associations remain retained.
  A concurrently edited/moved manuscript needs later reconciliation; this API
  refuses that association change and keeps the old work readable. It neither
  overwrites the file nor creates a replacement research history.
- For edited bytes at the same paper/Git identities, relative manuscript and
  anchor, call `preview_source_refresh(project, preview_association(...))`.
  `review.display(project)` exposes old/new source digests and separate paper/
  workspace locations, the v2 format change and remaining source-snapshot budget
  without writing. This is an association comparison, not
  a scientific content diff or confirmation that the paper matches the argument.
  Call `project.refresh_source(review)`, then
  `store.save(refreshed, source_review=review)` against the same loaded project.
  The save rechecks the entire earlier project, current source and destination;
  concurrent writing requires another explicit comparison. Do not combine this
  action with writing edits. The [v2 envelope](../../schemas/project-work-v2.json)
  retains exact prior associations and typed relocation/source-refresh events.
  Nested work, AI history, unfinished text and old review inputs remain unchanged;
  old reviews grant no current authority. Subsequent same-byte relocation still
  works. Matching bytes now report `unchanged-since-refresh` (or
  `unchanged-content-since-refresh` after metadata-only changes), including after
  a later move; they do not report scientific agreement. Editing and moving
  together is unsupported and receives an explicit error.
  Version 1 remains readable and unchanged until explicit refresh; old readers
  refuse v2. Both versions retain the existing maximum of 16 source snapshots
  and 256 KiB total. Reaching the bound refuses the change without pruning old
  history; this prototype has no rollover/migration command yet. Missing sources
  never prevent reading saved work. There is no CLI/TUI refresh integration yet.
  The source matches at the last read-only recheck before checkpoint encryption;
  the external editor is not locked. An edit after that check is detected by the
  next `source_status()` call. This is not graph/file atomicity or a fenced write.
- `backup(verify_recovery_key=...)` and `ProjectWorkStore.restore_backup(...)`
  reuse the [device recovery contract](#device-work-key-reopening-and-recovery).
  Restore creates only a fresh checkpoint and may succeed without the old paper
  or old device opener. It preserves the old association as historical metadata;
  relocating the paper afterward is explicit. No approval key is enrolled.

Tests use disposable synthetic Git papers, actual Mac native encryption and a
fresh Python process. They cover missing sources, relocation, changed preview,
linked paths, failed replacement, retained AI/workspace content and old-reader
refusal. This proves neither real replacement-device custody, hostile same-user
filesystem isolation nor the complete source-delivery journey.

```sh
python3.13 -B -m unittest tests.application.test_project_work tests.application.test_project_source_refresh -v
```

### Encrypted work commands

The source preview exposes `python3.13 -m claimbranch demo work --help`.
These Mac commands operate on synthetic candidate work; they do not connect
TUI drafts, accept research or edit a manuscript. Python 3.13, installed Xcode
command-line tools and an unlocked Apple Silicon Mac are required. The native
helper builds in a private temporary directory; nothing is installed.

Create three new, private directories outside all Git trees, for example:

```sh
mkdir -m 700 "$HOME/claimbranch-work-example" "$HOME/claimbranch-backup-example" "$HOME/claimbranch-restored-example"
python3.13 -m claimbranch demo work init --directory "$HOME/claimbranch-work-example" --variant recorded
python3.13 -m claimbranch demo work status --directory "$HOME/claimbranch-work-example"
python3.13 -m claimbranch demo work show --directory "$HOME/claimbranch-work-example"
python3.13 -m claimbranch demo work backup --directory "$HOME/claimbranch-work-example" --archive-directory "$HOME/claimbranch-backup-example"
python3.13 -m claimbranch demo work restore --directory "$HOME/claimbranch-restored-example" --archive-directory "$HOME/claimbranch-backup-example"
```

Initialization shows a fresh random recovery key only on the controlling
terminal. Retain it separately from the backup and enter it again, hidden,
before saving. Backup verifies that key before exporting; restore requires it.
Ordinary status/show reopen through the device without the recovery key.
Missing controlling terminals fail rather than falling back to echoed input.
For synthetic automated tests only, `--recovery-key-stdin` accepts exactly 64
hexadecimal characters and an optional newline through private stdin, ending
at EOF (an open producer can keep the command waiting). It is not a password KDF. Never put the key in command arguments, environment,
shell history, source files, ordinary logs or a provider request.

`status --json` reports saved work/history digests and explicitly absent
approval. `show --json` deliberately emits the argument and conditional pending
work to the chosen output; ordinary status and diagnostics omit scientific
content. The expected project defaults to the bundled `project`; reopening,
backup and restore can name an explicit `--project-id`. A mismatched identity
fails. Init starts only the bundled manual or recorded series, with no import
or own-project acceptance route.

Backup creates `backup.cbw` using exclusive creation, mode 600, bounded bytes
and file/directory full sync. Exclusive file creation prevents competing exports
from replacing the copy. Reading an archive creates no lock or staging files
and performs no cleanup; it can read a mode-700 directory on read-only media.
Existing copies are never replaced, and work/archive directories must differ. A failed/interrupted copy may remain incomplete;
no success is reported, and retry uses another new private destination. Restore
authenticates and replays the copy before creating destination work. It leaves
the source and backup unchanged and enrolls no approval key. A locked Mac can
refuse device key operations; unlock it and retry. After an uncertain initial
save, inspect `status` before retrying initialization. Exit 1 is failure, 130
is interruption, and 0 reports only the named synthetic operation. If saving
completed but output failed, stderr reports `work-output-failed` with
`operation_completed: true`; keep the recovery key and inspect the existing
work instead of repeating initialization. The exit remains nonzero.

Command tests include terminal key entry, portable path/failure checks and a
separate-process journey from an extracted source artifact. Native completion
requires an unlocked host; see the [current execution evidence](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#encrypted-work-command-integration).
The [device API](#device-work-key-reopening-and-recovery) owns cryptographic
mechanics and limitations. This is not replacement-device validation or a full
research backup/public-release claim.

### Device work-key reopening and recovery

`claimbranch.application.device_work_store.DevicePaperWorkStore` now connects
the same unaccepted checkpoint to actual Mac Secure Enclave **key agreement**.
Normal restart requires the device and unlocked access, without the caller
retaining the plaintext data key. This is separate from user-presence **signing**:
opening research does not approve it. The native helper disables interaction,
has no signing or Keychain-search API, and provides no software-device fallback.
The selected [device-replacement policy](../architecture/decisions/0014-device-replacement-recovery.md)
remains broader than this tested same-host data-restoration component.

- `DevicePaperWorkStore.create(directory, cipher=cipher, project_id=...,
  recovery_key=...)` returns a context manager for a new checkpoint. Supply a
  separately retained random 32-byte recovery key. Creation refuses any existing
  checkpoint, including the earlier raw-key format. The first save generates
  a random data key and a device key, and atomically publishes their encrypted
  envelope with the work. A failed save cannot publish only the key or work.
- `DevicePaperWorkStore(directory, cipher=cipher, project_id=...)` reopens an
  existing checkpoint. `load()` and `save(work)` preserve the earlier source/
  provenance validation and absence of resumed consent. Missing files, wrong
  project, unavailable device, changed ciphertext or unsupported format fail;
  ordinary reopen never creates replacement keys or invokes recovery.
- `backup()` returns validated encrypted checkpoint bytes, without writing an
  export file or uploading anything. This is an unaccepted-work developer API,
  not the future model-accessible context or human authorized project export.
  `backup(verify_recovery_key=...)` additionally unwraps and compares the data
  key through the supplied recovery secret. Without that option, backup does
  not prove that the researcher still possesses the matching recovery key.
  Keep the recovery key separately from these bytes and outside Git.
- `DevicePaperWorkStore.restore_backup(backup_bytes, new_directory,
  cipher=cipher, project_id=..., recovery_key=...)` authenticates/replays the
  backup before saving to a fresh destination. It unwraps via the recovery key,
  without reopening the old device key, and wraps that data key with a fresh
  Secure Enclave key for the destination. The source is untouched. Wrong key,
  corruption, source mismatch or an existing target cannot overwrite history.
  This does not revoke old-device access, rotate the recovery key, enroll a new
  approval key, re-sign history or convert candidate records to accepted ones.

The `CBWD` version-1 file contains a bounded `CBKY` version-1 wrapped-key
envelope and the existing `CBWK` encrypted work. The complete key/work snapshot
uses the same private-directory session lock, atomic replacement, full-sync,
staging cleanup and uncertainty behavior. The outer bound is 278,990 bytes;
the underlying canonical work stays at 256 KiB. Old raw-key readers reject the
new format rather than implicitly migrating it. Closing releases the adapter's
key references, without claiming Python/native memory zeroization.

Apple's [key-agreement API](https://developer.apple.com/documentation/cryptokit/secureenclave/p256/keyagreement/privatekey)
reopens the encrypted device representation. The implementation uses
`WhenUnlockedThisDeviceOnly` with private-key usage, and ECDH/HKDF-SHA256 to
derive the data-key wrapping key. A distinct HKDF purpose derives the recovery
wrapping key. AES-GCM authenticates the project binding and full header on both
paths; an independently derived HMAC-SHA256 authenticates the header and **both**
wrapped keys after either unlock. Thus damage to the unused route cannot go
undetected when making a backup. Work-content encryption derives another key
with a separate HKDF purpose and the digest of the complete outer prefix/key
envelope; splicing the original's ciphertext into a restored envelope fails.
Whole-checkpoint rollback remains outside this unaccepted-work contract.
The helper returns the data key only through
a captured pipe to the local application; no device private key is exported.
Data/recovery keys never enter filenames, arguments or ordinary diagnostics.
The adapter releases its recovery-secret reference once wrapping succeeds;
failed-save retries reuse the already prepared envelope.

Actual disposable native tests establish create/reopen and fresh-process return
on this Mac, including recovery into a new device-key identity on the same
host. They do not establish locked-host behavior, another physical device,
hostile same-user isolation, production signing/launch custody, TUI integration
or P0 source fidelity. No native approval prompt is part of these tests.

```sh
python3.13 -B -m unittest tests.application.test_device_work_store tests.application.test_paper_work_store -v
```

### Versioned understanding closure review

`claimbranch.core.debt` now supplies a separate understanding-only candidate
contract. It does not close the conditional work shown in the TUI. That v3
history has no accepted cause-review/receipt record; callers must not manufacture
one from `work-...` IDs or partial drafts. The existing `ClosureReview` and
`closure_candidate` remain legacy head/time-only helpers for their original
candidate tests, including manuscript verification. They are not the new route.

`UnderstandingClosureContext` binds the project, original cause episode, debt ID,
cause operation and exact sealed cause-review digest, current main head,
evidence watermark (0–32), `claimbranch.understanding-topics/v1`, full topic-set
digest and displayed-context digest. The topic digest must cover the ordered
topics, prompts and scientific references; the display digest must cover the
actual reviewed scientific context, not merely a UI layout or an unverified
embedded hash. These are supplied source bindings: this core checks equality,
format and causal consistency, not that a caller obtained them from accepted
storage or displayed them to a person. The future gateway must independently
reconstruct them from owned accepted state.

- `prepare_understanding_closure(debt, cause_review, displayed_context, *,
  current_context, operation_id, rationale, session_nonce, sealed_at, expires_at,
  now)` requires an exact open understanding Debt. It reconstructs the supplied
  sealed cause and its deferred debt candidate, including the original review
  digest that is not part of `Debt.id`. Both contexts must agree and current
  evidence cannot precede the cause. Closure is a distinct operation; its new
  review must be live, at most five minutes long and no earlier than the cause.
  An expired historical cause remains readable and does not grant new consent.
  Equal whole-second seal times are allowed; these timestamps cannot prove
  that the cause was accepted before closure. The future accepted loader must
  establish that ordering from its recorded operations, not inferred clock delay.
- The returned immutable `UnderstandingClosureReview` contains canonical NFC
  `payload` bytes and their `digest`. `rationale` can reuse existing writing;
  it is required nonblank text up to 16 KiB UTF-8, not a graded answer or a new
  retrospective form. Topics bind the reviewed subject without asserting that
  the person understood it.
- `restore_understanding_closure(raw, debt, cause_review, *, current_context,
  now)` rechecks canonical bytes, version, cause and current context/time.
  `understanding_closure_candidate(debt, cause_review, review, *, current_context,
  now)` additionally reconstructs and compares the complete sealed review value.
  A change in evidence alone, cause review, topics or display invalidates reuse.
  A hand-constructed dataclass is not validated merely by construction: never
  trust its `payload`/`digest` without this recheck against current owned inputs.
  A stale review must be prepared afresh; the separate partial draft retains its
  text. Rebinding that draft never refreshes closure authority.

The generated [closure review schema](../../schemas/understanding-closure-review-v1.json)
defines `claimbranch.understanding-closure-review/v1`; the reader rejects legacy
review bytes and unknown/extra authority fields. V1–v3 history formats and
goldens are unchanged. Schema validation is shape checking; runtime also checks
cross-record constraints and timing. Neither hashes nor serialized reviews
authenticate authorship: changed but otherwise valid bytes can describe another
unverified candidate and need a new exact human review/receipt.

The result is still a `ClosureCandidate` with `requires_authorization=True` and
`authorization_verified=False`; its proposed `closed-by-human` value never
updates the supplied Debt or history. Repeated calls calculate the same candidate
without consuming anything. Real use additionally needs independently loaded
accepted cause/debt/context, a receipt matching the exact review digest, fresh
session/time, global operation/receipt replay checks and atomic receipt
consumption with the accepted append. This API neither supplies those controls
nor changes the existing unavailable-closure flags in the application. The
future understanding gateway must admit only this versioned review/recheck path,
never a generic `ClosureCandidate` or its proposed debt status as authority.
The legacy helper can produce the same candidate result type with weaker
bindings; it must not become an alternate protected understanding route.

The contract tests include an explicit synthetic v3 sealed merge, its candidate
debt, partial explanation, same-head evidence correction and stale closure
refusal. The writing remains recoverable, even after explicit draft rebinding;
no conditional item is converted into accepted debt by that exercise.

```sh
python3.13 -m unittest tests.contract.test_debt_closure tests.application.test_paper_understanding -v
python3.13 -m scripts.export_research_schema --check
```

## Reproducible synthetic source preview

### Personal terminal alpha source

The existing source builder now packages the personal terminal alpha under
[ADR 0017](../architecture/decisions/0017-personal-terminal-alpha.md), retaining
synthetic demos separately. For daily own-project use, follow
[personal project writing](#personal-project-writing-in-the-terminal).
Run from a trusted checkout using Python 3.13; no package installation or
third-party build tool is needed:

```sh
python3.13 -m scripts.export_runtime_resources --check
python3.13 -m scripts.build_source --output /tmp/claimbranch-source.zip
python3.13 -m scripts.check_source_artifact /tmp/claimbranch-source.zip
```

Use an unused output path; the builder refuses to overwrite an existing file.
The ZIP contains `claimbranch/`, `START-HERE.txt`, the owner's selected MIT
`LICENSE` notice and a file-hash manifest, with
fixed archive metadata for byte-for-byte reproducibility. It excludes checkout
tools, tests, Git and caches. Generated runtime resources come from the explicit
verified inventory under `tests/fixtures/`; edit the canonical fixtures, then
run `python3.13 -m scripts.export_runtime_resources` to refresh copies.
CI checks both schemas and resources for staleness. The runtime imports its
validator and examples from `claimbranch`, not checkout-relative scripts/tests.
Repository `.gitattributes` keeps text checkouts at LF even with
`core.autocrlf=true`, preserving fixture/resource byte hashes on Windows.
Do not change manifest hashes or relax validation to accommodate line conversion.
The documentation checker permits the one generated baseline Markdown resource
at its exact runtime path only when its bytes match the canonical fixture;
this does not permit additional project documents outside `docs/`.

The checker verifies inventory/hashes before unpacking into an unrelated
temporary directory with spaces and Korean characters, then runs doctor,
both original replays, paper impact, the offline paper-draft, provider-response
and repeated-episode journeys and a real loopback HTTP session. It checks that
protected acceptance is unavailable and closes the listener. A fresh extracted
process then runs the public own-project init/dry-run, human result confirmation,
manual claim/shared scientific relations, reused judgment/reason, correction,
later question, wide/narrow actual PTY quit/reopen and public backup/export/restore.
The [personal smoke](../../scripts/personal_alpha_smoke.py) uses only the extracted
runtime and standard library; no repository tests/scripts are imported there.
It verifies original source/checkpoint bytes and restored complete saved content. This executes trusted
artifact code; it is not a sandbox for downloaded/untrusted ZIP files and the
hash manifest is not a signature. Source-artifact tests also cover stale
resources, links, tampering, traversal, bounded member inventory and no-overwrite behavior.

The synthetic loopback smoke has a 90-second subprocess bound and a 10-second
client socket timeout; other command smokes retain their 30-second bound.
The portable CI job has a 30-minute budget: observed full application checks
approached 15 minutes before the remaining harness/security/artifact phases.
Longer check budgets do not change product deadlines or claim a failed run passed.

To use the built alpha, extract into a new directory, then run
`python3.13 -m claimbranch doctor` and `python3.13 -m claimbranch project init --help`.
Python 3.13, curses, a Unix terminal and working system Git at `/usr/bin/git`
must already be available. Doctor
returns 0 when those alpha prerequisites and bundled replay are available,
otherwise 3 with the missing prerequisites. It checks no private project and
starts no native helper/provider. Its Git check verifies executable presence,
not an invocation; on Mac the system Git tools must already work, without an
installation prompt. Protected acceptance, live AI, automatic
manuscript apply/compile and Windows remain unavailable. A missing resource/hash
mismatch requires a fresh verified build/extraction, not manual runtime edits.
START-HERE.txt supplies version-matched setup, authoring, saving, backup and
problem-report guidance. Reports name runtime/OS, command/exit and artifact
SHA-256; omit private checkpoints, backup data and credentials.

The explicit `python3.13 scripts/verify.py --scope alpha` runs docs/whitespace,
the original fixture, generated schema/resource checks, portable contracts and
the named personal/portable application/actual-PTY/source-artifact dependency
selection. Add `--scope harness` for its runner checks. Native/encrypted suites
and explicitly named native methods stay in core/all; excluded features are not
passes, and an unexpected selected skip still exits 3. `--scope all` also checks
generated schema/resource freshness; a stale named alpha exclusion exits 2
before tests start. This does not replace
whole-core, native presence or protected release validation. The configured
Ubuntu/macOS CI runs alpha/harness, independent security regression and the
assembled artifact. Configuration is not an observed remote CI result.

The artifact is an experimental personal alpha; it confers no protected authority
or improved-understanding/V0 claim. Only locally observed Mac support is declared;
Linux/SSH/tmux, physical IME and independent-user observations stay explicit.
The project owner's license choice, commit/tag and publication are separate.
Building/checking never commits, pushes, uploads, installs or converts native
records. Later provider/manuscript/key capabilities require their own gates.

### Personal project writing in the terminal

The public personal path now creates a paper from your title, tentative thesis
and first unresolved question, then opens the existing graph with AI off. It
starts without example observations, runs or AI text. It uses ordinary private
local files, not application encryption, device keys or protected approval.
The personal path connects result confirmation and selected reasoning to the
same saved workspace. Public saved-work status, backup/export and fresh restore
now use that store; source-delivery evidence remains in the
[existing ledger](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#first-release-outcome-ledger).

Use an existing local Git paper, a relative `.tex` file with
`% claimbranch:start id=anchor` / `% claimbranch:end id=anchor` markers, and an
existing owner-private directory outside every Git tree. ClaimBranch reads the
manuscript; it does not add markers or edit that file. For example, create a new
private directory outside Git with `mkdir -m 700 /path/to/private-work` and run:

```sh
python3.13 -m claimbranch project init --directory /path/to/private-work --paper-root /path/to/paper --manuscript paper.tex --title "My paper" --thesis "My working thesis" --question "What remains uncertain?" --dry-run
python3.13 -m claimbranch project init --directory /path/to/private-work --paper-root /path/to/paper --manuscript paper.tex
python3.13 -m claimbranch project open --directory /path/to/private-work
```

The dry run requires explicit title/thesis/question and writes nothing. Interactive
init prompts for omitted fields, shows the source and separate storage preview,
and creates only after `create`; Enter cancels. An optional `--project-id` fixes
or checks identity; otherwise init generates it and open reads it from saved work.
A directory containing encrypted work is refused, with no automatic conversion.

In the TUI, `;` opens named manual actions, `n` edits a node note, `e` edits the
judgment and reason, and Ctrl+S keeps writing. Kept writing and separate unfinished
editors are checkpointed through the full workspace adapter. Normal `q` saves
before leaving; active input is retained on interrupted return when its checkpoint
succeeds. Reviews and the session-only exclusions shown on quit are not restored
as authority. Notes never replace scientific text. Missing or changed source
preserves the earlier basis and writing; it does not silently reconnect it.

**Record personal research:** `;` → Draft a result and source captures provisional
writing. Enter the observed content, run reference/method, source reference,
conditions, measurement definition/value/unit/comparison and optional tentative
judgment/reason. In its form, `c` previews a new personally confirmed observation.
Read the complete preview (End/PgDn), then Enter records and saves it; Esc returns
without confirmation. References are not opened by the application. Confirmation
records the experiment question from this episode and exactly your run/method
text, retaining entered limitations in the confirmation note; it cannot
establish source fidelity or scientific truth. The tentative
judgment becomes writing at the new observation, leaving other judgments separate.

Use the existing claim/subclaim, interpretation, connection and plan actions to
build the argument. `;` → Record selected reasoning personally reviews those
chosen records using the same judgment and reason. `G` compares the graphs; Enter
after inspecting the preview records main and preserves the alternative/omitted
drafts. If no interpretation exists, the preview explicitly reuses your judgment
as one with no inferred observation links. The original contribution chain stays
visible; inherited AI opens only conditional unfinished explanation work, never
protected debt. There is no quiz for ordinary manual recording.

To correct a result, select its observation, start another result draft, enter
the corrected statement/value and reason, then `a` previews an append-only
correction against the unchanged run/measurement. Other nonempty fields are
refused; this bounded correction cannot change units or experiment conditions.
Record a separate run/result for those changes. A successful correction consumes
its draft so the same correction cannot be recorded twice; a failed save retains
it. Earlier values remain in history
across branches. A confirmed capture offers `v` to open its recorded copy;
editing the earlier capture does not rewrite that copy. `;` → Start the
next research question previews closure of this episode and the next question;
earlier notes, judgments, draft text and unresolved manuscript follow-up remain.
Cancelled next-question text stays available in this session; only recording
saves the new question. Closing an episode leaves its result drafts readable,
but they cannot be confirmed afterwards. Finish them before starting the next
question. After the episode's chosen merge, another reasoning update requires
the next research question; the named action explains that limit.
This finite alpha currently supports 8 episodes, 8 runs, 16 observations, 32
evidence events and 64 commands; one interpretation/selected merge per episode.
Unsupported extra work is refused while retaining writing. Manuscript source and
wording review stay read-only; the app does not apply a file or close follow-up.

The distinct `personal.cbp` checkpoint is bounded validated plaintext with a
format header, exclusive session locking, expected-byte checks and atomic replace.
File permissions reduce accidental disclosure; they do not stop unrestricted
same-user programs or encrypt backups. A failed save keeps live text. Uncertain
replacement or external change freezes further saves and asks you to copy newer
writing before reopening for inspection. Never edit the checkpoint to repair it.

**Back up and restore saved work:** close the TUI first. Choose separate existing
owner-private directories outside Git for backup, readable export and restoration.

```sh
mkdir -m 700 /path/to/private-backup /path/to/private-export /path/to/restored-work
python3.13 -m claimbranch project status --directory /path/to/private-work --json
python3.13 -m claimbranch project backup --directory /path/to/private-work --archive-directory /path/to/private-backup
python3.13 -m claimbranch project export --directory /path/to/private-work --archive-directory /path/to/private-export
python3.13 -m claimbranch project restore --directory /path/to/restored-work --archive-directory /path/to/private-backup --dry-run
python3.13 -m claimbranch project restore --directory /path/to/restored-work --archive-directory /path/to/private-backup
python3.13 -m claimbranch project open --directory /path/to/restored-work
```

The create-only `backup.cbp` includes the saved project association, complete
history, origin, kept/unfinished writing and unresolved follow-up. It excludes
external experiment artifacts, manuscript files and unsaved live input. Its
SHA-256 checksum detects accidental damage, not authenticity or authorization.
The distinct readable `project.json` is an export, not a restore backup. Both
are unencrypted private files; nothing uploads or replaces an existing output.
If a copy is interrupted, preserve it and retry in a new private directory.
Dry-run checks backup contents, private placement and absence of work/archive
files; it creates no lock and cannot reserve the destination. Actual restore
rechecks its session lock and inventory. Restore checks bounded format/content
before creating a fresh checkpoint;
existing work is never replaced, and unknown/newer formats fail without migration.
Missing/changed manuscript preserves writing and its original basis. A restore
does not grant protected authority, rebind source or complete follow-up. The
`--json` summaries identify the saved-content digest without printing the writing.
Status and backup require an exclusive store session; close an open TUI first.
If the original checkpoint is damaged, preserve it and restore the verified
backup into another fresh private directory. If restore reports uncertainty
after replacement, open that destination to inspect its saved content; do not
overwrite it by retrying restoration. Stored source snapshots remain part of
writing context; these commands do not copy or restore external source files.

Observed locally: Python 3.13 on macOS, actual PTY Korean pasted judgment/reason,
multiline note, 132×38/80×24 resize, normal exit, fresh-process open and Ctrl+C
shell-mode restoration. This is not physical IME, SSH/tmux, Linux or unfamiliar-user
validation. Repeat the focused check with:

```sh
python3.13 -B -m unittest tests.application.test_personal_project tests.application.test_tui_terminal.TerminalProcessTests.test_personal_init_writing_resize_restart_without_device_keys -v
python3.13 -B -m unittest tests.application.test_personal_research tests.application.test_tui_personal tests.application.test_tui_terminal.TerminalProcessTests.test_personal_result_record_correction_next_question_and_restart -v
python3.13 -B -m unittest tests.application.test_personal_archive -v
python3.13 -B -m unittest tests.application.test_tui_terminal.TerminalProcessTests.test_personal_public_backup_restore_reopens_saved_and_unfinished_writing -v
```

### Selected synthetic project in the terminal

On the currently supported Mac, `demo project` connects a separately authored
synthetic Git paper to the terminal. It remains an unaccepted experiment, not
permission to enter private research or a completed public initialization flow.
Use an existing Git paper with one marked UTF-8 `.tex` source and a separate
existing private directory outside Git. The association limits above apply.

```sh
python3.13 -m claimbranch demo project init --paper-root /path/to/synthetic-paper --manuscript paper.tex --directory /path/to/private-work --project-id my-example --title "Synthetic study" --thesis "A tentative claim" --question "Which conditions matter?" --dry-run
python3.13 -m claimbranch demo project init --paper-root /path/to/synthetic-paper --manuscript paper.tex --directory /path/to/private-work --project-id my-example
python3.13 -m claimbranch demo project open --directory /path/to/private-work --project-id my-example
```

Interactive setup asks for the title, working thesis and first unresolved
question when omitted. Its preview names the paper, source, external workspace
and first candidate episode; it creates no evidence, judgment or AI suggestion.
`--dry-run` needs the three text fields and creates no lock, key or checkpoint.
Type `create` only after reviewing setup, then retain and confirm the separate
recovery key through the existing hidden key-entry flow. Any other response
cancels. Source/destination changes invalidate the preview before saved work is
created. Existing checkpoints cannot be overwritten. No paper file is edited,
no Git repository or marker is created, and no compiler/provider is invoked.

The graph starts from the person's thesis. `;` names claim construction, result
drafting and notes; a complete judgment is not required. AI stays off in this
connection. The typed project checkpoint retains its source association alongside
the existing encrypted writing scope, including separate unfinished input.
Use the same project identity when reopening; the ordinary `demo work` and
`demo tui --work-dir` readers remain separate formats. Missing/wrong project
data fails without replacement. The graph warns about changed, moved or missing
source **as observed at opening**, while retained writing stays accessible.
It neither follows a new path nor refreshes/reconciles source automatically.
The original source association is preserved by later saves.

Opening an existing project with no research episode shows its retained title,
working thesis and source status, then asks for the first unresolved question.
Review the question and type `start` to save unaccepted work and enter the graph,
`edit` to replace the question, or Enter at the preview to cancel. An unknown
choice keeps the preview available. EOF and Ctrl+C during entry leave the
checkpoint unchanged. This line input is session-only
until `start`; invalid/blank questions can be entered again. The existing device
key is reused, with no new recovery-key setup. A missing/changed source does not
prevent drafting or silently refresh its association. Reopening after a saved
start enters the same episode without asking again.

In this selected-project TUI, `;` → **Paper connection** shows the retained paper,
relative manuscript, marker and freshly observed status. Choose:

- `r` to relocate to another absolute Git root/relative `.tex` path containing
  exactly the same source bytes and marker. Tab changes path fields; Enter
  previews. Paths preserve filesystem Unicode rather than normalizing prose.
- `f` to refresh changed source at the same saved paper/manuscript location.
  A file moved and edited at once is unsupported; refusal preserves writing.
- `c` to check source status again. This updates the observation displayed by
  the panel and graph header without refreshing its stored association.

The preview shows before/after paths and SHA-256 fingerprints and the remaining bounded source-change capacity. On first showing
the preview, queued input is discarded so a key typed while it was being prepared
cannot immediately apply it. Scroll with PgUp/PgDn or End; `a` becomes usable after
the final preview content is visible.
Esc cancels the preview, then returns from the panel to the same graph/reader.
A successful apply changes only the encrypted association, retaining the complete
nested writing and its earlier scientific/source basis. Legacy association refresh
uses the v2 project format. Checkpoints with pooled review-writing require v3;
the preview names the applicable older-reader incompatibility.
No file moves, manuscript edits, evidence confirmation or renewed
review authority occur. Source/work changes require a fresh preview. An uncertain
save is reported as unconfirmed; reopen to inspect the retained checkpoint rather
than blindly retrying. Path-entry text is temporary and not a research checkpoint.
Below 48×18 controls pause, with Esc still available.

This connection does not add project discovery, full setup/doctor/backup rescue,
accepted evidence or manuscript application.
Those remain U4/B08 or their owning integration. It uses Mac device custody;
it does not establish protected SSH/Linux operation or real research readiness.

### Encrypted terminal judgment recovery

The synthetic cumulative TUI can retain judgments, argument drafts, provisional
results, partial explanations and unfinished scientific-review input separately from the manual `--draft-file` checkpoint. This is a bounded unaccepted-work connection,
not a full project save, accepted research storage or production server custody.
It uses `DevicePaperWorkStore` and the existing Mac cipher/key adapter above.
It requires macOS with the installed Swift toolchain and available Secure Enclave;
Linux/SSH device storage is not supplied by this adapter.

Create an **existing empty private directory outside every Git tree**. Creation
uses the shared `demo work` key-entry helper: it generates a random 32-byte
recovery key, displays it only on the controlling terminal, and requires the
researcher to retain it separately and re-enter it with input hidden. Keep it
outside the checkpoint directory and Git. Never put it in a command argument,
environment variable or ordinary diagnostic. Missing hidden terminal input
fails; there is no echoing fallback or key file. A missing device key on ordinary
reopening does not trigger recovery or replacement.

```sh
mkdir -m 700 "$HOME/claimbranch-judgment-demo"
python3.13 -m claimbranch demo tui --merge-example --ai-off --work-dir "$HOME/claimbranch-judgment-demo" --create-work
# Later: same example and variant, without --create-work or a plaintext key.
python3.13 -m claimbranch demo tui --merge-example --ai-off --work-dir "$HOME/claimbranch-judgment-demo"
```

`--series` is also supported; reopen
with the original example/variant. The ordinary version-two demo, `--snapshot`,
`--draft-file` and missing `--work-dir` with `--create-work` fail before entering
the terminal. Existing checkpoints are never overwritten by creation. A v1
backend checkpoint is not silently converted into a terminal workspace.

`claimbranch.paper-work/v2` adds a closed `claimbranch.judgment-workspace/v1`
value while preserving the v1 backend API/reader. It retains up to 16 independent
source-node sessions, complete adopted Judgment contributions, current partial
text/reason, pre-adoption text, explicit same-context work links/choices, personal
notes, separate unfinished judgment/note inputs and the selected episode/ref/node.
Intentional empty edits remain recoverable through `U`/`E`/`N`. AI-off reopening
keeps recorded AI influence visible. Exact source history is embedded and must
match the selected synthetic example; source changes are not silently rebound.
The three-dispatch offline example budget also survives restart; request traces
remain excluded. Restoring does not prepare a request, revive proposal adoption/consent, restore a
current review or accept anything. It never copies a shared judgment into its
linked nodes' separate work.

`claimbranch.paper-work/v3` extends this through a closed
`claimbranch.authoring-workspace/v2`. Older v1/v2 work remains readable; v1 is
still the separate backend format. Older TUI checkpoints upgrade only on a
changed save. New checkpoints also retain manual claim/link/interpretation/plan
candidates, kept versus unfinished forms, stable IDs/aliases, selection/omission,
revisions and the owning judgment. Original source-history prefix and query
digest reconstruct the original scientific context and contribution history;
changed source stays stale until explicit comparison/refresh. Incomplete forms
remain editable and are not promoted into a valid graph or review.

Up to 16 provisional results retain independent identity/number, original subject
and source context, partial source/measurement/judgment fields and separate
unfinished edits. Active candidate/result text editors checkpoint as unfinished
writing without applying it to kept fields, including empty deletions. Reopen
through `;` → **Open argument drafts**, **Return to authored work**, or **Resume
result drafts**. No result is confirmed, added to graph evidence or sent to AI.

`claimbranch.paper-work/v4` adds `claimbranch.explanation-workspace/v3`.
It retains W's conditional explanation topics: kept partial writing, explicit
original-rationale references, separate unfinished text, active editor text even
while inspecting source, and the selected topic. Reopen through `W` → explanation
item → `e`; `e` from the topic reader resumes unfinished writing. The original
judgment, AI contributions and writing basis are reconstructed from the owned
explanation snapshot and its verified source-history prefix. Changed evidence
remains distinguishable from that earlier basis. Empty edits stay unfinished;
pristine browsing and text canonically equal to kept text create no extra input.
An explanation stays open and unaccepted after reopening. Existing v2/v3 TUI
checkpoints still read; builds without v4 support refuse this newer format.

`claimbranch.paper-work/v5` adds `claimbranch.review-writing-workspace/v4`.
It retains U's unfinished scientific-change fields and review answers separately
from kept changes, including intentional empty edits and active source-view input.
Original episode/ref/node, field position, source-history prefix and typed
record baseline or judgment/selected-change inputs stay attached. Open `U` →
**Scientific change** or **Review explanation**. `Ctrl+O` inspects original/current
science, authored baseline and judgment/AI contributions while preserving text,
cursor and undo. In a changed field context, `r` then Enter explicitly chooses
the displayed current basis before Ctrl+S can keep fields. A later context change
refuses that choice. Reading and returning alone do not create pending writing.
Restored answers cannot complete an old review: Esc → R in Work → Enter → 1
prepares the current exact scope. Merely opening an answer keeps its earlier
basis; when that differs from the new review, Ctrl+O → r → Enter explicitly uses
the displayed new basis before completion. U's x-confirmed discard
removes only the selected input and its basis. Older v2/v3/v4 TUI checkpoints still
read; older builds refuse v5. No original review seal or authority is restored.

`claimbranch.paper-work/v6` adds `claimbranch.wording-workspace/v5`. Wording and
reason retain their original recorded/detached history, contribution chain and
exact supplied source bytes, including mixed line endings and decomposed Unicode.
Separate unfinished wording/source-path fields and their active field survive;
Ctrl+O scientific-basis inspection also checkpoints active wording. Pristine
browsing adds no saved draft. The named action `;` → **Resume manuscript drafts**
opens the retained list; Enter opens a draft, e resumes writing, and Tab exposes
its retained original source even without a current preview. W still reaches
recorded writing impact. Detached drafts do not appear as recorded obligations.
In that list, d then Enter discards only the selected wording draft and its
unfinished fields; Esc cancels. It does not remove scientific work or touch the
source file. This also permits explicit removal of unwanted writing after a
capacity error. An unchanged source shared by drafts is stored once by digest;
distinct sources and scientific histories still count toward the total limit.

Restore reads no source file and installs no live review. For recorded work,
R re-reads the matching source and requires unchanged scientific context before
preparing a new review. A missing/different source or changed context preserves
the original bytes and writing and blocks review under that old basis. Restored
detached parents remain historical: continue editing there or prepare a new
scientific review for separate wording; reopening cannot revive parent consent.
Earlier v2–v5 checkpoints still read; older builds refuse v6. Source-only browsing
without wording or unfinished input is not retained. Exact source bytes
count toward the aggregate checkpoint limit; oversize saves fail visibly.

`claimbranch.paper-work/v7` adds `claimbranch.review-pool-workspace/v6`.
Unfinished scientific fields and review answers now share identical original
writing sessions by their verified canonical digest. Each input still retains
its own owner, source prefix, authored record or selected-review request, text
and field position. Different earlier judgments at the same owner stay separate;
restored inputs have independent mutable copies. Missing, forged, duplicate or
unused session identities and invalid individual bindings reject the complete
checkpoint before installation. No review or consent is restored.
Existing v5/v6 files remain readable without rewriting them on open; later
changed saves use v7. Builds without v7 support refuse this newer format.
Selected-paper checkpoints containing v7 work use `claimbranch.project-work/v3`,
preserving prior relocation/refresh transitions. Existing v1/v2 project files
still read; the next terminal checkpoint upgrades the wrapper, including a
routine checkpoint with unchanged text after opening a legacy selected project.
Loading the value itself performs no write. Older project readers cannot reopen
that v3 file. This is prototype checkpoint versioning,
not the production accepted-store migration contract.

**Excluded:** live branch/merge work, manuscript review answers, completed reviews,
raw proposal request/response traces, undo, view settings and
hypothetical state. Status identifies writing recovery; normal quit names any
excluded writing/requests/reviews. Immediate Ctrl+C also names dirty excluded
editor text in the closing message. Adopted AI contributions survive even though
request execution cannot resume. This is still not a complete workspace save.

Changed covered writing checkpoints after one second without input, on
keep/cancel, suspend and exit; unchanged content is not encrypted again. Abrupt
process loss can lose newer input. The existing canonical limit is 256 KiB for
the entire work and 16,384 UTF-8 bytes per string, alongside the editor's 12,000
character limit. Review fields prefilled from longer valid source text can be
shortened and recovered up to the existing 16 KiB UTF-8 bound; new insertion
still follows the editor limit. Distinct original review-input sessions and
their contribution history still count toward the aggregate limit. No row is silently
omitted: shorten, keep or explicitly discard appropriate unfinished input while
the session remains open, then retry. Small manual fallback drafts beyond the 16 review-session limit
remain recoverable without manufacturing a review session. Oversize content fails visibly without truncating text or
replacing the previous checkpoint. A save failure keeps the TUI open on normal
quit; the original typed text stays in memory. Input/size failures before storage
ask for correction or shortening; storage/encryption failures report unconfirmed
saving and ask to check availability while keeping the session open. Press `;`
and choose **Inspect writing save status** to read complete guidance; PgUp/PgDn
scroll and Esc returns. Uncertain native durability or an external checkpoint
change blocks further terminal saves for that session. Copy newer writing before
exiting (`Ctrl+C` exits without saving newer input), then reopen to inspect
which writing is saved; the UI does not claim
that previous bytes survived replacement. No automatic rebind or overwrite follows. This is not a power-loss,
replacement-device or human-usability guarantee.

## Terminal paper prototype

Run in the checkout or extracted source preview, on the host where you want
to work. An interactive SSH terminal works as the intended host; the app
requires no browser, graphical login, forwarded port, AI key or pip packages.
Python 3.13 with its Unix `curses` module and a UTF-8 terminal is required.
The current observed host is macOS; actual Linux/SSH testing remains open.

```sh
python3.13 -m claimbranch demo tui
python3.13 -m claimbranch demo tui --ai-off
python3.13 -m claimbranch demo tui --navigation outline
python3.13 -m claimbranch demo tui --series --variant recorded
python3.13 -m claimbranch demo tui --merge-example --variant recorded
python3.13 -m claimbranch demo tui --layout three --variant recorded
python3.13 -m claimbranch demo tui --snapshot
python3.13 -m claimbranch demo tui --draft-file "$HOME/.local/state/claimbranch/demo-drafts.json"
```

Press `;` for named actions on the selected node. Choose with arrows and Enter;
Esc returns to the same graph/reader context. Judgment writing, personal notes,
connections and unfinished writing come first, followed by scientific change,
branch and merge review. Existing shortcut keys still work. Claim/subclaim and
scientific-connection and follow-up-plan creation open explicit manual forms.
Interpretation creation also opens a blank manual form where the episode/ref
has no interpretation yet; occupied contexts explain how to edit existing work.
Unconfirmed result capture opens a separate session draft; evidence confirmation
and graph staging remain unavailable.
Review actions show missing prerequisites before proceeding. This is a bounded
context list, not a general command palette.
`×` marks unavailable entries, with their reason below the selection. Keys such
as `w c` show the Work entry step required outside the menu; Enter in the menu
performs that route. The source excerpt uses `…` when it omits remaining text.

Choose **Write an interpretation** from `;` (or `i` in argument drafts). To try
creation on an available context, run `demo tui --merge-example --ai-off` and
stay on `main`: this episode has no interpretation there yet. The ordinary
populated example already has one; use **Edit scientific changes** to revise
it. Kept/unfinished interpretations in this work instead return through **Open
argument drafts**. Write your explanation and choose **Observations interpreted**;
Space toggles individual recorded observations, Enter uses the selection and
Esc cancels it. None is preselected. An empty selection is allowed and shows no
evidence links; statuses remain visible even at 48 columns. `r` reads the selected
observation's full statement, conditions, measurement and unopened source
reference; Esc restores the unchanged picker choices. Ctrl+S in the form keeps the candidate
for this session; `g` opens its graph. Add an explicit scientific connection
with `l` to explain how this interpretation relates to a claim.

With a kept **new** interpretation selected in argument drafts, `J` compares
its text with the owning judgment and reason. Enter reuses the kept wording,
retaining the reason and existing AI contributions; Esc changes nothing.
Resolve unkept candidate edits first. Source/work changes invalidate the
comparison. Existing recorded interpretations cannot use this manual-copy path.
`b` opens the owning judgment to continue its reason; `R` reviews selected kept
science once judgment and reason are complete. The exact interpretation text
must match that judgment, and edits require a new review. Reuse may invalidate
a pending AI reply, as disclosed before confirmation. Other judgments and
unfinished writing remain separate. Draft observation links and interpretation
fields stay outside the manual checkpoint; --work-dir retains them as unaccepted
writing. Without that option they are lost on exit. Reuse accepts no science.
The current domain validates all kept interpretation wording even when omitted
from the selected review. A mismatch names `J` reuse, editing or `u` unkeep as
the next action; unkeep retains the writing outside graph/review. Each independent
owning judgment can explore its own candidate interpretation; they are never
combined or installed automatically. A reason exceeding the review byte limit
blocks reuse without replacing the existing judgment.

Choose **Draft a result and source** from `;` to capture a new result beside
an existing recorded subject. Use synthetic content in this prototype. Write
observed content, run/source references, conditions, measurement definition,
value/unit/baseline and an optional tentative judgment/reason; all fields may
remain incomplete. References are text only: no file, SSH connection or artifact
is opened, and no completed run or confirmed observation is manufactured.
The tentative judgment stays with this result, separate from the selected
node's existing judgment and scientific review.

Arrows choose a field; Enter edits it. Ctrl+S keeps the field **in this session**;
Esc retains changed input separately from kept text. Enter resumes unfinished
input, including an intentional empty edit. Ctrl+O inspects the result and
original/current source; Tab switches result/source history, PgUp/PgDn scroll,
and Esc/Ctrl+O returns to the same text, cursor and undo. Recorded AI contribution
history stays inspectable as source history. A changed or unavailable source
retains the original context and writing, without rebinding or granting review.
`r` on the field list reads all kept/unfinished text; Esc returns through the
result list to the unchanged graph. Below 48×18 editing pauses with Escape
available to retain input.

**Resume result drafts** lists writing across original episode/ref/node contexts.
Several results may refer to the same subject without merging text. Up to 16
result drafts are retained; pristine browsing creates no pending writing, and
capacity errors never evict written work. `d` then Enter discards the selected
result after confirmation. These drafts are **excluded from --draft-file**, AI
requests, W's scientific obligations, graph edges and change reviews. Normal
quit discloses their loss unless encrypted --work-dir recovery is enabled.
The encrypted recovery path retains original context and both kept/unfinished
fields. Empty-project TUI entry, source confirmation and transfer into scientific
reasoning still require their owning integrations.

Choose **Add a claim or subclaim**, **Connect research records**, or **Plan a
follow-up experiment** from `;`.
Select each form field with arrows and Enter. Claims require an explicit level,
parent, statement and scope; connections require source, target claim, full
relationship name and reason. Parentage creates no scientific support. The
endpoint picker includes kept draft claims and existing evidence; it cannot
create an observation or run. Text fields support Korean/paste, multiline input
and undo/redo. Esc or Ctrl+S returns text to the unfinished form; Ctrl+S on the
form keeps that candidate. Incomplete values remain editable, while graph and
final review report validation errors rather than inventing missing fields.

For a new plan, explicitly choose an existing or kept draft claim, then write
its question/objective, experimental conditions, metric name, measurement
definition, unit and comparison/baseline. Scientific fields start blank; the
plan remains **UNRUN**. Reopening the target picker preserves its current
selection; the draft list names that target beside the objective. It creates
neither a completed run nor evidence and
does not execute an experiment. Its draft card uses the same stable D alias
as its owned work; its tests connection points to the chosen claim. Reading
exposes the complete conditions and measurement. Hypothetical scenarios on new
draft plans are not connected yet. Existing recorded plan amendments still
edit only the objective.
Exact review displays the target's alias and scientific text, with each metric
field separately readable. The shared UTF-8 field and canonical payload limits
still apply to plans; valid combined plan fields are not subject to the older
smaller claim/connection editor cap.

**Open argument drafts** lists the selected judgment's owned work. Enter edits, `n` adds a
claim, `l` adds a connection, `p` adds an unrun plan, Space includes/omits a kept candidate in final
review (editing preserves that choice), and `d` asks separately about removal
and dependent kept/unfinished drafts. `u` moves a kept candidate back to
unfinished writing without losing its text; any kept dependents still require
repair. Kept selection and unkept edits are labeled separately, and review warns
that unfinished candidate fields are excluded. `g` shows
all valid kept candidates in a **DRAFT GRAPH**, including candidates omitted
from review; unfinished unkept forms are excluded. Draft cards/connections
are labeled and existing shared observations retain their identity. Arrows,
Enter, `r`, Tab, `f` and HJKL inspect/read/follow/fit/pan; Esc returns to the map,
then owning work. Candidate nodes offer inspection; judgment/note editing stays
with existing source nodes. `b` returns to the owning node's judgment and `R`
prepares final review only after the judgment/reason and selection are complete.
**Return to authored work** restores the original episode/ref/node from another
selection. It also includes unfinished candidate forms, separately from `U`.

To reuse one judgment across related nodes, choose **Link this judgment to
nodes** from `;`. Arrows choose existing source nodes; Space links/unlinks them.
The original owner stays included. Enter previews the judgment, reason, original
owner and affected nodes; another Enter applies exactly those associations.
Esc returns without applying. Newly linked nodes select this work, preserving
their previous judgments separately. Already-linked nodes retain their current
choice; adding a reference never resets a separate judgment chosen there.
It adds no scientific relation.
At another node, **Choose a judgment for this node** offers existing judgments
in the same episode/ref and that node's own separate judgment. Preview then
confirm the choice; it changes only which judgment that node displays.

The editor title names the original judgment owner and its source panel names
the viewed node. **LINKED JUDGMENT** in Work lists the referenced aliases, marking
nodes that currently show a different judgment. Editing
from any chosen node updates the same judgment/reason and contribution history;
personal notes still belong to the viewed node. Candidates, AI requests and
unfinished judgment/review writing stay with the original owner. `U` and Return
to authored work explicitly restore that owning work even if its node currently
displays a different judgment. Membership changes revoke its change reviews.
At most 16 source nodes can reference one judgment; new draft graph nodes are
not eligible, and episode/ref changes never select foreign work.

Without `--work-dir`, judgment links and display choices are **session only**,
including with `--draft-file`. Encrypted recovery retains those associations. The checkpoint retains eligible manual text and unfinished
writing at its original node; after restarting, return to that node or `U`.
Links must be selected again. AI-influenced work retains its existing session-only
boundary; association never makes it eligible for a manual checkpoint. Normal
quit discloses link loss alongside other volatile work.

Candidates are owned by the original existing-node draft, with stable IDs and
session aliases, a candidate revision and exact source binding. Edits, selection
and removal revoke scientific/branch/child-merge reviews while retaining
independent AI proposals. Judgment edits or review expiry retain the candidates.
A changed source blocks graph/review while keeping text; `s` in the draft list
explicitly refreshes its binding before revalidation. If an amended source
record changed, a scrollable comparison shows previous/current source and the
retained draft first. Enter deliberately retains those draft values against
the new source; Esc keeps the prior binding. This is not automatic rebasing:
retained values can propose reverting newer source fields, which remain subject
to domain validation and exact final review. The existing 16-work
capacity remains; each work permits at most 64 candidates/unfinished forms.
Domain cardinalities may reject a smaller graph. Omission cannot repair invalid
fields; repair them or move them to unfinished writing before review. Existing
record forms retain their original field-edit limits; new claim/link/plan forms
expose explicit hierarchy/endpoints and complete plan measurements. Project
initialization, confirmed-result integration and typed AI adoption remain unconnected.

Without `--work-dir`, candidate fields and unfinished forms are **session only**,
including with `--draft-file`; normal quit warns about their loss. Encrypted
recovery retains this writing, selection and source binding, then reconstructs
the draft graph when requested. They never enter the manual-note checkpoint or
become accepted records.

`--ai-off` disables the fixed-response capability for every draft in this launch,
including after episode/ref navigation and in comparison graphs. The header,
action list and Work reader identify the state. The AI menu entry and Work's
`A` key do not open a context/request picker; manual notes, judgment writing and
review remain usable, with no new Proposal, attempt or trace. `--variant recorded`
still retains the bundled source's earlier AI history: disabling new assistance
does not rewrite provenance. Default launches retain the explicitly labeled
fixed offline example, available before a complete judgment; neither mode
configures or calls a live model. Snapshot mode also displays this capability.

Color follows terminal capabilities and a nonempty `NO_COLOR` disables it.
For a deliberately colored preview without changing shell preferences, run
`env -u NO_COLOR python3.13 -m claimbranch demo tui --series --variant recorded`.
Snapshots are intentionally plain text. Other nodes dim when they are outside
the selected neighborhood; that emphasis is independent of color availability.

`--series` opens the cumulative synthetic paper. `t` opens an episode picker;
Up/Down chooses an episode, Tab chooses main/alternative, and Enter opens that
context. Escape cancels without moving the graph; `b` still toggles branches
inside the current episode. Returning restores that context's selection,
reader, lens and viewport. Hypothetical previews clear on context changes.
The header distinguishes the episode's reasoning from current global evidence:
closed episodes are readable, but they are not historical evidence snapshots.
Notes, judgments, AI requests, staged changes and unfinished text stay with
their episode/ref/node. `U` can resume unfinished text across those contexts.
The paper workspace holds at most 16 review draft sessions; reaching its limit
retains existing reviews and manual note/judgment editing, with a visible review
limit rather than discarding text.

`W` lists reconstructed work across episodes. Enter reads its original
judgment/reason, explanation disposition, AI influence, scientific selection,
potentially affected claims/writing and changed-source flags. `g` opens a
related-node picker; Enter opens that node in its originating episode's main
view. `W` returns to the selected work item. These items are **pending if
accepted**, not accepted Debt records; reading them or closing an episode does
not resolve them. The list shows only service-projected manuscript and
understanding work, without inventing follow-up obligations. It is separate
from `U`, which lists local unfinished text. The legacy default example remains
available and points to `--series` when these cumulative actions are requested.

In an explanation item's detail, `e` opens its causal topics; Enter reads the
selected topic. `e` writes partial explanation, `r` links/unlinks the original
reason without copying it, and `[`/`]` changes topic. `Tab` cycles explanation,
original science, current science, the draft's earlier basis and AI history.
Scientific views include measurement definitions, conditions and exact
connections; source references remain unopened. Original and inherited judgment
contributions have separate labels. Missing current nodes/connections stay
explicit rather than disappearing from the comparison.

While editing, `Ctrl+O` opens full source context and returns to the same buffer,
cursor and undo state. `Ctrl+S` keeps partial text for this session; Esc retains
changed input separately. Reopening with `e` resumes it, including an intentional
empty edit. Restoring unfinished input to the kept text removes that redundant
buffer. Character and NFC UTF-8 byte counts are visible: the editor holds up to
12,000 characters, while keep requires at most 16,384 UTF-8 bytes per topic and
64 KiB for the complete encoded draft. A refused keep retains all input.
`Ctrl+_`/`Ctrl+Y` undo/redo while editing. Below 48×18 input pauses and Esc
retains and leaves the editor; wide views place the original judgment/reason
beside the text and narrow views keep a compact judgment strip above it.

Changed evidence or reasoning retains the earlier draft basis and writing.
From the topic reader, `s` previews earlier/current scientific context for all
topics and Enter explicitly uses that displayed basis; another source change
refuses the refresh. This grants no review or closure. If the source becomes
unavailable, earlier context and manual editing remain available, while basis
refresh is blocked. Esc returns through topics and the same pending item to the
original graph position. W identifies retained explanation work; U continues
to list node/change-review writing. These explanation drafts and rationale
references are **session-only** by default and remain outside `--draft-file`;
normal quit warns with manual recovery enabled. With `--work-dir`, the encrypted
checkpoint retains them and unfinished input, labeling this recovery in W and
the editor. No provider, grade, accepted debt or closure action is added.

The default graph gives each record one box and keeps shared evidence connected
to several claims without duplicating its node. It starts with compact cards
and a full-width map, with the selected source excerpt and named relationships
below it. `Enter` opens reading and `r` opens connections: beside the graph at
140 or more columns, or in a dedicated full-width pane below that width.
`P` pins/unpins the reader; a pinned reader returns after a narrow resize.
Pinning persists across node, scope and lens traversal. `f` temporarily expands
the map without clearing that preference; `Esc` restores the preceding view and
`P` can reveal the pinned reader again. `Esc` closes the view at the same selected
node/pan before returning along previous node visits.
Arrowheads point to recorded targets, including incoming and parallel relations.
The selected node, its direct neighbors and incident edges stay bright; other
cards and connections dim without moving or disappearing. Connected cards spell
out their recorded relationship to the selected node beside their title when
the whole phrase fits, for example `R1 RUN · produced E1`. Longer phrases and
additional parallel relations continue immediately below the title, above the
source preview. These header labels retain semantic colors with regular weight;
terminal font size is unchanged.
For example, selecting E1 shows `supported by E1` on a supported claim,
`challenged by E1` on a challenged claim, and `produced E1` on its run.
Selecting a claim instead shows `supports C1` on evidence directed toward it.
Parallel relations have separate full phrases; structural `contains C3` and
scientific `supported by C3` are never collapsed into a mixed code. Each card
reserves enough header continuation rows for its largest group of links to one
neighbor, including wrapped wording. Selection therefore does not resize or move boxes. Source
preview rows and personal-note markers keep their own space.

There are no mid-route words, crossing X marks or route-count digits. At a
crossing the inspected edge is drawn over other strokes, then direct incident
edges over subdued context. Routes sharing an actual contact keep their fork
visible only along that contact's common first leg. Independent crossings choose
one actual stroke without inventing a junction. This is visual occlusion;
every route identity and endpoint remains in the relation picker. `r` opens
that picker, arrows choose an exact edge, and Tab reads its complete FROM/TO,
type and rationale. A selected relation outside the lens remains explicit.
Incoming and outgoing routes use separate ports; reciprocal pairs keep their
actual target arrows. Relationship text stays in the card header band, away from
source text, route lanes and arrowheads. Exact-edge focus shows only that relationship's
phrase. The footer keeps the selected node's named relationships and directions;
full endpoint/type/rationale details remain in the reader. The same phrases and
target arrows work without color and require no code key.

Arrow keys select nodes spatially; `j`/`k` visit in-scope nodes in column order.
The viewport follows the selection. `H`/`J`/`K`/`L` pan manually. `f` opens the
full-width map with compact cards, resets pan and fits the current scope as
far as its readable minimum permits; Esc restores the previous view. It does
not silently discard nodes or shrink the terminal font. Oversized graphs still
pan. `l` opens a neighborhood rooted at the selected node; `+`/`-` adjusts its
depth from one to three connections. Moving selection within that scope keeps
its root/layout. `a` returns to all nodes in the current Argument/Evidence lens.
Following an edge or searching outside the local scope reveals the target in
the wider view; Esc restores the previous scope. The footer distinguishes
visible/in-scope cards from nodes and edges hidden by local scope. Incomplete
cards are omitted; the legend names
offscreen direct neighbors, reachable with `r`. `C1`/`C2`/`C3` distinguish claims,
while `E1`/`E2` identify observations. Four-row compact cards use authored short
captions for the frozen synthetic statements, matched against their complete
source text. Edited or unknown statements fall back to visibly abbreviated
source excerpts; these are not general AI summaries or persistent node titles.
`…` marks omission. `UNRUN` remains explicit on plans; `!` marks an unlinked
record, explained in its selected-source context. Evidence values abbreviate
percentage points to `pp`; the reader retains the full unit, run conditions,
statement and method. `o` switches the graph and the previous outline
for comparison over the same records; `--navigation outline` starts there.
Search matches source content, compact captions and personal notes in the
current lens, retaining the surrounding graph.

Press `n` to write a personal node note in the reader pane, keeping the graph
beside it when the terminal is wide enough. Enter adds a line, `Ctrl+S` keeps
the note in this session and Esc cancels the current edit. `✎` marks its
presence on a compact card; comfortable source cards show a labeled note
preview. `Enter`/`d` opens the full note beneath the source content.
Search includes notes on the current branch. Notes are distinct from the `e`
Judgment/reason draft and from source observations. Shared occurrences and
view changes retain one node/branch-bound note. `Ctrl+_` undoes and `Ctrl+Y`
redoes editor changes. The footer exposes the 12,000-character limit and warns
when insertion is truncated. `N` explicitly recovers a cancelled note; `E`
recovers a cancelled judgment. Lowercase `n`/`e` edits the kept version.
Cancelling unchanged text preserves an earlier unfinished edit. `U` lists
unfinished writing across nodes and branches and opens the selected buffer.
It also lists scientific-change fields and review explanations by original
episode/ref/node, explicitly labeled **Session only**. Their Esc action retains
changed text, including an empty edit; unchanged browsing adds no pending item.
Enter in `U` restores the original context and editor. These inputs are excluded
from `--draft-file`; normal quit warns even when manual notes are checkpointed.
For these session-only entries, `x` in `U` offers discard; a second `x`
confirms, and Esc cancels the confirmation. Only that unfinished input is
removed: staged fields, kept judgment and completed review remain unchanged.

`w` opens the selected judgment's Work reader. By default each branch/node has
its own judgment; explicit links reuse one original owner as described above.
Its judgment uses the existing paper drafting service. The following
journey is synthetic and unaccepted; no model server or scientific writer runs:

1. `e` writes a judgment and reason. Personal notes remain separate. The editor
   retains up to 12,000 characters per field; the service additionally limits
   each field to 16,384 UTF-8 bytes. Longer Korean text is kept locally with an
   actionable notice, while requests/reviews wait for a shorter draft. No older
   shorter draft is reviewed in its place.
   At 120 columns or wider, recorded subject context sits beside the writing
   fields; narrower terminals retain a compact source strip above them.
   `Ctrl+O` opens the full read-only context. PgUp/PgDn or arrows scroll;
   `Esc` or `Ctrl+O` returns to the same text, cursor, field and undo history.
   A second Esc retains unfinished writing through the normal editor path.
   Keys/paste in source reading do not edit or keep the draft. References are
   labeled **not opened**; no artifact is accessed. Below 48×18 editing pauses,
   Ctrl+O cannot change hidden views, and one Esc retains text and leaves.
   Episode/current-global-evidence and hypothetical status remain explicit.
   Manual private-recovery versus AI session-only status and failed-save
   warnings remain visible, including while reading source context.
2. Optionally press `A` in Work. Select context nodes with arrows/Space and
   choose whether to include the judgment with `d` (off initially). Scientific
   relations between checked endpoints are included and shown in the exact
   request preview. Notes and unchecked neighbors are excluded. Enter opens
   that preview; another Enter requests the fixed offline example. Esc cancels.
   Esc from the context chooser preserves the prior proposal; preparing a new
   outbound request explicitly supersedes it, as the chooser warns.
   This exercises consent and response handling, not live AI usefulness.
3. Drafting remains available while the example response is pending. `y` in
   Work opens a comparison of the existing judgment/reason and the whole proposed
   replacement. PgUp/PgDn and Home/End read its complete content; Enter explicitly
   replaces the judgment while keeping its reason, and Esc keeps your writing
   and leaves the proposal available. Changed/expired proposals or changed work
   block replacement until a new comparison. Resize below 48×18 pauses confirmation.
   Later edits retain AI origin. This is whole-text replacement, not selective
   incorporation of nodes/links or scientific acceptance.
   Editing/cancellation makes older replies unadoptable. `B` compares current
   writing with the earlier pre-adoption text/reason before Enter restores it;
   Esc preserves newer writing. Restoration does not erase AI contributions.
   Unkept judgment writing remains separately available in U in both comparisons.
4. `c` edits existing claim statements/scopes, interpretation wording, plan
   objectives or scientific relation types/rationales. Enter opens an editor;
   Ctrl+S stages and selects the authored change, Space includes/omits it.
   Editing or toggling amendments revokes scientific/branch review without
   cancelling an independent pending or ready AI proposal. Re-editing a change
   stages and includes it again, with a visible notice; Space can omit it.
   Observations, experiment records and structural links cannot be overwritten.
   The adapter never infers scientific amendments from the judgment or a note.
5. `R` prepares selected/required/omitted effects through the paper service.
   The reader shows exact field differences, affected/outside-path claims and
   unchanged evidence. `G` opens comparison graphs; Tab switches before/after,
   arrows select, HJKL pans and Esc restores the prior Work context. Enter
   completes a current unaccepted review. When source/draft AI influence requires
   explanation, choose to reuse/revise the existing reason or explicitly defer;
   deferral describes work that would remain if accepted later. It opens no debt.
6. `x` is Not now: cancel the request/review while retaining the judgment and
   staged changes. `p` still shows the frozen source episode's contributions;
   Work shows the current local judgment's contributions separately.

Work begins with recorded subject context and the local judgment/reason.
Prepared/completed review, length-limit, unfinished-text and offline-AI state
indicators precede long text so their status is still visible on small screens.
Full source and authored wording remain accessible; notes, scientific changes
and contribution details retain their separate meaning. Changing graph nodes
selects the judgment explicitly chosen for that node, or its own separate draft
when no choice exists.

Unkept review inputs are marked **unfinished** in the change list and disclosed
separately in Work; they do not replace staged fields or completed explanations.
Ctrl+S removes the matching unfinished entry only after staging/completion
succeeds. An expired graph comparison or completion prompt shows a stale notice.
An explanation can still be read and edited from `U`, but Ctrl+S cannot finish
an expired review: Esc retains it, `R` in Work refreshes the scope, and Enter → 1
reopens the explanation for that scope. Review controls pause below 48×18 with
an enlargement hint; Esc remains available and retains changed text.
With `--work-dir`, U and Work name encrypted retention for these inputs.
Ctrl+O reads their original/current context; it does not complete or stage work.
The [encrypted recovery contract](#encrypted-terminal-judgment-recovery) owns
source/basis reuse and version compatibility.

For branch/merge rehearsal, start `--merge-example`: it verifies the full series
against its frozen golden result, then replays the prefix before the last merge.
Episode two is explicitly active; `--series` still opens the fully closed series.
The flags are mutually exclusive. No closed episode is silently reopened.

- `M` from the graph opens changed records in the recorded alternative. Arrows
  choose, Space includes/omits, Enter reads the full record. `s` supplies a local
  UTF-8 manuscript snapshot read-only (regular file, at most 64 KiB); Ctrl+S
  reads it. `R` previews the selected merge with service-computed required
  dependencies, omitted changes, exact field effects and impact. Nothing has
  merged into the graph workspace.
- For an authored alternative, `b` switches to that ref. Keep your judgment with
  `e`, open Work with `w`, then `c` to stage scientific changes. Select this
  episode's Interpretation and `J` explicitly stages the judgment's wording
  there; other interpretation records are rejected. This keeps the required
  interpretation/judgment agreement explicit without retyping or inferring it.
  After closing the change list, `C` previews a detached branch. Enter calculates
  its candidate and opens separate merge selection; it does not install it.
- In branch or merge preview, Tab switches effects/basis, G opens exact
  before/after graphs, Tab switches phase, arrows select, HJKL pans and f fits.
  Escape restores the preview, then the original Work/graph position.
- In merge review, Enter completes the exact current unaccepted review. Retained
  AI origin requires explanation (reuse/revise the recorded rationale) or
  explicit deferral. `v` calculates the candidate and shows conditional pending
  work; source history and actual pending work are unchanged. This is not an
  authorization or storage action. `x` clears review while keeping selection.
- R, completion and candidate calculation re-read the supplied file. Changed,
  removed, unreadable or invalid UTF-8 source revokes the old review. Selection
  changes, expiry or changed parent draft/history also invalidate it. Supplied
  file identity remains unverified. An expired parent branch preview cannot be
  reused through a later merge review. Return to Work and C to prepare again.

These candidates, selections, source paths and unfinished explanation editors
are session-only, including with `--draft-file`. Re-preparing the same branch
keeps unfinished inputs. An adapter history refresh also retains those buffers
but requires supplying the source again; it never carries the old review. Escape retains unfinished text
separately from reviewed content; normal quit warns before discarding this work.
No graph, accepted research history, manuscript file or pending item is updated.

To continue that same scientific judgment into manuscript wording, press `m`
from merge review. The **From selected science** picker opens wording for the
current completed review or a retained earlier draft from the same original
work. Enter on the current review calculates its detached candidate and selects
the manuscript consequence by that exact merge operation; it does not install
the candidate or insert anything into W. The previously supplied source is
reused read-only and must match the parent review's bytes. Wording starts blank.
The same exact review reopens its existing wording. A different review starts
a separate blank draft only when explicitly chosen; older wording, unfinished
buffers and source AI stay accessible under their original basis. Recorded and
authored alternatives, different original judgments and episodes remain separate.

Parent judgment/link changes, reselection, expiry, workspace-history changes
and changed/unavailable source prevent new child previews and completion.
Earlier text remains readable/editable with a stale-basis message. Return to
science to prepare a new exact review; `m` still reaches its retained drafts.
There is no automatic wording transfer across different scientific bases or
restoration of expired consent. Candidate wording has its own 16-session limit,
separate from W's 16 recorded-work sessions. At capacity, a pristine candidate
may be removed; kept text, contributions and unfinished input are never evicted.
When all candidate slots contain writing, a new scope is refused and the
existing drafts remain reachable. Escape returns to
the originating merge review, then its selection and original graph position.

From `W`, open a **Writing impact** item with Enter, then press `m` for its
manuscript review. The working draft starts blank and belongs to that work ID,
independently of graph notes and judgments. Its header identifies the causal
episode and the current main context used by the wording service.

- `s`: enter a local UTF-8 manuscript path and Ctrl+S to read it. Only regular
  files up to 64 KiB are loaded; nothing is written. The reader shows the exact
  start/end marker names required for the item's anchor. A missing file or
  malformed markers cannot produce an exact preview.
- `e`: edit replacement wording and its reason, Tab between fields, Ctrl+S to
  keep. Existing 12,000-character editor and 16,384-byte service bounds apply.
  Escape retains an unfinished buffer for that work item; opening the same
  editor restores it. Unfinished text is explicitly excluded from the preview.
  The scientific judgment and reason stay above the editor at wide/narrow sizes.
  `Ctrl+O` opens the full judgment, contributions and (for a detached candidate)
  exact scientific effects; scrolling and return preserve buffers, cursor and
  undo. `Ctrl+R` explicitly reuses the displayed judgment reason; replacing a
  different reason shows both texts and requires Enter. Esc cancels that
  replacement, and Ctrl+_ in the reason field undoes it. Judgment text never
  automatically becomes manuscript wording. Below 48×18 editing pauses while
  Esc retains unfinished text. The same controls apply to W's existing route.
- `R`: re-read source and prepare a bounded exact preview. Tab/Shift+Tab switches
  diff, complete before, candidate after and scientific basis; PgUp/PgDn scrolls.
  Source views preserve indentation/repeated spaces and wrap by terminal cells.
  Display sanitizes controls and normalizes glyphs; the service's SHA-256
  bindings and candidate bytes retain exact supplied UTF-8 source bytes.
- Enter completes only the current **unaccepted review**. Source AI influence
  requires an explanation (reuse/revise the wording reason) or explicit deferral.
  Completion re-reads the file: changed, removed or unreadable source revokes
  the old review; the wording remains. Expired/changed wording also requires R
  again. A supplied file snapshot is not verified filesystem identity.
- `x` clears the review and retains wording. Esc returns to the same pending
  item, then list, then original graph without moving it. Opening or completing
  this view does not apply text, compile, accept reasoning or close pending work.

Manuscript wording and unfinished editors are session-only by default and with
`--draft-file`; the opt-in encrypted adapter retains wording/source input as
described in [encrypted recovery](#encrypted-terminal-judgment-recovery).
Manuscript review answers and review results remain session-only. Normal quit
names excluded work before discarding it. Up to 16 work-item sessions are kept;
reopening an existing item retains its buffers after that limit is reached.

Without `--work-dir`, AI-influenced judgments, proposal history, change selections
and review results remain session-only, including with `--draft-file`. Encrypted
recovery retains adopted judgment contributions and candidate selections, while
request traces and review results still remain session-only. Adoption is labeled as such
before the action; normal quit warns about discarding that work. The text-only
checkpoint keeps the pre-AI manual draft and excludes subsequent AI-influenced
kept/unfinished edits, so restart cannot present them as human-only writing.
Notes and other manual drafts retain their existing recovery behavior.
The terminal still lacks live AI and protected own-project storage. Branch/merge
and manuscript review are synthetic, unaccepted rehearsals; they do not provide
durable project opening, acceptance or resumption.

Without either recovery option, notes/drafts remain volatile: normal quit asks before
discarding them and interruption discards them. With the explicit option,
the private checkpoint stores kept and unfinished manual text separately, plus the
selected context/node. Single-episode checkpoints retain format version 1;
series checkpoints use version 2 and carry episode/ref/node keys. They cannot
be loaded as each other's history; no silent migration or overwrite occurs.
It checkpoints on idle input (about 100 ms), during
continuous input at roughly 250 ms intervals, and on keep/cancel, suspend and
clean exit. Abrupt process/host loss can lose text after the last completed
checkpoint. Reopen with the same path, fixture variant and `--series` choice, then `N` or `E` to
resume unfinished writing; `Ctrl+S` is still required to apply it as kept text.
Undo stacks, navigation history and scenarios are not restored.
If killed during atomic replacement, a private `.draft-*` temporary file can
remain beside the checkpoint; it is not loaded as accepted or recovered state.

The path must resolve outside Git working trees, with an owned parent directory
that is not writable by other users. Newly created directories use mode 700;
checkpoint/lock files are owned regular files with no group/other permissions.
Symlink files, hard-linked files, another open session, malformed content and
a different history fail before opening the UI. Existing files are never
silently reset. A save error keeps text in memory and reports failure; `q`
retries, while `Ctrl+C` exits with only the last completed checkpoint retained.
This is local unaccepted UI text, not production research custody or backup;
see [ADR 0013](../architecture/decisions/0013-terminal-draft-recovery.md).

The renderer uses the live terminal size even when exported `LINES`/`COLUMNS`
are stale, finishes frame updates during queued input, and fully redraws when
the pane composition changes. Unknown CSI/SS3 key sequences are ignored as a
unit instead of replayed as ordinary shortcuts. `Ctrl+L` redraws the current
screen, including an editor, without changing its buffer. Normal Enter outside
an editor navigates/reads inside the TUI and never writes a terminal newline.
Unmapped Alt/Option combinations are ignored as single modified keys, including
keypad suffixes returned by curses as integers. Alt+Backspace cannot become
standalone Esc and cancel writing. Control
bytes inside bracketed paste remain data rather than exit commands. A bare
Esc and another command must be sent separately from an Alt chord.

Bare Esc defaults to a 35 ms sequence-disambiguation delay, without a second
unconditional wait. Set `ESCDELAY=150` (milliseconds, bounded to 1–2000) for a
connection that splits escape sequences slowly. Actual SSH behavior still
needs host testing. Blank panel fills avoid per-character Unicode processing;
curses continues to compare the virtual and physical screen before output.

In the outline alternative, two panes prioritize long scientific text. Three panes retain a separate
relationship list at 118 or more columns; smaller widths collapse to two,
and below 76 columns show the focused pane. The minimum is 48 columns by 18
rows. `--snapshot` emits a plain-text frame without a TTY, useful in a pipe or
for inspecting the package before an interactive session. Noninteractive
launch otherwise exits 2 with a TTY/SSH hint; `TERM=dumb` exits 2 before changing
terminal modes. `NO_COLOR` retains text and selection cues without color.

Press `,` for **View settings**. Up/down selects a row; left/right or Space
changes it in the live preview. Enter keeps the settings, Escape restores the
prior settings and graph position, and `r` previews defaults. Below 48×18 the
controls pause and Escape remains available; resizing restores the panel. The three controls
are Balanced/Spacious node spacing, Brief/Source card detail, and On demand/Pinned
reading panel. A pinned reader stays beside the graph at 140+ columns. Spacing
and pinning are session preferences; card detail follows existing `z` and view
return behavior. They are not stored in the private manual-text checkpoint.
Notes, judgments, selected scientific changes and review bindings are untouched.
Scientific-change and branch/merge comparison graphs inherit spacing/detail.

Balanced keeps at least three cells between directly stacked connected cards;
Spacious raises that minimum to five and increases other gaps. A short screen pans/clips instead of
collapsing an arrow to one cell. The original ten-node example fits at 144×42
and 120×32; its five-node E1 local scope fits at 80×26. At 120×30 and 80×24 some
cards are offscreen. Visible/hidden counts and `r follows` precede less urgent
footer metadata; `l`, HJKL and the relation reader keep clipped records reachable.

The graph defaults to compact cards with two source-preview rows plus reserved
header continuation rows; `z` switches to/from larger
source cards with note previews. Compact width/gaps adapt to the available
graph viewport down to a readable minimum; source cards remain deliberately
larger. The outline starts comfortable and also responds to `z`. Shorter
screens reduce framing. The 256-color view uses dark panel
surfaces and distinct type/relation colors, with an eight-color fallback. Fonts
and physical line height remain terminal settings; the app changes no terminal
profile. If your environment sets `NO_COLOR`, explicitly preview colors for
just this invocation with `env -u NO_COLOR python3.13 -m claimbranch demo tui`.

The outline starts at the thesis and unfolds recorded links to claims,
evidence, experiment records and follow-up plans. The first argument path is
open initially; other branches can be expanded. Each connector shows its exact
edge types, including parallel `supports` and `part-of` links. `↑` means the
displayed node points to its parent; `↓` means its parent points to it. These
arrows describe recorded direction, not a new inference from reading order.
Evidence carries a consistent session label such as `E1 · 2 claims`: the count
is distinct claims directly connected by outgoing scientific relations, not
copies, structural connections or a claim-strength score. A repeated appearance
has `↪`; another visible appearance of the selected evidence has `↔`. Other
shared records retain `[shared]`/`[same]`. Drafts stay identical across
occurrences. `g` jumps to the primary location, and `Esc` restores the previous
occurrence and view. The status distinguishes visible positions from unique nodes.
If a record lacks a path to the thesis, it is marked `UNLINKED` without a
fabricated connection. Search preserves matching ancestry and automatically
opens those paths; `Esc` clears it before ordinary folding resumes.

The top view selector uses `1` for Argument and `2` for Evidence uses. The latter
starts at the selected observation, or chooses an observation connected to the
selected claim when possible; otherwise it opens the first observation. Its
graph displays the recorded claim paths together; the outline initially shows
direct claim destinations and unfolds their further paths on demand. `[` and
`]` switch observations. Search applies to the
current view. Following a source/experiment connection outside the evidence
projection opens its argument location; `Esc` restores the evidence context.
The views retain one source identity, draft and hypothetical state.

These are keyboard shortcuts on the graph, not use-case numbers or clickable
tabs. Close a menu/editor with Esc before using them; digits in a text editor
remain text. Pressing the already selected view key makes no navigation change.
An empty personal project has no observations, so `2` leaves Argument open and
reports **No observations in this branch. Argument view stays open.** Keeping a
provisional result does not enable Evidence uses. Explicitly confirm that result
through its personal preview first; `2` can then open the recorded observation.
It may initially have zero claim uses. Draft scientific connections appear in
their candidate graph; Evidence uses shows those connections only after the
selected reasoning is recorded. Return with `1` or Esc to continue construction.

Selecting evidence shows its named claim uses in READ. `u` focuses that list,
`Tab` reads the selected relation's full rationale, and `Enter` follows it from
the list or relation reader. `r` includes every incident relationship, including
experiment/source references; scientific relation types stay distinct. Empty
use lists are explicit and do not hide those other connections.

| Key | Action |
|---|---|
| Arrow keys; `j`/`k`; `Tab`/`Shift+Tab` | Graph: spatial selection or visit all nodes; lists: move selection; change panes |
| `o`; `f`; `H`/`J`/`K`/`L` | Compare graph/outline; full graph with selection in view; pan the graph |
| `←`, `→`, `Space` in outline | Fold or move to parent, unfold or enter child, toggle the current branch |
| `/`, `Esc` | Search content with ancestry, clear search or return along navigation history |
| `Enter` | Graph: read the node; outline: inspect its parent edge; relation list/reader: follow the linked node |
| `u`, `r`, `Tab`, `d` | Select evidence's claim uses or all incident relations, read full direction/rationale, return to node detail |
| `1`, `2`; `[`, `]` | Switch Argument/Evidence uses views; previous/next observation in Evidence uses |
| `g` | Jump from a shared reference to its primary occurrence; `Esc` returns |
| `v`, `b` | Switch two/three layouts or main/alternative reasoning views |
| `z` | Switch comfortable/compact spacing, retaining research context |
| `s`, then `1`/`2`/`3`; `i` | Preview supports/challenges/inconclusive for an unrun plan; revisit impact |
| `s`, then `0` | Clear the hypothetical preview |
| `e`, `Tab`, `Ctrl+S`, `Esc` | Edit judgment/reason, change field, keep in this session, or cancel edits |
| `;`, arrows, `Enter`, `Esc` | Choose named contextual actions, inspect availability, open or return |
| `Ctrl+O` inside judgment editing | Read full recorded subject context; Esc/Ctrl+O returns without changing text, cursor or undo |
| `n`, `Enter`, `Ctrl+S`, `Esc` | Edit a personal node note, add a line, keep in this session, or cancel edits |
| `N`, `E`; `Ctrl+_`, `Ctrl+Y` | Resume cancelled note/judgment editing; undo/redo editor text |
| `U` | List unfinished writing across nodes and branches, then Enter to resume |
| `Ctrl+Z`, then shell `fg` | Suspend with shell input modes restored; resume the same live editor |
| `Ctrl+L` | Redraw the screen without changing selection or an active editor buffer |
| `m`, `p` | Inspect writing context/text comparison or recorded human/AI contributions |
| `PgUp`/`PgDn`, `?`, `q` | Scroll, show keys, return to the shell |

Try this continuous loop: use `/obs-1` to find the pruning observation, `2`
to put it above its two direct claims, and `u` to choose a use. `Enter` follows
it and `Esc` returns. `1` restores the argument view. Use `s` then `2` to see
the hypothetical pruning review path and the comparison claim outside that
path. Press `e`, enter a judgment and reason,
then `Ctrl+S`; switch layouts with `v` and inspect the original contribution
history with `p`. Press `q`; a nonempty draft or note requires an explicit discard
choice in default volatile mode. With `--draft-file`, `q` saves and exits.
`Ctrl+C` exits with code 130, attempting a checkpoint when recovery is enabled.
Use `Ctrl+Z` and shell `fg`, or an existing terminal multiplexer, to issue
experiment commands in the same environment; the app itself executes none.
Sessions without shell job control, including a direct remote command whose
process group is the session group, refuse suspend and suggest an interactive
shell or multiplexer. This avoids stopping a process with no `fg` path back.

The paper service supplies all nodes, relationships and scenario results.
Drafts and personal notes are branch/node-bound, with the recovery option above; no
research record, manuscript or experiment artifact is written. The recorded-AI
variant displays frozen provenance; the TUI does not yet connect the separate
offline-AI draft/adoption service. The paper fixture has no manuscript source:
`m` labels that absence, and any displayed diff compares argument text with a
session draft, not an actual file patch.

```sh
python3.13 -m unittest discover -s tests/application -p 'test_tui*.py'
python3.13 scripts/verify.py --scope core
```

The terminal tests launch the real program in a PTY, exercise 256/eight-color
and monochrome paths, density and complete relationship reading, inject Unicode
and bracketed paste, resize, return to canonical shell input, and exercise
normal exit/interrupt/noninteractive errors. They do not establish physical Korean
IME composition, screen-reader access, live SSH latency/disconnection, Linux
runtime support, durable resumption or a protected server deployment. The
[terminal oracle](../validation/cases/saturation.md#103-terminal-prototype-oracle)
owns acceptance and the living design records remaining UX questions.

## Interactive synthetic Episode Review

From the repository root with the existing Python 3.13 runtime:

```sh
python3.13 -m claimbranch doctor --json
python3.13 -m claimbranch demo saturation --json
python3.13 -m claimbranch demo saturation --audit recorded
python3.13 -m claimbranch demo review
python3.13 -m claimbranch demo review --example
```

`doctor` reports personal-alpha prerequisites separately and returns 0 when that
path is available; it returns 3 for missing prerequisites. Protected acceptance,
manuscript writes/compile and live transport remain unavailable. The two replay variants
return exit 0 only after matching their candidate goldens. Audit output is
explicitly `unverified-candidate`, not a signed backup or H0 evidence. Invalid
CLI arguments return 2, runtime/fixture failure returns 1 with JSON on stderr,
and interruption returns 130. No command installs dependencies, asks for native
authentication, creates a sandbox container or contacts a provider.

`demo review` launches one stdlib server on an OS-selected `127.0.0.1` port and
opens the default browser. Use `--no-open` to copy its printed address yourself;
the fragment carries a one-use bootstrap, valid for 120 seconds. The browser
clears that fragment, exchanges it for an HttpOnly SameSite cookie, and uses
exact Host/Origin and CSRF checks. Mutations require the current session
revision, so a stale tab cannot overwrite newer work. The session lasts 15
minutes. Plain HTTP lacks the production Secure-cookie/OS boundary: this is an
explicitly synthetic prototype, not the approved H1 authority surface.

Start with a blank judgment and reason. You can continue manually, or review
the exact bounded request and load the fixed example AI reply. It is not
generated for your prompt and nothing goes to an endpoint. Bringing it into
the draft retains AI provenance after later human edits. Before previewing an
AI-influenced merge, explicitly answer the contextual question or defer it.
Selected/required/omitted changes, impact paths, original/edited contributions,
and escaped manuscript candidates are inspectable. Result preview describes
conditional manuscript/understanding debt; actual approval is unavailable.
Only a selected interpretation with a dependency path to the manuscript anchor
can supply a wording candidate. A plan-only selection keeps the original text
and identifies manuscript impact review separately from a proposed text edit.
The bounded merge contract still proposes an anchor-review debt; it does not
infer that new wording exists or that a compiler ran.

For the populated argument/evidence/experiment example, use `--example` or
choose **예시 논증·실험 불러오기** in a blank session, then **연결 그래프**.
It reuses the recorded manual judgment and adds one explicitly illustrative
follow-up experiment objective. The eight-node graph exposes completed fixture
experiment, three observations, claim, interpretation, manuscript anchor and
unrun plan. Click a node or follow an inspector link to see its original text
and relationships. Scientific edges, structural links, unrun plans and omitted
changes use distinct labels/styles. The application does not execute a new
experiment or accept the example. Existing draft input cannot be overwritten
by the example action. Editing text or selection clears the current drawing
until **선택한 변경 검토** regenerates it from the core's closure.

Drafts survive request cancellation, review expiry and a browser reload while
the same server session is live. They do not survive process exit or session
expiry. Adopting an AI proposal retains the most recent displaced text/reason
buffer, including an unfinished human draft, under **AI 제안을 가져오기 전 초안**.
It can be copied back into the editor; AI influence remains in the contribution
chain. This recovery buffer is volatile and is not a completed human Judgment.
A second-tab conflict requires inspecting/preserving current local
input before refreshing; the browser never silently overwrites it. Changed
drafts invalidate request consent and prepared review. Each prepared review
lasts 120 seconds; re-review uses the entered reason. Ctrl+C stops the server.
Do not enter real research or secrets. There is no private-project import,
durable recovery, signed restore, actual compiler or live-provider configuration.

Verify the portable lifecycles, context boundary and connected application:

```sh
python3.13 -m unittest tests.contract.test_lifecycles tests.security.test_context_egress -v
python3.13 -m unittest discover -s tests/application -v
python3.13 scripts/verify.py --scope core
```

For an opt-in real-browser smoke, point to an already installed Chrome:

```sh
python3.13 -m scripts.check_review_browser --chrome "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

It uses a temporary profile and local synthetic server, then closes both. The
1440/390-pixel runs cover manual and AI flows, plan-only wording exclusion,
Not now, cancellation, preserved
contributions, same-session reload, literal hostile provider text, keyboard
activation, focus and horizontal reflow. A second session at each width checks
the populated graph, keyboard relationship navigation, stale/omitted changes
and literal hostile text. Optional `--screenshots` takes an existing output
directory and writes review, argument-graph and experiment-inspector PNGs from
the real browser. This is not a full keyboard audit, VoiceOver/NVDA
evaluation, clean-machine onboarding, or H0/H1 completion. No browser or
package is installed by the command.

## Synthetic A1–A4 integration demo

Run the complete disposable integration on Mac or another supported Python
3.10+ host, without a provider, LaTeX, or Windows enrollment:

```sh
python -B -m scripts.authority_demo
python -B -m scripts.authority_demo --format json
python -m unittest tests.probes.test_authority_flow tests.probes.test_frozen_provider tests.contract.test_authority_demo -v
```

On the development Mac with Homebrew Python 3.13, use `python3.13` when
`python` resolves to an older interpreter. The demo has no project-path or
endpoint option. It verifies the committed saturation fixture, runs manual
and frozen-proposal histories, and removes only its own temporary sandbox.
The original fixture is unchanged. The paper association is fixed for the
lifetime of this integration; its API rejects rebinding an approval or recorded
patch to another paper. The workspace copy stays outside the
synthetic paper's Git directory; the temporary root must also be outside Git.

Each history binds the judgment, evidence, selected fixture changes and exact
manuscript bytes to a synthetic attempt. One transaction records the operation,
uniquely consumes its attempt and advances the expected head. Reopening and an
identical retry return the existing record. The demo then applies and restores
the manuscript copy. The JSON result includes the recorded rationale, separate
proposal provenance (`accepted: false`), and graph projection reconstructed
from the recorded selection. Tests kill child processes before/after commit,
after apply/restore intent, and after file replacement; recovery preserves
unexpected edits. Late/cancelled/malformed proposal output cannot write these
records or files, and manual continuation remains available.

This is a synthetic integration experiment, not the `claimbranch` product CLI
or completed H0. Its callback merely matches the synthetic challenge and is
forgeable; the real-signature assertion tests above remain a separate check.
SQLite and fixture copies are unencrypted and caller-accessible. The probe
does not establish private IPC, OS identity/isolation, trusted signing keys,
power-loss durability or protection against hostile concurrent filesystem
changes. Compiler verification and debt closure remain false. No live provider
is supported or contacted. The [active integration scope](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#mac-synthetic-a1a4-integration-increment)
tracks the remaining production and Windows gates.

## Read-only graph walkthrough

Inspect the fixed synthetic case now, without configuring AI or a workspace:

```powershell
python -B -m scripts.graph_demo show
python -B -m scripts.graph_demo show --view main
python -B -m scripts.graph_demo diff
python -B -m scripts.graph_demo preview --select relation:O-03
python -B -m scripts.graph_demo preview --select claim-status --select interpretation --select relation:O-03
python -B -m scripts.graph_demo diff --format json
```

Run from the repository root. `show` defaults to the candidate view; `main`
and `candidate` are calculated fixture views, not saved research branches.
The Korean presentation retains scientific statements and rationales in their
original fixture language. `diff` lists the five selectable changes. Repeat
`--select` to combine changes; without it, `preview` keeps the initial view.
Selecting the compression relationship does not silently select the competing
interpretation, claim-status change, or the other relationships.

Preview lists selected and omitted changes, required existing records, and
explicit paths to the manuscript anchor. These are structural review paths,
not proof of scientific causality or production merge validity. No path means
no recorded path, not no possible scientific impact. Both views retain the
same observations; this command does not accept evidence or copy it into a
branch. Every invocation verifies the existing fixture integrity first.

This contributor prototype writes no research state, journal, approval, or
manuscript and makes no provider call. It accepts no project, input-file,
output-file, or apply option. Successful `--format json` output is one
deterministic UTF-8 document with `applied: false`; invalid input exits 2 with
an error on stderr and no success output. It is not the planned installed
`claimbranch` CLI, full H0 demo, or a decision about the final UI. Run its
tests with `python -m unittest tests.contract.test_graph_demo -v`.
The [bounded increment](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#read-only-graph-cli-continuity-increment)
owns its remaining gates and retirement point.

## Storage and isolation probes

Run the synthetic storage and Windows-isolation experiments without research
data or Notion access:

```powershell
python -m unittest discover -s tests/probes -p "test_*.py" -v
```

The storage experiment creates and cleans up only probe-prefixed temporary
sandboxes. Its project factory selects distinct project locations under an explicitly
supplied external root and binds later operations to that project identity;
it does not select a production data directory or association format.
Its temporary root must be writable and outside every Git working tree. If
the operating system's default temporary directory is inside a Git tree,
select an existing non-Git temporary directory through `TMP`/`TEMP` for the
test process only; do not weaken the location check or change machine settings.
An unavailable directory-link capability is reported as a skipped test, not
verified protection. The augmented storage test passes the exact synthetic
first-pass judgment through the existing store, kills a real child process
before/after commit, and checks reopen/retry without a second entry or manuscript
modification. The SQLite backend is disposable experimental code, not
the application stack. The two process-exit cut points do not prove power-loss,
initialization-crash, concurrent-writer, or adversarial filesystem-race safety.
See the [bounded probe plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#source-independent-storage-probe)
for its scope and retirement gate. This suite is currently a local check, not
a configured CI job.

Run only the Windows isolation checks:

```powershell
python -m unittest tests.probes.test_windows_isolation -v
```

This separate experiment uses existing Windows APIs and the installed .NET
Framework C# compiler to run a tiny trusted file-access helper, not a model or
application. The ordinary helper must write fake accepted state and manuscript
text, read a fake signing secret, and write a proposal. A real AppContainer
helper must receive access-denied errors for the first three while still
writing the proposal; launch failure is not a successful denial. Protected
bytes must remain unchanged after the restricted run.

It uses the same non-Git temporary-root requirement, rejects reparse-point
topology, and changes filesystem ACLs only on its newly created sandbox.
Windows also creates a uniquely named per-user AppContainer profile with
OS-managed folders/registry storage; the probe deletes only the exact profile
it successfully created and removes its sandbox. An unsupported OS skips the
real Windows test. Missing compiler or Windows setup/runtime/cleanup failure
fails rather than skips. Host termination can prevent cleanup; never infer a
completed result from an interrupted run or sweep other profiles/directories.

The [isolation probe plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#windows-isolation-probe)
owns its evidence and limits. It proves neither model-server isolation,
network/IPC confinement, human presence, receipt issuance, nor general sandbox
escape resistance. No .NET, Python, or AppContainer production-stack choice is
made by using this disposable helper. The suite remains a local check, not CI.

### A2 Windows authorization capability check

From the repository root, inspect the candidate platform prerequisites:

```powershell
python -B -m scripts.probes.windows_authorization --check
python -m unittest discover -s tests/probes -p "test_windows_authorization.py" -v
```

This read-only probe loads the system WebAuthn library and queries its API
version and platform-authenticator availability. It never enrolls a device,
lists or creates credentials, opens an approval prompt, signs, issues a receipt,
or accesses research state. All reports retain `authorization_verified: false`.
API version 4 is only the investigation floor for a later experiment that must
delete its own disposable credential; it is not a product runtime selection.
The [primary API references](../references/windows-local-trust-and-recovery.md#foreground-authorization-candidate)
and [A2 plan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md#a2-demonstrate-a-real-foreground-authorization-boundary)
own the rationale and remaining gates.

Exit 0 / `available` means these capability prerequisites were observed, never
that authorization passed. Exit 3 reports `unsupported` on other OSes or
`unavailable` when a prerequisite is absent. Exit 1 / `error` means a Windows
API or DLL failure, not a successful access denial. The real Windows test is
skipped elsewhere; simulated outcomes test reporting only. Actual user
approval/cancellation, protected keys and IPC, signed review binding, and
receipt consumption remain unimplemented and unverified. This suite is a
local check, not CI.

### Notion helper checks

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
skill's deterministic query/create projection and update denial. It is offline and uses
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
