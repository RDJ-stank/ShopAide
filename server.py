"""ShopAide FastAPI 入口 — REST API 接口层"""

import json
import logging
import os
import uuid

from contextlib import asynccontextmanager
from secrets import compare_digest

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlmodel import Session

from shopaide.agent.agent import build_agent
from shopaide.config import settings
from shopaide.database.repository import (
    check_order_alert,
    create_dispute_case,
    create_escalation,
    create_invoice_reissue,
    create_return_order,
    get_dispute_by_id,
    get_invoice_by_order_id,
    get_logistics_trail,
    get_order_by_id,
    get_return_by_id,
    get_return_by_order_id,
    search_orders,
    update_order_address,
)
from shopaide.database.session import get_session, init_db
from shopaide.integrations.feishu import parse_message_event, send_text_message
from shopaide.messaging.redis_queue import RedisQueue

logger = logging.getLogger(__name__)

# ---- Sentry 错误监控（可选，未配 SENTRY_DSN 则跳过） ----
if settings.sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            environment=os.getenv("ENV", "development"),
        )
        logging.getLogger("sentry_sdk").setLevel(logging.WARNING)
    except ImportError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ShopAide API", version="0.5.0", lifespan=lifespan)

# CORS — 允许小程序、Web UI 等前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API 鉴权（Bearer Token 验证）
# ============================================================
_API_TOKEN = settings.api_access_token


def verify_token(authorization: str = Header(default="")) -> None:
    """验证 API 请求的 Bearer Token。

    若未配置 API_ACCESS_TOKEN 环境变量则跳过验证（兼容本地开发）。
    配置后所有业务端点都需携带 Authorization: Bearer <token> 请求头。
    """
    if not _API_TOKEN:
        return  # 未配置 token 时开放所有请求（本地开发模式）
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证令牌，请在 Authorization 请求头中提供 Bearer Token")
    token = authorization.removeprefix("Bearer ")
    if not compare_digest(token, _API_TOKEN):
        raise HTTPException(status_code=403, detail="认证令牌无效")


def get_db(_auth: None = Depends(verify_token)):
    """数据库 session 注入（同时携带 API 鉴权）。

    所有使用 Depends(get_db) 的端点自动需要 Bearer Token。
    /api/health 和 /api/feishu/callback 不使用 get_db，保持公开访问。
    """
    with get_session() as session:
        yield session


# ============================================================
# Schemas
# ============================================================
class OrderResponse(BaseModel):
    order_id: str; status: str; carrier: str; tracking_number: str
    current_location: str; estimated_delivery: str; recipient: str
    phone: str; address: str
    item_name: str; item_sku: str; item_price: float
    item_quantity: int; discount_amount: float; payment_method: str


class LogisticsEventResponse(BaseModel):
    timestamp: str; location: str; status_desc: str


class UpdateAddressRequest(BaseModel):
    new_address: str = Field(..., min_length=1, max_length=500, description="新收货地址")


class UpdateAddressResponse(BaseModel):
    success: bool; message: str
    order_id: str | None = None; new_address: str | None = None


class CreateReturnRequest(BaseModel):
    order_id: str = Field(..., min_length=1, max_length=32)
    reason: str = Field(..., min_length=1, max_length=500)


class ReturnResponse(BaseModel):
    return_id: str; order_id: str; reason: str; status: str
    apply_time: str; approved_time: str; shipped_time: str
    received_time: str; refund_time: str; refund_amount: float


class InvoiceResponse(BaseModel):
    invoice_id: str; order_id: str; title: str; tax_number: str
    status: str; issue_time: str; amount: float


class ReissueRequest(BaseModel):
    new_title: str = Field(..., min_length=1, max_length=200)
    tax_number: str = Field(default="", max_length=32)


class ProductResponse(BaseModel):
    order_id: str; item_name: str; item_sku: str
    item_price: float; item_quantity: int
    discount_amount: float; payment_method: str


class CreateDisputeRequest(BaseModel):
    order_id: str = Field(..., min_length=1, max_length=32)
    description: str = Field(..., min_length=1, max_length=1000)
    damage_type: str = Field(..., min_length=1, max_length=32)


class DisputeResponse(BaseModel):
    case_id: str; order_id: str; description: str; damage_type: str
    responsibility: str; resolution: str
    compensation_amount: float; status: str
    created_time: str; resolved_time: str


class AlertResponse(BaseModel):
    has_alert: bool; alert_type: str; detail: str; suggestion: str


class CreateEscalationRequest(BaseModel):
    order_id: str = Field(default="", max_length=32)
    reason: str = Field(..., min_length=1, max_length=100)
    context_summary: str = Field(..., min_length=1, max_length=2000)


class EscalationResponse(BaseModel):
    escalation_id: str; order_id: str; reason: str
    user_description: str; context_summary: str
    status: str; created_time: str


