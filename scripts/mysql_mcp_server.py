#!/usr/bin/env python
"""
MCP server for MySQL — launched as a subprocess by the AI Agent.
Connection config is read from environment variables (loaded from .env).
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure project root is on path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    print("请先安装 pymysql: pip install pymysql", file=sys.stderr)
    sys.exit(1)

from mcp.server import Server
import mcp.server.stdio
import mcp.types as types

server = Server("mysql-agent")


def get_conn():
    print(os.environ.get("MYSQL_HOST", "localhost"))
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DATABASE", ""),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="mysql_query",
            description="执行 SQL 查询（仅支持 SELECT 语句），返回查询结果列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT 查询语句",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="mysql_tables",
            description="列出当前数据库中所有表名",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="mysql_describe",
            description="查看指定表的字段结构",
            inputSchema={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "表名",
                    },
                },
                "required": ["table"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    conn = None
    try:
        conn = get_conn()

        if name == "mysql_query":
            query = arguments["query"].strip().rstrip(";")
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
            return [types.TextContent(type="text", text=json.dumps(rows, ensure_ascii=False, default=str))]

        elif name == "mysql_tables":
            with conn.cursor() as cur:
                cur.execute("SHOW TABLES")
                rows = cur.fetchall()
            tables = [list(r.values())[0] for r in rows]
            return [types.TextContent(type="text", text=json.dumps(tables, ensure_ascii=False))]

        elif name == "mysql_describe":
            with conn.cursor() as cur:
                cur.execute(f"DESCRIBE `{arguments['table']}`")
                rows = cur.fetchall()
            return [types.TextContent(type="text", text=json.dumps(rows, ensure_ascii=False, default=str))]

        else:
            raise ValueError(f"未知工具: {name}")

    except Exception as e:
        return [types.TextContent(type="text", text=f"数据库错误: {e}")]
    finally:
        if conn:
            conn.close()


async def main():
    async with mcp.server.stdio.stdio_server() as (read, write):
        await server.run(
            read,
            write,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
