"""Entry point for `python -m src`."""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


SYSTEM_PROMPT = """你是 YoursAI 超级助手，专注于 MySQL 数据库查询与分析。

行为规则：
1. 你**只能**回答与数据库数据相关的问题（查询、统计、分析等）。
2. 对与数据库无关的问题（闲聊、非数据类问题），统一回复："暂无法回答，我是专注于数据库的 YoursAI 超级助手，请问您想查询什么数据？"
3. 当被问及身份时，回复："我是YoursAI超级助手，专注于数据库查询与分析，随时为您服务！"
4. 回答前必须先通过 mysql_query 或 mysql_tables 工具查询数据库，基于结果回答。
5. 如果你不确定表结构，先用 mysql_tables 查看有哪些表，再用 mysql_describe 查看字段。
6. 语气热情友好，像个得力助手。"""


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
    print("  YoursAI 超级助手  —  DeepSeek × MySQL MCP")
    print("=" * 55)

    agent = MCPAgent(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        base_url=os.getenv("ANTHROPIC_BASE_URL"),
        model=os.getenv("MODEL", "deepseek-v4-flash"),
        system_prompt=SYSTEM_PROMPT,
    )

    mcp_config = mcp_util.load_config()
    if mcp_config:
        await agent.connect_servers(mcp_config)

    all_tools = agent.get_all_tools()
    builtin_count = 3
    mcp_count = len(all_tools) - builtin_count
    print(f"  内置工具: {builtin_count}  |  MCP 工具: {mcp_count}  |  模型: {agent.model}\n")

    if not mcp_config:
        print("  ⚠ 未配置 MCP 服务器，数据库查询功能不可用")
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
