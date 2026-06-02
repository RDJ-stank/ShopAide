"""SQLModel 数据表定义 — Order 订单 + LogisticsEvent 物流轨迹 + ReturnOrder 退货单"""

from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING_SHIPPING = "待发货"
    IN_TRANSIT = "运输中"
    DELIVERED = "已签收"
    CANCELLED = "已取消"


class ReturnStatus(str, Enum):
    """退货状态枚举"""
    REVIEWING = "审核中"
    WAITING_SHIP = "待寄回"
    INSPECTING = "验收中"
    REFUNDING = "退款中"
    COMPLETED = "已完成"
    REJECTED = "已拒绝"


class Order(SQLModel, table=True):
    """订单表"""
    __tablename__ = "orders"

    id: int | None = Field(default=None, primary_key=True)
    order_id: str = Field(max_length=32, unique=True, index=True, description="订单号")
    status: str = Field(max_length=16, default=OrderStatus.PENDING_SHIPPING)
    carrier: str = Field(max_length=64, default="")
    tracking_number: str = Field(max_length=64, default="")
    current_location: str = Field(max_length=128, default="")
    estimated_delivery: str = Field(max_length=32, default="")
    recipient: str = Field(max_length=64, default="")
    address: str = Field(max_length=256, default="")


class LogisticsEvent(SQLModel, table=True):
    """物流轨迹事件表 — 一个订单关联多条轨迹记录"""
    __tablename__ = "logistics_events"

    id: int | None = Field(default=None, primary_key=True)
    order_id: str = Field(max_length=32, index=True, description="关联订单号")
    timestamp: str = Field(max_length=32, description="事件时间")
    location: str = Field(max_length=128, description="发生地点")
    status_desc: str = Field(max_length=64, description="状态描述（已揽收/运输中/派送中等）")


class ReturnOrder(SQLModel, table=True):
    """退货单表 — 一次退货申请对应一条记录"""
    __tablename__ = "return_orders"

    id: int | None = Field(default=None, primary_key=True)
    return_id: str = Field(max_length=32, unique=True, index=True, description="退货单号，如 RTN20260601-001")
    order_id: str = Field(max_length=32, index=True, description="原订单号")
    reason: str = Field(max_length=256, description="退货原因")
    status: str = Field(max_length=16, default=ReturnStatus.REVIEWING)
    apply_time: str = Field(max_length=32, default="")
    approved_time: str = Field(max_length=32, default="")
    shipped_time: str = Field(max_length=32, default="")
    received_time: str = Field(max_length=32, default="")
    refund_time: str = Field(max_length=32, default="")
    refund_amount: float = Field(default=0.0, description="退款金额")
