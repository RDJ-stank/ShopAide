"""SQLModel 数据表定义 — Order + LogisticsEvent + ReturnOrder + Invoice"""

from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class OrderStatus(str, Enum):
    PENDING_SHIPPING = "待发货"
    IN_TRANSIT = "运输中"
    DELIVERED = "已签收"
    CANCELLED = "已取消"


class ReturnStatus(str, Enum):
    REVIEWING = "审核中"
    WAITING_SHIP = "待寄回"
    INSPECTING = "验收中"
    REFUNDING = "退款中"
    COMPLETED = "已完成"
    REJECTED = "已拒绝"


class InvoiceStatus(str, Enum):
    UNISSUED = "未开"
    ISSUED = "已开"
    REISSUE_PENDING = "已申请补开"


class Order(SQLModel, table=True):
    """订单表"""
    __tablename__ = "orders"

    id: int | None = Field(default=None, primary_key=True)
    order_id: str = Field(max_length=32, unique=True, index=True)
    status: str = Field(max_length=16, default=OrderStatus.PENDING_SHIPPING)
    carrier: str = Field(max_length=64, default="")
    tracking_number: str = Field(max_length=64, default="")
    current_location: str = Field(max_length=128, default="")
    estimated_delivery: str = Field(max_length=32, default="")
    recipient: str = Field(max_length=64, default="")
    phone: str = Field(max_length=20, default="")
    address: str = Field(max_length=256, default="")
    # 商品信息
    item_name: str = Field(max_length=128, default="")
    item_sku: str = Field(max_length=64, default="")
    item_price: float = Field(default=0.0)
    item_quantity: int = Field(default=1)
    discount_amount: float = Field(default=0.0)
    # 支付
    payment_method: str = Field(max_length=32, default="")


class LogisticsEvent(SQLModel, table=True):
    """物流轨迹事件表"""
    __tablename__ = "logistics_events"

    id: int | None = Field(default=None, primary_key=True)
    order_id: str = Field(max_length=32, index=True)
    timestamp: str = Field(max_length=32)
    location: str = Field(max_length=128)
    status_desc: str = Field(max_length=64)


class ReturnOrder(SQLModel, table=True):
    """退货单表"""
    __tablename__ = "return_orders"

    id: int | None = Field(default=None, primary_key=True)
    return_id: str = Field(max_length=32, unique=True, index=True)
    order_id: str = Field(max_length=32, index=True)
    reason: str = Field(max_length=256)
    status: str = Field(max_length=16, default=ReturnStatus.REVIEWING)
    apply_time: str = Field(max_length=32, default="")
    approved_time: str = Field(max_length=32, default="")
    shipped_time: str = Field(max_length=32, default="")
    received_time: str = Field(max_length=32, default="")
    refund_time: str = Field(max_length=32, default="")
    refund_amount: float = Field(default=0.0)


class Invoice(SQLModel, table=True):
    """发票表 — 每个订单最多一条发票记录"""
    __tablename__ = "invoices"

    id: int | None = Field(default=None, primary_key=True)
    invoice_id: str = Field(max_length=32, unique=True, index=True)
    order_id: str = Field(max_length=32, index=True)
    title: str = Field(max_length=128, description="发票抬头")
    tax_number: str = Field(max_length=32, default="", description="税号")
    status: str = Field(max_length=16, default=InvoiceStatus.UNISSUED)
    issue_time: str = Field(max_length=32, default="")
    amount: float = Field(default=0.0)
