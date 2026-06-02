"""售后业务工具 — 对接 SQLite 数据库，通过 repository 执行实际数据操作"""

from langchain_core.tools import tool

from shopaide.database.repository import get_order_by_id, update_order_address
from shopaide.database.session import get_session


@tool
def query_order_status(order_id: str) -> str:
    """根据订单号查询物流状态和详细信息。

    Args:
        order_id: 订单号，格式如 GY10086
    """
    with get_session() as session:
        order = get_order_by_id(session, order_id)
        if not order:
            return f"未找到订单 {order_id}，请核实订单号是否正确。"

        lines = [
            f"订单号：{order.order_id}",
            f"状态：{order.status}",
            f"快递公司：{order.carrier}",
            f"运单号：{order.tracking_number or '暂无'}",
            f"当前位置：{order.current_location}",
            f"预计送达：{order.estimated_delivery}",
            f"收件人：{order.recipient}",
            f"收件地址：{order.address}",
        ]
        return "\n".join(lines)


@tool
def modify_shipping_address(order_id: str, new_address: str) -> str:
    """修改指定订单的收货地址（模拟 — 实际会调用OMS接口）。

    Args:
        order_id: 订单号，格式如 GY10086
        new_address: 新的收货地址全称
    """
    with get_session() as session:
        # 先查是否存在并记录原地址
        order = get_order_by_id(session, order_id)
        if not order:
            return f"未找到订单 {order_id}，请核实订单号是否正确。"

        old_address = order.address

        # 执行地址更新（repository 内部做状态校验）
        updated, error = update_order_address(session, order_id, new_address)
        if error:
            return error

        return (
            f"地址修改成功！\n"
            f"订单号：{order_id}\n"
            f"原地址：{old_address}\n"
            f"新地址：{new_address}"
        )
