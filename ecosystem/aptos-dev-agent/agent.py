"""Interactive aptos-core development agent built on the Claude Agent SDK.

The agent can explore this repository with read-only built-in tools and query
an Aptos node's REST API through a small in-process MCP server.
"""

import argparse
import asyncio
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NODE_URL = os.environ.get("APTOS_NODE_URL", "http://127.0.0.1:8080")

SYSTEM_PROMPT = """\
You are a development assistant for the aptos-core repository (Rust node
implementation and Move framework of the Aptos blockchain).

- Answer questions about the code by reading it; cite files as path:line.
- Use the aptos_* tools when the user asks about live chain state (ledger
  info, accounts, resources, modules, transactions).
- You are read-only: do not modify files or run commands that change state.
- Reply in the language the user writes in.
"""

ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{1,64}$")
TXN_ID_RE = re.compile(r"^(0x[0-9a-fA-F]{64}|\d+)$")


def _text(payload: str, is_error: bool = False) -> dict:
    result = {"content": [{"type": "text", "text": payload}]}
    if is_error:
        result["is_error"] = True
    return result


def _get(path: str) -> dict:
    """GET a path from the configured node and wrap the JSON as a tool result."""
    url = DEFAULT_NODE_URL.rstrip("/") + path
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return _text(f"HTTP {e.code} from {url}: {e.read().decode(errors='replace')}", True)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return _text(f"Request to {url} failed: {e}", True)
    return _text(json.dumps(body, indent=2)[:50_000])


def _check_address(address: str) -> dict | None:
    if not ADDRESS_RE.match(address):
        return _text(f"Invalid address: {address!r} (expected 0x-prefixed hex)", True)
    return None


@tool("ledger_info", "Get the node's current ledger info (chain id, version, timestamp).", {})
async def ledger_info(args):
    return _get("/")


@tool("account", "Get an account's sequence number and authentication key.", {"address": str})
async def account(args):
    return _check_address(args["address"]) or _get(f"/accounts/{args['address']}")


@tool("account_resources", "List the Move resources stored under an account.", {"address": str})
async def account_resources(args):
    return _check_address(args["address"]) or _get(f"/accounts/{args['address']}/resources")


@tool("account_modules", "List the Move modules published under an account.", {"address": str})
async def account_modules(args):
    return _check_address(args["address"]) or _get(f"/accounts/{args['address']}/modules")


@tool("transaction", "Get a transaction by hash (0x...) or by version number.", {"id": str})
async def transaction(args):
    if not TXN_ID_RE.match(args["id"]):
        return _text(f"Invalid transaction id: {args['id']!r}", True)
    return _get(f"/transactions/{args['id']}")


APTOS_TOOLS = [ledger_info, account, account_resources, account_modules, transaction]


def build_options(model: str | None) -> ClaudeAgentOptions:
    aptos = create_sdk_mcp_server(name="aptos", version="0.1.0", tools=APTOS_TOOLS)
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        cwd=str(REPO_ROOT),
        model=model,
        mcp_servers={"aptos": aptos},
        allowed_tools=["Read", "Glob", "Grep"] + [f"mcp__aptos__{t.name}" for t in APTOS_TOOLS],
        # Anything not in allowed_tools (Bash, Edit, Write, ...) is refused.
        permission_mode="dontAsk",
        max_turns=40,
    )


async def print_response(client: ClaudeSDKClient) -> None:
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text, flush=True)
                elif isinstance(block, ToolUseBlock):
                    print(f"  [{block.name}] {json.dumps(block.input, ensure_ascii=False)}", flush=True)
        elif isinstance(message, ResultMessage):
            cost = f"${message.total_cost_usd:.4f}" if message.total_cost_usd is not None else "n/a"
            status = "error: " + message.subtype if message.is_error else "done"
            print(f"\n({status}, {message.num_turns} turns, {cost})\n", flush=True)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="*", help="one-shot prompt; omit for interactive chat")
    parser.add_argument("--model", default=None, help="model alias or id (default: SDK default)")
    args = parser.parse_args()

    async with ClaudeSDKClient(options=build_options(args.model)) as client:
        if args.prompt:
            await client.query(" ".join(args.prompt))
            await print_response(client)
            return

        print(f"aptos-dev-agent (repo: {REPO_ROOT}, node: {DEFAULT_NODE_URL}). Ctrl-D to quit.")
        while True:
            try:
                prompt = input("> ").strip()
            except EOFError:
                break
            if prompt:
                await client.query(prompt)
                await print_response(client)


if __name__ == "__main__":
    asyncio.run(main())
