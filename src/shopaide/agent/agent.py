"""Agent 模块 — 创建具备 Tool Calling + RAG 知识检索能力的 LangChain Agent"""

from typing import Sequence

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from shopaide.config import settings
from shopaide.tools import ALL_TOOLS

# 系统提示词：定义 Agent 的角色边界和行为规范
SYSTEM_PROMPT = """你是一名电商售后助手，名字叫「谷雨」。

你可以使用的工具：
- query_order_status: 查询订单物流状态
- modify_shipping_address: 修改收货地址（未签收的订单）
- search_return_policy: 搜索退换货政策与售后规则

规则：
- 回答问题时请简洁专业，使用纯文本，不要使用 emoji 表情符号
- 涉及订单操作时，必须使用工具获取真实数据，禁止编造
- 涉及退货、换货、退款等政策类问题时，必须先用 search_return_policy 查询
  政策原文，再根据原文回答，禁止凭记忆编造规则
- 如果用户的问题超出你的能力范围，礼貌告知并建议联系人工客服
"""


def build_agent(extra_tools: Sequence[BaseTool] | None = None) -> AgentExecutor:
    """构建并返回一个即用型 AgentExecutor。

    Args:
        extra_tools: 调用方可注入额外工具（Chainlit 等场景按需扩展）

    Returns:
        AgentExecutor 实例，调用 agent.invoke({"input": "..."}) 即可
    """

    # ---- ⚠️ Pydantic 兼容性提醒 ----
    # LangChain 0.3+ 已全面适配 Pydantic v2。
    # 如果环境中同时安装了 pydantic v1 和 v2，可能出现
    # "ValidationError" 或 "Cannot find reference" 等错误。
    # 解决方法：确保只安装 pydantic>=2.0.0，不要混装 v1。
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
