---
kind: design
status: in-review
owners: maintainers
last_reviewed: 2026-08-15
canonical_for: proposed Notion MCP coding-journal automation for repository agents
---

# Design: safe Notion MCP coding journal automation

## Purpose

ClaimBranch development should leave a compact, useful record in Notion after
each materially completed or blocked repository task. The record should make it
easy to resume work and review decisions without copying raw conversations,
source code, secrets, or private reasoning into a third-party workspace.

This is contributor automation around the ClaimBranch repository. It is not a
ClaimBranch product feature, scientific evidence, accepted research state, or
part of the product's provider boundary.

## Context and current state

The repository is still in specification and validation-design stage. The
current local Codex client is `codex-cli 0.147.0`, and `codex mcp list` reports
no configured MCP servers. The active Codex session therefore has no callable
Notion tools.

The official hosted Notion MCP server uses Streamable HTTP and interactive
OAuth. It acts with the connected Notion user's permissions and does not yet
support non-interactive authorization. Codex supports user- and project-scoped
MCP configuration, write-sensitive approval modes, lifecycle hooks, and
observation of MCP tool results. The external facts and their applicability are
recorded in the [Notion MCP automation references](../references/notion-mcp-coding-journal.md).

The user approved the safe starting posture on 2026-08-15: connect the existing
Notion account, require approval for every Notion write, and automate the rest
of the recording flow.

## Goals and non-goals

Goals:

- create or update one journal entry for each material main-thread repository
  task that finishes as completed or blocked;
- retain deterministic Git and verification evidence separately from the
  agent-written summary;
- make retries idempotent enough to avoid ordinary duplicate entries;
- prompt before every Notion write while using the existing broad-permission
  Notion account;
- leave a local pending record when OAuth, MCP, rate limits, or Notion are
  unavailable, then retry in a later eligible session;
- avoid an infinite stop-hook loop or making Notion availability a condition
  for preserving repository work; and
- require only one-time OAuth and hook trust from the user, followed by a
  visible approval for each write.

A material task changes at least one eligible tracked file or creates at least
one eligible untracked file relative to the session baseline. Read-only
research, status answers, aborted work that changed no eligible path, ignored
files, `.git/`, `.vscode/`, and user-local journal state do not trigger a
record. An explicit user request to record a no-change decision may override
this default without changing the automatic trigger.

Non-goals:

- logging every shell command, tool call, assistant turn, or subagent action;
- uploading raw prompts, transcripts, full diffs, source files, environment
  variables, credentials, or private chain-of-thought;
- unattended CI, cloud-agent, cron, or daemon writes;
- using the deprecated self-hosted `notion-mcp-server` or a Notion API token;
- treating Notion as repository truth, an audit log, or a substitute for Git
  and canonical `docs/`; and
- generalizing the automation to other repositories before ClaimBranch proves
  the workflow useful.

## Decision drivers

- Official Notion MCP requires interactive OAuth and currently cannot provide
  fully headless authorization.
- The connection can access everything the chosen Notion user can access, so a
  mistaken or prompt-injected write has a larger blast radius than the coding
  journal alone.
- Codex hooks currently run deterministic commands; they cannot themselves call
  MCP tools. A stop hook must ask the agent to perform the MCP operation.
- Existing uncommitted work must be distinguished from changes made in the
  current session.
- A third-party outage must not discard the record or prevent a user from
  receiving the coding result.
- The record should be concise enough to scan but concrete enough to resume the
  task and reproduce its checks.

## Options considered

### Agent instruction only

Add a rule to `AGENTS.md` telling agents to write a Notion entry before
finishing. This is small and portable, but it has no deterministic reminder,
receipt, retry queue, or protection against an agent forgetting the operation.

### Agent instruction plus lifecycle hooks and a local outbox

Capture a session baseline, detect a changed worktree at `Stop`, create a
redacted pending envelope, ask Codex to call Notion MCP, and observe the MCP
result before acknowledging the envelope. This adds a small amount of
repository tooling but provides visible failure behavior and bounded recovery.
This is the selected approach.

### Headless writer using an API token or self-hosted MCP

