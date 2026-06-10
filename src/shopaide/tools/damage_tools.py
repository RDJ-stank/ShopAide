"""判责与预警工具 — 商品问题报告 + 时效风险检查"""

from langchain_core.tools import tool

from shopaide.database.models import DamageType, Responsibility
from shopaide.database.repository import (
    check_order_alert as _repo_check_alert,
    create_dispute_case as _repo_create_dispute,
    get_dispute_by_id,
    get_order_by_id,
)
from shopaide.database.session import get_session

_VALID_DAMAGE_TYPES = tuple(d.value for d in DamageType)


@tool
def report_damage(order_id: str, description: str, damage_type: str) -> str:
    """报告订单商品问题（损坏/瑕疵/缺失等），系统将自动判定责任方并给出处理方案。

    当用户说"收到的东西坏了/少了/不对"时，使用此工具创建判责工单。

    Args:
        order_id: 订单号，格式如 GY10086
        description: 问题描述（用户原文即可）
        damage_type: 问题类型，可选值：物流损坏 / 商品瑕疵 / 缺失件 / 错发漏发 / 其他
    """
    if damage_type not in _VALID_DAMAGE_TYPES:
        options = " / ".join(_VALID_DAMAGE_TYPES)
        return f"无效的问题类型「{damage_type}」，请从以下选项中选择：{options}"

    with get_session() as session:
        dispute, error = _repo_create_dispute(session, order_id, description, damage_type)
        if error:
            return error

        lines = [
            f"判责工单已创建！",
            f"",
            f"工单编号：{dispute.case_id}",
            f"订单号：{order_id}",
            f"问题类型：{dispute.damage_type}",
            f"问题描述：{dispute.description}",
            f"",
            f"--- 系统判定 ---",
            f"责任方：{dispute.responsibility}",
            f"推荐方案：{dispute.resolution}",
            f"",
        ]
        if dispute.responsibility == Responsibility.COURIER.value:
            lines.append("快递运输过程中造成的损坏，将由物流公司赔付。")
            lines.append("我们将为您安排换货，新商品将在 2 个工作日内发出。")
        elif dispute.responsibility == Responsibility.SELLER.value:
            lines.append("此问题为商家责任，我们将按以下流程处理：")
            if "退货退款" in dispute.resolution:
                lines.append("→ 商家承担运费，全额退款（含原运费）。")
            elif "换货" in dispute.resolution:
                lines.append("→ 商家承担运费，为您换发新商品。")
            elif "补发" in dispute.resolution:
                lines.append("→ 商家为您补发缺失商品，无需退回。")
        else:
            lines.append("客服将在 24 小时内人工复核，请保持手机畅通。")

        return "\n".join(lines)


@tool
def check_order_alert(order_id: str) -> str:
    """检查订单是否存在时效风险（延迟发货、物流停滞、配送超时等）。

    当用户询问"怎么还没到/为什么这么慢"时，使用此工具检查异常状态。

    Args:
        order_id: 订单号，格式如 GY10086
    """
    with get_session() as session:
        alert = _repo_check_alert(session, order_id)

        if not alert["has_alert"]:
            return alert["detail"]

        return (
            f"⚠️ {alert['alert_type']}\n"
            f"{alert['detail']}\n"
            f"\n"
            f"建议：{alert['suggestion']}"
        )
