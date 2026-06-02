"""数据库会话管理 — SQLite 同步引擎 + 初始化 + 种子数据"""

import os
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine, select

from shopaide.database.models import LogisticsEvent, Order, ReturnOrder

_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..")
_DB_DIR = os.path.abspath(_DB_DIR)
DATABASE_URL = f"sqlite:///{os.path.join(_DB_DIR, 'shopaide.db')}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

# ============================================================
# 种子数据 — 订单
# ============================================================
_SEED_ORDERS: list[dict] = [
    dict(
        order_id="GY10086",
        status="运输中", carrier="顺丰速运", tracking_number="SF1234567890",
        current_location="广州市白云分拣中心", estimated_delivery="2026-06-05",
        recipient="张三", address="北京市朝阳区望京SOHO T1-1806",
    ),
    dict(
        order_id="GY10010",
        status="已签收", carrier="中通快递", tracking_number="ZT9876543210",
        current_location="已送达", estimated_delivery="2026-05-28",
        recipient="李四", address="上海市浦东新区张江高科技园区",
    ),
    dict(
        order_id="GY20480",
        status="待发货", carrier="待分配", tracking_number="",
        current_location="仓库", estimated_delivery="2026-06-08",
        recipient="王五", address="深圳市南山区科技园南路 9 号",
    ),
]

# ============================================================
# 种子数据 — 物流轨迹
# ============================================================
_SEED_LOGISTICS: list[dict] = [
    # GY10086 — 运输中（深圳→广州→北京）
    dict(order_id="GY10086", timestamp="2026-05-31 08:30", location="深圳宝安仓库", status_desc="已揽收"),
    dict(order_id="GY10086", timestamp="2026-05-31 20:15", location="深圳分拣中心", status_desc="运输中"),
    dict(order_id="GY10086", timestamp="2026-06-01 14:00", location="广州白云分拣中心", status_desc="到达中转"),
    dict(order_id="GY10086", timestamp="2026-06-02 06:30", location="广州白云分拣中心", status_desc="已发往北京"),
    # GY10010 — 已签收
    dict(order_id="GY10010", timestamp="2026-05-26 09:00", location="上海浦东仓库", status_desc="已揽收"),
    dict(order_id="GY10010", timestamp="2026-05-26 22:00", location="上海分拣中心", status_desc="运输中"),
    dict(order_id="GY10010", timestamp="2026-05-27 15:00", location="上海浦东新区张江网点", status_desc="派送中"),
    dict(order_id="GY10010", timestamp="2026-05-28 10:20", location="已签收", status_desc="已签收（本人）"),
    # GY20480 — 待发货（暂无轨迹）
]

# ============================================================
# 种子数据 — 退货单
# ============================================================
_SEED_RETURNS: list[dict] = [
    dict(
        return_id="RTN20260530-001",
        order_id="GY10010",
        reason="尺码不合适",
        status="已完成",
        apply_time="2026-05-30 14:00",
        approved_time="2026-05-30 16:00",
        shipped_time="2026-05-31 10:00",
        received_time="2026-06-02 09:00",
        refund_time="2026-06-02 14:30",
        refund_amount=299.00,
    ),
]


def init_db() -> None:
    """初始化数据库：建表 + 写入种子数据（幂等）。"""
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # 订单
        existing_ids = session.exec(select(Order.order_id)).all()
        existing_set = set(existing_ids)
        new_orders = [Order(**d) for d in _SEED_ORDERS if d["order_id"] not in existing_set]
        if new_orders:
            session.add_all(new_orders)
            session.commit()

    with Session(engine) as session:
        # 物流轨迹
        existing_logistics = session.exec(select(LogisticsEvent.id)).all()
        if not existing_logistics:
            session.add_all([LogisticsEvent(**d) for d in _SEED_LOGISTICS])
            session.commit()

    with Session(engine) as session:
        # 退货单
        existing_returns = session.exec(select(ReturnOrder.return_id)).all()
        existing_return_set = set(existing_returns)
        new_returns = [ReturnOrder(**d) for d in _SEED_RETURNS if d["return_id"] not in existing_return_set]
        if new_returns:
            session.add_all(new_returns)
            session.commit()


@contextmanager
def get_session():
    """同步 session 生成器（context manager 模式）。"""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
