"""售后业务工具 — 当前为纯 Python 模拟函数，后续替换为真实 API 调用"""

import time
from langchain_core.tools import tool

# ============================================================
# 模拟数据库：用字典存储订单信息，仅供 MVP 演示
# ============================================================
_MOCK_ORDERS = {
    "GY10086": {
        "order_id": "GY10086",
        "status": "运输中",
        "carrier": "顺丰速运",
        "tracking_number": "SF1234567890",
        "current_location": "广州市白云分拣中心",
        "estimated_delivery": "2026-06-05",
        "recipient": "张三",
        "address": "北京市朝阳区望京SOHO T1-1806",
    },
    "GY10010": {
        "order_id": "GY10010",
        "status": "已签收",
        "carrier": "中通快递",
        "tracking_number": "ZT9876543210",
        "current_location": "已送达",
        "estimated_delivery": "2026-05-28",
        "recipient": "李四",
        "address": "上海市浦东新区张江高科技园区",
    },
    "GY20480": {
        "order_id": "GY20480",
        "status": "待发货",
        "carrier": "待分配",
        "tracking_number": "",
        "current_location": "仓库",
        "estimated_delivery": "2026-06-08",
        "recipient": "王五",
        "address": "深圳市南山区科技园南路 9 号",
    },
}


@tool
def query_order_status(order_id: str) -> str:
    """根据订单号查询物流状态和详细信息。

    Args:
        order_id: 订单号，格式如 GY10086
    """
    order = _MOCK_ORDERS.get(order_id)
    if not order:
        return f"未找到订单 {order_id}，请核实订单号是否正确。"

    lines = [
        f"订单号：{order['order_id']}",
        f"状态：{order['status']}",
        f"快递公司：{order['carrier']}",
        f"运单号：{order['tracking_number'] or '暂无'}",
        f"当前位置：{order['current_location']}",
        f"预计送达：{order['estimated_delivery']}",
        f"收件人：{order['recipient']}",
        f"收件地址：{order['address']}",
    ]
    return "\n".join(lines)


@tool
def modify_shipping_address(order_id: str, new_address: str) -> str:
    """修改指定订单的收货地址（模拟 — 实际会调用OMS接口）。

    Args:
        order_id: 订单号，格式如 GY10086
        new_address: 新的收货地址全称
    """
    order = _MOCK_ORDERS.get(order_id)
    if not order:
        return f"未找到订单 {order_id}，请核实订单号是否正确。"

    if order["status"] in ("已签收", "已取消"):
        return f"订单 {order_id} 当前状态为「{order['status']}」，不支持修改地址。"

    old_address = order["address"]
    order["address"] = new_address
    return (
        f"地址修改成功！\n"
        f"订单号：{order_id}\n"
        f"原地址：{old_address}\n"
        f"新地址：{new_address}"
    )


# 工具列表，Agent 初始化时注册
ALL_TOOLS = [query_order_status, modify_shipping_address]
