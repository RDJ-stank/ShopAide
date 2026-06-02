"""数据仓库层 — 订单 + 物流轨迹 + 退货 + 发票 的原子数据库操作"""

from datetime import datetime, timedelta

from sqlmodel import Session, select

from shopaide.database.models import Invoice, LogisticsEvent, Order, ReturnOrder

_IMMUTABLE_STATUSES = {"已签收", "已取消"}


# ============================================================
# 订单
# ============================================================
def get_order_by_id(session: Session, order_id: str) -> Order | None:
    return session.exec(select(Order).where(Order.order_id == order_id)).first()


def search_orders(session: Session, keyword: str) -> list[Order]:
    """模糊搜索订单：匹配 order_id / recipient / phone（任一字段包含 keyword）。"""
    k = f"%{keyword}%"
    return session.exec(
        select(Order).where(
            Order.order_id.contains(keyword)
            | Order.recipient.contains(keyword)
            | Order.phone.contains(keyword)
        )
    ).all()


def update_order_address(session: Session, order_id: str, new_address: str) -> tuple[Order | None, str | None]:
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
    return session.exec(
        select(LogisticsEvent)
        .where(LogisticsEvent.order_id == order_id)
        .order_by(LogisticsEvent.timestamp)
    ).all()


# ============================================================
# 退货
# ============================================================
def create_return_order(session: Session, order_id: str, reason: str) -> tuple[ReturnOrder | None, str | None]:
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
            pass

    existing = session.exec(select(ReturnOrder).where(ReturnOrder.order_id == order_id)).first()
    if existing:
        return None, f"订单 {order_id} 已存在退货申请（单号：{existing.return_id}），请勿重复提交。"

    today = datetime.now().strftime("%Y%m%d")
    count = len(session.exec(
        select(ReturnOrder).where(ReturnOrder.return_id.like(f"RTN{today}-%"))
    ).all())
    return_id = f"RTN{today}-{count + 1:03d}"

    return_order = ReturnOrder(
        return_id=return_id, order_id=order_id, reason=reason,
        status="审核中", apply_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    session.add(return_order)
    return return_order, None


def get_return_by_id(session: Session, return_id: str) -> ReturnOrder | None:
    return session.exec(select(ReturnOrder).where(ReturnOrder.return_id == return_id)).first()


def get_return_by_order_id(session: Session, order_id: str) -> ReturnOrder | None:
    return session.exec(select(ReturnOrder).where(ReturnOrder.order_id == order_id)).first()


# ============================================================
# 发票
# ============================================================
def get_invoice_by_order_id(session: Session, order_id: str) -> Invoice | None:
    """查询订单的发票记录。无记录表示尚未开票。"""
    return session.exec(select(Invoice).where(Invoice.order_id == order_id)).first()


def create_invoice_reissue(
    session: Session, order_id: str, new_title: str, tax_number: str = ""
) -> tuple[Invoice | None, str | None]:
    """补开发票（仅已开发票才能申请补开，且只能申请一次）。

    校验：
    1. 订单存在且发票状态为"已开"
    2. 不能已存在一个"已申请补开"的记录
    """
    order = get_order_by_id(session, order_id)
    if not order:
        return None, f"未找到订单 {order_id}，请核实订单号是否正确。"

    existing = get_invoice_by_order_id(session, order_id)
    if not existing:
        return None, f"订单 {order_id} 尚未开票，请先申请开具发票。"
    if existing.status == "未开":
        return None, f"订单 {order_id} 的发票尚未开具，请先联系客服申请开票。"
    if existing.status == "已申请补开":
        return None, f"订单 {order_id} 已存在补开申请（发票号：{existing.invoice_id}），请勿重复申请。"

    # 更新发票抬头和状态
    existing.title = new_title
    existing.tax_number = tax_number
    existing.status = "已申请补开"
    session.add(existing)
    return existing, None
