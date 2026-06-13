"""工具模块 — 统一注册所有 Tools 供 Agent 使用"""

from shopaide.database.session import init_db
from shopaide.tools.damage_tools import check_order_alert, report_damage
from shopaide.tools.escalation_tools import escalate_to_human
from shopaide.tools.invoice_tools import query_invoice_status, request_invoice_reissue
from shopaide.tools.knowledge_tool import search_return_policy
from shopaide.tools.order_tools import modify_shipping_address, query_order_status
from shopaide.tools.return_tools import query_return_progress, submit_return_request
from shopaide.tools.search_tools import query_product_info, search_orders

init_db()

ALL_TOOLS = [
    query_order_status,
    search_orders,
    query_product_info,
    modify_shipping_address,
    submit_return_request,
    query_return_progress,
    query_invoice_status,
    request_invoice_reissue,
    search_return_policy,
    report_damage,
    check_order_alert,
    escalate_to_human,
]
