# ShopAide（谷雨电商智能售后 Agent）

基于 **LangChain + FastAPI + ChromaDB + Chainlit + 飞书开放平台** 的电商智能售后 Copilot。

Agent 拥有 **12 个工具**，覆盖订单查询、物流轨迹、退货管理、智能判责、时效预警、发票管理、政策检索（RAG）和情绪升级。已接入飞书 IM 成为可交互的 Bot，支持通过 Chainlit Web UI 和飞书 App 双通道使用。

---

## 项目全貌

```
飞书用户 ─→ 飞书开放平台 ─→ cloudflared tunnel ─→ localhost:9090 ─→ FastAPI
                                                                      │
浏览器用户 ─→ Chainlit(UI) ─→ Agent(12 tools) ─→ repository ─→ SQLite
                   │ 流式输出                         │
                   │ 多轮记忆               RAG 检索 ─→ ChromaDB
                                                                 │
                                                         17 个 REST API 开放调用
```

### 双通道交互

| 通道 | 用户群体 | 交互方式 | 入口 |
|------|---------|---------|------|
| **飞书 Bot** | 客服团队 / 业务运营 | 在飞书群聊或单聊中 @机器人 提问 | 飞书客户端 |
| **Chainlit Web UI** | 外部用户 / 演示 / 调试 | 浏览器打开发送消息，流式逐字输出 | `http://localhost:8000` |

两个通道共享同一套 Agent 引擎——消息通道是独立的适配层，Agent 核心逻辑完全复用。

---

## 接入飞书的架构细节

### 消息流转

```
用户在飞书群发消息
  → 飞书服务端 POST JSON 到配置的回调 URL
  → cloudflared tunnel 转发到 localhost:9090
  → POST /api/feishu/callback
  → 解析事件体（URL 验证 or 消息事件）
  → Agent.ainvoke() 处理
  → 飞书 API send_text_message() 回复到群聊
```

### 飞书适配层（`src/shopaide/integrations/feishu.py`）

| 组件 | 实现 |
|------|------|
| Tenant Access Token | 自动获取 + 内存缓存 + 过期前 5 分钟刷新（线程安全 Lock） |
| URL 验证 | 兼容新旧两版飞书协议（`type: url_verification` 和 `schema: 2.0` 格式） |
| 消息解析 | `parse_message_event()` — 从飞书事件体中提取 `chat_id` + `text` |
| 消息发送 | `send_text_message()` — 通过飞书 IM API 以应用身份回复 |

### 部署拓扑

```
┌─────────────────────────────────────────┐
│  本地开发机 (Windows)                     │
│                                          │
│  uvicorn server:app --port 9090          │
│         ↑  localhost:9090                │
│  cloudflared tunnel --url                │
│         ↑                                │
│         │  出站 QUIC 连接（无需开端口）       │
│  ┌──────┴──────────────────────────┐     │
│  │  Cloudflare CDN                  │     │
│  │  https://xxx.trycloudflare.com   │←公网│
│  └─────────────────────────────────┘     │
└─────────────────────────────────────────┘
```

> cloudflared 生成的是临时域名，每次重启会变。生产环境可用 Named Tunnel 固定域名 + Cloudflare Access 做 SSO 鉴权。

---

## 项目结构

