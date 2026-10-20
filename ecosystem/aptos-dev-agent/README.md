# aptos-dev-agent

An interactive development assistant for aptos-core, built on the
[Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/python).

- Explores this repository with read-only tools (`Read`, `Glob`, `Grep`).
- Queries an Aptos node's REST API through custom tools: `ledger_info`,
  `account`, `account_resources`, `account_modules`, `transaction`.
- Cannot edit files or run shell commands (`permission_mode="dontAsk"`).

## Setup

```bash
cd ecosystem/aptos-dev-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # or log in with Claude Code
```

## Usage

```bash
# Interactive chat
python agent.py

# One-shot question
python agent.py "Where is the mempool's transaction validation implemented?"

# Point at a different node (default: http://127.0.0.1:8080)
APTOS_NODE_URL=https://fullnode.devnet.aptoslabs.com/v1 python agent.py
```

The REST paths in this repository's `api/` crate have no `/v1` prefix, so a
local node built from this tree works with the default URL. Public networks
serve the API under `/v1`; include it in `APTOS_NODE_URL`.

## Extending

Add a tool with the `@tool` decorator in `agent.py` and append it to
`APTOS_TOOLS`; it is registered and auto-allowed as `mcp__aptos__<name>`.
To let the agent edit code, add `"Edit"`/`"Write"` to `allowed_tools`.
