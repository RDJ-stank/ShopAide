"""发票管理工具 — 查询发票状态 + 补开发票"""

from langchain_core.tools import tool

from shopaide.database.repository import create_invoice_reissue, get_invoice_by_order_id
from shopaide.database.session import get_session


@tool
def query_invoice_status(order_id: str) -> str:
    """查询订单的发票状态（未开/已开/已申请补开）及详情。

    Args:
        order_id: 订单号，格式如 GY10086
    """
    with get_session() as session:
        invoice = get_invoice_by_order_id(session, order_id)
        if not invoice:
            return (
                f"订单 {order_id} 尚未开具发票。\n"
                f"如需开发票，请在订单签收后联系客服或使用 request_invoice_reissue 工具申请补开。"
            )

        lines = [
            f"发票号：{invoice.invoice_id}",
            f"订单号：{invoice.order_id}",
            f"抬头：{invoice.title}",
            f"税号：{invoice.tax_number or '无'}",
            f"状态：{invoice.status}",
            f"开票金额：{invoice.amount:.2f} 元",
        ]
        if invoice.issue_time:
            lines.append(f"开票时间：{invoice.issue_time}")
        return "\n".join(lines)


@tool
def request_invoice_reissue(order_id: str, new_title: str, tax_number: str = "") -> str:
    """为已开发票的订单申请补开或修改发票抬头。仅已开票的订单支持此操作。

    Args:
        order_id: 订单号，格式如 GY10086
        new_title: 新发票抬头（个人姓名或公司全称）
        tax_number: 纳税人识别号（公司抬头时需提供，个人可不填）
    """
    with get_session() as session:
        invoice, error = create_invoice_reissue(session, order_id, new_title, tax_number)
        if error:
            return error

        return (
            f"补开发票申请已提交！\n"
            f"发票号：{invoice.invoice_id}\n"
            f"订单号：{order_id}\n"
            f"新抬头：{new_title}\n"
            f"税号：{tax_number or '无'}\n"
            f"状态：已申请补开\n\n"
            f"电子发票将在 1-3 个工作日内发送到您的注册邮箱。"
            f"如需加急，请联系人工客服。"
        )
