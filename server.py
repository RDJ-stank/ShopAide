"""ShopAide FastAPI 入口 — REST API 接口层

启动方式:
    uvicorn server:app --reload --port 9090
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from shopaide.database.repository import get_order_by_id, update_order_address
from shopaide.database.session import get_session, init_db


# ============================================================
# Pydantic schemas（API 层与 ORM 层解耦）
# ============================================================
class OrderResponse(BaseModel):
    order_id: str
    status: str
    carrier: str
    tracking_number: str
    current_location: str
    estimated_delivery: str
    recipient: str
    address: str


class UpdateAddressRequest(BaseModel):
    new_address: str


class UpdateAddressResponse(BaseModel):
    success: bool
    message: str
    order_id: str | None = None
    new_address: str | None = None


# ============================================================
# 应用生命周期
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ShopAide API",
    version="0.2.0",
    lifespan=lifespan,
)


# ============================================================
# 依赖注入
# ============================================================
def get_db():
    """FastAPI Depends 生成器 — 每次请求注入一个 session，响应后自动释放。"""
    with get_session() as session:
        yield session


# ============================================================
# 接口
# ============================================================
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, session: Session = Depends(get_db)):
    """查询订单详情"""
    order = get_order_by_id(session, order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"订单 {order_id} 不存在")
    return order


@app.put("/api/orders/{order_id}/address", response_model=UpdateAddressResponse)
def change_address(
    order_id: str,
    body: UpdateAddressRequest,
    session: Session = Depends(get_db),
):
    """修改订单收货地址"""
    order, error = update_order_address(session, order_id, body.new_address)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return UpdateAddressResponse(
        success=True,
        message="地址修改成功",
        order_id=order_id,
        new_address=body.new_address,
    )
