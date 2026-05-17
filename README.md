# AI Agent with MCP — DeepSeek × Anthropic API

基于 DeepSeek Anthropic 兼容 API 的 AI Agent，支持 MCP（Model Context Protocol）工具扩展。

## 目录结构

```
├── agent.py                 # 兼容入口：python agent.py
├── pyproject.toml           # 项目元数据与依赖声明
├── requirements.txt         # pip 依赖
├── run.ps1                  # 一键启动脚本 (Windows)
│
├── src/                     # 源代码包
│   ├── __init__.py
│   ├── __main__.py          # 入口：python -m src
│   ├── agent.py             # MCPAgent 核心类（对话循环）
│   ├── tools.py             # 内置工具定义与执行
│   └── mcp.py               # MCP 服务器加载与通信
│
├── mcp_servers.json         # MCP 服务器配置
├── .env                     # 项目配置（API Key 等）
├── .gitignore
│
├── env/                     # Python 虚拟环境
└── .claude/
    └── settings.local.json  # Claude Code 自身配置
```

## 前置要求

- Python 3.11+
- DeepSeek API Key（[申请地址](https://platform.deepseek.com/)）
- （可选）Node.js 18+ — MCP 服务器需要

## 快速开始

### 1. 创建虚拟环境

```powershell
python -m venv env
```

### 2. 安装依赖

```powershell
.\env\Scripts\python -m pip install -r requirements.txt
```

### 3. 配置 API Key

编辑项目根目录下的 `.env` 文件，填入你的 DeepSeek API Key：

```
ANTHROPIC_API_KEY=sk-你的真实key
```

> `ANTHROPIC_BASE_URL` 和 `MODEL` 已预填，通常无需修改。

### 4. 启动

```powershell
.\run.ps1
```

或直接：

```powershell
.\env\Scripts\python -m src
```

也保留向下兼容：

```powershell
.\env\Scripts\python agent.py
```

## 使用示例

启动后进入交互模式，直接输入问题：

```
> Python 的装饰器是什么？
>
> 用 read_file 读取当前目录下的 README.md
>
> 把 "Hello Agent" 写入 test.txt
>
> quit
```

## 内置工具

无需额外配置。

| 工具 | 说明 |
|------|------|
| `read_file` | 读取文件内容 |
| `write_file` | 写入文件（会覆盖） |
| `list_files` | 列出目录中的文件 |

## MCP 服务器扩展

MCP（Model Context Protocol）让 Agent 可以使用外部数据库、GitHub API、浏览器等工具。

### 前提

安装 Node.js（[下载地址](https://nodejs.org/)）。

### 配置

编辑 `mcp_servers.json`，添加需要的服务器：

```json
{
  "servers": {
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    }
  }
}
```

重新启动 Agent 即可自动加载。

### 常用 MCP 服务器

| 服务器 | 用途 | 命令 |
|--------|------|------|
| `@modelcontextprotocol/server-filesystem` | 文件系统操作 | `npx -y @modelcontextprotocol/server-filesystem .` |
| `@modelcontextprotocol/server-github` | GitHub API | `npx -y @modelcontextprotocol/server-github` |
| `@modelcontextprotocol/server-postgres` | PostgreSQL 数据库 | `npx -y @modelcontextprotocol/server-postgres` |
| `@modelcontextprotocol/server-sqlite` | SQLite 数据库 | `npx -y @modelcontextprotocol/server-sqlite` |
| `@modelcontextprotocol/server-puppeteer` | 浏览器自动化 | `npx -y @modelcontextprotocol/server-puppeteer` |

## 开发

### 可编辑安装

在项目目录下执行，之后可以在任意路径通过 `agent` 命令启动：

```powershell
.\env\Scripts\python -m pip install -e .
```

## 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_BASE_URL` | API 端点 | `https://api.deepseek.com/anthropic` |
| `ANTHROPIC_API_KEY` | API 密钥 | （必填） |
| `MODEL` | 模型名 | `deepseek-v4-pro` |

> DeepSeek 会将不支持的模型名自动映射到 `deepseek-v4-flash`。

## 常见问题

**MCP 服务器连接失败？**  
检查是否已安装 Node.js（`node --version`）。不需要 MCP 时保持 `mcp_servers.json` 内容为 `{"servers": {}}`。

**控制台输出乱码？**  
Agent 会自动将 stdout 切换为 UTF-8。仍有问题则在运行前执行：
```powershell
$env:PYTHONIOENCODING="utf-8"
```

**如何更换模型？**  
修改 `.env` 中的 `MODEL` 值，例如 `MODEL=deepseek-v4-flash`。