```
ShopAide/
├── pyproject.toml              # 项目元数据 + 所有依赖
├── .env.example                # 环境变量模板（LLM + 飞书凭证）
├── .gitignore
├── README.md
│
├── app.py                      # Chainlit Web UI（流式 + 多轮记忆 + 异常兜底）
├── server.py                   # FastAPI（17 个 REST + 1 个飞书回调端点）
├── .chainlit/
│   └── config.toml             # Chainlit UI 配置（浅色主题/中文/宽屏）
│
├── public/
│   └── style.css               # 品牌样式表（谷雨青 #0d9488 色系）
│
├── src/shopaide/
│   ├── __init__.py
│   ├── config.py               # LLM 多提供商预设（DeepSeek/Qwen/OpenAI）
│   │
│   ├── agent/
│   │   └── agent.py            # SYSTEM_PROMPT（情绪识别/判责/预警/升级规则）
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
│   ├── integrations/
│   │   ├── __init__.py
│   │   └── feishu.py            # 飞书 Bot 适配（Token管理/消息解析/回复发送）
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
| `orders` | 订单主表（含商品/支付/收件人/联系人） | 11 条（运输中 4 / 已签收 4 / 待发货 2 / 已取消 1） |
| `logistics_events` | 物流轨迹事件表 | 15 条 |
| `return_orders` | 退货单（6 种状态：审核中/待寄回/验收中/退款中/已完成/已拒绝） | 3 条 |
| `invoices` | 发票（3 种状态：未开/已开/已申请补开） | 3 条（个人 / 企业 / 未开） |
| `dispute_cases` | 判责工单（5 种类型 × 4 种责任方） | 2 条（已解决 / 处理中） |
| `escalations` | 升级工单（情绪升级/超AI能力升级） | 按需动态创建 |

---

## Agent 12 个工具全览

### 订单与物流（3 个）

| # | 工具 | 功能 | 触发场景 |
|---|------|------|----------|
| 1 | `query_order_status` | 查订单 + 商品信息 + 完整物流轨迹 | "帮我查一下 GY10086" |
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
| 10 | `report_damage` | 创建判责工单（自动定责+分流+检测已有退货） | "收到的东西坏了" |
| 11 | `check_order_alert` | 时效预警（延迟发货/物流停滞/配送超时） | "怎么还没到" |
| 12 | `escalate_to_human` | 创建升级工单+转达客服热线 | "太差劲了我要投诉" |

---

## REST API 接口一览（18 个端点）

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

### 飞书 Bot 回调（1 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/feishu/callback` | 飞书事件订阅（URL 验证 + 消息接收 + Agent 回复） |

---

## 环境变量配置

```ini
# ============================================================
# LLM 提供商（三选一）：deepseek / qwen / openai
# ============================================================
LLM_PROVIDER=deepseek
OPENAI_API_KEY=sk-你的key

# ============================================================
# 飞书集成（接入飞书 Bot 时必填）
# ============================================================
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

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

> **测试数据设计意图**：
> - GY10086 物流轨迹最后更新于 2026-05-30，距今 >48h → 测试物流停滞预警
> - GY20480 创建时间为 2026-06-01，距今 >72h → 测试延迟发货预警
> - GY10102 已有退货单 RTN20260601-001（审核中）→ 测试判责防重复逻辑
> - GY10012 已有判责工单 DSP20260602-001（处理中）→ 测试判责重复提交拦截

---

## 系统验证步骤

### 前提条件
- Python >= 3.11
- 有效的 LLM API Key（支持 DeepSeek / 通义千问 / OpenAI）
- 飞书开放平台应用（App ID + App Secret，如需接入飞书 Bot）
- cloudflared 可执行文件（如需公网暴露）

### 第 1 步：安装

```bash
cd ShopAide
pip install -e ".[dev]"
```

### 第 2 步：配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```ini
LLM_PROVIDER=deepseek
OPENAI_API_KEY=sk-你的key

# 飞书（可选，不配则飞书回调端点不会发消息）
FEISHU_APP_ID=cli_你的appid
FEISHU_APP_SECRET=你的secret
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

首次运行会下载 BAAI/bge-small-zh-v1.5 嵌入模型（约 100MB），后续复用缓存。

### 第 6 步：启动 FastAPI + Chainlit

```bash
# 终端 1：API 服务器
uvicorn server:app --reload --port 9090

# 终端 2：Chainlit Web UI
chainlit run app.py
```

验证 API：
```bash
curl http://localhost:9090/api/health
curl "http://localhost:9090/api/orders/search?keyword=张三"
curl http://localhost:9090/api/orders/GY20480/alert
```

浏览器打开 `http://localhost:8000` 测试 Chainlit 对话。

### 第 7 步：接入飞书 Bot（可选）

```bash
# 终端 3：启动公网隧道
.\cloudflared.exe tunnel --url http://localhost:9090
# 输出: https://xxx.trycloudflare.com
```

将生成的公网地址配置到飞书开放平台：
1. 飞书开放平台 → 你的应用 → 事件与回调
2. 请求网址填入 `https://xxx.trycloudflare.com/api/feishu/callback`
3. 添加事件 `im.message.receive_v1`
4. 创建版本并发布

