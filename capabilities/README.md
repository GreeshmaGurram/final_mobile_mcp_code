# Tool Capabilities Registry

This folder contains client-side capability definitions for MCP tools.

- One file per tool is stored in `tools/`.
- `index.json` maps a tool name to its capability file.
- The MCP client can select a capability from user intent and call the mapped tool with defaults + extracted slots.

## Recommended client flow

1. Load `index.json`.
2. For each capability, evaluate `when_to_use` against the user query.
3. Pick the best match.
4. Extract `required_slots` from the query (ask follow-up for missing slots).
5. Build args as `defaults` overridden by extracted slots.
6. Call the `tool_name`.

These files are an orchestration layer only; MCP tool schemas remain the source of truth.
