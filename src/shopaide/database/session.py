"""数据库会话管理 — SQLite 同步引擎 + 初始化 + 种子数据"""

import os
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine, select

from shopaide.database.models import Order

# 数据库文件路径（项目根目录下 shopaide.db）
_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..")
_DB_DIR = os.path.abspath(_DB_DIR)
DATABASE_URL = f"sqlite:///{os.path.join(_DB_DIR, 'shopaide.db')}"

# 全局引擎（同步模式，check_same_thread=False 允许跨线程访问）
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

# ============================================================
# 种子数据（用纯 dict 存储，避免 SQLAlchemy expunge 导致的 DetachedInstanceError）
# ============================================================
_SEED_DATA: list[dict] = [
    dict(
        order_id="GY10086",
        status="运输中",
        carrier="顺丰速运",
        tracking_number="SF1234567890",
        current_location="广州市白云分拣中心",
        estimated_delivery="2026-06-05",
        recipient="张三",
        address="北京市朝阳区望京SOHO T1-1806",
    ),
    dict(
        order_id="GY10010",
        status="已签收",
        carrier="中通快递",
        tracking_number="ZT9876543210",
        current_location="已送达",
        estimated_delivery="2026-05-28",
        recipient="李四",
        address="上海市浦东新区张江高科技园区",
    ),
    dict(
        order_id="GY20480",
        status="待发货",
        carrier="待分配",
        tracking_number="",
        current_location="仓库",
        estimated_delivery="2026-06-08",
        recipient="王五",
        address="深圳市南山区科技园南路 9 号",
    ),
]


def init_db() -> None:
    """初始化数据库：建表 + 写入种子数据（幂等：已存在的订单跳过）。"""
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        existing_ids = session.exec(select(Order.order_id)).all()
        existing_set = set(existing_ids)

        new_orders = [Order(**d) for d in _SEED_DATA if d["order_id"] not in existing_set]
        if new_orders:
            session.add_all(new_orders)
            session.commit()


@contextmanager
def get_session():
    """同步 session 生成器（context manager 模式）。

    用法:
        with get_session() as session:
            order = session.exec(select(Order).where(...)).first()
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
