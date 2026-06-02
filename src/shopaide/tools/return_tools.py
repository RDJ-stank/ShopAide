"""退货业务工具 — 提交退货申请 + 查询退货进度"""

from langchain_core.tools import tool

from shopaide.database.repository import (
    create_return_order,
    get_order_by_id,
    get_return_by_id,
    get_return_by_order_id,
)
from shopaide.database.session import get_session


@tool
def submit_return_request(order_id: str, reason: str) -> str:
    """为指定订单提交退货申请。仅已签收且签收不超过7天的订单支持退货。

    Args:
        order_id: 订单号，格式如 GY10086
        reason: 退货原因（如"尺码不合适"、"商品有瑕疵"等）
    """
    with get_session() as session:
        returned, error = create_return_order(session, order_id, reason)
        if error:
            return error

        return (
            f"退货申请提交成功！\n"
            f"退货单号：{returned.return_id}\n"
            f"订单号：{order_id}\n"
            f"退货原因：{reason}\n"
            f"当前状态：审核中\n\n"
            f"客服将在 24 小时内审核您的申请。审核通过后，"
            f"您需在 3 天内寄回商品并填写运单号。"
        )


@tool
def query_return_progress(return_id: str = "", order_id: str = "") -> str:
    """查询退货进度。通过退货单号或原订单号查询。

    Args:
        return_id: 退货单号，如 RTN20260601-001（与 order_id 二选一）
        order_id: 原订单号，如 GY10086（与 return_id 二选一）
    """
    if not return_id and not order_id:
        return "请提供退货单号（return_id）或原订单号（order_id）。"

    with get_session() as session:
        if return_id:
            rt = get_return_by_id(session, return_id)
        else:
            rt = get_return_by_order_id(session, order_id)

        if not rt:
            identifier = return_id or order_id
            return f"未找到退货记录 {identifier}，请核实单号是否正确。"

        lines = [
            f"退货单号：{rt.return_id}",
            f"原订单号：{rt.order_id}",
            f"退货原因：{rt.reason}",
            f"当前状态：{rt.status}",
            f"申请时间：{rt.apply_time}",
        ]
        if rt.approved_time:
            lines.append(f"审核通过：{rt.approved_time}")
        if rt.shipped_time:
            lines.append(f"商品寄回：{rt.shipped_time}")
        if rt.received_time:
            lines.append(f"仓库验收：{rt.received_time}")
        if rt.refund_time:
            lines.append(f"退款时间：{rt.refund_time}")
            lines.append(f"退款金额：{rt.refund_amount:.2f} 元")

        return "\n".join(lines)
