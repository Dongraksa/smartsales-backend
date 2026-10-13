import psycopg2
import random
from datetime import datetime, timedelta

# ข้อมูลการเชื่อมต่อ Render Database
DB_HOST = "dpg-db6qm58m7kps73avm6ig-a.singapore-postgres.render.com"
DB_NAME = "smartsales_r99y"
DB_USER = "smartsales_user"
DB_PASS = "uWGpl4U5DfZzw4jjIK8CY2G6UrFjCdQG"
DB_PORT = "5432"

print("🔄 กำลังเชื่อมต่อกับ Render PostgreSQL Database...")

try:
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
        sslmode="require"
    )
    cursor = conn.cursor()
    print("✅ เชื่อมต่อฐานข้อมูลสำเร็จ!")

    # 1. สร้างตารางถ้ายังไม่มี
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            sale_id SERIAL PRIMARY KEY,
            customer_name VARCHAR(255) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            payment_method VARCHAR(50) DEFAULT 'PromptPay',
            total_amount NUMERIC(10, 2) NOT NULL,
            status VARCHAR(50) DEFAULT 'Paid'
        );

        CREATE TABLE IF NOT EXISTS order_items (
            item_id SERIAL PRIMARY KEY,
            sale_id INT REFERENCES orders(sale_id) ON DELETE CASCADE,
            product_name VARCHAR(255) NOT NULL,
            quantity INT NOT NULL,
            subtotal NUMERIC(10, 2) NOT NULL
        );
    """)
    conn.commit()
    print("✅ สร้างโครงสร้างตาราง orders และ order_items เรียบร้อยแล้ว")

    # 2. ข้อมูลจำลองสำหรับสุ่ม
    products = [
        {"name": "อเมริกาโน่เย็น (Iced Americano)", "price": 55.0},
        {"name": "ลาเต้เย็น (Iced Latte)", "price": 65.0},
        {"name": "ครัวซองต์เนยสด (Croissant)", "price": 45.0},
        {"name": "คัปปุชชีโนเย็น (Iced Cappuccino)", "price": 60.0},
        {"name": "เค้กช็อกโกแลต (Chocolate Cake)", "price": 75.0}
    ]

    customers = [
        "สมชาย สายเปย์", "สมหญิง รักสงบ", "แป้ง สุภาพร", "อนันต์ ตั้งใจเรียน",
        "วิชัย ขายดี", "กนกวรรณ วันเพ็ญ", "ณัฐพงษ์ สมบูรณ์", "ชลธิชา น่ารัก",
        "ธนกฤต ใจดี", "ภัทรวดี มีสุข", "ลูกค้าทั่วไป"
    ]

    payments = ["PromptPay", "Cash", "Credit Card"]
    end_date = datetime.now()

    print("🚀 กำลังเพิ่มข้อมูลคำสั่งซื้อย้อนหลัง 1,000 รายการ...")

    for i in range(1000):
        customer = random.choice(customers)
        payment = random.choice(payments)
        
        # สุ่มช่วงเวลาย้อนหลัง 90 วัน (เน้นช่วง 12:00 - 13:00 น. ให้เป็น Peak Hours)
        random_days = random.randint(0, 90)
        random_hour = random.choice([12, 13]) if random.random() < 0.4 else random.randint(8, 19)
        random_min = random.randint(0, 59)
        random_sec = random.randint(0, 59)
        
        order_time = (end_date - timedelta(days=random_days)).replace(
            hour=random_hour, minute=random_min, second=random_sec
        )

        # สุ่มรายการสินค้าในออเดอร์
        num_items = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
        selected_prods = random.sample(products, num_items)
        
        items_data = []
        total_amount = 0.0

        for p in selected_prods:
            qty = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
            subtotal = p["price"] * qty
            total_amount += subtotal
            items_data.append((p["name"], qty, subtotal))

        # Insert เข้าตาราง orders
        cursor.execute("""
            INSERT INTO orders (customer_name, timestamp, payment_method, total_amount, status)
            VALUES (%s, %s, %s, %s, %s) RETURNING sale_id;
        """, (customer, order_time, payment, total_amount, "Paid"))
        
        sale_id = cursor.fetchone()[0]

        # Insert รายการสินค้าเข้าตาราง order_items
        for item in items_data:
            cursor.execute("""
                INSERT INTO order_items (sale_id, product_name, quantity, subtotal)
                VALUES (%s, %s, %s, %s);
            """, (sale_id, item[0], item[1], item[2]))

    conn.commit()
    print("🎉 ยัดข้อมูล 1,000 รายการเข้าสู่ Render Database สำเร็จเรียบร้อยแล้ว!")

except Exception as e:
    print(f"❌ เกิดข้อผิดพลาด: {e}")
finally:
    if 'conn' in locals() and conn:
        cursor.close()
        conn.close()
        print("🔒 ปิดการเชื่อมต่อ Database เรียบร้อย")