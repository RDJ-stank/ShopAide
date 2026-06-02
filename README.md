# ShopAide（谷雨电商智能售后 Agent）

基于 **LangChain + FastAPI + ChromaDB + Chainlit** 的电商智能售后 Copilot。

Agent 能够自主调用后端工具（查询物流、修改地址），并结合本地 RAG 知识库检索退换货政策，回答用户的售后问题。

---

## 架构概览

```
用户 → Chainlit(UI) → AgentExecutor → Tools ─→ repository ─→ SQLite
                 ↓                        ↓
         流式输出 + 多轮记忆        RAG 检索 ─→ ChromaDB
                                    ↑
                              FastAPI(server.py) ── REST API 对外开放
```

| 层级 | 技术 | 文件 |
|------|------|------|
| UI 层 | Chainlit（流式 + 多轮记忆） | `app.py` |
| API 层 | FastAPI + Pydantic | `server.py` |
| Agent 层 | LangChain Tool Calling | `src/shopaide/agent/agent.py` |
| Tool 层 | `@tool` 装饰器 → repository | `src/shopaide/tools/` |
| 数据层 | SQLModel + SQLite（同步） | `src/shopaide/database/` |
| 知识层 | ChromaDB + BGE 中文 Embedding | `src/shopaide/knowledge/` |

---

## 项目结构

```
ShopAide/
├── pyproject.toml                # 项目元数据与依赖声明
├── .env.example                  # 环境变量模板（LLM 提供商 + API Key）
├── .gitignore
├── README.md
│
├── app.py                        # Chainlit 聊天入口（流式输出 + 多轮记忆）
├── server.py                     # FastAPI REST API 入口
├── .chainlit/
│   └── config.toml               # Chainlit UI 配置
│
├── src/shopaide/
│   ├── __init__.py
│   ├── config.py                 # 全局配置（.env → LLM 参数）
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   └── agent.py              # Agent 构建 + SYSTEM_PROMPT
│   │
│   ├── tools/
│   │   ├── __init__.py           # 工具汇总 + init_db() 启动挂载
│   │   ├── order_tools.py        # 业务工具：查询物流 / 修改地址
│   │   └── knowledge_tool.py     # RAG 工具：search_return_policy
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py             # Order 表 + OrderStatus 枚举
│   │   ├── session.py            # 同步引擎 + init_db() 种子数据 + get_session()
│   │   └── repository.py         # 数据访问：get_order_by_id / update_order_address
│   │
│   └── knowledge/
│       ├── __init__.py
│       ├── policies.py           # 退换货政策文本（6 条规则）
│       └── vector_store.py       # ChromaDB 向量存储 + retriever
│
└── tests/
    ├── __init__.py
    ├── test_agent.py             # Phase 1 工具调用集成测试（4 场景）
    └── test_rag.py               # Phase 2 RAG 检索测试（4 场景）
```

---

## 系统验证步骤

### 前提条件

- Python >= 3.11
- 有效的 LLM API Key（支持 DeepSeek / 通义千问 / OpenAI）

### 第 1 步：安装依赖

```bash
cd ShopAide
pip install -e ".[dev]"
```

### 第 2 步：配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，根据你的 LLM 提供商填写：

```ini
# 三选一：deepseek / qwen / openai
LLM_PROVIDER=deepseek
OPENAI_API_KEY=sk-你的真实key
```

> `LLM_PROVIDER=deepseek` 会自动设置 `base_url=https://api.deepseek.com/v1` 和 `model=deepseek-chat`，无需手动填写。

### 第 3 步：验证数据库层

```bash
python -c "
from shopaide.database.session import init_db, get_session
from shopaide.database.repository import get_order_by_id, update_order_address

init_db()
with get_session() as s:
    order = get_order_by_id(s, 'GY10086')
    print(f'订单 {order.order_id}: {order.recipient} - {order.status}')
    print('数据库层验证通过')
"
```

预期输出：

```
订单 GY10086: 张三 - 运输中
数据库层验证通过
```

### 第 4 步：验证 Agent 工具调用（4 个测试场景）

```bash
python tests/test_agent.py
```

预期输出：

```
============================================================
  ShopAide Phase 1 — Tool Calling 闭环验证
============================================================

============================================================
【测试 1 — 查询物流】
============================================================
订单 GY10086 的物流信息如下：...

============================================================
【测试 2 — 修改地址】
============================================================
已成功修改订单 GY10086 的收货地址...

============================================================
【测试 3 — 不存在的订单】
============================================================
未找到订单号为 GY99999 的订单...

============================================================
【测试 4 — 越权拒绝】
============================================================
抱歉，我无法协助进行任何非法活动...

✅ 全部测试完成
```

### 第 5 步：验证 RAG 知识检索（4 个测试场景）

```bash
python tests/test_rag.py
```

> 首次运行会自动下载 BAAI/bge-small-zh-v1.5 嵌入模型（约 100MB），后续启动复用缓存。

预期输出：

