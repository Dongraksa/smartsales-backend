import os
import shutil
import math
from typing import List, Optional, Any, Dict
from datetime import datetime, timedelta
from collections import defaultdict
from itertools import combinations
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="SmartSales Enterprise API",
    description="ระบบบริหารจัดการร้านค้า สต็อกสินค้า ระบบหลังบ้าน และ Real-Data Analytics (ROP, Market Basket, RFM, Churn Risk & Personal Patterns)",
    version="2.3.0"
)

# ----------------------------------------------------
# 1. ตั้งค่า CORS
# ----------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# 2. ฐานข้อมูลเริ่มต้น (In-Memory / Dynamic Storage)
# ----------------------------------------------------
users_db = [
    {
        "user_id": 1,
        "full_name": "ผู้ดูแลระบบ",
        "email": "admin@example.com",
        "phone": "0800000000",
        "password": "admin",
        "role": "admin"
    },
    {
        "user_id": 2,
        "full_name": "สมชาย สายเปย์",
        "email": "user@example.com",
        "phone": "0812345678",
        "password": "123",
        "role": "customer"
    }
]

products_db = [
    {
        "product_id": 1,
        "product_name": "อเมริกาโน่เย็น (Iced Americano)",
        "category": "เครื่องดื่ม",
        "cost_price": 25.0,
        "selling_price": 55.0,
        "stock_quantity": 45,
        "reorder_threshold": 20,
        "image_url": "https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=300",
        "lead_time_days": 3,
        "safety_stock": 10
    },
    {
        "product_id": 2,
        "product_name": "ลาเต้เย็น (Iced Latte)",
        "category": "เครื่องดื่ม",
        "cost_price": 30.0,
        "selling_price": 65.0,
        "stock_quantity": 12,
        "reorder_threshold": 20,
        "image_url": "https://images.unsplash.com/photo-1570968915860-54d5c301fa9f?w=300",
        "lead_time_days": 4,
        "safety_stock": 15
    },
    {
        "product_id": 3,
        "product_name": "ครัวซองต์เนยสด (Croissant)",
        "category": "เบเกอรี่",
        "cost_price": 20.0,
        "selling_price": 45.0,
        "stock_quantity": 8,
        "reorder_threshold": 20,
        "image_url": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=300",
        "lead_time_days": 2,
        "safety_stock": 10
    }
]

