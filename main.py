import os
import json
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
from pydantic import BaseModel

app = FastAPI(
    title="SmartSales Enterprise API",
    description="ระบบบริหารจัดการร้านค้า สต็อกสินค้า ระบบหลังบ้าน และ Real-Data Analytics",
    version="2.2.0"
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
# 2. ฟังก์ชันช่วย อ่าน/เขียน ข้อมูล JSON
# ----------------------------------------------------
ORDERS_FILE = "mock_orders.json"

def load_orders_data():
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_orders_data():
    try:
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(orders_db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving orders: {e}")

# โหลดข้อมูลคำสั่งซื้อเริ่มต้น
orders_db = load_orders_data()

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
        "cost_price": 25.0,
        "selling_price": 55.0,
        "stock_quantity": 45,
        "image_url": "https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=300",
        "lead_time_days": 3,
        "safety_stock": 10
    },
    {
        "product_id": 2,
        "product_name": "ลาเต้เย็น (Iced Latte)",
        "cost_price": 30.0,
        "selling_price": 65.0,
        "stock_quantity": 12,
        "image_url": "https://images.unsplash.com/photo-1570968915860-54d5c301fa9f?w=300",
        "lead_time_days": 4,
        "safety_stock": 15
    },
    {
        "product_id": 3,
        "product_name": "ครัวซองต์เนยสด (Croissant)",
        "cost_price": 20.0,
        "selling_price": 45.0,
        "stock_quantity": 8,
        "image_url": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=300",
        "lead_time_days": 2,
        "safety_stock": 10
    },
    {
        "product_id": 4,
        "product_name": "คัปปุชชีโนเย็น (Iced Cappuccino)",
        "cost_price": 28.0,
        "selling_price": 60.0,
        "stock_quantity": 25,
        "image_url": "https://images.unsplash.com/photo-1534778101976-62847782c213?w=300",
        "lead_time_days": 3,
        "safety_stock": 10
    },
    {
        "product_id": 5,
        "product_name": "เค้กช็อกโกแลต (Chocolate Cake)",
        "cost_price": 35.0,
        "selling_price": 75.0,
        "stock_quantity": 15,
        "image_url": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=300",
        "lead_time_days": 2,
        "safety_stock": 5
    }
]

