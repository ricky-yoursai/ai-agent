# YoursAI 超级助手 — DeepSeek × MySQL MCP

基于 DeepSeek Anthropic 兼容 API 的数据库 AI Agent，通过 MCP 连接 MySQL，专注于数据查询与分析。

> 我是 **YoursAI 超级助手**，专注于数据库查询与分析，随时为您服务！

## 目录结构

```
├── agent.py                 # 兼容入口：python agent.py
├── pyproject.toml           # 项目元数据与依赖声明
├── requirements.txt         # pip 依赖
├── run.ps1                  # 一键启动脚本 (Windows)
│
├── src/                     # 源代码包
│   ├── __init__.py
│   ├── __main__.py          # 入口 + 行为约束系统提示词
│   ├── agent.py             # MCPAgent 核心类（对话循环）
│   ├── tools.py             # 内置文件工具
│   └── mcp.py               # MCP 服务器加载与通信
│
├── scripts/
│   └── mysql_mcp_server.py  # MySQL MCP 服务器（自定义 Python）
│
├── mcp_servers.json         # MCP 服务器配置
├── .env                     # 项目配置（API Key + MySQL 连接信息）
├── .gitignore
│
├── env/                     # Python 虚拟环境
└── .claude/
    └── settings.local.json
```

## 前置要求

- Python 3.11+
- DeepSeek API Key（[申请地址](https://platform.deepseek.com/)）
- MySQL 数据库（本地或远程均可）

## 快速开始

### 1. 创建虚拟环境

```powershell
python -m venv env
```

### 2. 安装依赖

```powershell
.\env\Scripts\python -m pip install -r requirements.txt
```

### 3. 配置 API Key 和数据库连接

编辑项目根目录下的 `.env` 文件：

```ini
# DeepSeek 配置
ANTHROPIC_API_KEY=sk-你的deepseek-key

# MySQL 数据库连接（按需填写）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的密码
MYSQL_DATABASE=你的数据库名
```

### 4. 启动

```powershell
.\run.ps1
```

或：

```powershell
.\env\Scripts\python -m src
```

## 使用示例

启动后进入交互模式，Agent 会自动连接 MySQL 并探索表结构：

```
> 这个数据库里有哪些表？
>
> 查看 users 表的结构
>
> 查询最近 10 条订单记录
>
> 统计每个分类的商品数量
```

### 非数据库问题

Agent 会自动拒绝回答无关问题：

```
> 今天天气怎么样？
暂无法回答，我是专注于数据库的 YoursAI 超级助手，请问您想查询什么数据？
```

### 身份询问

```
> 你是谁？
我是YoursAI超级助手，专注于数据库查询与分析，随时为您服务！
```

## 行为规则

Agent 受系统提示词约束，行为规则如下：

1. **只回答数据库相关问题** — 查询、统计、分析等
2. **非数据库问题** → 统一回复："暂无法回答..."
3. **身份问题** → "我是YoursAI超级助手，专注于数据库查询与分析，随时为您服务！"
4. **回答前先查库** — 自动探索表结构，基于真实数据回答
5. **语气热情友好** — 像个得力助手

## 自定义 MCP 服务器

如果需要额外的 MCP 服务器（文件系统、GitHub 等），编辑 `mcp_servers.json` 添加即可。

本项目的 MySQL MCP 服务器是自定义 Python 实现，无需 Node.js，直接通过 `pymysql` 连接数据库。

## 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_BASE_URL` | API 端点 | `https://api.deepseek.com/anthropic` |
| `ANTHROPIC_API_KEY` | DeepSeek API 密钥 | （必填） |
| `MODEL` | 模型名 | `deepseek-v4-flash` |
| `MYSQL_HOST` | 数据库主机 | `localhost` |
| `MYSQL_PORT` | 数据库端口 | `3306` |
| `MYSQL_USER` | 数据库用户 | `root` |
| `MYSQL_PASSWORD` | 数据库密码 | （空） |
| `MYSQL_DATABASE` | 数据库名 | （必填） |

## 开发

### 可编辑安装

```powershell
.\env\Scripts\python -m pip install -e .
```

安装后可在任意路径通过 `agent` 命令启动。

## 常见问题

**MySQL 连接失败？**  
检查 `.env` 中的数据库配置是否正确，确认 MySQL 服务是否运行。确保 MySQL 允许从当前主机连接。

**控制台输出乱码？**  
Agent 会自动切换 UTF-8。仍有问题则运行前执行：
```powershell
$env:PYTHONIOENCODING="utf-8"
```

**如何更换模型？**  
修改 `.env` 中的 `MODEL` 值，可选 `deepseek-v4-pro` 或 `deepseek-v4-flash`。

**不想用 MySQL 了？**  
将 `mcp_servers.json` 内容改为 `{"servers": {}}` 即可禁用所有 MCP 服务器。