orders_db = [
    {
        "sale_id": 1001,
        "customer_name": "สมชาย สายเปย์",
        "timestamp": "2026-10-08 08:30:15",
        "payment_method": "PromptPay",
        "total_amount": 120.0,
        "status": "Paid",
        "items": [
            {"product_name": "อเมริกาโน่เย็น (Iced Americano)", "quantity": 1, "subtotal": 55.0, "image_url": "https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=300"},
            {"product_name": "ลาเต้เย็น (Iced Latte)", "quantity": 1, "subtotal": 65.0, "image_url": "https://images.unsplash.com/photo-1570968915860-54d5c301fa9f?w=300"}
        ]
    },
    {
        "sale_id": 1002,
        "customer_name": "สมหญิง รักสงบ",
        "timestamp": "2026-09-20 14:15:00",
        "payment_method": "PromptPay",
        "total_amount": 100.0,
        "status": "Paid",
        "items": [
            {"product_name": "อเมริกาโน่เย็น (Iced Americano)", "quantity": 1, "subtotal": 55.0, "image_url": "https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=300"},
            {"product_name": "ครัวซองต์เนยสด (Croissant)", "quantity": 1, "subtotal": 45.0, "image_url": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=300"}
        ]
    },
    {
        "sale_id": 1003,
        "customer_name": "สมชาย สายเปย์",
        "timestamp": "2026-10-12 08:45:00",
        "payment_method": "PromptPay",
        "total_amount": 55.0,
        "status": "Paid",
        "items": [
            {"product_name": "อเมริกาโน่เย็น (Iced Americano)", "quantity": 1, "subtotal": 55.0, "image_url": "https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=300"}
        ]
    }
]

promotions_db = [
    {
        "promo_id": 1,
        "title": "เซตคู่กาแฟ & ครัวซองต์สุดคุ้ม",
        "promo_type": "bundle",
        "product_ids": [1, 3],
        "trigger_product_ids": [],
        "coupon_code": None,
        "discount_type": "fixed",
        "discount_amount": 15.0,
        "discount_text": "ซื้อคู่กันลด 15 บาท",
        "condition_summary": "อเมริกาโน่เย็น + ครัวซองต์เนยสด",
        "usage_count": 28,
        "is_active": True,
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }
]

# ----------------------------------------------------
# 3. Schemas
# ----------------------------------------------------
class LoginSchema(BaseModel):
    email: str
    password: str
    role: Optional[str] = "customer"

class RegisterSchema(BaseModel):
    full_name: str
    email: str
    phone: str
    password: str

class OrderStatusUpdate(BaseModel):
    status: str

class PromotionSchema(BaseModel):
    title: str
    promo_type: str
    product_ids: List[int] = Field(default_factory=list)
    trigger_product_ids: List[int] = Field(default_factory=list)
    coupon_code: Optional[str] = None
    discount_type: str = "fixed"
    discount_amount: float
    start_date: str
    end_date: str

class WinBackCouponSchema(BaseModel):
    customer_name: str
    discount_amount: float

# ----------------------------------------------------
# 4. Page Shortcut Routes
# ----------------------------------------------------
@app.get("/admin")
def route_admin_page():
    if os.path.exists("static/admin.html"):
        return FileResponse("static/admin.html")
    raise HTTPException(status_code=404, detail="ไม่พบไฟล์ static/admin.html")

@app.get("/login")
def route_login_page():
    if os.path.exists("static/login.html"):
        return FileResponse("static/login.html")
    raise HTTPException(status_code=404, detail="ไม่พบไฟล์ static/login.html")

@app.get("/register")
def route_register_page():
    if os.path.exists("static/register.html"):
        return FileResponse("static/register.html")
    raise HTTPException(status_code=404, detail="ไม่พบไฟล์ static/register.html")

# ----------------------------------------------------
# 5. API Endpoints
# ----------------------------------------------------

# --- AUTHENTICATION ---
@app.post("/api/v1/auth/login")
def login(data: LoginSchema):
    if data.role == "admin" or data.email == "admin@example.com":
        if data.password in ["admin", "1234"]:
            return {
                "status": "success",
                "role": "admin",
                "name": "ผู้ดูแลระบบ",
                "token": "admin-secret-token"
            }
        raise HTTPException(status_code=401, detail="รหัสผ่านผู้ดูแลระบบไม่ถูกต้อง")
    
    user = next((u for u in users_db if u["email"] == data.email and u["password"] == data.password), None)
    if user:
        return {
            "status": "success",
            "role": user["role"],
            "name": user["full_name"],
            "token": f"user-token-{user['user_id']}"
        }
    
    raise HTTPException(status_code=401, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")

@app.post("/api/v1/auth/register")
def register(data: RegisterSchema):
    if any(u["email"] == data.email for u in users_db):
        raise HTTPException(status_code=400, detail="อีเมลนี้ถูกใช้งานในระบบแล้ว")
    new_user = {
        "user_id": len(users_db) + 1,
        "full_name": data.full_name,
        "email": data.email,
        "phone": data.phone,
        "password": data.password,
        "role": "customer"
    }
    users_db.append(new_user)
    return {
        "status": "success",
        "message": "สมัครสมาชิกเรียบร้อยแล้ว",
        "user_id": new_user["user_id"]
    }

# --- CHECKOUT & ORDERS HANDLER ---
@app.post("/api/v1/pos/checkout")
@app.post("/api/v1/orders")
@app.post("/api/v1/checkout")
async def create_order(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="รูปแบบข้อมูล JSON ไม่ถูกต้อง")
    
    raw_items = []
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict):
        raw_items = data.get("items") or data.get("cart") or data.get("order_items") or []
    if not raw_items:
        raise HTTPException(status_code=400, detail="ไม่มีรายการสินค้าในตะกร้า")
    
    processed_items = []
    total_amount = 0.0
    product_subtotals = defaultdict(float)
    for item in raw_items:
        p_name = item.get("product_name") or item.get("name") or item.get("title") or "สินค้า"
        qty = int(item.get("quantity") or item.get("qty") or item.get("count") or 1)
        price = float(item.get("selling_price") or item.get("price") or item.get("cost") or 0.0)
        p_id = item.get("product_id") or item.get("id")
        subtotal = price * qty
        total_amount += subtotal
        
        prod = next((p for p in products_db if (p_id and p["product_id"] == p_id) or p["product_name"] == p_name), None)
        if prod:
            prod["stock_quantity"] = max(0, prod["stock_quantity"] - qty)
            product_id = prod["product_id"]
            product_subtotals[product_id] += subtotal
        else:
            product_id = p_id
            
        processed_items.append({
            "product_id": product_id,
            "product_name": p_name,
            "quantity": qty,
            "subtotal": subtotal,
            "image_url": prod["image_url"] if prod else "https://via.placeholder.com/150"
        })
    applied_promotion_ids = []
    total_discount = 0.0
    now = datetime.now() + timedelta(hours=7)
    today = now.strftime("%Y-%m-%d")
    requested_promo_ids = data.get("promotion_ids", []) if isinstance(data, dict) else []
    if not isinstance(requested_promo_ids, list):
        requested_promo_ids = []
    coupon_code = str(data.get("coupon_code", "")).strip().upper() if isinstance(data, dict) else ""
    cart_product_ids = set(product_subtotals)
    seen_promo_ids = set()
    for raw_promo_id in requested_promo_ids:
        try:
            promo_id = int(raw_promo_id)
        except (TypeError, ValueError):
            continue
        if promo_id in seen_promo_ids:
            continue
        seen_promo_ids.add(promo_id)
        promo = next((p for p in promotions_db if p["promo_id"] == promo_id), None)
        if not promo or not promo.get("is_active"):
            continue
        if not promo.get("start_date", "") <= today <= promo.get("end_date", ""):
            continue
        try:
            product_ids = {int(product_id) for product_id in promo.get("product_ids", [])}
            trigger_product_ids = {int(product_id) for product_id in promo.get("trigger_product_ids", [])}
            discount_amount = max(0.0, float(promo.get("discount_amount", 0)))
        except (TypeError, ValueError):
            continue
        if promo.get("promo_type") == "bundle":
            if len(product_ids) < 2 or not product_ids.issubset(cart_product_ids):
                continue
            eligible_product_ids = product_ids
        elif promo.get("promo_type") == "cross_sell":
            if not (trigger_product_ids & cart_product_ids) or not (product_ids & cart_product_ids):
                continue
            eligible_product_ids = product_ids & cart_product_ids
        elif promo.get("promo_type") == "discount_code":
            expected_code = str(promo.get("coupon_code", "")).strip().upper()
            if not expected_code or coupon_code != expected_code:
                continue
            eligible_product_ids = product_ids & cart_product_ids if product_ids else cart_product_ids
        else:
            continue
        eligible_subtotal = sum(product_subtotals[product_id] for product_id in eligible_product_ids)
        if promo.get("discount_type", "fixed") == "percent":
            applied_discount = eligible_subtotal * min(discount_amount, 100.0) / 100
        else:
            applied_discount = min(discount_amount, eligible_subtotal)
        if applied_discount > 0:
            total_discount += applied_discount
            applied_promotion_ids.append(promo["promo_id"])
            promo["usage_count"] = promo.get("usage_count", 0) + 1
    total_discount = min(total_discount, total_amount)
    final_total = max(0.0, total_amount - total_discount)
    payment_method = "PromptPay"
    customer_name = "ลูกค้าทั่วไป"
    if isinstance(data, dict):
        payment_method = data.get("payment_method") or data.get("payment") or "PromptPay"
        customer_name = data.get("customer_name") or "ลูกค้าทั่วไป"
        
    sale_id = max([o["sale_id"] for o in orders_db], default=1000) + 1
    new_order = {
        "sale_id": sale_id,
        "customer_name": customer_name,
        "timestamp": (datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
        "payment_method": payment_method,
        "subtotal_amount": round(total_amount, 2),
        "discount_amount": round(total_discount, 2),
        "total_amount": round(final_total, 2),
        "status": "Paid",
        "items": processed_items
    }
    orders_db.insert(0, new_order)
    return {
        "status": "success",
        "message": "สั่งซื้อสำเร็จเรียบร้อยแล้ว",
        "sale_id": sale_id,
        "subtotal_amount": round(total_amount, 2),
        "discount_amount": round(total_discount, 2),
        "total_amount": round(final_total, 2),
        "promotion_ids": applied_promotion_ids
    }

# --- PRODUCTS MANAGEMENT ---
@app.get("/api/v1/products")
def get_products():
    return products_db

@app.post("/api/v1/admin/products")
def create_product(
    product_name: str = Form(...),
    category: str = Form(...),
    cost_price: float = Form(...),
    selling_price: float = Form(...),
    stock_quantity: int = Form(...),
    reorder_threshold: int = Form(20, ge=0),
    lead_time_days: int = Form(3, ge=0),
    safety_stock: int = Form(10, ge=0),
    manufacture_date: str = Form(""),
    expiration_date: str = Form(""),
    image_file: Optional[UploadFile] = File(None)
):
    new_id = len(products_db) + 1
    image_url = "https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=300"
    
    if image_file:
        os.makedirs("static/uploads", exist_ok=True)
        file_path = f"static/uploads/{new_id}_{image_file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        image_url = f"/uploads/{new_id}_{image_file.filename}"
    new_prod = {
        "product_id": new_id,
        "product_name": product_name,
        "category": category.strip() or "อื่นๆ",
        "cost_price": cost_price,
        "selling_price": selling_price,
        "stock_quantity": stock_quantity,
        "reorder_threshold": reorder_threshold,
        "manufacture_date": manufacture_date,
        "expiration_date": expiration_date,
        "lead_time_days": lead_time_days,
        "safety_stock": safety_stock,
        "image_url": image_url
    }
    products_db.append(new_prod)
    return {"status": "success", "product": new_prod}

@app.put("/api/v1/admin/products/{product_id}")
def update_product(
    product_id: int,
    product_name: str = Form(...),
    category: Optional[str] = Form(None),
    cost_price: float = Form(...),
    selling_price: float = Form(...),
    stock_quantity: int = Form(...),
    reorder_threshold: Optional[int] = Form(None, ge=0),
    lead_time_days: int = Form(3, ge=0),
    safety_stock: int = Form(10, ge=0),
    manufacture_date: str = Form(""),
    expiration_date: str = Form(""),
    image_file: Optional[UploadFile] = File(None)
):
    prod = next((p for p in products_db if p["product_id"] == product_id), None)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
        
    prod["product_name"] = product_name
    if category is not None:
        prod["category"] = category.strip() or "อื่นๆ"
    prod["cost_price"] = cost_price
    prod["selling_price"] = selling_price
    prod["stock_quantity"] = stock_quantity
    if reorder_threshold is not None:
        prod["reorder_threshold"] = reorder_threshold
    prod["manufacture_date"] = manufacture_date
    prod["expiration_date"] = expiration_date
    prod["lead_time_days"] = lead_time_days
    prod["safety_stock"] = safety_stock
    if image_file:
        os.makedirs("static/uploads", exist_ok=True)
        file_path = f"static/uploads/{product_id}_{image_file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        prod["image_url"] = f"/uploads/{product_id}_{image_file.filename}"
    return {"status": "success", "product": prod}

@app.delete("/api/v1/admin/products/{product_id}")
def delete_product(product_id: int):
    global products_db
    products_db = [p for p in products_db if p["product_id"] != product_id]
    return {"status": "success"}

# --- DASHBOARD & ANALYTICS ---
@app.get("/api/v1/admin/dashboard-summary")
def get_dashboard_summary(period: str = "all"):
    now = datetime.now() + timedelta(hours=7)
    valid_orders = []
    for o in orders_db:
        if o.get("status") in ["Paid", "Completed"]:
            try:
                ts = datetime.strptime(o["timestamp"], "%Y-%m-%d %H:%M:%S")
                if period == "daily" and ts.date() != now.date():
                    continue
                elif period == "weekly" and ts < (now - timedelta(days=7)):
                    continue
                elif period == "monthly" and ts < (now - timedelta(days=30)):
                    continue
                valid_orders.append(o)
            except Exception:
                valid_orders.append(o)
    total_revenue = sum(o["total_amount"] for o in valid_orders)
    total_orders = len(valid_orders)
    total_cost = 0.0
    for o in valid_orders:
        for item in o.get("items", []):
            prod = next((p for p in products_db if p["product_name"] == item["product_name"]), None)
            cost_price = prod["cost_price"] if prod else 0.0
            total_cost += cost_price * item.get("quantity", 1)
    total_profit = total_revenue - total_cost
    low_stock_count = len([p for p in products_db if p["stock_quantity"] < p.get("reorder_threshold", 20)])
    return {
        "total_revenue": round(total_revenue, 2),
        "total_cost": round(total_cost, 2),
        "total_profit": round(total_profit, 2),
        "total_orders": total_orders,
        "low_stock_count": low_stock_count
    }

@app.get("/api/v1/admin/orders")
def get_orders():
    return orders_db

@app.patch("/api/v1/admin/orders/{sale_id}/status")
def update_order_status(sale_id: int, status_update: OrderStatusUpdate):
    order = next((o for o in orders_db if o["sale_id"] == sale_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order["status"] = status_update.status
    return {"status": "success", "order": order}

@app.get("/api/v1/analytics/peak-hours")
def get_peak_hours():
    hours_map = {
        "08:00 - 09:00": 0.0, "09:00 - 10:00": 0.0, "10:00 - 11:00": 0.0,
        "11:00 - 12:00": 0.0, "12:00 - 13:00": 0.0, "13:00 - 14:00": 0.0,
        "14:00 - 15:00": 0.0, "15:00 - 16:00": 0.0, "16:00 - 17:00": 0.0,
        "17:00 - 18:00": 0.0, "18:00 - 19:00": 0.0, "19:00 - 20:00": 0.0
    }
    for order in orders_db:
        if order.get("status") in ["Paid", "Completed"]:
            try:
                ts = order.get("timestamp", "")
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                h = dt.hour
                slot_label = f"{h:02d}:00 - {h+1:02d}:00"
                amount = float(order.get("total_amount", 0.0))
                if slot_label in hours_map:
                    hours_map[slot_label] += amount
            except Exception:
                pass
    return [{"hour": hour_label, "total_revenue": round(rev, 2)} for hour_label, rev in hours_map.items()]

@app.get("/api/v1/analytics/abc-analysis")
def get_abc_analysis():
    summary = defaultdict(float)
    for order in orders_db:
        if order.get("status") in ["Paid", "Completed"]:
            for item in order.get("items", []):
                p_name = item.get("product_name", "สินค้าทั่วไป")
                subtotal = float(item.get("subtotal", 0.0))
                summary[p_name] += subtotal
    result = [{"product_name": name, "revenue": round(rev, 2)} for name, rev in summary.items()]
    return result or [{"product_name": "ยังไม่มีข้อมูลการขาย", "revenue": 0.0}]

# --- REAL-DATA MARKET BASKET ANALYSIS ---
@app.get("/api/v1/analytics/market-basket")
def get_market_basket(min_support: float = 0.01, min_confidence: float = 0.01):
    valid_orders = [o for o in orders_db if o.get("status") in ["Paid", "Completed"]]
    total_orders = len(valid_orders)
    
    if total_orders == 0:
        return {"status": "success", "rules": []}
    item_counts = defaultdict(int)
    pair_counts = defaultdict(int)
    for order in valid_orders:
        items = list(set([item["product_name"] for item in order.get("items", []) if "product_name" in item]))
        for item in items:
            item_counts[item] += 1
        for pair in combinations(sorted(items), 2):
            pair_counts[pair] += 1
    rules = []
    for (item1, item2), pair_count in pair_counts.items():
        support = pair_count / total_orders
        if support < min_support:
            continue
            
        conf1 = pair_count / item_counts[item1]
        prob_item2 = item_counts[item2] / total_orders
        lift1 = conf1 / prob_item2 if prob_item2 > 0 else 1.0
        
        if conf1 >= min_confidence:
            rules.append({
                "antecedents": [item1],
                "consequents": [item2],
                "support": round(support, 2),
                "confidence": round(conf1, 2),
                "lift": round(lift1, 2)
            })
    rules = sorted(rules, key=lambda x: x["lift"], reverse=True)
    return {"status": "success", "rules": rules}

# --- REAL-DATA REORDER POINT (ROP) ANALYSIS ---
@app.get("/api/v1/analytics/reorder-points")
def get_reorder_points():
    now = datetime.now() + timedelta(hours=7)
    cutoff = now - timedelta(days=30)
    product_sales_qty = defaultdict(int)
    for order in orders_db:
        if order.get("status") not in ["Paid", "Completed"]:
            continue
        try:
            order_time = datetime.strptime(order.get("timestamp", ""), "%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            continue
        if not cutoff <= order_time <= now:
            continue
        for item in order.get("items", []):
            p_name = item.get("product_name")
            try:
                qty = int(item.get("quantity", 1))
            except (TypeError, ValueError):
                continue
            if p_name and qty > 0:
                product_sales_qty[p_name] += qty
    results = []
    days_evaluated = 30
    
    for p in products_db:
        p_name = p["product_name"]
        total_sold = product_sales_qty.get(p_name, 0)
        
        daily_usage = total_sold / days_evaluated
        lead_time = p.get("lead_time_days", 3)
        safety = p.get("safety_stock", 10)
        stock = p.get("stock_quantity", 0)
        
        rop = math.ceil((daily_usage * lead_time) + safety)
        status = "CRITICAL" if stock == 0 else ("REORDER_NOW" if stock <= rop else "OK")
        
        results.append({
            "product_id": p["product_id"],
            "product_name": p_name,
            "current_stock": stock,
            "daily_usage": round(daily_usage, 2),
            "lead_time_days": lead_time,
            "safety_stock": safety,
            "reorder_point": rop,
            "status": status
        })
    return {"status": "success", "reorder_points": results}

# --- REAL-DATA RFM ANALYSIS ---
@app.get("/api/v1/analytics/rfm")
def get_rfm_analysis():
    now = datetime.now() + timedelta(hours=7)
    valid_orders = [o for o in orders_db if o.get("status") in ["Paid", "Completed"]]
    
    customer_stats = defaultdict(lambda: {"last_date": None, "frequency": 0, "monetary": 0.0})
    
    for order in valid_orders:
        c_name = order.get("customer_name") or "ลูกค้าทั่วไป"
        amount = float(order.get("total_amount", 0.0))
        ts_str = order.get("timestamp")
        
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            dt = now
            
        stats = customer_stats[c_name]
        stats["frequency"] += 1
        stats["monetary"] += amount
        if stats["last_date"] is None or dt > stats["last_date"]:
            stats["last_date"] = dt
    rfm_results = []
    for c_name, stats in customer_stats.items():
        recency_days = (now - stats["last_date"]).days if stats["last_date"] else 0
        f = stats["frequency"]
        m = stats["monetary"]
        
        r_score = 5 if recency_days <= 3 else (4 if recency_days <= 7 else (3 if recency_days <= 14 else (2 if recency_days <= 30 else 1)))
        f_score = 5 if f >= 5 else (4 if f >= 3 else (3 if f >= 2 else 1))
        m_score = 5 if m >= 1000 else (4 if m >= 500 else (3 if m >= 300 else 1))
        
        if f_score >= 4 or m_score >= 4:
            segment = "Champions (ลูกค้า VIP)"
        elif f_score >= 2 or m_score >= 3:
            segment = "Loyal Customers (ลูกค้าประจำ)"
        elif recency_days > 14:
            segment = "At Risk (เสี่ยงเลิกซื้อ)"
        elif f == 1:
            segment = "New Customer (ลูกค้าใหม่)"
        else:
            segment = "General Customer (ลูกค้าทั่วไป)"
            
        rfm_results.append({
            "customer_name": c_name,
            "recency_days": recency_days,
            "frequency": f,
            "monetary": round(m, 2),
            "scores": f"R:{r_score} F:{f_score} M:{m_score}",
            "segment": segment
        })
        
    return {"status": "success", "rfm_data": rfm_results}

# --- NEW FEATURE 1: CUSTOMER CHURN RISK & WIN-BACK ---
@app.get("/api/v1/analytics/churn-risk")
def get_churn_risk_analysis():
    now = datetime.now() + timedelta(hours=7)
    valid_orders = [o for o in orders_db if o.get("status") in ["Paid", "Completed"]]
    
    customer_history = defaultdict(list)
    for order in valid_orders:
        c_name = order.get("customer_name") or "ลูกค้าทั่วไป"
        if c_name == "ลูกค้าทั่วไป":
            continue
        ts_str = order.get("timestamp")
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            customer_history[c_name].append(dt)
        except Exception:
            pass

    churn_results = []
    for c_name, dates in customer_history.items():
        dates.sort()
        last_date = dates[-1]
        recency_days = (now - last_date).days
        total_orders = len(dates)
        
        if total_orders >= 2:
            first_date = dates[0]
            total_span_days = max(1, (last_date - first_date).days)
            avg_interval_days = round(total_span_days / (total_orders - 1), 1)
        else:
            avg_interval_days = 7.0  # ค่าตั้งต้นความถี่มาตรฐานสำหรับซื้อครั้งเดียว

        # คำนวณความเสี่ยง: หากจำนวนวันไม่ได้ซื้อ เกิน 2 เท่าของรอบปกติ ถือเป็นความเสี่ยงสูง
        risk_threshold = max(7, avg_interval_days * 2)
        if recency_days > risk_threshold:
            risk_level = "Critical (เสี่ยงสูงมาก)"
        elif recency_days > avg_interval_days * 1.3:
            risk_level = "Warning (เริ่มขาดการติดต่อ)"
        else:
            risk_level = "Normal (ปกติ)"

        churn_results.append({
            "customer_name": c_name,
            "total_orders": total_orders,
            "avg_interval_days": avg_interval_days,
            "recency_days": recency_days,
            "risk_threshold": risk_threshold,
            "risk_level": risk_level
        })
    
    churn_results.sort(key=lambda x: x["recency_days"], reverse=True)
    return {"status": "success", "churn_data": churn_results}

# --- NEW FEATURE 2: PERSONAL SHOPPING PATTERNS & TIME PREFERENCES ---
@app.get("/api/v1/analytics/personal-patterns")
def get_personal_patterns():
    valid_orders = [o for o in orders_db if o.get("status") in ["Paid", "Completed"]]
    
    days_th = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
    customer_patterns = defaultdict(lambda: {
        "day_counts": defaultdict(int),
        "hour_counts": defaultdict(int),
        "favorite_items": defaultdict(int)
    })
    
    for order in valid_orders:
        c_name = order.get("customer_name") or "ลูกค้าทั่วไป"
        if c_name == "ลูกค้าทั่วไป":
            continue
        ts_str = order.get("timestamp")
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            day_name = days_th[dt.weekday()]
            hour_slot = f"{dt.hour:02d}:00 - {dt.hour+1:02d}:00 น."
            
            customer_patterns[c_name]["day_counts"][day_name] += 1
            customer_patterns[c_name]["hour_counts"][hour_slot] += 1
            
            for item in order.get("items", []):
                p_name = item.get("product_name")
                if p_name:
                    customer_patterns[c_name]["favorite_items"][p_name] += item.get("quantity", 1)
        except Exception:
            pass

    pattern_results = []
    for c_name, data in customer_patterns.items():
        pref_day = max(data["day_counts"].items(), key=lambda x: x[1])[0] if data["day_counts"] else "ไม่ระบุ"
        pref_hour = max(data["hour_counts"].items(), key=lambda x: x[1])[0] if data["hour_counts"] else "ไม่ระบุ"
        pref_item = max(data["favorite_items"].items(), key=lambda x: x[1])[0] if data["favorite_items"] else "ไม่ระบุ"
        
        pattern_results.append({
            "customer_name": c_name,
            "preferred_day": pref_day,
            "preferred_hour": pref_hour,
            "favorite_item": pref_item
        })

    return {"status": "success", "patterns": pattern_results}

# --- AI PROMOTION RECOMMENDATIONS (จับคู่สินค้าขายดี + สินค้าขายช้า) ---
@app.get("/api/v1/analytics/promo-recommendations")
def get_promo_recommendations():
    valid_orders = [o for o in orders_db if o.get("status") in ["Paid", "Completed"]]
    
    product_sales = defaultdict(int)
    for order in valid_orders:
        for item in order.get("items", []):
            p_name = item.get("product_name")
            qty = item.get("quantity", 1)
            if p_name:
                product_sales[p_name] += qty

    sorted_products = []
    for p in products_db:
        p_name = p["product_name"]
        sold_qty = product_sales.get(p_name, 0)
        sorted_products.append({
            "product_id": p["product_id"],
            "product_name": p_name,
            "selling_price": p["selling_price"],
            "sold_qty": sold_qty
        })
    
    sorted_products.sort(key=lambda x: x["sold_qty"], reverse=True)
    recommendations = []
    
    if len(sorted_products) >= 2:
        top_product = sorted_products[0]
        slow_product = sorted_products[-1]

        recommended_discount = round((top_product["selling_price"] + slow_product["selling_price"]) * 0.15, -1)
        if recommended_discount < 10: recommended_discount = 10

        recommendations.append({
            "rec_id": 1,
            "title": f"เซตกระตุ้นยอดขาย: {top_product['product_name']} + {slow_product['product_name']}",
            "promo_type": "Bundle Deal",
            "condition_summary": f"{top_product['product_name']} + {slow_product['product_name']}",
            "discount_text": f"ซื้อคู่กันลด {int(recommended_discount)} บาท",
            "reason": f"จับคู่สินค้าขายดี ({top_product['product_name']} ขายได้ {top_product['sold_qty']} ชิ้น) กับสินค้าขายช้า ({slow_product['product_name']} ขายได้ {slow_product['sold_qty']} ชิ้น) เพื่อเร่งการระบายสต็อก"
        })

    if len(sorted_products) >= 3:
        second_top = sorted_products[1]
        slow_product = sorted_products[-1]

        recommended_discount_2 = round((second_top["selling_price"] + slow_product["selling_price"]) * 0.10, -1)
        if recommended_discount_2 < 10: recommended_discount_2 = 10

        recommendations.append({
            "rec_id": 2,
            "title": f"เซ็ตจับคู่เพิ่มยอด: {second_top['product_name']} + {slow_product['product_name']}",
            "promo_type": "Cross-Selling",
            "condition_summary": f"{second_top['product_name']} + {slow_product['product_name']}",
            "discount_text": f"ซื้อคู่กันลด {int(recommended_discount_2)} บาท",
            "reason": f"ช่วยดันยอดขาย {slow_product['product_name']} (ขายได้ {slow_product['sold_qty']} ชิ้น) โดยพ่วงกับ {second_top['product_name']}"
        })

    return {"status": "success", "recommendations": recommendations}

# --- PROMOTIONS API ENDPOINTS ---
@app.get("/api/v1/admin/promotions")
def get_promotions():
    return promotions_db

@app.post("/api/v1/admin/promotions")
def create_promotion(promo: PromotionSchema):
    if not math.isfinite(promo.discount_amount) or promo.discount_amount <= 0:
        raise HTTPException(status_code=422, detail="Discount must be greater than zero")
    if promo.discount_type not in {"fixed", "percent"}:
        raise HTTPException(status_code=422, detail="Discount type must be fixed or percent")
    if promo.discount_type == "percent" and promo.discount_amount > 100:
        raise HTTPException(status_code=422, detail="Percentage discount cannot exceed 100")
    if promo.promo_type not in {"bundle", "cross_sell", "discount_code"}:
        raise HTTPException(status_code=422, detail="Unsupported promotion type")
    try:
        start_date = datetime.strptime(promo.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(promo.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="Dates must use YYYY-MM-DD format")
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="End date must be on or after start date")
    if len(set(promo.product_ids)) != len(promo.product_ids) or len(set(promo.trigger_product_ids)) != len(promo.trigger_product_ids):
        raise HTTPException(status_code=422, detail="Product selections must be unique")
    if promo.promo_type == "bundle" and (len(promo.product_ids) < 2 or promo.trigger_product_ids):
        raise HTTPException(status_code=422, detail="Bundle promotions require at least two products")
    if promo.promo_type == "cross_sell":
        if not promo.product_ids or not promo.trigger_product_ids:
            raise HTTPException(status_code=422, detail="Cross-selling requires trigger and discounted products")
        if set(promo.product_ids) & set(promo.trigger_product_ids):
            raise HTTPException(status_code=422, detail="Trigger and discounted products must differ")
    if promo.promo_type == "discount_code":
        if not promo.coupon_code or not promo.coupon_code.strip():
            raise HTTPException(status_code=422, detail="Coupon code is required")
        promo.coupon_code = promo.coupon_code.strip().upper()
        if any((p.get("coupon_code") or "").upper() == promo.coupon_code for p in promotions_db):
            raise HTTPException(status_code=409, detail="Coupon code already exists")

    selected_ids = set(promo.product_ids) | set(promo.trigger_product_ids)
    selected_products = [p for p in products_db if p["product_id"] in selected_ids]
    if len(selected_products) != len(selected_ids) or any(p["stock_quantity"] <= 0 for p in selected_products):
        raise HTTPException(status_code=400, detail="Selected products must exist and have stock")

    new_id = len(promotions_db) + 1
    products_by_id = {p["product_id"]: p for p in selected_products}
    target_names = [products_by_id[product_id]["product_name"] for product_id in promo.product_ids]
    trigger_names = [products_by_id[product_id]["product_name"] for product_id in promo.trigger_product_ids]
    if promo.promo_type == "bundle":
        condition_summary = " + ".join(target_names)
    elif promo.promo_type == "cross_sell":
        condition_summary = f"เมื่อซื้อ {' / '.join(trigger_names)} รับส่วนลดสินค้า {' / '.join(target_names)}"
    else:
        condition_summary = "สินค้าทั้งหมด" if not target_names else " / ".join(target_names)
        condition_summary = f"รหัส {promo.coupon_code}: {condition_summary}"
    discount_label = f"ลด {promo.discount_amount:g}%" if promo.discount_type == "percent" else f"ลด {promo.discount_amount:g} บาท"
    new_promo = {
        "promo_id": new_id,
        "title": promo.title,
        "promo_type": promo.promo_type,
        "product_ids": promo.product_ids,
        "trigger_product_ids": promo.trigger_product_ids,
        "coupon_code": promo.coupon_code,
        "discount_type": promo.discount_type,
        "discount_amount": promo.discount_amount,
        "discount_text": discount_label,
        "condition_summary": condition_summary,
        "usage_count": 0,
        "is_active": True,
        "start_date": promo.start_date,
        "end_date": promo.end_date
    }
    promotions_db.insert(0, new_promo)
    return {"status": "success", "promotion": new_promo}

@app.post("/api/v1/admin/promotions/win-back")
def create_win_back_coupon(data: WinBackCouponSchema):
    new_id = len(promotions_db) + 1
    today = datetime.now().strftime("%Y-%m-%d")
    next_month = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    new_promo = {
        "promo_id": new_id,
        "title": f"คูปองต้อนรับกลับสำหรับคุณ {data.customer_name}",
        "promo_type": "discount_code",
        "product_ids": [],
        "trigger_product_ids": [],
        "coupon_code": f"WELCOME{new_id}",
        "discount_type": "fixed",
        "discount_amount": data.discount_amount,
        "discount_text": f"รับส่วนลดทันที {int(data.discount_amount)} บาท",
        "condition_summary": f"สิทธิ์เฉพาะคุณ {data.customer_name}",
        "usage_count": 0,
        "is_active": True,
        "start_date": today,
        "end_date": next_month
    }
    promotions_db.insert(0, new_promo)
    return {"status": "success", "message": f"ส่งคูปองง้อลูกค้าให้คุณ {data.customer_name} เรียบร้อยแล้ว", "promotion": new_promo}

@app.patch("/api/v1/admin/promotions/{promo_id}/toggle")
def toggle_promotion_status(promo_id: int):
    promo = next((p for p in promotions_db if p["promo_id"] == promo_id), None)
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")
    promo["is_active"] = not promo["is_active"]
    return {"status": "success", "is_active": promo["is_active"]}

@app.delete("/api/v1/admin/promotions/{promo_id}")
def delete_promotion(promo_id: int):
    global promotions_db
    promotions_db = [p for p in promotions_db if p["promo_id"] != promo_id]
    return {"status": "success"}

# ----------------------------------------------------
# 6. Static Files Mount (วางไว้ล่างสุด)
# ----------------------------------------------------
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/", StaticFiles(directory="static", html=True), name="static")