在飞书客户端搜索机器人名字，发送：
```
帮我查一下订单 GY10086 的物流
```

---

## 技术决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据库 | SQLite + SQLModel（同步） | MVP 零配置单文件，`contextmanager` + `Depends` 安全注入 |
| 向量库 | ChromaDB + BGE Embedding | 本地 CPU 推理，数据不出境，零 API 成本 |
| LLM | OpenAI-compatible API | 一套代码支持 DeepSeek/Qwen/OpenAI，`.env` 一行切换 |
| Agent 流式输出 | `agent.astream_events(v2)` 手动迭代 | 零回调黑盒，每个 token/工具调用显式控制 |
| 对话记忆 | `cl.user_session` + `chat_history` | Chainlit 会话天然隔离，不依赖 LangChain Memory |
| 判责逻辑 | Python 规则引擎 | `_determine_responsibility()` 查表判定，杜绝 LLM 幻觉 |
| 情绪升级 | LLM 识别关键词 → 强制调工具 | prompt 中写"第一个动作必须是调工具"，不可只口头安抚 |
| 飞书通道 | 独立 `integrations/` 模块 | 消息通道与 Agent 核心完全解耦，替换其他 IM 只需写新适配层 |
| 公网暴露 | Cloudflare Tunnel | 出站 QUIC 连接，无需开路由器端口或配置防火墙 |
| ORM/API 分离 | SQLModel + Pydantic v2 分别定义 | 数据模型变更不影响 API Schema |

---

## 演进路线（已完成）

| Phase | 主题 | 工具数 | 核心交付 |
|-------|------|--------|----------|
| Phase 1 | Tool Calling 闭环 | 2 | LangChain Agent + mock 工具，跑通调用链路 |
| Phase 2 | RAG 知识库 + Chainlit | 3 | ChromaDB + BGE Embedding + 政策检索工具 + Web UI |
| Phase 3 | 数据持久化 + API | 3 | SQLModel + FastAPI + 流式输出 + 多轮记忆 |
| Phase 4 | 售后核心闭环 | 5 | 4节点物流轨迹 + 退货申请 + 退货进度追踪 |
| Phase 5 | Tier 2 信息增强 | 9 | 多维度查单 + 商品详情 + 发票管理 + 政策扩展 |
| Phase 6 | Tier 3 智能判断 | 12 | Python 规则引擎判责 + 时效预警 + 情绪识别升级 |
| Phase 7 | 飞书 Bot 接入 | 12 | IM 消息桥接 + Tenant Token 管理 + cloudflared 部署 |

---

## 飞书 Bot 接入 — 面试问答复盘

### Q: 你是怎么把 Agent 接入飞书的？

> 飞书提供开放平台的事件订阅机制。我在 FastAPI 里建了一个回调端点 `/api/feishu/callback`，用户发的消息会被飞书服务端 POST 到这个地址。端点收到 JSON 后由 `parse_message_event()` 提取文本内容，交给 Agent 的 `ainvoke()` 处理，结果通过飞书 IM API 的 `send_text_message()` 发回群聊。

### Q: 接入飞书和 Chainlit 有什么区别？

> Chainlit 是 Web 端的用户界面，飞书是 IM 端的 Bot。两个通道背后的 Agent 是同一个实例，12 个工具完全共享。区别只在消息适配层——Chainlit 用 `astream_events` 做流式逐字渲染，飞书用 HTTP API 一次性回复。因为我把消息解析和 Agent 核心分离了，换其他 IM 平台（如钉钉、企业微信）只需要写新的 `integrations/xxx.py`，Agent 本身一行不改。

### Q: 你没有服务器，是怎么让飞书回调访问到你本地的？

> 用的是 Cloudflare Tunnel。cloudflared 从我的电脑建立一个出站 QUIC 连接，Cloudflare CDN 给这个连接分配一个公网域名。飞书的回调请求打到这个域名上，Cloudflare 通过隧道转发到我本机的 `localhost:9090`。整个过程不需要在路由器上映射端口，也不依赖公网 IP。生产环境可以用 Named Tunnel 固定域名并加上 Cloudflare Access 的 SSO 鉴权。