# ============================================================
# 健康检查
# ============================================================
@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---- 微信校验文件（业务域名验证用） ----
@app.get("/{filename}.txt")
def wechat_verify(filename: str):
    """微信业务域名校验文件路由。

    将微信下载的 .txt 校验文件放到项目根目录,
    微信会自动访问 https://域名/XXXX.txt 验证。
    验证通过后可删除此路由。
    """
    filepath = os.path.join(os.path.dirname(__file__), f"{filename}.txt")
    if os.path.exists(filepath):
        return FileResponse(filepath)
    raise HTTPException(status_code=404)


# ============================================================
# 订单
# ============================================================
@app.get("/api/orders/search", response_model=list[OrderResponse])
def api_search_orders(keyword: str = Query(..., min_length=1), session: Session = Depends(get_db)):
    return search_orders(session, keyword)


@app.get("/api/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, session: Session = Depends(get_db)):
    order = get_order_by_id(session, order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"订单 {order_id} 不存在")
    return order


@app.get("/api/orders/{order_id}/logistics", response_model=list[LogisticsEventResponse])
def get_logistics(order_id: str, session: Session = Depends(get_db)):
    order = get_order_by_id(session, order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"订单 {order_id} 不存在")
    return get_logistics_trail(session, order_id)


@app.put("/api/orders/{order_id}/address", response_model=UpdateAddressResponse)
def change_address(order_id: str, body: UpdateAddressRequest, session: Session = Depends(get_db)):
    order, error = update_order_address(session, order_id, body.new_address)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return UpdateAddressResponse(success=True, message="地址修改成功", order_id=order_id, new_address=body.new_address)


@app.get("/api/orders/{order_id}/products", response_model=ProductResponse)
def get_products(order_id: str, session: Session = Depends(get_db)):
    order = get_order_by_id(session, order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"订单 {order_id} 不存在")
    return order


@app.get("/api/orders/{order_id}/alert", response_model=AlertResponse)
def get_alert(order_id: str, session: Session = Depends(get_db)):
    return check_order_alert(session, order_id)


# ============================================================
# 退货
# ============================================================
@app.post("/api/returns/", response_model=ReturnResponse, status_code=201)
def create_return(body: CreateReturnRequest, session: Session = Depends(get_db)):
    rt, error = create_return_order(session, body.order_id, body.reason)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return rt


@app.get("/api/returns/{return_id}", response_model=ReturnResponse)
def get_return(return_id: str, session: Session = Depends(get_db)):
    rt = get_return_by_id(session, return_id)
    if not rt:
        raise HTTPException(status_code=404, detail=f"退货单 {return_id} 不存在")
    return rt


# ============================================================
# 发票
# ============================================================
@app.get("/api/invoices/{order_id}", response_model=InvoiceResponse)
def get_invoice(order_id: str, session: Session = Depends(get_db)):
    invoice = get_invoice_by_order_id(session, order_id)
    if not invoice:
        raise HTTPException(status_code=404, detail=f"订单 {order_id} 尚无发票记录")
    return invoice


@app.post("/api/invoices/{order_id}/reissue", response_model=InvoiceResponse)
def reissue_invoice(order_id: str, body: ReissueRequest, session: Session = Depends(get_db)):
    invoice, error = create_invoice_reissue(session, order_id, body.new_title, body.tax_number)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return invoice


# ============================================================
# 判责工单
# ============================================================
@app.post("/api/disputes/", response_model=DisputeResponse, status_code=201)
def create_dispute(body: CreateDisputeRequest, session: Session = Depends(get_db)):
    dispute, error = create_dispute_case(session, body.order_id, body.description, body.damage_type)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return dispute


@app.get("/api/disputes/{case_id}", response_model=DisputeResponse)
def get_dispute(case_id: str, session: Session = Depends(get_db)):
    dispute = get_dispute_by_id(session, case_id)
    if not dispute:
        raise HTTPException(status_code=404, detail=f"判责工单 {case_id} 不存在")
    return dispute


# ============================================================
# 升级工单
# ============================================================
@app.post("/api/escalations/", response_model=EscalationResponse, status_code=201)
def create_escalation_api(body: CreateEscalationRequest, session: Session = Depends(get_db)):
    esc = create_escalation(session, body.order_id, body.reason, body.context_summary, body.context_summary)
    return esc


# ============================================================
# 飞书 Bot 回调（接入飞书开放平台）
# ============================================================

# 飞书应用凭证（从环境变量加载）
_FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
_FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

# Redis 队列（可选，未配 REDIS_URL 则走同步 Agent 调用）
_redis_queue: RedisQueue | None = None
if settings.redis_url:
    try:
        _redis_queue = RedisQueue(settings.redis_url)
        _redis_queue.queue_length()  # 探测连接
        logger.info(f"Redis 队列已连接: {settings.redis_url}")
    except Exception as e:
        logger.warning(f"Redis 连接失败({e})，回退到同步 Agent 模式")

# Agent 实例（延迟初始化，避免启动时加载 LLM）
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


@app.post("/api/feishu/callback")
async def feishu_callback(request: Request):
    """飞书事件订阅回调端点。

    1. URL 验证 — 飞书首次配置时会发送 challenge，原样返回
    2. 消息接收 — 用户发消息 → 解析 → Agent 处理 → 飞书 API 回复
    """
    body = await request.json()

    # 始终打印完整请求体，方便排查格式问题
    logger.info(f"飞书回调: type={body.get('type', 'N/A')}, "
                f"header_event={body.get('header', {}).get('event_type', 'N/A')}, "
                f"keys={list(body.keys())}")

    # ---- URL 验证（兼容新旧两版飞书格式） ----
    # 旧格式: {"type": "url_verification", "challenge": "xxx"}
    # 新格式: {"schema": "2.0", "header": {"event_type": "url_verification"}, "event": {"challenge": "xxx"}}
    challenge = None
    if body.get("type") == "url_verification":
        challenge = body.get("challenge", "")
    elif body.get("header", {}).get("event_type") == "url_verification":
        challenge = body.get("event", {}).get("challenge", "")

    if challenge:
        logger.info(f"飞书 URL 验证请求, challenge={challenge[:20]}...")
        return JSONResponse({"challenge": challenge})

    # ---- 消息事件处理 ----
    parsed = parse_message_event(body)
    if not parsed:
        logger.info(f"飞书回调 非消息事件, 忽略")
        return JSONResponse({"code": 0, "msg": "ignored"})

    chat_id = parsed["chat_id"]
    user_text = parsed["text"]
    logger.info(f"飞书消息: chat_id={chat_id[:12]}..., text={user_text[:80]}")

    # 调用 Agent 处理用户消息
    try:
        agent = _get_agent()
        result = await agent.ainvoke(
            {"input": user_text, "chat_history": []},
        )
        reply = result["output"]
    except Exception:
        logger.exception("Agent 调用失败")
        reply = (
            "抱歉，处理您的请求时遇到了问题。\n"
            "可能原因：后端服务暂时不可用或请求超时。\n"
            "如问题持续，请联系人工客服。"
        )

    # 通过飞书 API 发送回复
    if _FEISHU_APP_ID and _FEISHU_APP_SECRET:
        try:
            send_text_message(_FEISHU_APP_ID, _FEISHU_APP_SECRET, chat_id, reply)
        except Exception:
            logger.exception("飞书回复发送失败")
    else:
        logger.warning("FEISHU_APP_ID/FEISHU_APP_SECRET 未配置，无法发送飞书消息")

    return JSONResponse({"code": 0, "msg": "ok"})


# ============================================================
# 通用聊天（消息队列模式 — 高并发入口）
# ============================================================

class ChatRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=2000)
    chat_history: list = Field(default_factory=list)


