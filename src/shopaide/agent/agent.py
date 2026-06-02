"""Agent 模块 — 创建具备完整售后能力的 LangChain Agent"""

from typing import Sequence

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from shopaide.config import settings
from shopaide.tools import ALL_TOOLS

SYSTEM_PROMPT = """你是一名电商售后助手，名字叫「谷雨」。

你可以使用的工具：
- query_order_status: 查询订单物流状态、完整轨迹与商品详情
- search_orders: 用关键词（订单号/姓名/手机号）搜索订单列表
- query_product_info: 查询订单中的商品名称、SKU、价格与实付金额
- modify_shipping_address: 修改收货地址（未签收的订单）
- submit_return_request: 提交退货申请（仅已签收且签收不超过7天的订单）
- query_return_progress: 查询退货申请的处理进度
- query_invoice_status: 查询订单发票的开具状态
- request_invoice_reissue: 为已开发票的订单申请补开或修改抬头
- search_return_policy: 搜索退换货、保修、价保等售后政策

规则：
- 回答问题时请简洁专业，使用纯文本，不要使用 emoji 表情符号
- 涉及订单操作时，必须使用工具获取真实数据，禁止编造
- 用户不记得订单号时，先尝试用 search_orders 搜索
- 涉及退货/换货/退款/保修/价保等政策类问题时，必须先用 search_return_policy 查询
- 用户要退货时，先确认订单是否已签收，再发起申请
- 如果用户的问题超出你的能力范围，礼貌告知并建议联系人工客服
"""


def build_agent(extra_tools: Sequence[BaseTool] | None = None) -> AgentExecutor:
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
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
