"""工具模块 — 统一注册所有 Tools 供 Agent 使用"""

from shopaide.database.session import init_db
from shopaide.tools.order_tools import query_order_status, modify_shipping_address
from shopaide.tools.knowledge_tool import search_return_policy
from shopaide.tools.return_tools import submit_return_request, query_return_progress

# 系统启动时确保数据库表结构和种子数据已就位（幂等）
init_db()

ALL_TOOLS = [
    query_order_status,
    modify_shipping_address,
    submit_return_request,
    query_return_progress,
    search_return_policy,
]
