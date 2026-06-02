"""Agent 模块 — 创建具备 Tool Calling + RAG + 退货能力的 LangChain Agent"""

from typing import Sequence

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from shopaide.config import settings
from shopaide.tools import ALL_TOOLS

SYSTEM_PROMPT = """你是一名电商售后助手，名字叫「谷雨」。

你可以使用的工具：
- query_order_status: 查询订单物流状态与完整轨迹
- modify_shipping_address: 修改收货地址（未签收的订单）
- submit_return_request: 提交退货申请（仅已签收且签收不超过7天的订单）
- query_return_progress: 查询退货申请的处理进度
- search_return_policy: 搜索退换货政策与售后规则

规则：
- 回答问题时请简洁专业，使用纯文本，不要使用 emoji 表情符号
- 涉及订单操作时，必须使用工具获取真实数据，禁止编造
- 涉及退货、换货、退款等政策类问题时，必须先用 search_return_policy 查询政策原文
- 用户要退货时，先确认订单是否已签收，再发起申请
- 如果用户的问题超出你的能力范围，礼貌告知并建议联系人工客服
"""


def build_agent(extra_tools: Sequence[BaseTool] | None = None) -> AgentExecutor:
    """构建并返回一个即用型 AgentExecutor。"""
    llm = ChatOpenAI(**settings.llm_kwargs)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    tools = list(ALL_TOOLS)
    if extra_tools:
        tools.extend(extra_tools)

    agent = create_tool_calling_agent(llm, tools, prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
    )

    return executor
