# ShopAide（谷雨电商智能售后 Agent）

基于 **LangChain + FastAPI + ChromaDB + Chainlit** 的电商智能售后 Copilot。

Agent 拥有 **12 个工具**，覆盖订单查询、物流轨迹、退货管理、智能判责、时效预警、发票管理、政策检索（RAG）和情绪升级，能自主从对话中识别用户意图并调用对应后端工具执行售后业务。

---

## 项目全貌

```
用户 ─→ Chainlit(UI) ─→ Agent(12 tools) ─→ repository ─→ SQLite
              │ 流式输出                      │
              │ 多轮记忆            RAG 检索 ─→ ChromaDB
              │                           ↑
        FastAPI(server.py) ─── 17 个 REST 端点
```

| 层级 | 技术栈 | 核心文件 |
|------|--------|---------|
| UI 层 | Chainlit 2.x（astream_events 流式 + session 多轮记忆） | `app.py` |
| API 层 | FastAPI + Pydantic v2 + Depends 依赖注入 | `server.py` |
| Agent 层 | LangChain Tool Calling + ChatOpenAI（兼容 DeepSeek/Qwen） | `src/shopaide/agent/agent.py` |
| Tool 层 | 12 个 `@tool` 函数，底层调用 repository | `src/shopaide/tools/` |
| 数据层 | SQLModel + SQLite 同步引擎，6 张表 | `src/shopaide/database/` |
| 知识层 | ChromaDB + BAAI/bge-small-zh-v1.5 中文 Embedding（本地） | `src/shopaide/knowledge/` |

---

## 项目结构

```
ShopAide/
├── pyproject.toml              # 项目元数据 + 所有依赖
├── .env.example                # 环境变量模板（支持 DeepSeek/Qwen/OpenAI）
├── .gitignore
├── README.md
│
├── app.py                      # Chainlit 聊天入口（流式 astream_events + 多轮记忆）
├── server.py                   # FastAPI REST API（17 个端点）
├── .chainlit/
│   └── config.toml             # Chainlit UI 配置
│
├── src/shopaide/
│   ├── __init__.py
│   ├── config.py               # LLM 多提供商预设 + 全局配置
│   │
│   ├── agent/
│   │   └── agent.py            # SYSTEM_PROMPT（含情绪识别/判责/预警规则）
│   │
│   ├── tools/
│   │   ├── __init__.py          # 12 工具注册 + init_db() 启动挂载
│   │   ├── order_tools.py       # query_order_status / modify_shipping_address
│   │   ├── return_tools.py      # submit_return_request / query_return_progress
│   │   ├── search_tools.py      # search_orders / query_product_info
│   │   ├── invoice_tools.py     # query_invoice_status / request_invoice_reissue
│   │   ├── damage_tools.py      # report_damage / check_order_alert
│   │   ├── escalation_tools.py  # escalate_to_human
│   │   └── knowledge_tool.py    # search_return_policy（RAG）
│   │
│   ├── database/
│   │   ├── models.py            # 6 张表：Order / LogisticsEvent / ReturnOrder
│   │   │                        #        Invoice / DisputeCase / Escalation
│   │   ├── session.py           # 同步引擎 + init_db() + 11 个种子用户
│   │   └── repository.py        # 13 个原子函数（含判责/预警/升级）
│   │
│   └── knowledge/
│       ├── policies.py          # 9 条售后政策（退货/保修/价保/仅退款等）
│       └── vector_store.py      # ChromaDB 向量存储 + retriever
│
└── tests/
    ├── test_agent.py             # 11 个 Agent 集成测试场景
    └── test_rag.py               # 4 个 RAG 检索测试场景
```

---

## 数据库设计（6 张表）

| 表名 | 说明 | 种子数据 |
|------|------|----------|
| `orders` | 订单主表（含商品/支付/收件人信息） | 11 条（运输中 4 / 已签收 4 / 待发货 2 / 已取消 1） |
| `logistics_events` | 物流轨迹事件表 | 15 条 |
| `return_orders` | 退货单（6 种状态） | 3 条（已完成 / 审核中 / 待寄回） |
| `invoices` | 发票（未开/已开/已申请补开） | 3 条（个人 / 企业 / 未开） |
| `dispute_cases` | 判责工单（5 种类型 × 4 种责任方） | 2 条（已解决 / 处理中） |
| `escalations` | 升级工单（情绪升级/超AI能力升级） | 按需动态创建 |

---

## Agent 12 个工具全览

### 订单与物流（3 个）

| # | 工具 | 功能 | 触发场景 |
|---|------|------|----------|
| 1 | `query_order_status` | 查订单 + 商品信息 + 完整物流轨迹 + 联系电话 | "帮我查一下 GY10086" |
| 2 | `search_orders` | 按订单号/姓名/手机号模糊搜索 | "我不记得订单号，手机号是139..." |
| 3 | `query_product_info` | 查商品 SKU/单价/数量/优惠/实付 | "GY20480 买了什么" |

