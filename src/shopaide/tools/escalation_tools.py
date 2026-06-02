"""升级工具 — 情绪识别后升级给人工客服"""

from langchain_core.tools import tool

from shopaide.database.repository import create_escalation
from shopaide.database.session import get_session


@tool
def escalate_to_human(order_id: str, reason: str, context_summary: str) -> str:
    """将当前问题升级给人工客服处理。

    当以下情况之一发生时调用此工具：
    1. 用户表现出强烈不满或愤怒情绪（反复投诉、威胁差评、说脏话等）
    2. 问题复杂度超出AI能力范围，需要人工介入
    3. 用户明确要求转人工客服
    4. 同一问题已反复沟通 3 轮以上仍未解决

    Args:
        order_id: 关联订单号（如无关联订单，填 "无"）
        reason: 升级原因（如"用户情绪激动" / "复杂判责" / "用户要求人工"）
        context_summary: 整理好的上下文摘要（问题背景、已尝试的方案、用户诉求）
    """
    with get_session() as session:
        esc = create_escalation(
            session,
            order_id=order_id,
            reason=reason,
            user_description=context_summary,
            context_summary=context_summary,
        )

        return (
            f"已为您转接人工客服，请稍候。\n"
            f"\n"
            f"升级工单编号：{esc.escalation_id}\n"
            f"升级原因：{reason}\n"
            f"创建时间：{esc.created_time}\n"
            f"\n"
            f"--- 立即联系人工客服 ---\n"
            f"客服热线：400-XXX-XXXX（9:00-21:00）\n"
            f"在线客服：工作日 9:00-21:00，周末 10:00-18:00\n"
            f"邮箱：support@guyu-shop.example.com\n"
            f"\n"
            f"如 30 分钟内无人响应，请直接拨打客服热线。"
        )
