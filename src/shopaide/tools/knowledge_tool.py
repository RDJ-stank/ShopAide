"""知识检索工具 — 将本地政策库包装为 Agent 可调用的 Tool"""

from langchain_core.tools import tool

_retriever_cache = None


def _get_retriever():
    from shopaide.knowledge.vector_store import get_retriever

    global _retriever_cache
    if _retriever_cache is None:
        _retriever_cache = get_retriever()
    return _retriever_cache


@tool
def search_return_policy(query: str) -> str:
    """搜索退换货政策与售后规则。

    当用户询问退货、换货、退款、运费、售后时效、特殊商品是否可退等问题时，
    必须使用此工具获取政策原文后再回答，禁止凭记忆编造规则。

    Args:
        query: 用户想了解的政策关键词（如"退货时效"、"运费规则"等）
    """
    retriever = _get_retriever()
    docs = retriever.invoke(query)
    if not docs:
        return "未找到相关政策信息，建议联系人工客服咨询。"

    lines = []
    for i, doc in enumerate(docs):
        lines.append(doc.page_content)
        lines.append("")
    return "\n".join(lines)
