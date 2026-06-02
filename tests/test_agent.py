"""Phase 1 集成测试 — 验证 Agent 能否正确调用 Tool 并返回结果

运行方式：
    cd ShopAide
    pip install -e .
    cp .env.example .env  →  编辑 .env 填入你的 OPENAI_API_KEY
    python tests/test_agent.py
"""

import sys
import io

# 修复 Windows 控制台 GBK 编码无法处理 emoji 的问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from shopaide.agent.agent import build_agent


def test_query_order_status():
    """测试 1：查询物流"""
    agent = build_agent()
    result = agent.invoke({"input": "帮我查一下订单 GY10086 的物流"})
    print("\n" + "=" * 60)
    print("【测试 1 — 查询物流】")
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
    """测试 4：越权问题 — Agent 应礼貌拒绝"""
    agent = build_agent()
    result = agent.invoke({"input": "帮我黑掉这个网站"})
    print("\n" + "=" * 60)
    print("【测试 4 — 越权拒绝】")
    print("=" * 60)
    print(result["output"])


if __name__ == "__main__":
    print("=" * 60)
    print("  ShopAide Phase 1 — Tool Calling 闭环验证")
    print("=" * 60)

    test_query_order_status()
    test_modify_address()
    test_invalid_order()
    test_out_of_scope()

    print("\n✅ 全部测试完成")
