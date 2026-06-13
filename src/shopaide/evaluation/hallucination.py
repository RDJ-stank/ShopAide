"""Agent 幻觉检测与评估引擎

对 Agent 的每一轮回复进行多维检测：
  - TOOL_BACKED:    输出是否基于工具返回的结果（检测"口头答应但没调工具"）
  - NO_FABRICATION: 输出中的事实值（订单号/金额/日期）是否与工具返回一致
  - POLICY_GROUNDED: 涉及政策的回答是否引用了 search_return_policy 的原文
"""

import re
from dataclasses import dataclass, field
from typing import Any

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.callbacks import BaseCallbackHandler


# ============================================================
# 1. 工具调用追踪器（LangChain Callback）
# ============================================================
class ToolTraceCallback(BaseCallbackHandler):
    """捕获 Agent 执行过程中的每一次工具调用及其返回值。"""

    def __init__(self):
        self.calls: list[dict] = []  # [{tool_name, input, output}, ...]

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """Agent 决定调用工具时触发。"""
        self.calls.append({
            "tool_name": action.tool,
            "input": action.tool_input,
            "output": None,
        })

    def on_tool_end(self, output: str, *, name: str = "", **kwargs: Any) -> None:
        """工具返回结果时触发。"""
        for call in reversed(self.calls):
            if call["tool_name"] == name and call["output"] is None:
                call["output"] = output
                break


# ============================================================
# 2. 评估结果数据类
# ============================================================
class EvalFlag:
    GROUNDED   = "GROUNDED"      # 输出基于工具结果，可信
    UNVERIFIED = "UNVERIFIED"    # 无法验证（无相关工具调用但内容无害）
    SUSPICIOUS = "SUSPICIOUS"    # 可疑（工具返回了结果但回复可能编造了额外内容）
    HALLUCINATED = "HALLUCINATED"  # 幻觉（明显编造了不存在的数据）


@dataclass
class EvalResult:
    flag: str                              # EvalFlag 值
    dimension: str                         # TOOL_BACKED / NO_FABRICATION / POLICY_GROUNDED
    score: float                           # 0.0-1.0
    detail: str                            # 人类可读的评估说明
    tool_calls: list[dict] = field(default_factory=list)
    evidence: str = ""                     # 支撑结论的证据

    def is_clean(self) -> bool:
        return self.flag in (EvalFlag.GROUNDED, EvalFlag.UNVERIFIED)


# ============================================================
# 3. 核心评估函数
# ============================================================
def evaluate_reply(
    user_query: str,
    agent_output: str,
    trace: ToolTraceCallback,
) -> list[EvalResult]:
    """对 Agent 的一轮回复做全维度幻觉评估。

    Args:
        user_query: 用户原始提问
        agent_output: Agent 最终回复文本
        trace: 工具调用追踪器（已完成本轮执行）

    Returns:
        3 个维度的 EvalResult 列表：[TOOL_BACKED, NO_FABRICATION, POLICY_GROUNDED]
    """
    results = []
    results.append(_check_tool_backed(user_query, agent_output, trace))
    results.append(_check_fabrication(agent_output, trace))
    results.append(_check_policy_grounded(user_query, agent_output, trace))
    return results


# ---- 维度 1: TOOL_BACKED ----

# 关键词 → 预期应该调用的工具
# 注意：关键词按优先级排列，先匹配的更精确的模式不会被后续宽泛模式覆盖
_TOOL_EXPECTATION = [
    # 精确匹配优先
    (("我要投诉", "叫你们经理", "转人工", "太差劲了", "太差", "太烂了"), "escalate_to_human"),
    (("退货单", "退货进度", "退货到哪里", "退货到哪"), None),  # None = 仅查进度，不需要调 submit_return_request
    (("我要退货", "我要退", "帮我退货", "申请退货", "退掉", "退了", "想退货"), "submit_return_request"),
    (("收到.*坏", "收到.*瑕疵", "收到.*划痕", "收到.*破损", "不工作", "没声音", "不能用"), "report_damage"),
    (("怎么还没到", "为什么这么慢", "太慢了", "还没到", "什么时候发货"), "check_order_alert"),
    (("查一下.*物流", "查.*物流", "到哪了", "物流信息"), "query_order_status"),
    (("保修", "质保", "价保", "退差价", "降了价"), "search_return_policy"),
    (("发票", "开票"), "query_invoice_status"),
    (("搜一下", "不记得订单号", "帮我搜", "搜索.*订单"), None),  # None = search_orders 已经会被 Agent 自动调用
    (("买了什么", "商品.*信息", "商品.*详情"), None),  # None = query_product_info 代理调用
]


