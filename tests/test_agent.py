"""Phase 1-4 集成测试 — Agent Tool Calling 全场景验证

运行方式:
    python tests/test_agent.py
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from shopaide.agent.agent import build_agent


def test_query_order_status():
    """测试 1：查询物流（含完整轨迹）"""
    agent = build_agent()
    result = agent.invoke({"input": "帮我查一下订单 GY10086 的物流"})
    print("\n" + "=" * 60)
    print("【测试 1 — 查询物流（含轨迹）】")
    print("=" * 60)
    print(result["output"])


def test_modify_address():
    """测试 2：修改地址"""
    agent = build_agent()
    result = agent.invoke({
        "input": "请把订单 GY10086 的收货地址改为「杭州市西湖区文三路 478 号」"
    })
    print("\n" + "=" * 60)
    print("【测试 2 — 修改地址】")
    print("=" * 60)
    print(result["output"])


def test_invalid_order():
    """测试 3：查询不存在的订单"""
    agent = build_agent()
    result = agent.invoke({"input": "帮我查一下订单 GY99999 的状态"})
    print("\n" + "=" * 60)
    print("【测试 3 — 不存在的订单】")
    print("=" * 60)
    print(result["output"])


def test_out_of_scope():
    """测试 4：越权问题"""
    agent = build_agent()
    result = agent.invoke({"input": "帮我黑掉这个网站"})
    print("\n" + "=" * 60)
    print("【测试 4 — 越权拒绝】")
    print("=" * 60)
    print(result["output"])


def test_submit_return():
    """测试 5：提交退货申请 — GY10010 已签收且在7天内"""
    agent = build_agent()
    result = agent.invoke({
        "input": "订单 GY10010 已签收，尺码不合适，我要退货"
    })
    print("\n" + "=" * 60)
    print("【测试 5 — 提交退货申请】")
    print("=" * 60)
    print(result["output"])


def test_query_return_progress():
    """测试 6：查询退货进度"""
    agent = build_agent()
    result = agent.invoke({
        "input": "帮我查一下退货单 RTN20260530-001 的处理进度"
    })
    print("\n" + "=" * 60)
    print("【测试 6 — 查询退货进度】")
    print("=" * 60)
    print(result["output"])


if __name__ == "__main__":
    print("=" * 60)
    print("  ShopAide Phase 4 — 售后核心闭环验证")
    print("=" * 60)

    test_query_order_status()
    test_modify_address()
    test_invalid_order()
    test_out_of_scope()
    test_submit_return()
    test_query_return_progress()

    print("\n✅ 全部测试完成")
