"""信息查询工具 — 多维度查单 + 商品详情"""

from langchain_core.tools import tool

from shopaide.database.repository import get_order_by_id
from shopaide.database.repository import search_orders as _repo_search_orders
from shopaide.database.session import get_session


@tool
def search_orders(keyword: str) -> str:
    """用关键词搜索订单。支持按订单号、收件人姓名或手机号模糊搜索。

    当用户不记得订单号、只说"我的订单"或提供姓名/手机号时，使用此工具。

    Args:
        keyword: 搜索关键词（订单号/姓名/手机号均可）
    """
    with get_session() as session:
        results = _repo_search_orders(session, keyword)
        if not results:
            return f"未找到与「{keyword}」相关的订单，请尝试其他关键词或提供完整订单号。"

        lines = [f"搜索「{keyword}」共找到 {len(results)} 个订单：\n"]
        for o in results:
            item = getattr(o, "item_name", "") or "无商品信息"
            lines.append(
                f"  [{o.order_id}] {o.status} | "
                f"{o.recipient} {o.phone} | "
                f"{item} | "
                f"{o.estimated_delivery}"
            )
        return "\n".join(lines)


@tool
def query_product_info(order_id: str) -> str:
    """查询订单中包含的商品详情（名称、SKU、价格、优惠、实付金额等）。

    Args:
        order_id: 订单号，格式如 GY10086
    """
    with get_session() as session:
        order = get_order_by_id(session, order_id)
        if not order:
            return f"未找到订单 {order_id}，请核实订单号是否正确。"

        if not order.item_name:
            return f"订单 {order_id} 暂无商品信息。"

        actual_pay = order.item_price * order.item_quantity - order.discount_amount

        lines = [
            f"订单号：{order_id}",
            f"商品名称：{order.item_name}",
            f"商品SKU：{order.item_sku}",
            f"单价：{order.item_price:.2f} 元",
            f"数量：{order.item_quantity}",
        ]
        if order.discount_amount > 0:
            lines.append(f"优惠金额：-{order.discount_amount:.2f} 元")
        lines.extend([
            f"实付金额：{actual_pay:.2f} 元",
            f"支付方式：{order.payment_method}",
        ])
        return "\n".join(lines)
