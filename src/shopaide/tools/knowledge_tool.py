"""知识检索工具 — 将本地政策库包装为 Agent 可调用的 Tool"""

from langchain.tools.retriever import create_retriever_tool

from shopaide.knowledge.vector_store import get_retriever

_retriever = get_retriever()

search_return_policy = create_retriever_tool(
    retriever=_retriever,
    name="search_return_policy",
    description=(
        "搜索退换货政策与售后规则。"
        "当用户询问退货、换货、退款、运费、售后时效、特殊商品是否可退等问题时，"
        "必须使用此工具获取政策原文后再回答，禁止凭记忆编造规则。"
    ),
)
