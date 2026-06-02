"""ShopAide FastAPI 入口 — REST API 接口层"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from shopaide.database.repository import (
    create_invoice_reissue,
    create_return_order,
    get_invoice_by_order_id,
    get_logistics_trail,
    get_order_by_id,
    get_return_by_id,
    get_return_by_order_id,
    search_orders,
    update_order_address,
)
from shopaide.database.session import get_session, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ShopAide API", version="0.4.0", lifespan=lifespan)


def get_db():
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
    new_address: str


class UpdateAddressResponse(BaseModel):
    success: bool; message: str
    order_id: str | None = None; new_address: str | None = None


class CreateReturnRequest(BaseModel):
    order_id: str; reason: str


class ReturnResponse(BaseModel):
    return_id: str; order_id: str; reason: str; status: str
    apply_time: str; approved_time: str; shipped_time: str
    received_time: str; refund_time: str; refund_amount: float


class InvoiceResponse(BaseModel):
    invoice_id: str; order_id: str; title: str; tax_number: str
    status: str; issue_time: str; amount: float

class ReissueRequest(BaseModel):
    new_title: str; tax_number: str = ""


class ProductResponse(BaseModel):
    order_id: str; item_name: str; item_sku: str
    item_price: float; item_quantity: int
    discount_amount: float; payment_method: str


# ============================================================
# 健康检查
# ============================================================
@app.get("/api/health")
def health():
    return {"status": "ok"}


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
