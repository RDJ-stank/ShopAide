"""数据仓库层 — 订单 + 物流轨迹 + 退货 的原子数据库操作"""

from datetime import datetime, timedelta

from sqlmodel import Session, select

from shopaide.database.models import LogisticsEvent, Order, ReturnOrder

_IMMUTABLE_STATUSES = {"已签收", "已取消"}


# ============================================================
# 订单
# ============================================================
def get_order_by_id(session: Session, order_id: str) -> Order | None:
    """根据订单号查询订单。"""
    return session.exec(
        select(Order).where(Order.order_id == order_id)
    ).first()


def update_order_address(session: Session, order_id: str, new_address: str) -> tuple[Order | None, str | None]:
    """修改收货地址（含状态校验）。"""
    order = get_order_by_id(session, order_id)
    if not order:
        return None, f"未找到订单 {order_id}，请核实订单号是否正确。"
    if order.status in _IMMUTABLE_STATUSES:
        return None, f"订单 {order_id} 当前状态为「{order.status}」，不支持修改地址。"
    order.address = new_address
    session.add(order)
    return order, None


# ============================================================
# 物流轨迹
# ============================================================
def get_logistics_trail(session: Session, order_id: str) -> list[LogisticsEvent]:
    """查询订单的完整物流轨迹，按时间升序排列。"""
    return session.exec(
        select(LogisticsEvent)
        .where(LogisticsEvent.order_id == order_id)
        .order_by(LogisticsEvent.timestamp)
    ).all()


# ============================================================
# 退货
# ============================================================
def create_return_order(
    session: Session, order_id: str, reason: str
) -> tuple[ReturnOrder | None, str | None]:
    """提交退货申请（含完整业务校验）。

    校验规则：
    1. 订单必须存在且已签收
    2. 签收后 7 天内支持无理由退货
    3. 同一订单不能重复申请退货
    """
    order = get_order_by_id(session, order_id)
    if not order:
        return None, f"未找到订单 {order_id}，请核实订单号是否正确。"
    if order.status != "已签收":
        return None, f"订单 {order_id} 当前状态为「{order.status}」，仅已签收的订单支持退货。"
    if order.estimated_delivery:
        try:
            delivery_date = datetime.strptime(order.estimated_delivery, "%Y-%m-%d")
            if datetime.now() > delivery_date + timedelta(days=7):
                return None, (
                    f"订单 {order_id} 签收已超过 7 天，不支持无理由退货。"
                    f"如为质量问题，请联系人工客服。"
                )
        except ValueError:
            pass  # 日期解析失败时不阻塞，仅跳过时效校验

    existing = session.exec(
        select(ReturnOrder).where(ReturnOrder.order_id == order_id)
    ).first()
    if existing:
        return None, f"订单 {order_id} 已存在退货申请（单号：{existing.return_id}），请勿重复提交。"

    # 生成退货单号：RTN + 年月日 + - + 三位序号
    today = datetime.now().strftime("%Y%m%d")
    count = len(session.exec(
        select(ReturnOrder).where(ReturnOrder.return_id.like(f"RTN{today}-%"))
    ).all())
    return_id = f"RTN{today}-{count + 1:03d}"

    return_order = ReturnOrder(
        return_id=return_id,
        order_id=order_id,
        reason=reason,
        status="审核中",
        apply_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    session.add(return_order)
    return return_order, None


def get_return_by_id(session: Session, return_id: str) -> ReturnOrder | None:
    """根据退货单号查询退货进度。"""
    return session.exec(
        select(ReturnOrder).where(ReturnOrder.return_id == return_id)
    ).first()


def get_return_by_order_id(session: Session, order_id: str) -> ReturnOrder | None:
    """根据原订单号查询退货记录。"""
    return session.exec(
        select(ReturnOrder).where(ReturnOrder.order_id == order_id)
    ).first()
