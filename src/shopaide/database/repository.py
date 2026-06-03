"""数据仓库层 — 订单 + 物流 + 退货 + 发票 + 判责 + 升级 + 预警"""

from datetime import datetime, timedelta

from sqlmodel import Session, select

from shopaide.database.models import (
    DisputeCase, Escalation, Invoice, LogisticsEvent, Order, ReturnOrder,
)

_IMMUTABLE_STATUSES = {"已签收", "已取消"}


# ============================================================
# 订单
# ============================================================
def get_order_by_id(session: Session, order_id: str) -> Order | None:
    return session.exec(select(Order).where(Order.order_id == order_id)).first()


def search_orders(session: Session, keyword: str) -> list[Order]:
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
# 物流
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
                return None, f"订单 {order_id} 签收已超过 7 天，不支持无理由退货。如为质量问题，请联系人工客服。"
        except ValueError:
            pass
    existing = session.exec(select(ReturnOrder).where(ReturnOrder.order_id == order_id)).first()
    if existing:
        return None, f"订单 {order_id} 已存在退货申请（单号：{existing.return_id}），请勿重复提交。"
    today = datetime.now().strftime("%Y%m%d")
    count = len(session.exec(select(ReturnOrder).where(ReturnOrder.return_id.like(f"RTN{today}-%"))).all())
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
    return session.exec(select(Invoice).where(Invoice.order_id == order_id)).first()


def create_invoice_reissue(session: Session, order_id: str, new_title: str, tax_number: str = "") -> tuple[Invoice | None, str | None]:
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
    existing.title = new_title
    existing.tax_number = tax_number
    existing.status = "已申请补开"
    session.add(existing)
    return existing, None


# ============================================================
# 判责工单
# ============================================================
def _determine_responsibility(order: Order, damage_type: str) -> tuple[str, str]:
    """根据伤害类型和订单上下文自动判定责任方和推荐处理方案。"""
    if damage_type == "物流损坏":
        if order.status in ("运输中", "已签收"):
            return "物流责任", "换货"
        return "待判定", ""
    elif damage_type == "商品瑕疵":
        if order.status == "已签收":
            return "商家责任", "退货退款"
        return "商家责任", "换货"
    elif damage_type == "缺失件":
        return "商家责任", "补发"
    elif damage_type == "错发漏发":
        return "商家责任", "换货"
    else:
        return "待判定", ""


def create_dispute_case(
    session: Session, order_id: str, description: str, damage_type: str
) -> tuple[DisputeCase | None, str | None]:
    """创建商品问题判责工单（自动判定责任方 + 推荐方案）。"""
    order = get_order_by_id(session, order_id)
    if not order:
        return None, f"未找到订单 {order_id}，请核实订单号是否正确。"
    if order.status not in ("运输中", "已签收"):
        return None, f"订单 {order_id} 当前状态为「{order.status}」，不支持创建判责工单。"

    existing = session.exec(select(DisputeCase).where(
        DisputeCase.order_id == order_id, DisputeCase.status == "处理中"
    )).first()
    if existing:
        return None, f"订单 {order_id} 已有处理中的判责工单（编号：{existing.case_id}），请勿重复提交。"

    # 检查是否已有活跃的退货工单
    active_return = session.exec(select(ReturnOrder).where(
        ReturnOrder.order_id == order_id,
        ReturnOrder.status.not_in(["已完成", "已拒绝"]),
    )).first()
    if active_return:
        return None, (
            f"订单 {order_id} 已有退货工单（编号：{active_return.return_id}）"
            f"正在处理中（状态：{active_return.status}），无需重复提交判责。"
            f"请告知用户关注退货进度或联系客服查询。"
        )

    responsibility, resolution = _determine_responsibility(order, damage_type)

    today = datetime.now().strftime("%Y%m%d")
    count = len(session.exec(select(DisputeCase).where(DisputeCase.case_id.like(f"DSP{today}-%"))).all())
    case_id = f"DSP{today}-{count + 1:03d}"

    dispute = DisputeCase(
        case_id=case_id, order_id=order_id,
        description=description, damage_type=damage_type,
        responsibility=responsibility, resolution=resolution,
        status="处理中",
        created_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    session.add(dispute)
    return dispute, None


def get_dispute_by_id(session: Session, case_id: str) -> DisputeCase | None:
    return session.exec(select(DisputeCase).where(DisputeCase.case_id == case_id)).first()


# ============================================================
# 时效预警
# ============================================================
def check_order_alert(session: Session, order_id: str) -> dict:
    """检查订单是否存在时效风险（延迟发货/物流停滞/配送超时）。

    Returns:
        dict with keys: has_alert (bool), alert_type, detail, suggestion
    """
    order = get_order_by_id(session, order_id)
    if not order:
        return {"has_alert": False, "alert_type": "", "detail": "订单不存在", "suggestion": ""}

    now = datetime.now()

    # 待发货超过 48h
    if order.status == "待发货":
        if order.created_time:
            try:
                created_dt = datetime.strptime(order.created_time, "%Y-%m-%d %H:%M")
                if now > created_dt + timedelta(hours=48):
                    return {
                        "has_alert": True,
                        "alert_type": "延迟发货",
                        "detail": f"订单 {order_id} 于 {order.created_time} 下单，已超过 48 小时未发货。",
                        "suggestion": "建议催促卖家发货，或申请取消订单并退款。如为预售商品请忽略。",
                    }
            except ValueError:
                pass

    # 运输中：最后物流事件超过 48h → 物流停滞
    if order.status == "运输中":
        trail = get_logistics_trail(session, order_id)
        if trail:
            last_event = trail[-1]
            try:
                last_time = datetime.strptime(last_event.timestamp, "%Y-%m-%d %H:%M")
                if now > last_time + timedelta(hours=48):
                    return {
                        "has_alert": True,
                        "alert_type": "物流停滞",
                        "detail": (
                            f"订单 {order_id} 最后物流更新于 {last_event.timestamp}，"
                            f"已超过 48 小时未更新（{last_event.location} — {last_event.status_desc}）。"
                        ),
                        "suggestion": (
                            "建议联系物流公司确认包裹状态。如持续无更新，"
                            "可申请物流投诉或联系商家协调处理。"
                        ),
                    }
            except ValueError:
                pass

        # 超预计送达日期
        try:
            delivery_dt = datetime.strptime(order.estimated_delivery, "%Y-%m-%d")
            if now > delivery_dt:
                return {
                    "has_alert": True,
                    "alert_type": "配送超时",
                    "detail": f"订单 {order_id} 预计送达日期为 {order.estimated_delivery}，现已超时。",
                    "suggestion": "可申请延迟配送补偿（优惠券 10 元），或联系客服查询最新物流状态。",
                }
        except ValueError:
            pass

    return {
        "has_alert": False,
        "alert_type": "无异常",
        "detail": f"订单 {order_id} 当前状态正常。",
        "suggestion": "",
    }


# ============================================================
# 升级工单
# ============================================================
def create_escalation(
    session: Session, order_id: str, reason: str, user_description: str, context_summary: str
) -> Escalation:
    """创建升级工单（情绪激动/复杂问题超过AI能力时调用）。"""
    today = datetime.now().strftime("%Y%m%d")
    count = len(session.exec(select(Escalation).where(Escalation.escalation_id.like(f"ESC{today}-%"))).all())
    esc_id = f"ESC{today}-{count + 1:03d}"

    esc = Escalation(
        escalation_id=esc_id, order_id=order_id,
        reason=reason, user_description=user_description,
        context_summary=context_summary, status="待处理",
        created_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    session.add(esc)
    return esc
