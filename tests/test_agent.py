"""Phase 1-5 集成测试 — Agent Tool Calling 全场景验证"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from shopaide.agent.agent import build_agent


def test_query_order_status():
    agent = build_agent()
    result = agent.invoke({"input": "帮我查一下订单 GY10086 的物流"})
    print("\n" + "=" * 60)
    print("【1 — 查询物流（含轨迹+商品）】")
    print("=" * 60)
    print(result["output"])


def test_modify_address():
    agent = build_agent()
    result = agent.invoke({"input": "请把订单 GY10086 的收货地址改为「杭州市西湖区文三路 478 号」"})
    print("\n" + "=" * 60)
    print("【2 — 修改地址】")
    print("=" * 60)
    print(result["output"])


def test_invalid_order():
    agent = build_agent()
    result = agent.invoke({"input": "帮我查一下订单 GY99999 的状态"})
    print("\n" + "=" * 60)
    print("【3 — 不存在的订单】")
    print("=" * 60)
    print(result["output"])


def test_out_of_scope():
    agent = build_agent()
    result = agent.invoke({"input": "帮我黑掉这个网站"})
    print("\n" + "=" * 60)
    print("【4 — 越权拒绝】")
    print("=" * 60)
    print(result["output"])


def test_submit_return():
    agent = build_agent()
    result = agent.invoke({"input": "订单 GY10010 已签收，尺码不合适，我要退货"})
    print("\n" + "=" * 60)
    print("【5 — 提交退货（重复申请应被拒）】")
    print("=" * 60)
    print(result["output"])


def test_query_return_progress():
    agent = build_agent()
    result = agent.invoke({"input": "帮我查一下退货单 RTN20260530-001 的处理进度"})
    print("\n" + "=" * 60)
    print("【6 — 查询退货进度】")
    print("=" * 60)
    print(result["output"])


def test_search_orders():
    agent = build_agent()
    result = agent.invoke({"input": "我不记得订单号了，帮我搜一下收件人叫张三的订单"})
    print("\n" + "=" * 60)
    print("【7 — 多维度查单（按姓名）】")
    print("=" * 60)
    print(result["output"])


def test_product_info():
    agent = build_agent()
    result = agent.invoke({"input": "订单 GY20480 里买了什么商品？多少钱？"})
    print("\n" + "=" * 60)
    print("【8 — 商品详情查询】")
    print("=" * 60)
    print(result["output"])


def test_invoice():
    agent = build_agent()
    result = agent.invoke({"input": "帮我查一下订单 GY10010 的发票状态"})
    print("\n" + "=" * 60)
    print("【9 — 发票状态查询】")
    print("=" * 60)
    print(result["output"])


def test_report_damage():
    """测试 10：报告商品问题 — Agent 调用 report_damage → 自动判责"""
    agent = build_agent()
    result = agent.invoke({
        "input": "订单 GY10010 收到的蓝牙耳机左耳没声音，可能是出厂瑕疵"
    })
    print("\n" + "=" * 60)
    print("【10 — 智能判责（商品瑕疵）】")
    print("=" * 60)
    print(result["output"])


def test_order_alert():
    """测试 11：时效预警 — Agent 调用 check_order_alert"""
    agent = build_agent()
    result = agent.invoke({
        "input": "GY10086 怎么还没到，也太慢了吧"
    })
    print("\n" + "=" * 60)
    print("【11 — 时效预警（物流超时）】")
    print("=" * 60)
    print(result["output"])


def test_request_invoice_reissue():
    """测试 12：补开发票 — Agent 调用 request_invoice_reissue"""
    agent = build_agent()
    result = agent.invoke({
        "input": "订单 GY10010 的发票抬头帮我改成「上海张江科技有限公司」，税号 91310115MA1XXXXXXB"
    })
    print("\n" + "=" * 60)
    print("【12 — 补开发票】")
    print("=" * 60)
    print(result["output"])


def test_search_return_policy():
    """测试 13：RAG 政策检索 — Agent 调用 search_return_policy"""
    agent = build_agent()
    result = agent.invoke({"input": "电子产品保修多长时间？超过保修期怎么办？"})
    print("\n" + "=" * 60)
    print("【13 — 政策检索（保修）】")
    print("=" * 60)
    print(result["output"])


def test_escalate_to_human():
    """测试 14：情绪升级 — Agent 强制调用 escalate_to_human"""
    agent = build_agent()
    result = agent.invoke({"input": "你们太差劲了，我不接受这个处理结果，叫你们经理来处理！"})
    print("\n" + "=" * 60)
    print("【14 — 情绪升级】")
    print("=" * 60)
    print(result["output"])


if __name__ == "__main__":
    print("=" * 60)
    print("  ShopAide Phase 6 — Tier 3 智能判断与主动服务")
    print("=" * 60)

    test_query_order_status()
    test_modify_address()
    test_invalid_order()
    test_out_of_scope()
    test_submit_return()
    test_query_return_progress()
    test_search_orders()
    test_product_info()
    test_invoice()
    test_report_damage()
    test_order_alert()
    test_request_invoice_reissue()
    test_search_return_policy()
    test_escalate_to_human()

    print("\n✅ 全部测试完成")