class ChatResponse(BaseModel):
    task_id: str
    message: str = "任务已接收，请轮询结果"


class ChatResultResponse(BaseModel):
    task_id: str
    ready: bool
    output: str | None = None
    queue_length: int = 0


# 同步回退缓存（无 Redis 时用）
_fallback_results: dict[str, str] = {}


@app.post("/api/chat", response_model=ChatResponse)
def chat_queue(body: ChatRequest):
    """将用户消息推入 Redis 队列，异步处理。

    Worker 进程从队列消费后，结果写入 Redis 缓存。
    前端轮询 /api/chat/{task_id} 获取结果。
    如未配置 REDIS_URL，则回退到同步 Agent 调用（兼容本地开发）。
    """
    if _redis_queue is None:
        agent = _get_agent()
        result = agent.invoke({
            "input": body.input,
            "chat_history": body.chat_history,
        })
        tid = str(uuid.uuid4())[:8]
        _fallback_results[tid] = result["output"]
        return {"task_id": tid, "message": "任务已完成（同步模式）"}

    task_id = _redis_queue.push({
        "input": body.input,
        "chat_history": [{"role": getattr(m, "type", "user"), "content": getattr(m, "content", "")}
                         for m in body.chat_history],
    })
    return ChatResponse(task_id=task_id)


@app.get("/api/chat/{task_id}", response_model=ChatResultResponse)
def chat_result(task_id: str):
    """轮询任务结果。客户端每 1-2 秒调用一次，直到 ready=true。"""
    if _redis_queue is None:
        output = _fallback_results.pop(task_id, None)
        if output is not None:
            return ChatResultResponse(task_id=task_id, ready=True, output=output)
        return ChatResultResponse(task_id=task_id, ready=False)

    output = _redis_queue.get_result(task_id)
    if output is not None:
        return ChatResultResponse(task_id=task_id, ready=True, output=output)
    qlen = _redis_queue.queue_length()
    return ChatResultResponse(task_id=task_id, ready=False, queue_length=qlen)
