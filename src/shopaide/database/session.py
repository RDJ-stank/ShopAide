"""数据库会话管理 — SQLite 同步引擎 + 初始化 + 种子数据"""

import os
from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlmodel import Session, SQLModel, create_engine, select

from shopaide.database.models import (
    DisputeCase, Escalation, Invoice, LogisticsEvent, Order, ReturnOrder,
)

_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..")
_DB_DIR = os.path.abspath(_DB_DIR)
DATABASE_URL = f"sqlite:///{os.path.join(_DB_DIR, 'shopaide.db')}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

# ============================================================
# 种子数据 — 订单
# ============================================================
_SEED_ORDERS: list[dict] = [
    dict(
        order_id="GY10086", status="运输中", carrier="顺丰速运", tracking_number="SF1234567890",
        current_location="广州市白云分拣中心", estimated_delivery="2026-06-05",
        recipient="张三", phone="13800001111",
        address="北京市朝阳区望京SOHO T1-1806",
        item_name="春季新款男士运动夹克", item_sku="SP25-MJ-001-L",
        item_price=399.00, item_quantity=1, discount_amount=40.00,
        payment_method="微信支付",
    ),
    dict(
        order_id="GY10010", status="已签收", carrier="中通快递", tracking_number="ZT9876543210",
        current_location="已送达", estimated_delivery="2026-05-28",
        recipient="李四", phone="13900002222",
        address="上海市浦东新区张江高科技园区",
        item_name="蓝牙降噪耳机 Pro", item_sku="EP-BT-2026-BLK",
        item_price=299.00, item_quantity=1, discount_amount=0.00,
        payment_method="支付宝",
    ),
    dict(
        order_id="GY20480", status="待发货", carrier="待分配", tracking_number="",
        current_location="仓库", estimated_delivery="2026-06-08",
        recipient="王五", phone="13700003333",
        address="深圳市南山区科技园南路 9 号",
        item_name="有机绿茶礼盒装 250g", item_sku="FD-TEA-OG-250",
        item_price=128.00, item_quantity=2, discount_amount=10.00,
        payment_method="银行卡",
    ),
]

# ============================================================
# 种子数据 — 物流轨迹
# GY10086 最后轨迹距今>48h，触发物流停滞预警
# ============================================================
_SEED_LOGISTICS: list[dict] = [
    dict(order_id="GY10086", timestamp="2026-05-28 08:30", location="深圳宝安仓库", status_desc="已揽收"),
    dict(order_id="GY10086", timestamp="2026-05-29 20:15", location="深圳分拣中心", status_desc="运输中"),
    dict(order_id="GY10086", timestamp="2026-05-30 06:30", location="广州白云分拣中心", status_desc="已发往北京"),
    dict(order_id="GY10010", timestamp="2026-05-26 09:00", location="上海浦东仓库", status_desc="已揽收"),
    dict(order_id="GY10010", timestamp="2026-05-26 22:00", location="上海分拣中心", status_desc="运输中"),
    dict(order_id="GY10010", timestamp="2026-05-27 15:00", location="上海浦东新区张江网点", status_desc="派送中"),
    dict(order_id="GY10010", timestamp="2026-05-28 10:20", location="已签收", status_desc="已签收（本人）"),
]

# ============================================================
# 种子数据 — 退货单
# ============================================================
_SEED_RETURNS: list[dict] = [
    dict(
        return_id="RTN20260530-001", order_id="GY10010",
        reason="尺码不合适", status="已完成",
        apply_time="2026-05-30 14:00", approved_time="2026-05-30 16:00",
        shipped_time="2026-05-31 10:00", received_time="2026-06-02 09:00",
        refund_time="2026-06-02 14:30", refund_amount=299.00,
    ),
]

# ============================================================
# 种子数据 — 发票
# ============================================================
_SEED_INVOICES: list[dict] = [
    dict(
        invoice_id="INV20260529-001", order_id="GY10010",
        title="李四", tax_number="", status="已开",
        issue_time="2026-05-29 10:00", amount=299.00,
    ),
]

# ============================================================
# 种子数据 — 判责工单
# ============================================================
_SEED_DISPUTES: list[dict] = [
    dict(
        case_id="DSP20260601-001", order_id="GY10010",
        description="蓝牙耳机左耳无声，可能为出厂瑕疵",
        damage_type="商品瑕疵", responsibility="商家责任",
        resolution="退货退款", compensation_amount=299.00,
        status="已解决",
        created_time="2026-06-01 09:00", resolved_time="2026-06-01 17:00",
    ),
]


def init_db() -> None:
    """初始化数据库：建表 + 写入种子数据（幂等）。"""
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        existing_ids = session.exec(select(Order.order_id)).all()
        existing_set = set(existing_ids)
        new_orders = [Order(**d) for d in _SEED_ORDERS if d["order_id"] not in existing_set]
        if new_orders:
            session.add_all(new_orders)
            session.commit()

    with Session(engine) as session:
        existing_log = session.exec(select(LogisticsEvent.id)).all()
        if not existing_log:
            session.add_all([LogisticsEvent(**d) for d in _SEED_LOGISTICS])
            session.commit()

    with Session(engine) as session:
        existing_ret = session.exec(select(ReturnOrder.return_id)).all()
        existing_ret_set = set(existing_ret)
        new_returns = [ReturnOrder(**d) for d in _SEED_RETURNS if d["return_id"] not in existing_ret_set]
        if new_returns:
            session.add_all(new_returns)
            session.commit()

    with Session(engine) as session:
        existing_inv = session.exec(select(Invoice.invoice_id)).all()
        existing_inv_set = set(existing_inv)
        new_invoices = [Invoice(**d) for d in _SEED_INVOICES if d["invoice_id"] not in existing_inv_set]
        if new_invoices:
            session.add_all(new_invoices)
            session.commit()

    with Session(engine) as session:
        existing_dsp = session.exec(select(DisputeCase.case_id)).all()
        existing_dsp_set = set(existing_dsp)
        new_disputes = [DisputeCase(**d) for d in _SEED_DISPUTES if d["case_id"] not in existing_dsp_set]
        if new_disputes:
            session.add_all(new_disputes)
            session.commit()


@contextmanager
def get_session():
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