promotions_db = [
    {
        "promo_id": 1,
        "title": "เซตคู่กาแฟ & ครัวซองต์สุดคุ้ม",
        "promo_type": "bundle",
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
    discount_text: str
    condition_summary: str
    start_date: str
    end_date: str

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

# --- CHECKOUT & ORDERS HANDLER (เพิ่มคำสั่งซื้อใหม่และเซฟลง JSON) ---
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
            
        processed_items.append({
            "product_name": p_name,
            "quantity": qty,
            "subtotal": subtotal,
            "image_url": prod["image_url"] if prod else "https://via.placeholder.com/150"
        })
    payment_method = "PromptPay"
    customer_name = "ลูกค้าทั่วไป"
    if isinstance(data, dict):
        payment_method = data.get("payment_method") or data.get("payment") or "PromptPay"
        customer_name = data.get("customer_name") or "ลูกค้าทั่วไป"
        
    # รัน ID ถัดไป
    max_id = max([o.get("sale_id", 1000) for o in orders_db], default=1000)
    sale_id = max_id + 1
    
    # คำนวณเวลาประเทศไทย GMT+7
    thaitime = (datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
    
    new_order = {
        "sale_id": sale_id,
        "customer_name": customer_name,
        "timestamp": thaitime,
        "payment_method": payment_method,
        "total_amount": round(total_amount, 2),
        "status": "Paid",
        "items": processed_items
    }
    
    orders_db.insert(0, new_order)
    save_orders_data() # เซฟลง mock_orders.json ทันที
    
    return {
        "status": "success",
        "message": "สั่งซื้อสำเร็จเรียบร้อยแล้ว",
        "sale_id": sale_id,
        "total_amount": round(total_amount, 2)
    }

# --- PRODUCTS MANAGEMENT ---
@app.get("/api/v1/products")
def get_products():
    return products_db

@app.post("/api/v1/admin/products")
def create_product(
    product_name: str = Form(...),
    cost_price: float = Form(...),
    selling_price: float = Form(...),
    stock_quantity: int = Form(...),
    lead_time_days: int = Form(3),
    safety_stock: int = Form(10),
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
        "cost_price": cost_price,
        "selling_price": selling_price,
        "stock_quantity": stock_quantity,
        "lead_time_days": lead_time_days,
        "safety_stock": safety_stock,
        "image_url": image_url
    }
    products_db.append(new_prod)
    return {"status": "success", "product": new_prod}

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
    low_stock_count = len([p for p in products_db if p["stock_quantity"] < 20])
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
    save_orders_data()
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
    result = [{"hour": hour_label, "total_revenue": round(rev, 2)} for hour_label, rev in hours_map.items()]
    return result

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
    return result or [{"product_name": "ยังไม่มีข้อมูล", "revenue": 0.0}]

# --- REAL-DATA ANALYTICS ---
@app.get("/api/v1/analytics/market-basket")
def get_market_basket(min_support: float = 0.001, min_confidence: float = 0.001):
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
                "support": round(support, 3),
                "confidence": round(conf1, 3),
                "lift": round(lift1, 2)
            })

    rules = sorted(rules, key=lambda x: x["lift"], reverse=True)
    return {"status": "success", "rules": rules}

@app.get("/api/v1/analytics/reorder-points")
def get_reorder_points():
    valid_orders = [o for o in orders_db if o.get("status") in ["Paid", "Completed"]]
    product_sales_qty = defaultdict(int)
    for order in valid_orders:
        for item in order.get("items", []):
            p_name = item.get("product_name")
            qty = item.get("quantity", 1)
            if p_name:
                product_sales_qty[p_name] += qty

    results = []
    days_evaluated = 90
    for p in products_db:
        p_name = p["product_name"]
        total_sold = product_sales_qty.get(p_name, 0)
        daily_usage = round(max(0.5, total_sold / days_evaluated), 1)
        lead_time = p.get("lead_time_days", 3)
        safety = p.get("safety_stock", 10)
        stock = p.get("stock_quantity", 0)
        
        rop = math.ceil((daily_usage * lead_time) + safety)
        status = "CRITICAL" if stock == 0 else ("REORDER_NOW" if stock <= rop else "OK")
        
        results.append({
            "product_id": p["product_id"],
            "product_name": p_name,
            "current_stock": stock,
            "daily_usage": daily_usage,
            "lead_time_days": lead_time,
            "safety_stock": safety,
            "reorder_point": rop,
            "status": status
        })
    return {"status": "success", "reorder_points": results}

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
        
        r_score = 5 if recency_days <= 7 else (4 if recency_days <= 15 else (3 if recency_days <= 30 else (2 if recency_days <= 60 else 1)))
        f_score = 5 if f >= 50 else (4 if f >= 20 else (3 if f >= 10 else (2 if f >= 2 else 1)))
        m_score = 5 if m >= 3000 else (4 if m >= 1500 else (3 if m >= 500 else (2 if m >= 200 else 1)))
        
        if f_score >= 4 or m_score >= 4:
            segment = "Champions (ลูกค้า VIP)"
        elif f_score >= 2 or m_score >= 3:
            segment = "Loyal Customers (ลูกค้าประจำ)"
        elif recency_days > 45:
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

# --- PROMOTIONS ---
@app.get("/api/v1/admin/promotions")
def get_promotions():
    return promotions_db

@app.post("/api/v1/admin/promotions")
def create_promotion(promo: PromotionSchema):
    new_id = len(promotions_db) + 1
    new_promo = {
        "promo_id": new_id,
        "title": promo.title,
        "promo_type": promo.promo_type,
        "discount_text": promo.discount_text,
        "condition_summary": promo.condition_summary,
        "usage_count": 0,
        "is_active": True,
        "start_date": promo.start_date,
        "end_date": promo.end_date
    }
    promotions_db.insert(0, new_promo)
    return {"status": "success", "promotion": new_promo}

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
# 6. Static Files Mount
# ----------------------------------------------------
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/", StaticFiles(directory="static", html=True), name="static")