### 地址与退货（3 个）

| # | 工具 | 功能 | 触发场景 |
|---|------|------|----------|
| 4 | `modify_shipping_address` | 修改收货地址（校验状态） | "把地址改成杭州" |
| 5 | `submit_return_request` | 提交退货申请（校验签收+7天窗口+防重复） | "我要退货" |
| 6 | `query_return_progress` | 查询退货进度（审核→寄回→验收→退款） | "退货到哪一步了" |

### 发票与政策（3 个）

| # | 工具 | 功能 | 触发场景 |
|---|------|------|----------|
| 7 | `query_invoice_status` | 查发票状态（未开/已开/补开中） | "开发票了吗" |
| 8 | `request_invoice_reissue` | 补开发票+修改抬头（校验已开票+防重复） | "发票抬头改成公司" |
| 9 | `search_return_policy` | RAG 检索 9 条售后政策 | "能保修吗/能价保吗" |

### 智能判责与主动服务（3 个）

| # | 工具 | 功能 | 触发场景 |
|---|------|------|----------|
| 10 | `report_damage` | 创建判责工单（自动判定责任方+分流方案+检测已有退货） | "收到的东西坏了" |
| 11 | `check_order_alert` | 时效预警（延迟发货/物流停滞/配送超时） | "怎么还没到" |
| 12 | `escalate_to_human` | 创建升级工单+转达客服热线（情绪触发/投诉触发） | "太差劲了我要投诉" |

---

## REST API 接口一览（17 个端点）

### 健康检查
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | `{"status":"ok"}` |

### 订单（6 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/orders/{order_id}` | 查询订单详情 |
| GET | `/api/orders/search?keyword=` | 多维度搜索订单 |
| GET | `/api/orders/{order_id}/logistics` | 物流轨迹 |
| GET | `/api/orders/{order_id}/products` | 商品详情 |
| GET | `/api/orders/{order_id}/alert` | 时效预警 |
| PUT | `/api/orders/{order_id}/address` | 修改地址 |

### 退货（2 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/returns/` | 提交退货申请 |
| GET | `/api/returns/{return_id}` | 查询退货进度 |

### 发票（2 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/invoices/{order_id}` | 查询发票状态 |
| POST | `/api/invoices/{order_id}/reissue` | 补开发票 |

### 判责与升级（2 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/disputes/` | 创建判责工单 |
| GET | `/api/disputes/{case_id}` | 查询判责工单 |
| POST | `/api/escalations/` | 创建升级工单 |

---

## 种子用户数据（11 个用户）

| 订单号 | 状态 | 收件人 | 手机 | 城市 | 商品 | 金额 |
|--------|------|--------|------|------|------|------|
| GY10086 | 运输中 | 张三 | 138-0000-1111 | 北京 | 春季男士运动夹克 | ¥359 |
| GY10099 | 运输中 | 赵六 | 136-0000-4444 | 成都 | 华为 MateBook 14 | ¥5,699 |
| GY10101 | 运输中 | 孙七 | 135-0000-5555 | 武汉 | SK-II 神仙水 230ml | ¥1,270 |
| GY10105 | 运输中 | 陈十一 | 131-0000-9999 | 杭州 | 三只松鼠坚果礼包 | ¥148 |
| GY10010 | 已签收 | 李四 | 139-0000-2222 | 上海 | 蓝牙降噪耳机 Pro | ¥299 |
| GY10012 | 已签收 | 刘八 | 133-0000-6666 | 南京 | Nike Air Max 270 | ¥849 |
| GY10015 | 已签收 | 周九 | 132-0000-7777 | 杭州 | 戴森 V15 吸尘器 | ¥3,590 |
| GY10102 | 已签收 | 吴十 | 134-0000-8888 | 广州 | 小米空气净化器 4 Pro | ¥1,299 |
| GY20480 | 待发货 | 王五 | 137-0000-3333 | 深圳 | 有机绿茶礼盒装 250g | ¥246 |
| GY10103 | 待发货 | 郑十二 | 130-0000-1110 | 重庆 | LEGO 兰博基尼 42115 | ¥2,799 |
| GY10104 | 已取消 | 冯十三 | 129-0000-1111 | 长沙 | Apple AirPods Pro 2 | ¥1,799 |

> GY10086 物流轨迹最后更新为 2026-05-30，距今 >48h，用于测试物流停滞预警
> GY20480 创建时间为 2026-06-01，距今 >72h，用于测试延迟发货预警
> GY10102 有退货单 RTN20260601-001（审核中），用于测试判责防重复逻辑

---

## 系统验证步骤

### 前提条件
- Python >= 3.11
- 有效的 LLM API Key（支持 DeepSeek / 通义千问 / OpenAI）

