"""数据仓库层 — 原子数据库操作函数"""

from sqlmodel import Session, select

from shopaide.database.models import Order

# 不可修改地址的订单状态
_IMMUTABLE_STATUSES = {"已签收", "已取消"}


def get_order_by_id(session: Session, order_id: str) -> Order | None:
    """根据订单号查询订单，不存在时返回 None。

    Args:
        session: 数据库会话
        order_id: 订单号（如 GY10086）
    """
    return session.exec(
        select(Order).where(Order.order_id == order_id)
    ).first()


def update_order_address(session: Session, order_id: str, new_address: str) -> tuple[Order | None, str | None]:
    """修改订单收货地址（含业务校验）。

    Args:
        session: 数据库会话
        order_id: 订单号
        new_address: 新收货地址

    Returns:
        (Order, None)  — 修改成功，返回更新后的订单
        (None, str)    — 修改失败，返回错误描述
    """
    order = get_order_by_id(session, order_id)
    if not order:
        return None, f"未找到订单 {order_id}，请核实订单号是否正确。"

    if order.status in _IMMUTABLE_STATUSES:
        return None, f"订单 {order_id} 当前状态为「{order.status}」，不支持修改地址。"

    order.address = new_address
    session.add(order)
    return order, None
