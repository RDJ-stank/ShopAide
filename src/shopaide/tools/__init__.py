"""工具模块 — 统一注册所有 Tools 供 Agent 使用"""

from shopaide.database.session import init_db
from shopaide.tools.order_tools import query_order_status, modify_shipping_address
from shopaide.tools.knowledge_tool import search_return_policy
from shopaide.tools.return_tools import submit_return_request, query_return_progress
from shopaide.tools.search_tools import search_orders, query_product_info
from shopaide.tools.invoice_tools import query_invoice_status, request_invoice_reissue

init_db()

ALL_TOOLS = [
    query_order_status,
    modify_shipping_address,
    submit_return_request,
    query_return_progress,
    search_return_policy,
    search_orders,
    query_product_info,
    query_invoice_status,
    request_invoice_reissue,
]