def _check_tool_backed(query: str, output: str, trace: ToolTraceCallback) -> EvalResult:
    """检测 Agent 是否调用了应该调用的工具。"""
    called_names = {c["tool_name"] for c in trace.calls}
    expected: list[str] = []
    has_tool_call_required = False

    for keywords, tool_name in _TOOL_EXPECTATION:
        if not any(kw in query for kw in keywords):
            continue
        if tool_name is None:
            # None = 这个场景可以有工具调用但不强制特定工具
            if trace.calls:
                return EvalResult(EvalFlag.GROUNDED, "TOOL_BACKED", 1.0,
                                  f"工具调用完整(非强制): {called_names}", trace.calls, "")
            has_tool_call_required = True
            continue
        if tool_name not in called_names:
            expected.append(tool_name)
            has_tool_call_required = True

    if not expected:
        if not trace.calls and has_tool_call_required:
            return EvalResult(EvalFlag.SUSPICIOUS, "TOOL_BACKED", 0.4,
                              "检测到工具需求但 Agent 未调用任何工具", trace.calls, "")
        if not trace.calls and any(kw in query for kw in ["你好", "谢谢", "再见"]):
            return EvalResult(EvalFlag.GROUNDED, "TOOL_BACKED", 1.0,
                              "闲聊场景，不需要工具调用", trace.calls, "")
        if not trace.calls and len(query) > 5:
            return EvalResult(EvalFlag.UNVERIFIED, "TOOL_BACKED", 0.6,
                              "无工具调用痕迹，但未检测到明显的工具需求", trace.calls, "")
        if not trace.calls:
            return EvalResult(EvalFlag.GROUNDED, "TOOL_BACKED", 1.0,
                              "无需工具调用", trace.calls, "")
        return EvalResult(EvalFlag.GROUNDED, "TOOL_BACKED", 1.0,
                          f"工具调用完整: {called_names}", trace.calls, "")

    # 有缺失的工具调用 → 可疑/幻觉
    return EvalResult(
        EvalFlag.HALLUCINATED, "TOOL_BACKED", 0.0,
        f"缺少预期工具调用: {expected}。Agent 回复中可能口头描述了功能但未实际调用工具。",
        trace.calls,
        f"Query 含关键词触发预期工具, 实际调用: {called_names}"
    )


# ---- 维度 2: NO_FABRICATION ----

def _check_fabrication(output: str, trace: ToolTraceCallback) -> EvalResult:
    """检测输出中的数字/日期/金额是否与工具返回一致。"""
    tool_outputs = "\n".join(c["output"] or "" for c in trace.calls)

    if not tool_outputs:
        return EvalResult(EvalFlag.UNVERIFIED, "NO_FABRICATION", 0.7,
                          "无工具输出可对比，跳过数值校验", trace.calls, "")

    # 从 Agent 输出中提取所有疑似数值的片段
    # 检查是否在工具返回中能找到对应值
    suspicious_pairs: list[str] = []

    # 提取金额 (¥123 或 123元)
    amounts = re.findall(r'(?:¥|￥)?(\d+\.?\d*)\s*元', output)
    for amt in amounts:
        if amt not in tool_outputs:
            suspicious_pairs.append(f"金额{amt}元")

    # 提取订单号
    order_ids = re.findall(r'GY\d{5}', output)
    for oid in order_ids:
        if oid not in tool_outputs:
            suspicious_pairs.append(f"订单号{oid}")

    # 提取退货单号
    return_ids = re.findall(r'RTN\d{8}-\d{3}', output)
    for rid in return_ids:
        if rid not in tool_outputs:
            suspicious_pairs.append(f"退货单号{rid}")

    # 提取日期 (YYYY-MM-DD)
    dates = re.findall(r'20\d{2}-\d{2}-\d{2}', output)
    for d in dates:
        if d not in tool_outputs:
            suspicious_pairs.append(f"日期{d}")

    if suspicious_pairs:
        return EvalResult(
            EvalFlag.SUSPICIOUS, "NO_FABRICATION", 0.3,
            f"发现未在工具返回中出现的事实值: {suspicious_pairs}。"
            "这些值可能是 Agent 从上下文推理得出的而非编造，但建议人工复核。",
            trace.calls,
            f"工具返回中未找到: {suspicious_pairs}"
        )

    return EvalResult(EvalFlag.GROUNDED, "NO_FABRICATION", 1.0,
                      "输出中的关键事实值均可在工具返回中找到对应", trace.calls, "")


