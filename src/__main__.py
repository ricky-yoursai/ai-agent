"""Entry point for `python -m src`."""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def _ensure_utf8():
    if sys.stdout.encoding and sys.stdout.encoding.upper() == "GBK":
        sys.stdout.reconfigure(encoding="utf-8")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _validate_env():
    missing = [
        k for k, v in [
            ("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY")),
            ("ANTHROPIC_BASE_URL", os.getenv("ANTHROPIC_BASE_URL")),
        ] if not v
    ]
    if missing:
        print(f"[错误] .env 中缺少配置: {', '.join(missing)}")
        print("请确保 .env 文件包含以下内容：")
        print("  ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic")
        print("  ANTHROPIC_API_KEY=sk-你的key")
        sys.exit(1)


async def main():
    _ensure_utf8()
    _validate_env()

    from . import mcp as mcp_util
    from .agent import MCPAgent

    print("=" * 55)
    print("  AI Agent with MCP  —  DeepSeek × Anthropic API")
    print("=" * 55)

    agent = MCPAgent(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        base_url=os.getenv("ANTHROPIC_BASE_URL"),
        model=os.getenv("MODEL", "deepseek-v4-flash"), # deepseek-v4-flash deepseek-v4-pro
    )

    mcp_config = mcp_util.load_config()
    if mcp_config:
        await agent.connect_servers(mcp_config)

    all_tools = agent.get_all_tools()
    builtin_count = 3
    mcp_count = len(all_tools) - builtin_count
    print(f"  内置工具: {builtin_count}  |  MCP 工具: {mcp_count}  |  模型: {agent.model}\n")
    print("  输入问题 (quit 退出)\n")

    try:
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if user_input.lower() in ("quit", "exit", "q"):
                break
            if not user_input:
                continue

            result = await agent.run(user_input)
            print(f"\n{result}\n")
    finally:
        await agent.shutdown()


def entry_point():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n再见！")


if __name__ == "__main__":
    entry_point()
