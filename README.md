# ShopAide（谷雨电商智能售后 Agent）

基于 LangChain + FastAPI + Chainlit 的电商智能售后 Copilot。

## Phase 1 — Tool Calling 闭环（当前阶段）

验证 Agent 能够理解用户意图并自主调用后端工具：

- `query_order_status` — 查询订单物流状态（模拟）
- `modify_shipping_address` — 修改收货地址（模拟）

### 快速启动

```bash
# 1. 安装依赖
pip install -e .

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY

# 3. 运行测试
python tests/test_agent.py
```

## 项目结构

```
ShopAide/
├── pyproject.toml          # 项目元数据与依赖
├── .env.example            # 环境变量模板
├── .gitignore
├── README.md
├── src/shopaide/
│   ├── __init__.py
│   ├── config.py           # 全局配置（从 .env 加载）
│   ├── tools/
│   │   ├── __init__.py
│   │   └── order_tools.py  # 业务工具（当前为 mock）
│   └── agent/
│       ├── __init__.py
│       └── agent.py        # Agent 构建与提示词
└── tests/
    ├── __init__.py
    └── test_agent.py       # Phase 1 集成测试
```
