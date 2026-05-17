"""
Aurora AI Chat Server
Serves the company website + WebSocket that dispatches browser commands
to the Chrome extension for execution in the user's actual browser.
"""
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

load_dotenv()

PORT = int(os.getenv("CHAT_PORT", "8080"))
HOST = os.getenv("CHAT_HOST", "0.0.0.0")
WEB_DIR = Path(__file__).parent

app = FastAPI()

# ── Session state ───────────────────────────────────────────
# session_id -> {"ws": WebSocket, "pending": Event, "result": str, "busy": bool}
sessions = {}


# ── Tool definitions (Anthropic tool format) ────────────────
TOOLS = [
    {
        "name": "browser_navigate",
        "description": "在浏览器中打开一个新网页（当前页面跳转或新标签页）",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "要访问的完整 URL"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "browser_click",
        "description": "点击页面上的元素，支持 CSS 选择器或文本内容查找",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS 选择器或元素上的可见文本，例如: #submit, button, .class, '提交', '确定'"},
            },
            "required": ["selector"],
        },
    },
    {
        "name": "browser_fill",
        "description": "在输入框中填入文本",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS 选择器定位输入框"},
                "value": {"type": "string", "description": "要填入的文本"},
            },
            "required": ["selector", "value"],
        },
    },
    {
        "name": "browser_select",
        "description": "选择下拉框中的某个选项",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "select 元素的 CSS 选择器"},
                "value": {"type": "string", "description": "要选中的 option value"},
            },
            "required": ["selector", "value"],
        },
    },
    {
        "name": "browser_get_text",
        "description": "获取页面上元素的文本内容，不传 selector 则获取整个页面",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS 选择器，可选"},
            },
        },
    },
    {
        "name": "browser_scroll",
        "description": "滚动页面",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["down", "up"], "description": "滚动方向"},
                "amount": {"type": "integer", "description": "像素值，默认 500"},
            },
            "required": ["direction"],
        },
    },
    {
        "name": "browser_evaluate",
        "description": "在页面中执行 JavaScript 代码并返回结果",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "要执行的 JavaScript 代码"},
            },
            "required": ["code"],
        },
    },
]


SYSTEM_PROMPT = """你叫 Aurora，是一个运行在浏览器中的 AI 助手。

## 你的能力
你可以控制用户当前正在浏览的网页——点击按钮、填写表单、滚动页面、获取内容、跳转页面。
所有操作都在用户的真实浏览器中执行，用户可以看到每一步。

## 工作流程
1. 收到用户指令后，先理解用户当前在什么页面上
2. 按步骤操作浏览器，每一步都向用户说明你的计划
3. 操作完成后，总结结果告诉用户

## 操作守则
- 打开页面后，先获取页面文本内容了解页面结构
- 点击元素时，优先使用可见文本定位（比如 '搜索'、'提交'），其次使用 CSS 选择器
- 如果需要登录或验证码，告诉用户需要手动操作
- 始终用中文回复，语气热情专业
"""


# ── Agent loop: sends commands to extension, waits for results ──
async def process_chat(session_id: str, msg: dict):
    session = sessions.get(session_id)
    if not session:
        return
    session["busy"] = True

    client = AsyncAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        base_url=os.getenv("ANTHROPIC_BASE_URL"),
    )

    # Build initial context with current page info
    context_parts = [msg["content"]]
    if msg.get("url") and msg["url"] != "about:blank":
        context_parts.insert(0, f"[当前页面: {msg.get('title', '')}]({msg.get('url')})")
    if msg.get("pageContent"):
        context_parts.insert(1, f"\n页面内容:\n{msg['pageContent']}")

    messages = [{"role": "user", "content": "\n\n".join(context_parts)}]

    try:
        while True:
            response = await client.messages.create(
                model=os.getenv("MODEL", "deepseek-v4-flash"),
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            text_parts = [b.text for b in response.content if b.type == "text" and b.text]
            tool_calls = [b for b in response.content if b.type == "tool_use"]

            if text_parts:
                await send_ws(session, {"type": "thinking", "content": "\n".join(text_parts)})

            if not tool_calls:
                await send_ws(session, {"type": "done"})
                break

            messages.append({"role": "assistant", "content": response.content})
            results = []

            for tool in tool_calls:
                cmd_id = str(uuid.uuid4())
                await send_ws(session, {
                    "type": "command",
                    "id": cmd_id,
                    "action": tool.name,
                    "params": tool.input,
                    "session": session_id,
                })

                # Wait for result from extension
                session["pending"].clear()
                session["result"] = None

                try:
                    await asyncio.wait_for(session["pending"].wait(), timeout=120)
                except asyncio.TimeoutError:
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tool.id,
                        "content": "❌ 操作超时: 命令执行超过 120 秒",
                    })
                    continue

                if session_id not in sessions:
                    return

                result_content = session["result"] or "操作完成"
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool.id,
                    "content": result_content,
                })

            messages.append({"role": "user", "content": results})

    except Exception as e:
        try:
            await send_ws(session, {"type": "error", "content": f"服务器错误: {e}"})
        except Exception:
            pass
    finally:
        if session_id in sessions:
            sessions[session_id]["busy"] = False


async def send_ws(session, data):
    """Send JSON to the extension, handling stale connections."""
    try:
        await session["ws"].send_json(data)
    except Exception:
        pass


# ── WebSocket ───────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "ws": ws,
        "pending": asyncio.Event(),
        "result": None,
        "busy": False,
    }
    actual_id = session_id  # may change on resume

    try:
        while True:
            raw = await ws.receive_json()

            if raw["type"] == "resume":
                # Extension reconnected after page navigation
                old_id = raw.get("session", "")
                if old_id in sessions and old_id != actual_id:
                    # Transfer state to the old session
                    sessions[old_id]["ws"] = ws
                    sessions[old_id]["result"] = raw.get("content", "")
                    sessions[old_id]["pending"].set()
                    # Remove temporary session
                    if actual_id in sessions and actual_id != old_id:
                        del sessions[actual_id]
                    actual_id = old_id
                    await ws.send_json({"type": "thinking", "content": f"✅ 已恢复会话，继续操作..."})
                else:
                    await ws.send_json({"type": "error", "content": "会话已过期，请重新输入指令"})
                continue

            session = sessions.get(actual_id)
            if not session:
                break

            if raw["type"] == "chat":
                if session["busy"]:
                    await ws.send_json({"type": "error", "content": "正在处理上一个指令，请稍候..."})
                else:
                    asyncio.create_task(process_chat(actual_id, raw))

            elif raw["type"] == "result":
                session["result"] = raw.get("content", "")
                session["pending"].set()

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if actual_id in sessions:
            del sessions[actual_id]


# ── Serve HTML ──────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(WEB_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    print(f"  Aurora AI Server → http://127.0.0.1:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