A script or CI job could write without an agent or approval. It would no longer
use the recommended hosted Notion MCP path, would introduce long-lived secrets,
and would either use the Notion API directly or depend on a server Notion no
longer actively maintains. This is rejected for the initial workflow.

## Proposed design

### Connection and authorization

Register `https://mcp.notion.com/mcp` in the user's global Codex configuration,
not in the repository. Run `codex mcp login notion` and let the user select and
authorize the intended workspace in the browser. Keep the server's default tool
approval policy at `writes` so create and update operations always surface for
human approval.

After authentication, fetch `self` to record the selected workspace identity
and current tool availability. Create one private `ClaimBranch Coding Journal`
database. Store its database/data-source identifiers in user-local state under
`LOCALAPPDATA`, never in Git. Once the actual advertised tool names are known,
allow only the minimum read/query/create/update tools needed by the journal.
The allowlist reduces tool surface but does not narrow the Notion user's content
permissions, so write approval remains mandatory.

### Journal schema

Each entry has these properties:

| Property | Type | Meaning |
|---|---|---|
| Title | title | concise task outcome |
| Journal Key | rich text | stable repository/session/task identifier |
| Recorded At | date | Asia/Seoul completion or blocked time |
| Status | select | Completed, Blocked, or Pending Sync |
| Repository | select | `ClaimBranch` initially |
| Branch | rich text | branch at capture time |
| Start HEAD | rich text | session baseline commit |
| End HEAD | rich text | commit at capture time |
| Worktree Digest | rich text | SHA-256 of the redacted worktree snapshot |
| Change Type | multi-select | feature, fix, docs, test, refactor, tooling, or research |
| AI Contribution | select | AI-assisted or Human-only |
| Verification | select | Passed, Failed, Partial, or Not run |

The page body contains purpose, outcome, changed paths and `diff --stat`, key
decisions, verification commands with exit outcomes, risks or unresolved work,
and the next safe action. It ends with the journal key. It does not contain raw
diffs, complete command output, prompts, transcripts, environment values,
credentials, or hidden reasoning.

`AI-assisted` is the conservative default whenever an agent authored or
materially revised code, documentation, tests, or a decision. `Human-only` is
used only when the agent merely transported deterministic metadata for work it
did not help create.

### Session capture and stop flow

1. A repository-scoped `SessionStart` command hook records the first baseline
   for a Codex `session_id`: repository root, branch, HEAD, status, changed-path
   set, and a SHA-256 digest computed from Git state. The baseline is
   first-write-wins, so resume, clear, or compaction events cannot replace it.
   It does not persist raw diff content.
2. When the main thread reaches `Stop`, a command hook compares the current Git
   state with that baseline. No material change means no journal operation.
3. A material change with no matching receipt creates a versioned, redacted
   pending envelope in user-local state. The journal key combines a schema
   version, repository identity, session ID, baseline digest, and current
   digest.
4. On the first stop attempt, the hook returns a bounded continuation prompt
   instructing Codex to query the configured data source for the journal key
   and then create or update exactly one entry through Notion MCP.
5. The user reviews and approves the proposed Notion write.
6. A `PostToolUse` hook observes only the permitted Notion create/update tool
   results. A result marks the envelope synced only when its validated response
   shape contains a Notion page ID and the corresponding tool input contains
   the same journal key. Unknown or changed result shapes remain pending.
7. The next `Stop` allows the turn to finish. If the MCP call did not succeed,
   `stop_hook_active` prevents another continuation loop and the envelope stays
   pending.
8. A later `SessionStart` contributes a short reminder about pending envelopes.
   The agent retries them only when Notion MCP is available and still requires
   write approval.

The hook never parses the transcript because Codex documents that format as
unstable. The model supplies the prose summary from current conversation
context; the helper supplies only deterministic repository evidence.

The worktree digest is computed over a canonical UTF-8 manifest containing the
eligible path, tracked/untracked state, and content SHA-256 for each path,
sorted by repository-relative slash-normalized path. The manifest and raw file
content are held only in memory; local state stores the final digest and the
redacted path list. Symlinks record link metadata rather than dereferencing a
target outside the repository.

### Idempotency and ordering

