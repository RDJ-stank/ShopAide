"""工具模块 — 统一注册所有 Tools 供 Agent 使用"""

from shopaide.tools.order_tools import query_order_status, modify_shipping_address
from shopaide.tools.knowledge_tool import search_return_policy

# 所有工具汇总（后续新增工具只需追加到此列表）
ALL_TOOLS = [
    query_order_status,
    modify_shipping_address,
    search_return_policy,
]
