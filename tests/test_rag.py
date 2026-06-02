"""Phase 2 RAG 集成测试

运行方式:
    python tests/test_rag.py
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from shopaide.knowledge.policies import POLICIES
from shopaide.knowledge.vector_store import build_vector_store
from shopaide.agent.agent import build_agent


def test_vector_store():
    """测试 1：向量库构建 + 检索"""
    print("\n" + "=" * 60)
    print("【测试 1 — 向量库构建 + 检索测试】")
    print("=" * 60)
    print(f"政策条目数: {len(POLICIES)}")
    print(f"第一条摘要: {POLICIES[0][:60]}...")

    vs = build_vector_store(POLICIES)
    results = vs.similarity_search("退货需要什么条件", k=2)
    print(f"\n检索 '退货需要什么条件' 的 top-2 结果:")
    for i, doc in enumerate(results):
        print(f"\n--- 结果 {i+1} (score 越高越相关) ---")
        print(doc.page_content[:200])
    assert len(results) == 2, "应返回 2 条结果"
    print("\n✅ 向量库构建 + 检索测试通过")


def test_rag_agent_returns():
    """测试 2：Agent + RAG — 退换货政策问答"""
    print("\n" + "=" * 60)
    print("【测试 2 — Agent + RAG：退货政策问答】")
    print("=" * 60)

    agent = build_agent()
    result = agent.invoke({"input": "我买了一件衣服，签收已经5天了，还能退货吗？"})
    print(result["output"])
    print("\n✅ Agent + RAG 政策问答测试通过")


def test_rag_agent_refund():
    """测试 3：Agent + RAG — 退款时效问答"""
    print("\n" + "=" * 60)
    print("【测试 3 — Agent + RAG：退款时效问答】")
    print("=" * 60)

    agent = build_agent()
    result = agent.invoke({"input": "退款一般多久到账？"})
    print(result["output"])
    print("\n✅ Agent + RAG 退款时效问答测试通过")


def test_rag_agent_nonreturnable():
    """测试 4：Agent + RAG — 特殊商品不可退"""
    print("\n" + "=" * 60)
    print("【测试 4 — Agent + RAG：特殊商品不可退】")
    print("=" * 60)

    agent = build_agent()
    result = agent.invoke({"input": "我买的护肤品拆开了还能退吗？"})
    print(result["output"])
    print("\n✅ Agent + RAG 特殊商品问答测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("  ShopAide Phase 2 — RAG 知识检索验证")
    print("=" * 60)

    # 先构建向量库
    print("\n初始化向量库（首次运行会下载 BAAI/bge-small-zh-v1.5 模型，约 100MB）...")
    build_vector_store(POLICIES)

    test_vector_store()
    test_rag_agent_returns()
    test_rag_agent_refund()
    test_rag_agent_nonreturnable()

    print("\n✅ 全部 RAG 测试完成")
