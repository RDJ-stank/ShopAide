"""数据库会话管理 — SQLite 同步引擎 + 初始化 + 种子数据"""

import os
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine, select

from shopaide.database.models import (
    DisputeCase, Escalation, Invoice, LogisticsEvent, Order, ReturnOrder,
)

_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..")
_DB_DIR = os.path.abspath(_DB_DIR)
DATABASE_URL = f"sqlite:///{os.path.join(_DB_DIR, 'shopaide.db')}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

# ============================================================
# 种子数据 — 订单（11 个用户，含 created_time 用于时效预警）
# ============================================================
_SEED_ORDERS: list[dict] = [
    # ---- 运输中 ----
    dict(order_id="GY10086", status="运输中", created_time="2026-05-27 09:00",
        carrier="顺丰速运", tracking_number="SF1234567890",
        current_location="广州市白云分拣中心", estimated_delivery="2026-06-05",
        recipient="张三", phone="13800001111",
        address="北京市朝阳区望京SOHO T1-1806",
        item_name="春季新款男士运动夹克", item_sku="SP25-MJ-001-L",
        item_price=399.00, item_quantity=1, discount_amount=40.00,
        payment_method="微信支付"),
    dict(order_id="GY10099", status="运输中", created_time="2026-06-01 10:00",
        carrier="京东物流", tracking_number="JD20260601001",
        current_location="成都分拣中心", estimated_delivery="2026-06-07",
        recipient="赵六", phone="13600004444",
        address="成都市武侯区天府大道 168 号",
        item_name="华为 MateBook 14 轻薄本", item_sku="HW-MB14-2026-SLV",
        item_price=5999.00, item_quantity=1, discount_amount=300.00,
        payment_method="花呗分期"),
    dict(order_id="GY10101", status="运输中", created_time="2026-06-02 08:00",
        carrier="圆通速递", tracking_number="YT20260602001",
        current_location="武汉中转站", estimated_delivery="2026-06-06",
        recipient="孙七", phone="13500005555",
        address="武汉市洪山区珞喻路 1037 号",
        item_name="SK-II 神仙水 230ml", item_sku="SK2-ESS-230",
        item_price=1370.00, item_quantity=1, discount_amount=100.00,
        payment_method="支付宝"),
    dict(order_id="GY10105", status="运输中", created_time="2026-06-02 15:00",
        carrier="中通快递", tracking_number="ZT20260602003",
        current_location="杭州分拣中心", estimated_delivery="2026-06-06",
        recipient="陈十一", phone="13100009999",
        address="杭州市西湖区浙大路 38 号",
        item_name="三只松鼠坚果大礼包", item_sku="SQS-GIFT-2026",
        item_price=168.00, item_quantity=1, discount_amount=20.00,
        payment_method="微信支付"),

    # ---- 已签收 ----
    dict(order_id="GY10010", status="已签收", created_time="2026-05-24 09:00",
        carrier="中通快递", tracking_number="ZT9876543210",
        current_location="已送达", estimated_delivery="2026-05-28",
        recipient="李四", phone="13900002222",
        address="上海市浦东新区张江高科技园区",
        item_name="蓝牙降噪耳机 Pro", item_sku="EP-BT-2026-BLK",
        item_price=299.00, item_quantity=1, discount_amount=0.00,
        payment_method="支付宝"),
    dict(order_id="GY10012", status="已签收", created_time="2026-05-27 09:00",
        carrier="顺丰速运", tracking_number="SF20260528001",
        current_location="已送达", estimated_delivery="2026-05-30",
        recipient="刘八", phone="13300006666",
        address="南京市鼓楼区汉口路 22 号",
        item_name="Nike Air Max 270 跑鞋 42码", item_sku="NK-AM270-42",
        item_price=899.00, item_quantity=1, discount_amount=50.00,
        payment_method="微信支付"),
    dict(order_id="GY10015", status="已签收", created_time="2026-05-22 09:00",
        carrier="邮政EMS", tracking_number="EMS20260525001",
        current_location="已送达", estimated_delivery="2026-05-26",
        recipient="周九", phone="13200007777",
        address="杭州市余杭区文一西路 969 号",
        item_name="戴森 V15 无线吸尘器", item_sku="DS-V15-2026",
        item_price=3990.00, item_quantity=1, discount_amount=400.00,
        payment_method="银行卡"),
    dict(order_id="GY10102", status="已签收", created_time="2026-05-18 09:00",
        carrier="韵达快递", tracking_number="YD20260520001",
        current_location="已送达", estimated_delivery="2026-05-21",
        recipient="吴十", phone="13400008888",
        address="广州市天河区体育西路 100 号",
        item_name="小米空气净化器 4 Pro", item_sku="XM-AP4P-2026",
        item_price=1299.00, item_quantity=1, discount_amount=0.00,
        payment_method="花呗分期"),

    # ---- 待发货（created_time 距今>48h 触发延迟预警） ----
    dict(order_id="GY20480", status="待发货", created_time="2026-06-01 10:00",
        carrier="待分配", tracking_number="",
        current_location="仓库", estimated_delivery="2026-06-08",
        recipient="王五", phone="13700003333",
        address="深圳市南山区科技园南路 9 号",
        item_name="有机绿茶礼盒装 250g", item_sku="FD-TEA-OG-250",
        item_price=128.00, item_quantity=2, discount_amount=10.00,
        payment_method="银行卡"),
    dict(order_id="GY10103", status="待发货", created_time="2026-06-03 09:00",
        carrier="待分配", tracking_number="",
        current_location="仓库", estimated_delivery="2026-06-09",
        recipient="郑十二", phone="13000001110",
        address="重庆市渝中区解放碑步行街 88 号",
        item_name="LEGO 机械组 兰博基尼", item_sku="LG-TECH-42115",
        item_price=2999.00, item_quantity=1, discount_amount=200.00,
        payment_method="支付宝"),

    # ---- 已取消 ----
    dict(order_id="GY10104", status="已取消", created_time="2026-06-01 14:00",
        carrier="", tracking_number="",
        current_location="", estimated_delivery="",
        recipient="冯十三", phone="12900001111",
        address="长沙市岳麓区麓山南路 932 号",
        item_name="Apple AirPods Pro 2", item_sku="AP-APP2-2026",
        item_price=1799.00, item_quantity=1, discount_amount=0.00,
        payment_method="微信支付"),
]

