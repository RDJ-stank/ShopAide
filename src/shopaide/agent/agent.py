"""Agent 模块 — 创建具备 Tool Calling 能力的 LangChain Agent"""

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from shopaide.config import settings
from shopaide.tools.order_tools import ALL_TOOLS

# 系统提示词：定义 Agent 的角色边界和行为规范
SYSTEM_PROMPT = """你是一名电商售后助手，名字叫「谷雨」。

你的职责：
1. 帮助用户查询订单物流状态
2. 帮助用户修改收货地址（在订单未签收的前提下）
3. 根据退换货政策回答用户的售后问题

规则：
- 回答问题时请简洁专业，使用纯文本，不要使用 emoji 表情符号
- 涉及订单操作时，必须使用工具获取真实数据，禁止编造
- 如果用户的问题超出你的能力范围，礼貌告知并建议联系人工客服
"""


def build_agent() -> AgentExecutor:
    """构建并返回一个即用型 AgentExecutor。

    调用方只需 agent.invoke({"input": "用户问题"}) 即可。
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

    agent = create_tool_calling_agent(llm, ALL_TOOLS, prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=True,               # 打印完整推理链，方便调试
        handle_parsing_errors=True, # 解析失败时自动重试，避免直接报错
    )

    return executor
