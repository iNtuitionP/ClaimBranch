---
kind: reference
status: active
owners: maintainers
last_reviewed: 2026-08-15
canonical_for: external evidence for the Notion MCP coding-journal automation proposal
---

# Notion MCP coding-journal references

Reviewed 2026-08-15. These sources inform the contributor-automation proposal;
they do not make the automation implemented behavior.

## Primary sources

- [Notion MCP connection guide](https://developers.notion.com/guides/mcp/get-started-with-mcp)
- [Notion MCP supported tools](https://developers.notion.com/guides/mcp/mcp-supported-tools)
- [Notion MCP security best practices](https://developers.notion.com/guides/mcp/mcp-security-best-practices)
- [Notion MCP help and administration](https://www.notion.com/help/notion-mcp)
- [OpenAI Codex MCP configuration](https://developers.openai.com/codex/mcp)
- [OpenAI Codex lifecycle hooks](https://learn.chatgpt.com/docs/hooks)

## Findings and applicability

Notion's hosted, actively maintained endpoint is
`https://mcp.notion.com/mcp`. The Codex setup uses a `notion` MCP entry and
`codex mcp login notion`. Authentication is interactive OAuth; Notion does not
currently support non-interactive authorization for the hosted server. The
deprecated open-source server can use bearer tokens but is not the recommended
foundation for new automation.

The hosted server exposes workspace identity and tool availability through
`fetch self`. Relevant tools can fetch a database or data source, create and
update pages, create a database, and query a configured data source. Tool
availability and quotas can vary by workspace plan, so bootstrap must inspect
the live `current_tool_access` result rather than assume every optional query
surface is unlimited.

Notion states that a connected MCP client acts with the permissions of the
connected user. It also warns that content read through MCP can contain prompt
injection and recommends confirmation before changes. The initial ClaimBranch
workflow therefore keeps write approval enabled, avoids workspace-wide search,
uses a direct configured data-source identifier, and treats all Notion content
as untrusted.

Official OpenAI documentation says local Codex clients share MCP configuration,
support Streamable HTTP with OAuth, and allow server/tool approval policy. It
also documents project and user configuration layers.

Codex lifecycle hooks can observe session start, stop, and supported MCP tool
calls. A `Stop` hook can continue the agent with a new prompt, and `PostToolUse`
receives MCP tool input and output. Current hook handlers are deterministic
commands only, so the hook cannot write Notion itself. This requires a split
design: a local command prepares and tracks a redacted envelope, while the
agent performs the user-approved MCP operation.
