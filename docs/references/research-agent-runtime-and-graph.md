---
kind: reference
status: active
owners: maintainers
last_reviewed: 2026-08-14
canonical_for: external research on personal-agent runtimes, graph retrieval, and local inference serving
---

# Research-agent runtime, graph, and local-serving references

Reviewed 2026-08-14. These sources inform ClaimBranch's boundaries; they do not
make an integration or technology implemented truth.

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

These sources support:

- [ADR 0006](../architecture/decisions/0006-three-graph-planes-and-provider-boundary.md);
- the conditional OpenClaw, GraphRAG, storage, and serving triggers in the
  [active ExecPlan](../plans/active/2026-08-04-claimbranch-v1-and-gpu-systems.md);
  and
- the provider-neutral, proposal-only behavior in the
  [product specification](../product/product-spec.md).
