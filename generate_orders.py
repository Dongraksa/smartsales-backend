import json
import random
from datetime import datetime, timedelta

# 1. รายชื่อสินค้าอ้างอิงจากฐานข้อมูลจริง
products = [
    {"product_id": 1, "product_name": "อเมริกาโน่เย็น (Iced Americano)", "selling_price": 55.0, "image_url": "https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=300"},
    {"product_id": 2, "product_name": "ลาเต้เย็น (Iced Latte)", "selling_price": 65.0, "image_url": "https://images.unsplash.com/photo-1570968915860-54d5c301fa9f?w=300"},
    {"product_id": 3, "product_name": "ครัวซองต์เนยสด (Croissant)", "selling_price": 45.0, "image_url": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=300"},
    {"product_id": 4, "product_name": "คัปปุชชีโนเย็น (Iced Cappuccino)", "selling_price": 60.0, "image_url": "https://images.unsplash.com/photo-1534778101976-62847782c213?w=300"},
    {"product_id": 5, "product_name": "เค้กช็อกโกแลต (Chocolate Cake)", "selling_price": 75.0, "image_url": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=300"}
]

# 2. รายชื่อลูกค้าสำหรับวิเคราะห์ RFM (มีทั้ง VIP, ลูกค้าประจำ และซื้อครั้งเดียว)
customers = [
    "สมชาย สายเปย์", "สมหญิง รักสงบ", "แป้ง สุภาพร", "อนันต์ ตั้งใจเรียน",
    "วิชัย ขายดี", "กนกวรรณ วันเพ็ญ", "ณัฐพงษ์ สมบูรณ์", "ชลธิชา น่ารัก",
    "ธนกฤต ใจดี", "ภัทรวดี มีสุข", "ลูกค้าทั่วไป"
]

payment_methods = ["PromptPay", "Cash", "Credit Card"]

# 3. สุ่มสร้างข้อมูลย้อนหลัง 90 วัน
end_date = datetime.now()
start_date = end_date - timedelta(days=90)

generated_orders = []

for i in range(1000, 0, -1):
    sale_id = 1000 + i
    customer = random.choice(customers)
    payment = random.choice(payment_methods)
    
    # สุ่มวันที่ย้อนหลัง
    random_days = random.randint(0, 90)
    # สุ่มเวลาโดยเน้นช่วงขายดี (08:00 - 18:00 น.)
    if random.random() < 0.4:
        random_hour = random.choice([12, 13]) # ช่วงเที่ยง peak hour
    else:
        random_hour = random.randint(8, 19)
    random_minute = random.randint(0, 59)
    random_second = random.randint(0, 59)
    
    order_time = (end_date - timedelta(days=random_days)).replace(
        hour=random_hour, minute=random_minute, second=random_second
    )
    
    # สุ่มสินค้าในตะกร้า 1-3 รายการ
    num_items = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
    selected_products = random.sample(products, num_items)
    
    order_items = []
    total_amount = 0.0
    
    for p in selected_products:
        qty = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
        subtotal = p["selling_price"] * qty
        total_amount += subtotal
        order_items.append({
            "product_name": p["product_name"],
            "quantity": qty,
            "subtotal": subtotal,
            "image_url": p["image_url"]
        })
        
    generated_orders.append({
        "sale_id": sale_id,
        "customer_name": customer,
        "timestamp": order_time.strftime("%Y-%m-%d %H:%M:%S"),
        "payment_method": payment,
        "total_amount": round(total_amount, 2),
        "status": "Paid",
        "items": order_items
    })

# จัดเรียงจากออเดอร์ใหม่สุดไปเก่าสุด
generated_orders.sort(key=lambda x: x["timestamp"], reverse=True)

# บันทึกลงไฟล์ JSON
with open("mock_orders.json", "w", encoding="utf-8") as f:
    json.dump(generated_orders, f, ensure_ascii=False, indent=2)

print(f"สร้างข้อมูลคำสั่งซื้อสำเร็จเรียบร้อยแล้ว {len(generated_orders)} รายการ ในไฟล์ mock_orders.json")