### 第 1 步：安装

```bash
cd ShopAide
pip install -e ".[dev]"
```

### 第 2 步：配置 LLM

```bash
cp .env.example .env
# 编辑 .env，填写 LLM_PROVIDER 和 OPENAI_API_KEY
```

### 第 3 步：验证数据库层

```bash
python -c "
from shopaide.database.session import init_db, get_session
from shopaide.database.repository import get_order_by_id
init_db()
with get_session() as s:
    o = get_order_by_id(s, 'GY10086')
    print(f'{o.order_id}: {o.recipient} - {o.status} - {o.item_name}')
print('OK')
"
```

### 第 4 步：运行 Agent 集成测试（11 场景）

```bash
python tests/test_agent.py
```

覆盖：查物流、搜订单、商品详情、改地址、退货申请、退货进度、发票查询、智能判责、时效预警。

### 第 5 步：运行 RAG 检索测试（4 场景）

```bash
python tests/test_rag.py
```

首次运行会下载 BAAI/bge-small-zh-v1.5 嵌入模型（约 100MB）。

### 第 6 步：验证 FastAPI

```bash
uvicorn server:app --reload --port 9090
```

```bash
# 健康检查
curl http://localhost:9090/api/health

# 搜索订单
curl "http://localhost:9090/api/orders/search?keyword=张三"

# 物流轨迹
curl http://localhost:9090/api/orders/GY10086/logistics

# 时效预警
curl http://localhost:9090/api/orders/GY20480/alert

# 判责工单
curl -X POST http://localhost:9090/api/disputes/ \
  -H "Content-Type: application/json" \
  -d '{"order_id":"GY10086","description":"包装破损","damage_type":"物流损坏"}'

# 升级工单
curl -X POST http://localhost:9090/api/escalations/ \
  -H "Content-Type: application/json" \
  -d '{"order_id":"GY10086","reason":"用户投诉","context_summary":"用户情绪激动要求转人工"}'
```

### 第 7 步：启动 Chainlit 聊天界面

```bash
chainlit run app.py
```

浏览器打开 `http://localhost:8000`，推荐测试下列对话：

| 测试输入 | 预期行为 |
|----------|----------|
| "帮我查一下 GY10099" | 流式输出：赵六 MateBook + 物流轨迹 + 商品信息 |
| "搜一下收件人叫周九的订单" | 返回 GY10015 戴森吸尘器 |
| "GY20480 怎么还没发货" | 调 check_order_alert → 延迟发货预警 + 建议 |
| "GY10010 我要退货，尺码不对" | 提示已有退货记录或提交新申请 |
| "GY10102 净化器噪音很大" | 调 report_damage → 检出 RTN20260601-001 退货单 |
| "耳机三个月了还能保修吗" | 调 search_return_policy → 检索保修政策 |
| "你们太差劲了我要投诉" | 调 escalate_to_human → 升级工单 + 客服热线 |

---

## 技术决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据库 | SQLite + SQLModel（同步） | MVP 零配置单文件，后续可换 PostgreSQL |
| 会话管理 | `contextmanager` + `Depends` 注入 | 自动 commit/rollback/close，无泄漏 |
| 向量库 | ChromaDB（本地持久化） | 嵌入式运行，无需额外服务 |
| Embedding | BAAI/bge-small-zh-v1.5 | 中文检索 SOTA 轻量模型，本地 CPU 推理 |
| LLM | OpenAI-compatible API | 一套代码支持 DeepSeek/Qwen/OpenAI |
| 流式输出 | `agent.astream_events(v2)` 手动迭代 | 零回调黑盒，每个 token/工具调用显式控制 |
| 对话记忆 | `cl.user_session` + `chat_history` | Chainlit 会话天然隔离 |
| 判责逻辑 | Python 规则引擎（非 LLM） | 确定性结果，不可幻觉 |
| 情绪升级 | LLM 识别关键词 → 强制调工具 | prompt 中写"第一个动作必须是调工具" |
| 模型与 API Schema | 分离（Pydantic v2） | 数据层 ↔ 接口层解耦 |

---

## 演进路线（已完成）

| Phase | 主题 | 工具数 | 核心交付 |
|-------|------|--------|----------|
| Phase 1 | Tool Calling 闭环 | 2 | LangChain Agent + mock 工具 |
| Phase 2 | RAG 知识库 + Chainlit | 3 | ChromaDB + BGE Embedding + 聊天 UI |
| Phase 3 | 数据持久化 + API | 3 | SQLModel + FastAPI + 流式输出 |
| Phase 4 | 售后核心闭环 | 5 | 物流轨迹 + 退货申请/进度 |
| Phase 5 | Tier 2 信息增强 | 9 | 多维度查单 + 商品详情 + 发票 |
| Phase 6 | Tier 3 智能判断 | 12 | 判责 + 预警 + 情绪升级 |