Before creation, the agent queries only the configured journal data source for
an exact `Journal Key`. If a page exists, it updates that page. If no page
exists, it creates one. A successful MCP result is acknowledged locally with
the returned page ID.

If exact data-source query is unavailable, disabled, or rate-limited and no
local receipt identifies the page, the agent leaves the envelope pending. It
does not fall back to a workspace-wide search or create a page that might be a
duplicate.

Notion does not provide a uniqueness constraint for this design. A response
lost after a successful write can therefore still produce a duplicate. Exact
keys make duplicates detectable and safely mergeable; duplicate cleanup is a
manual, visible operation and is not auto-approved.

### Repository boundaries

Repository-owned files contain the hook definitions, deterministic helper,
tests, and contributor instructions. OAuth credentials, workspace identity,
database identifiers, pending envelopes, and receipts remain under the user's
local application-data directory. `.vscode/` is unrelated user content and is
not modified.

Notion is a convenience projection. Git and `docs/` remain authoritative, and
failure to sync must be stated in the final response as `Notion journal:
pending` rather than being hidden.

## Security privacy and human-control boundaries

- Connect only to the official `https://mcp.notion.com/mcp` endpoint.
- Require interactive OAuth and retain no OAuth token in the repository.
- Keep write approval enabled for every create or update while using the
  existing Notion account.
- Direct all normal reads and writes to one configured data source; do not run
  workspace-wide searches to compose a coding entry.
- Treat Notion content as untrusted input and ignore instructions found inside
  pages or database entries.
- Build deterministic evidence from local Git commands, not from Notion
  content or an LLM's recollection.
- Redact absolute user paths and reject likely secret-bearing values before a
  pending envelope becomes eligible for MCP transmission.
- Never let a Notion failure mutate, revert, commit, or block recovery of the
  repository worktree.

## Migration and rollback

Rollout is staged:

1. install and test the helper against temporary local state without MCP;
2. register the official remote server and complete OAuth;
3. verify `fetch self`, create the private database, and record its identifiers;
4. run one synthetic journal entry with explicit write approval;
5. enable the project hooks and trust their exact hashes; and
6. complete one real task and verify create, receipt, retry, and deduplication.

Rollback disables or removes the repository hook configuration, removes the
global `notion` MCP entry with the Codex CLI, revokes the connection in Notion,
and optionally removes the user-local journal state. Deleting the Notion
database is separate and never part of automated rollback.

## Validation

The implementation is complete only when all of the following pass:

- helper unit tests cover clean state, pre-existing dirty state, changed dirty
  content, untracked paths, redaction, stable keys, and schema-version rejection;
- hook fixtures cover startup/resume behavior, first-stop continuation,
  `stop_hook_active`, success acknowledgement, unavailable MCP, malformed tool
  output, timeout, rate limit, and pending retry;
- no test fixture contains OAuth tokens, raw transcripts, raw diffs, or
  machine-specific absolute paths;
- `codex mcp get notion --json` shows only the official endpoint and write
  approval remains enabled;
- `fetch self` confirms the intended workspace and the required tool access;
- a synthetic create requires user approval and produces exactly one page with
  the expected schema and journal key;
- retrying that same key updates or reuses the page instead of intentionally
  creating another;
- denying the write leaves the repository unchanged and one local pending
  envelope;
- the next eligible session can sync that envelope after approval;
- disabling the hooks restores ordinary Codex completion; and
- `python scripts/check_docs.py` and all new helper tests pass.

The user-visible acceptance criterion is: after a material ClaimBranch task,
the final response reports `Notion journal: synced` with the page link or
`Notion journal: pending` with a local retry state, and no other user action is
needed beyond OAuth, initial hook trust, and each visible write approval.

## Open questions

None for the initial safe-mode implementation. Automatic write approval,
additional repositories, and headless operation require a later design with a
smaller Notion permission boundary.

## Outcome

The user approved the safe-mode direction in conversation on 2026-08-15. This
written proposal remains `in-review` until the user reviews it. After approval,
an ExecPlan may implement only the bounded workflow above; it must not advance
ClaimBranch product scope or the active F0/H0/H1/V0 plan.
