---
kind: reference
status: active
owners: maintainers
last_reviewed: 2026-10-12
canonical_for: external research on personal-agent runtimes, graph retrieval, and local inference serving
---

# Research-agent runtime, graph, and local-serving references

Runtime/graph sources reviewed 2026-08-14; the personal-provider configuration
sources below were inspected 2026-10-10. These inform ClaimBranch's boundaries; they do not
make an integration or technology implemented truth.

## Contextual conversation and selected graph actions

Reviewed 2026-10-12 against official documentation and the primary VISAR paper.
This is source inspection, not hands-on product validation or a dependency
selection. The [workspace design review](../designs/2026-09-22-episode-review.md#contextual-conversation-and-small-edit-proposals)
owns the proposed application to ClaimBranch.

| Source | Observed mechanism | What to borrow / boundary |
|---|---|---|
| [VISAR, sections 4.3.1–4.3.3](https://arxiv.org/html/2304.07810v2) | Users select text and add it to the graph, directly edit nodes/edges, and select suggested counterarguments before reviewing the outline. Text and graph selections highlight their counterparts. | Closest interaction reference for selective incorporation. Its tree-based essay outline and generated evidence suggestions do not establish empirical observations, shared-evidence semantics or research authority. |
| [tldraw agent starter](https://tldraw.dev/starter-kits/agent) | Context parts and action utilities are separate. Each action supplies its schema, validation, application and presentation; stale/nonexistent shape references may cancel an action. Modes narrow available capabilities. | Reuse separation of reading and small operations. The starter also modifies the canvas during generation; ClaimBranch must stage proposals and retain human recording instead. This is not a reason to replace the TUI with a canvas SDK. |
| [Tana Outliner AI Chat](https://outliner.tana.inc/learn/features/ai-chat), [AI Agents](https://outliner.tana.inc/learn/features/ai-agents) | Chat can start from a node; node references supply context. Agent commands appear below chat and operate in the originating node's context. Referencing a tree includes its descendant nodes. | Borrow object-bound conversation and explicit follow-up commands. Do not copy automatic subtree disclosure or optional background startup requests into ClaimBranch's reviewed-context boundary. |
| [CopilotKit v2 human input hook](https://docs.copilotkit.ai/reference/v2/hooks/useHumanInTheLoop) | An interactive tool pauses for a custom confirmation/form UI and resumes through a user-response callback. Its parameter schema and UI are separate from ordinary prose. | Borrow editable action cards and explicit responses. A UI callback alone does not prove exact scientific scope, stale-state refusal or authority; those remain application checks. No React dependency is selected. |
| [OpenClaw execution approvals](https://docs.openclaw.ai/tools/exec-approvals) | An approval-backed execution binds concrete command/context and rechecks applicable identities; allow-once differs from durable policy. Documentation explicitly limits approvals' security guarantees. | Borrow explicit pending-action review and rechecking. This is command-execution infrastructure, not a scientific graph or ClaimBranch authority implementation; no shell, general tools or gateway is admitted. |

Inference from these patterns: conversation can remain readable independently
of an optional, narrowly typed edit proposal. They do not prove this will improve
ClaimBranch research, eliminate malformed edits or resolve its observed L04
failure. Validate that outcome locally, then through the actual selected service.

## OpenClaw

Primary sources:

- [OpenClaw repository](https://github.com/openclaw/openclaw)
- [Getting started](https://docs.openclaw.ai/getting-started)
- [Gateway protocol](https://docs.openclaw.ai/gateway/protocol)
- [Operator scopes](https://docs.openclaw.ai/gateway/operator-scopes)
- [Memory](https://docs.openclaw.ai/concepts/memory)
- [Context](https://docs.openclaw.ai/concepts/context)
- [Local models](https://docs.openclaw.ai/gateway/local-models)
- [Execution approvals](https://docs.openclaw.ai/tools/exec-approvals)

The relevant product pattern is not a particular model. OpenClaw combines a
short onboarding path, an always-available assistant experience, a durable
gateway/control plane, existing communication surfaces, skills/tools, memory,
provider replacement, and explicit execution controls. This reduces the cost
of returning to the assistant and lets integrations accumulate around one
runtime.

ClaimBranch should reuse or integrate with that runtime only after live use
shows repeated transfer friction. Its distinctive responsibility is scientific
authority: accepted evidence, branchable reasoning, contribution provenance,
understanding debt, and manuscript consequences. Rebuilding OpenClaw's channel,
daemon, plugin, or general agent platform inside ClaimBranch would delay that
wedge and create a second control plane.

OpenClaw's local-model guidance also cautions that smaller or heavily quantized
models can weaken context handling and security. ClaimBranch therefore treats
an 8 GB local GPU as useful for bounded structured tasks and learning, not as
evidence that one local model should control the complete research workflow.

### Personal provider configuration

The user requested that individual researchers connect their own LLM, using
OpenClaw's connection approach as a reference. Directly inspected sources:

- [Custom providers and local runtimes](https://docs.openclaw.ai/concepts/model-providers/custom-providers)
- [SecretRef contract](https://docs.openclaw.ai/gateway/secrets/secretref-contract)
- [OpenAI Chat Completions request](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [Anthropic Messages request](https://platform.claude.com/docs/en/api/messages/create)
- [vLLM OpenAI protocol source](https://docs.vllm.ai/en/stable/api/vllm/entrypoints/openai/chat_completion/protocol/)

OpenClaw separates endpoint base URL, API dialect, model IDs and authentication
references. Its SecretRef contract supports explicit secret sources rather than
requiring inline values. ClaimBranch borrows that separation, initially using
only an environment-variable name; it does not import OpenClaw credentials or
its runtime, secret execution, model router, OAuth or plugins. The smaller
ClaimBranch adapter records a complete POST endpoint instead of assembling a
route from a base URL.

OpenAI chat takes role-tagged messages and optional JSON-object mode; Anthropic
Messages separates system text from user messages and requires `max_tokens`.
JSON mode alone cannot validate ClaimBranch's scientific references or confer
authority, so both formats require the existing closed typed decoder. These
API documents establish wire shape, not compatibility or account access for an
arbitrary user-selected model. Provider retention and actual access remain
separate checks; configuration is not deployment qualification under ADR 0018.
The decoder treats null/empty tool fields as absence while refusing actual
tool-bearing output and malformed field shapes; it executes no tool. This is
an adapter rule, not an observed vLLM deployment compatibility pass.
The [implemented preparation workflow](../development/workflow.md#personal-llm-configuration-and-unsent-preview)
owns current commands and limitations.

## Graph engineering and GraphRAG

Primary sources:

- [Microsoft GraphRAG overview](https://microsoft.github.io/graphrag/index/overview/)
- [Microsoft GraphRAG getting started](https://microsoft.github.io/graphrag/get_started/)
- [Temporal memory-graph reference](https://graphrag.com/reference/knowledge-graph/memory-graph-temporal/)

GraphRAG builds derived entities, relationships, communities, summaries, and
query context from source material. Those techniques can help retrieval across
many research records, but model extraction and community summaries are not
scientific acceptance.

ClaimBranch applies graph engineering in three different planes:

- a small typed canonical graph for accepted research and authority;
- disposable retrieval/context projections; and
- append-only provider/tool execution traces.

The initial retrieval baseline is deterministic typed-neighborhood traversal
plus optional full-text search. Embeddings or GraphRAG enter only when a frozen
retrieval corpus shows recall below the active plan's threshold after bounded
tuning. A graph-native database similarly requires a correctness or measured
workload failure; the logical graph model does not mandate physical graph
storage.

## Local inference serving

Primary sources:

- [llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [llama.cpp function calling](https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md)

The server exposes OpenAI-compatible model, chat, response, embedding, schema-
constrained output, function/tool, usage, and timing surfaces. That is enough
for ClaimBranch to teach connection-level serving concepts against an already-
running endpoint: reachability, model identity, context ceiling, structured
output, cancellation, time to first token, token usage, and throughput.

ClaimBranch does not initially download models, select quantization, manage
VRAM, supervise processes, route providers, or provide fallback. A deterministic
stub and a provider add/probe/test/explain flow keep accepted-state tests
repeatable while giving the researcher a real serving-learning path after the
manual workflow works.

## Decision impact

For L04's internal asynchronous transport, Python's official
[subprocess documentation](https://docs.python.org/3.13/library/subprocess.html)
distinguishes timeout from child termination and requires deliberate cleanup.
The [HTTP client reference](https://docs.python.org/3.13/library/http.client.html)
supplies the direct bounded-read adapter, while
[SSL verification paths](https://docs.python.org/3.13/library/ssl.html#ssl.get_default_verify_paths)
distinguish default roots from environment CA overrides. The implementation
uses a short-lived same-user child for cancellation and explicitly omits CA
environment imports. These APIs establish neither provider isolation nor actual
deployment support; current behavior belongs in the
[transport workflow](../development/workflow.md#internal-asynchronous-transport).

These sources support:

- [ADR 0006](../architecture/decisions/0006-three-graph-planes-and-provider-boundary.md);
- the conditional OpenClaw, GraphRAG, storage, and serving triggers in the
  [active ExecPlan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md);
  and
- the provider-neutral, proposal-only behavior in the
  [product specification](../product/product-spec.md).
