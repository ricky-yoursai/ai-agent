from pathlib import Path

BUILTIN_TOOLS = [
    {
        "name": "read_file",
        "description": "读取指定文件的内容",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "文件路径"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "写入内容到指定文件（会覆盖已有内容）",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "要写入的内容"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "列出目录中的文件和子目录",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目录路径，默认为当前目录"}
            },
        },
    },
]

TOOL_NAMES = {t["name"] for t in BUILTIN_TOOLS}


def execute(name: str, args: dict) -> str:
    if name == "read_file":
        path = Path(args["path"])
        if not path.exists():
            return f"文件不存在: {path}"
        return path.read_text(encoding="utf-8")

    if name == "write_file":
        path = Path(args["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")
        return f"已写入 {len(args['content'])} 字符到 {path}"

    if name == "list_files":
        path = Path(args.get("path", "."))
        if not path.is_dir():
            return f"目录不存在: {path}"
        items = []
        for f in path.iterdir():
            items.append(f"[{'D' if f.is_dir() else 'F'}] {f.name}")
        return "\n".join(items) if items else "(空目录)"

    return f"未知的内置工具: {name}"
