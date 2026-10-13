import os
import shutil
import math
import time
import psycopg2
from psycopg2.extras import RealDictCursor
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
    description="ระบบบริหารจัดการร้านค้า สต็อกสินค้า ระบบหลังบ้าน และ Real-Data Analytics (ROP, Market Basket, RFM)",
    version="2.4.0"
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
# 2. ฟังก์ชันจัดการ PostgreSQL Database + Simple Cache
# ----------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "dpg-db6qm58m7kps73avm6ig-a.singapore-postgres.render.com")
DB_NAME = os.getenv("DB_NAME", "smartsales_r99y")
DB_USER = os.getenv("DB_USER", "smartsales_user")
DB_PASS = os.getenv("DB_PASS", "uWGpl4U5DfZzw4jjIK8CY2G6UrFjCdQG")
DB_PORT = os.getenv("DB_PORT", "5432")

# ระบบ Cache เก็บข้อมูลออเดอร์ในแรม 15 วินาที เพื่อไม่ให้ DB ทำงานหนัก
ORDERS_CACHE = {"timestamp": 0, "data": []}
CACHE_TTL = 15  # วินาที

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
        sslmode="require",
        connect_timeout=3
    )

def fetch_orders_from_db(force_refresh=False):
    now = time.time()
    # ถ้ามีข้อมูล Cache อยู่และยังไม่หมดอายุ ให้ใช้ข้อมูลเดิมทันที (เร็วปร๋อ)
    if not force_refresh and (now - ORDERS_CACHE["timestamp"] < CACHE_TTL) and ORDERS_CACHE["data"]:
        return ORDERS_CACHE["data"]

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT o.sale_id, o.customer_name, 
                   to_char(o.timestamp, 'YYYY-MM-DD HH24:MI:SS') as timestamp, 
                   o.payment_method, o.total_amount, o.status,
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'product_name', oi.product_name,
                               'quantity', oi.quantity,
                               'subtotal', oi.subtotal
                           )
                       ) FILTER (WHERE oi.item_id IS NOT NULL), '[]'
                   ) as items
            FROM orders o
            LEFT JOIN order_items oi ON o.sale_id = oi.sale_id
            GROUP BY o.sale_id
            ORDER BY o.sale_id DESC;
        """)
        orders = cur.fetchall()
        cur.close()
        
        # อัปเดต Cache
        ORDERS_CACHE["timestamp"] = now
        ORDERS_CACHE["data"] = orders
        return orders
    except Exception as e:
        print(f"❌ Database Read Error: {e}")
        return ORDERS_CACHE["data"] or []
    finally:
        if conn:
            conn.close()

# ----------------------------------------------------
# 3. ข้อมูลเริ่มต้นอื่นๆ (In-Memory)
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
# 4. Schemas
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
# 5. Page Shortcut Routes
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
# 6. API Endpoints
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
            
        processed_items.append((p_name, qty, subtotal))
        
    payment_method = "PromptPay"
    customer_name = "ลูกค้าทั่วไป"
    if isinstance(data, dict):
        payment_method = data.get("payment_method") or data.get("payment") or "PromptPay"
        customer_name = data.get("customer_name") or "ลูกค้าทั่วไป"
        
    thaitime = datetime.now() + timedelta(hours=7)
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO orders (customer_name, timestamp, payment_method, total_amount, status)
            VALUES (%s, %s, %s, %s, %s) RETURNING sale_id;
        """, (customer_name, thaitime, payment_method, total_amount, "Paid"))
        sale_id = cur.fetchone()[0]
        
        for p_name, qty, subtotal in processed_items:
            cur.execute("""
                INSERT INTO order_items (sale_id, product_name, quantity, subtotal)
                VALUES (%s, %s, %s, %s);
            """, (sale_id, p_name, qty, subtotal))
            
        conn.commit()
        cur.close()
        
        # รีเฟรช Cache ให้ทันทีเมื่อมีออเดอร์ใหม่เข้ามา
        fetch_orders_from_db(force_refresh=True)
        
        return {
            "status": "success",
            "message": "สั่งซื้อสำเร็จเรียบร้อยแล้ว",
            "sale_id": sale_id,
            "total_amount": round(total_amount, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database insert error: {e}")
    finally:
        if conn:
            conn.close()

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

@app.put("/api/v1/admin/products/{product_id}")
def update_product(
    product_id: int,
    product_name: str = Form(...),
    cost_price: float = Form(...),
    selling_price: float = Form(...),
    stock_quantity: int = Form(...),
    lead_time_days: int = Form(3),
    safety_stock: int = Form(10),
    image_file: Optional[UploadFile] = File(None)
):
    prod = next((p for p in products_db if p["product_id"] == product_id), None)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
        
    prod["product_name"] = product_name
    prod["cost_price"] = cost_price
    prod["selling_price"] = selling_price
    prod["stock_quantity"] = stock_quantity
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

# --- DASHBOARD & ANALYTICS FROM DATABASE ---
@app.get("/api/v1/admin/dashboard-summary")
def get_dashboard_summary(period: str = "all"):
    orders_db = fetch_orders_from_db()
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
    total_revenue = sum(float(o["total_amount"]) for o in valid_orders)
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
    return fetch_orders_from_db()

@app.patch("/api/v1/admin/orders/{sale_id}/status")
def update_order_status(sale_id: int, status_update: OrderStatusUpdate):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status = %s WHERE sale_id = %s;", (status_update.status, sale_id))
        conn.commit()
        cur.close()
        fetch_orders_from_db(force_refresh=True)
        return {"status": "success", "sale_id": sale_id, "new_status": status_update.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.get("/api/v1/analytics/peak-hours")
def get_peak_hours():
    orders_db = fetch_orders_from_db()
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
    orders_db = fetch_orders_from_db()
    summary = defaultdict(float)
    for order in orders_db:
        if order.get("status") in ["Paid", "Completed"]:
            for item in order.get("items", []):
                p_name = item.get("product_name", "สินค้าทั่วไป")
                subtotal = float(item.get("subtotal", 0.0))
                summary[p_name] += subtotal
    result = [{"product_name": name, "revenue": round(rev, 2)} for name, rev in summary.items()]
    return result or [{"product_name": "ยังไม่มีข้อมูล", "revenue": 0.0}]

# --- REAL-DATA ANALYTICS FROM DATABASE ---
@app.get("/api/v1/analytics/market-basket")
def get_market_basket(min_support: float = 0.001, min_confidence: float = 0.001):
    orders_db = fetch_orders_from_db()
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
    orders_db = fetch_orders_from_db()
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
    orders_db = fetch_orders_from_db()
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
# 7. Static Files Mount
# ----------------------------------------------------
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/", StaticFiles(directory="static", html=True), name="static")