```
============================================================
  ShopAide Phase 2 — RAG 知识检索验证
============================================================

============================================================
【测试 1 — 向量库构建 + 检索测试】
============================================================
✅ 向量库构建 + 检索测试通过

============================================================
【测试 2 — Agent + RAG：退货政策问答】
============================================================
✅ Agent + RAG 政策问答测试通过

============================================================
【测试 3 — Agent + RAG：退款时效问答】
============================================================
✅ Agent + RAG 退款时效问答测试通过

============================================================
【测试 4 — Agent + RAG：特殊商品不可退】
============================================================
✅ Agent + RAG 特殊商品问答测试通过

✅ 全部 RAG 测试完成
```

### 第 6 步：验证 FastAPI REST 接口

启动服务器：

```bash
uvicorn server:app --reload --port 9090
```

另开终端，逐条验证：

```bash
# 健康检查
curl http://localhost:9090/api/health
# → {"status":"ok"}

# 查询订单
curl http://localhost:9090/api/orders/GY10086
# → {"order_id":"GY10086","status":"运输中","carrier":"顺丰速运",...}

# 查询不存在的订单
curl http://localhost:9090/api/orders/GY99999
# → 404 — {"detail":"订单 GY99999 不存在"}

# 修改地址
curl -X PUT http://localhost:9090/api/orders/GY10086/address \
  -H "Content-Type: application/json" \
  -d '{"new_address":"浙江省杭州市西湖区"}'
# → {"success":true,"message":"地址修改成功",...}

# 尝试修改已签收订单（应被拒绝）
curl -X PUT http://localhost:9090/api/orders/GY10010/address \
  -H "Content-Type: application/json" \
  -d '{"new_address":"北京"}'
# → 400 — {"detail":"订单 GY10010 当前状态为「已签收」，不支持修改地址。"}
```

或使用 Python 一键验证：

```bash
python -c "
import requests
BASE = 'http://localhost:9090'
assert requests.get(f'{BASE}/api/health').json() == {'status': 'ok'}
assert requests.get(f'{BASE}/api/orders/GY10086').status_code == 200
assert requests.get(f'{BASE}/api/orders/GY99999').status_code == 404
assert requests.put(f'{BASE}/api/orders/GY10086/address', json={'new_address':'杭州'}).json()['success']
assert requests.put(f'{BASE}/api/orders/GY10010/address', json={'new_address':'北京'}).status_code == 400
print('All API tests passed')
"
```

### 第 7 步：启动 Chainlit 聊天界面

```bash
chainlit run app.py
```

浏览器打开 `http://localhost:8000`，尝试以下对话：

| 测试输入 | 预期行为 |
|----------|----------|
| "帮我查一下订单 GY10086 的物流" | Agent 调用 `query_order_status`，返回物流详情 |
| "把 GY10086 的地址改成广州" | Agent 调 `modify_shipping_address`，返回修改结果 |
| "我买的东西签收 5 天了还能退吗" | Agent 调 `search_return_policy`，基于政策原文回答 |
| "护肤品拆开了能退吗" | Agent 调 `search_return_policy`，告知不可退 |
| "刚才那个订单现在到哪了" | 多轮记忆生效，Agent 能理解"刚才"指 GY10086 |

---

## API 接口一览

| 方法 | 路径 | 说明 | 成功 | 失败 |
|------|------|------|------|------|
| GET | `/api/health` | 健康检查 | 200 `{"status":"ok"}` | — |
| GET | `/api/orders/{order_id}` | 查询订单详情 | 200 Order JSON | 404 `{"detail":"..."}` |
| PUT | `/api/orders/{order_id}/address` | 修改收货地址 | 200 `{"success":true,...}` | 400 `{"detail":"..."}` |

---

## Agent 拥有的工具

| 工具名 | 功能 | 数据来源 |
|--------|------|----------|
| `query_order_status` | 查询订单物流状态与详情 | SQLite → repository |
| `modify_shipping_address` | 修改收货地址（含状态校验） | SQLite → repository |
| `search_return_policy` | 检索退换货政策与售后规则 | ChromaDB 向量库 |

---

## 技术决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据库 | SQLite + SQLModel（同步） | MVP 零配置，单文件，后续可换 PostgreSQL |
| 向量库 | ChromaDB（本地持久化） | 嵌入式运行，无需额外服务 |
| Embedding | BAAI/bge-small-zh-v1.5 | 中文检索 SOTA 轻量模型，本地 CPU 推理 |
| LLM 连接 | 兼容 OpenAI API 协议 | 一套代码支持 DeepSeek / Qwen / OpenAI |
| 流式输出 | AsyncLangchainCallbackHandler | Chainlit 原生支持，token 级渲染 |
| 对话记忆 | cl.user_session + chat_history | Chainlit 会话天然隔离，比 LangChain Memory 更轻量 |
| ORM 与 API Schema | 分离（Pydantic v2） | 数据层与接口层解耦，互不影响 |