# ---- 维度 3: POLICY_GROUNDED ----

_POLICY_KEYWORDS = [
    "退货", "换货", "退款", "保修", "质保", "价保", "无理由", "运费", "签收",
    "日内", "天内", "工作日", "到账", "发票", "仅退款", "降价", "差价", "优惠",
]

def _check_policy_grounded(query: str, output: str, trace: ToolTraceCallback) -> EvalResult:
    """检测涉及政策的回答是否基于 search_return_policy 检索结果。"""
    is_policy_query = any(kw in query for kw in _POLICY_KEYWORDS)
    called_search = any(c["tool_name"] == "search_return_policy" for c in trace.calls)

    if not is_policy_query:
        return EvalResult(EvalFlag.GROUNDED, "POLICY_GROUNDED", 1.0,
                          "非政策类问题，无需校验", trace.calls, "")

    if called_search:
        # 检查是否有政策特有的数字+单位出现在 output 中
        policy_cite_markers = ["7 天", "7天", "15 天", "15天", "30 天", "30天",
                               "24 小时", "3 天", "1-3 个工作日", "3-7 个工作日",
                               "1 年", "3 个月", "48 小时"]
        cited = any(marker in output for marker in policy_cite_markers)
        if cited:
            return EvalResult(EvalFlag.GROUNDED, "POLICY_GROUNDED", 1.0,
                              "已调用 search_return_policy 且回复中引用了政策原文数字", trace.calls, "")
        else:
            return EvalResult(EvalFlag.SUSPICIOUS, "POLICY_GROUNDED", 0.5,
                              "已调用 search_return_policy 但回复中未检测到明确引用标记",
                              trace.calls, "Agent 可能概括了政策但未精确引用原文")

    # 政策类问题但没有调 search_return_policy → 可疑
    return EvalResult(
        EvalFlag.SUSPICIOUS, "POLICY_GROUNDED", 0.2,
        "政策类问题但 Agent 未调用 search_return_policy 工具，"
        "回复可能基于 LLM 自身记忆而非项目知识库。",
        trace.calls,
        "Query 含政策关键词但无 RAG 工具调用"
    )


# ============================================================
# 4. 批量评估报告
# ============================================================
@dataclass
class BatchReport:
    total: int = 0
    grounded: int = 0
    suspicious: int = 0
    hallucinated: int = 0
    details: list[dict] = field(default_factory=list)

    def add(self, query: str, results: list[EvalResult]):
        self.total += len(results)
        for r in results:
            if r.flag == EvalFlag.GROUNDED:
                self.grounded += 1
            elif r.flag in (EvalFlag.SUSPICIOUS, EvalFlag.UNVERIFIED):
                self.suspicious += 1
            else:
                self.hallucinated += 1
            self.details.append({
                "query": query[:60],
                "dimension": r.dimension,
                "flag": r.flag,
                "detail": r.detail,
            })

    def summary(self) -> str:
        pct = self.grounded / max(self.total, 1) * 100
        lines = [
            "=" * 60,
            "  幻觉评估报告",
            "=" * 60,
            f"  总检测维度: {self.total}",
            f"  GROUNDED   (可信):    {self.grounded} ({pct:.0f}%)",
            f"  SUSPICIOUS (待复核):  {self.suspicious}",
            f"  HALLUCINATED (幻觉):  {self.hallucinated}",
            "=" * 60,
        ]
        for d in self.details:
            icon = "✅" if d["flag"] == EvalFlag.GROUNDED else ("⚠️" if d["flag"] != EvalFlag.HALLUCINATED else "❌")
            lines.append(f"  {icon} [{d['dimension']}] {d['detail'][:80]}")
        return "\n".join(lines)
