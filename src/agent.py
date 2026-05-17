from anthropic import AsyncAnthropic

from . import mcp, tools

TOOL_NAMES = tools.TOOL_NAMES


class MCPAgent:
    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-v4-pro", system_prompt: str | None = None):
        self.client = AsyncAnthropic(api_key=api_key, base_url=base_url)
        self.model = model
        self.system_prompt = system_prompt
        self.servers: dict[str, dict] = {}
        self._cleaners: list = []

    async def connect_servers(self, config: dict):
        if not config:
            return
        print(f"正在连接 {len(config)} 个 MCP 服务器...")
        for name, cfg in config.items():
            try:
                result = await mcp.connect_server(name, cfg)
                if result:
                    self.servers[name] = {
                        "session": result["session"],
                        "tools": result["tools"],
                    }
                    self._cleaners.append(result["cleanup"])
            except Exception as e:
                print(f"  [..] {name}: {e}")

    def get_all_tools(self) -> list[dict]:
        all_tools = list(tools.BUILTIN_TOOLS)
        seen = {t["name"] for t in all_tools}
        for srv in self.servers.values():
            for t in srv["tools"]:
                if t.name not in seen:
                    seen.add(t.name)
                    all_tools.append(mcp.to_anthropic_tool(t))
        return all_tools

    def _find_server(self, tool_name: str) -> str | None:
        for name, srv in self.servers.items():
            for t in srv["tools"]:
                if t.name == tool_name:
                    return name
        return None

    async def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        if tool_name in TOOL_NAMES:
            return tools.execute(tool_name, arguments or {})

        server = self._find_server(tool_name)
        if not server:
            return f"错误: 工具 '{tool_name}' 不可用"

        result = await self.servers[server]["session"].call_tool(tool_name, arguments or {})
        return mcp.format_content(result.content)

    async def run(self, user_input: str) -> str:
        messages = [{"role": "user", "content": user_input}]
        all_tools = self.get_all_tools()

        while True:
            res = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=all_tools,
                messages=messages,
            )

            if res.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": res.content})
                results = []
                for block in res.content:
                    if block.type == "tool_use":
                        result = await self._execute_tool(block.name, block.input)
                        results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(result)})
                messages.append({"role": "user", "content": results})
            else:
                return "".join(b.text for b in res.content if b.type == "text") or "(无文本回复)"

    async def shutdown(self):
        for cleanup in reversed(self._cleaners):
            await cleanup()
        self._cleaners.clear()
        self.servers.clear()
