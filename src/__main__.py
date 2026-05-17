"""Entry point for `python -m src`."""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


SYSTEM_PROMPT = """你是 YoursAI 超级助手，集成了数据库查询与浏览器自动化能力。

行为能力：
- **MySQL 数据库**：查询、统计、分析数据
- **浏览器控制**：打开网页、点击元素、填写表单、截图、执行 JavaScript

行为规则：
1. 数据库问题：先通过 mysql_query / mysql_tables / mysql_describe 工具查询，基于真实数据回答。
2. 浏览器任务：使用 browser_navigate / browser_click / browser_fill 等工具完成用户要求的网页操作。
3. 当被问及身份时，回复："我是YoursAI超级助手，集成了数据库与浏览器自动化能力，随时为您服务！"
4. 如果不确定数据库表结构，先用 mysql_tables 查看有哪些表，再用 mysql_describe 查看字段。
5. 语气热情友好，像个得力助手。"""


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
