"""SQLModel 数据表定义 — Order 订单模型与状态枚举"""

from enum import Enum

from sqlmodel import Field, SQLModel


class OrderStatus(str, Enum):
    """订单状态枚举（中文值，与业务侧保持一致）"""
    PENDING_SHIPPING = "待发货"
    IN_TRANSIT = "运输中"
    DELIVERED = "已签收"
    CANCELLED = "已取消"


class Order(SQLModel, table=True):
    """订单表 — 映射到 SQLite 的 orders 表"""
    __tablename__ = "orders"

    id: int | None = Field(default=None, primary_key=True)
    order_id: str = Field(max_length=32, unique=True, index=True, description="订单号，如 GY10086")
    status: str = Field(max_length=16, default=OrderStatus.PENDING_SHIPPING, description="订单状态")
    carrier: str = Field(max_length=64, default="", description="快递公司")
    tracking_number: str = Field(max_length=64, default="", description="运单号")
    current_location: str = Field(max_length=128, default="", description="当前位置")
    estimated_delivery: str = Field(max_length=32, default="", description="预计送达日期")
    recipient: str = Field(max_length=64, default="", description="收件人")
    address: str = Field(max_length=256, default="", description="收货地址")
