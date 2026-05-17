"""Web server for AI Agent — FastAPI + WebSocket chat interface."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from . import mcp as mcp_util
from .agent import MCPAgent

HERE = Path(__file__).parent


def _make_agent() -> MCPAgent:
    return MCPAgent(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        base_url=os.getenv("ANTHROPIC_BASE_URL"),
        model=os.getenv("MODEL", "deepseek-v4-flash"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent = _make_agent()
    config = mcp_util.load_config()
    if config:
        await agent.connect_servers(config)
    tools = agent.get_all_tools()
    print(f"  Agent 就绪: {len(tools)} 个工具")
    app.state.agent = agent
    yield
    await agent.shutdown()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


@app.get("/")
async def index():
    return FileResponse(HERE / "static" / "index.html")


@app.websocket("/chat")
async def chat(ws: WebSocket):
    await ws.accept()
    agent: MCPAgent = app.state.agent
    try:
        while True:
            msg = await ws.receive_text()
            answer = await agent.run(msg)
            await ws.send_text(answer)
    except WebSocketDisconnect:
        pass