# ============================================================
# 种子数据 — 物流轨迹
# ============================================================
_SEED_LOGISTICS: list[dict] = [
    dict(order_id="GY10086", timestamp="2026-05-28 08:30", location="深圳宝安仓库", status_desc="已揽收"),
    dict(order_id="GY10086", timestamp="2026-05-29 20:15", location="深圳分拣中心", status_desc="运输中"),
    dict(order_id="GY10086", timestamp="2026-05-30 06:30", location="广州白云分拣中心", status_desc="已发往北京"),
    dict(order_id="GY10010", timestamp="2026-05-26 09:00", location="上海浦东仓库", status_desc="已揽收"),
    dict(order_id="GY10010", timestamp="2026-05-26 22:00", location="上海分拣中心", status_desc="运输中"),
    dict(order_id="GY10010", timestamp="2026-05-27 15:00", location="上海浦东新区张江网点", status_desc="派送中"),
    dict(order_id="GY10010", timestamp="2026-05-28 10:20", location="已签收", status_desc="已签收（本人）"),
    dict(order_id="GY10099", timestamp="2026-06-01 09:00", location="北京京东仓", status_desc="已揽收"),
    dict(order_id="GY10099", timestamp="2026-06-02 03:00", location="郑州分拣中心", status_desc="运输中"),
    dict(order_id="GY10099", timestamp="2026-06-02 18:00", location="成都分拣中心", status_desc="到达派送网点"),
    dict(order_id="GY10012", timestamp="2026-05-28 10:00", location="上海嘉定仓库", status_desc="已揽收"),
    dict(order_id="GY10012", timestamp="2026-05-29 08:00", location="南京分拣中心", status_desc="运输中"),
    dict(order_id="GY10012", timestamp="2026-05-30 11:20", location="已签收", status_desc="已签收（家人代收）"),
    dict(order_id="GY10101", timestamp="2026-06-02 07:00", location="深圳前海保税仓", status_desc="已揽收"),
    dict(order_id="GY10101", timestamp="2026-06-02 22:00", location="武汉中转站", status_desc="运输中"),
]

# ============================================================
# 种子数据 — 退货单
# ============================================================
_SEED_RETURNS: list[dict] = [
    dict(return_id="RTN20260530-001", order_id="GY10010",
        reason="尺码不合适", status="已完成",
        apply_time="2026-05-30 14:00", approved_time="2026-05-30 16:00",
        shipped_time="2026-05-31 10:00", received_time="2026-06-02 09:00",
        refund_time="2026-06-02 14:30", refund_amount=299.00),
    dict(return_id="RTN20260601-001", order_id="GY10102",
        reason="净化器噪音过大", status="审核中",
        apply_time="2026-06-01 20:00", approved_time="",
        shipped_time="", received_time="", refund_time="", refund_amount=1299.00),
    dict(return_id="RTN20260602-001", order_id="GY10015",
        reason="吸尘器充电底座故障", status="待寄回",
        apply_time="2026-06-02 10:00", approved_time="2026-06-02 15:00",
        shipped_time="", received_time="", refund_time="", refund_amount=0.00),
]

# ============================================================
# 种子数据 — 发票
# ============================================================
_SEED_INVOICES: list[dict] = [
    dict(invoice_id="INV20260529-001", order_id="GY10010",
        title="李四", tax_number="", status="已开",
        issue_time="2026-05-29 10:00", amount=299.00),
    dict(invoice_id="INV20260601-001", order_id="GY10099",
        title="成都羽田科技有限公司", tax_number="91510100MA6XXXXXXA",
        status="已开", issue_time="2026-06-01 14:00", amount=5699.00),
    dict(invoice_id="INV20260602-001", order_id="GY10103",
        title="郑十二", tax_number="", status="未开",
        issue_time="", amount=2799.00),
]

# ============================================================
# 种子数据 — 判责工单
# ============================================================
_SEED_DISPUTES: list[dict] = [
    dict(case_id="DSP20260601-001", order_id="GY10010",
        description="蓝牙耳机左耳无声，可能为出厂瑕疵",
        damage_type="商品瑕疵", responsibility="商家责任",
        resolution="退货退款", compensation_amount=299.00,
        status="已解决",
        created_time="2026-06-01 09:00", resolved_time="2026-06-01 17:00"),
    dict(case_id="DSP20260602-001", order_id="GY10012",
        description="收到时鞋盒严重压烂，鞋子表面有划痕",
        damage_type="物流损坏", responsibility="物流责任",
        resolution="换货", compensation_amount=0.00,
        status="处理中",
        created_time="2026-06-02 14:00", resolved_time=""),
]


def init_db() -> None:
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
