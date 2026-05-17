import json
import os
from collections.abc import Callable
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def load_config(path: str = "mcp_servers.json") -> dict:
    if not Path(path).exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("servers", {})


def to_anthropic_tool(mcp_tool) -> dict:
    return {
        "name": mcp_tool.name,
        "description": mcp_tool.description or "",
        "input_schema": mcp_tool.inputSchema,
    }


def format_content(content_list) -> str:
    parts = []
    for item in content_list:
        if hasattr(item, "text") and item.text:
            parts.append(item.text)
        else:
            parts.append(str(item))
    return "\n".join(parts)


async def connect_server(name: str, cfg: dict) -> dict | None:
    """Connect to a single stdio MCP server.

    Returns {name, session, tools, cleanup} where cleanup is a list of
    no-argument coroutine factories for orderly teardown.
    """
    if cfg.get("type") != "stdio":
        print(f"  [..] {name}: 不支持的连接类型 '{cfg.get('type')}'")
        return None

    # Merge full parent env + config-specific overrides.
    # MCP SDK's get_default_environment() uses a whitelist that drops
    # custom vars (MYSQL_HOST, etc.), so we pass os.environ explicitly.
    server_env = cfg.get("env") or {}

    params = StdioServerParameters(
        command=cfg["command"],
        args=cfg.get("args", []),
        env={**os.environ, **server_env},
    )

    streams_cm = stdio_client(params)
    streams = await streams_cm.__aenter__()
    read, write = streams

    session_cm = ClientSession(read, write)
    session = await session_cm.__aenter__()
    await session.initialize()

    tools_result = await session.list_tools()

    async def _cleanup():
        for cm in (session_cm, streams_cm):
            try:
                await cm.__aexit__(None, None, None)
            except Exception:
                pass

    return {
        "name": name,
        "session": session,
        "tools": tools_result.tools,
        "cleanup": _cleanup,
    }
