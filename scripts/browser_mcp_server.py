#!/usr/bin/env python
"""
MCP server for browser automation — powered by Playwright.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
import mcp.server.stdio
import mcp.types as types

from playwright.async_api import async_playwright

server = Server("browser-agent")
_browser = None
_page = None


async def get_page():
    global _browser, _page
    if _page is None:
        p = await async_playwright().__aenter__()
        _browser = await p.chromium.launch(headless=False)
        _page = await _browser.new_page()
    return _page


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="browser_navigate",
            description="打开一个网页，返回页面标题和文本内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "要访问的 URL"},
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="browser_click",
            description="点击页面上的元素（通过 CSS 选择器定位）",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS 选择器"},
                },
                "required": ["selector"],
            },
        ),
        types.Tool(
            name="browser_fill",
            description="在输入框中填入文本",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS 选择器"},
                    "value": {"type": "string", "description": "要填入的文本"},
                },
                "required": ["selector", "value"],
            },
        ),
        types.Tool(
            name="browser_get_text",
            description="获取页面上元素的文本内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS 选择器，不传则返回整个页面文本"},
                },
            },
        ),
        types.Tool(
            name="browser_screenshot",
            description="保存页面截图到文件",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "截图保存路径，默认 screenshot.png"},
                },
            },
        ),
        types.Tool(
            name="browser_evaluate",
            description="在页面中执行 JavaScript 代码",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要执行的 JavaScript 代码"},
                },
                "required": ["code"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        page = await get_page()

        if name == "browser_navigate":
            await page.goto(arguments["url"], wait_until="domcontentloaded")
            title = await page.title()
            text = await page.evaluate("document.body.innerText.slice(0, 3000)")
            return [types.TextContent(type="text", text=f"标题: {title}\n\n页面内容:\n{text}")]

        elif name == "browser_click":
            await page.click(arguments["selector"])
            return [types.TextContent(type="text", text=f"已点击: {arguments['selector']}")]

        elif name == "browser_fill":
            await page.fill(arguments["selector"], arguments["value"])
            return [types.TextContent(type="text", text=f"已填入 {len(arguments['value'])} 字符到 {arguments['selector']}")]

        elif name == "browser_get_text":
            sel = arguments.get("selector")
            if sel:
                el = await page.query_selector(sel)
                text = await el.inner_text() if el else "元素未找到"
            else:
                text = await page.evaluate("document.body.innerText.slice(0, 5000)")
            return [types.TextContent(type="text", text=text)]

        elif name == "browser_screenshot":
            path = arguments.get("path", "screenshot.png")
            await page.screenshot(path=path, full_page=True)
            return [types.TextContent(type="text", text=f"截图已保存: {path}")]

        elif name == "browser_evaluate":
            result = await page.evaluate(arguments["code"])
            return [types.TextContent(type="text", text=str(result))]

        else:
            raise ValueError(f"未知工具: {name}")

    except Exception as e:
        return [types.TextContent(type="text", text=f"浏览器错误: {e}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read, write):
        await server.run(
            read,
            write,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
