from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# ==========================================
# 1. USER MODEL (ระบบสมาชิกเดิม)
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="staff")  # admin, staff
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="user")


# ==========================================
# 2. PRODUCT MODEL (สินค้ารวมเดิม + ฟิลด์ ROP เพิ่มเติม)
# ==========================================
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    category = Column(String, index=True, nullable=True)
    image_url = Column(String, nullable=True)
    
    # [ฟีเจอร์ใหม่] ฟิลด์สำหรับคำนวณ ROP (Reorder Point)
    lead_time_days = Column(Integer, default=3)   # ระยะเวลารอสินค้าจาก Supplier (วัน)
    safety_stock = Column(Integer, default=10)     # สต็อกสำรองกันสินค้าหมด

    order_items = relationship("OrderItem", back_populates="product")


# ==========================================
# 3. ORDER & ORDER ITEM MODELS (ระบบการขายเดิม)
# ==========================================
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    customer_name = Column(String, default="General Customer", index=True)
    total_price = Column(Float, default=0.0)
    status = Column(String, default="completed")  # pending, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


# ==========================================
# 4. PROMOTION BUNDLE MODEL [ฟีเจอร์ใหม่: Market Basket Analysis]
# ==========================================
class PromotionBundle(Base):
    __tablename__ = "promotion_bundles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)                        # ชื่อโปรโมชั่น
    top_product_id = Column(Integer, ForeignKey("products.id"))   # สินค้าขายดี (Top Seller)
    slow_product_id = Column(Integer, ForeignKey("products.id"))  # สินค้าขายไม่ดี (Slow Mover)
    discount_percentage = Column(Float, default=10.0)            # ส่วนลด %
    lift_score = Column(Float, nullable=True)                     # ค่าความสัมพันธ์ (Lift Score)
    is_active = Column(Boolean, default=True)                     # สถานะการใช้งาน
    created_at = Column(DateTime, default=datetime.utcnow)

    top_product = relationship("Product", foreign_keys=[top_product_id])
    slow_product = relationship("Product", foreign_keys=[slow_product_id])


# ==========================================
# 5. CUSTOMER RFM MODEL [ฟีเจอร์ใหม่: RFM Analysis]
# ==========================================
class CustomerRFM(Base):
    __tablename__ = "customer_rfm"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, index=True, nullable=False)
    recency_days = Column(Integer, default=0)    # ล่าสุดกี่วันที่แล้ว
    frequency = Column(Integer, default=0)       # จำนวนครั้งที่ซื้อรวม
    monetary = Column(Float, default=0.0)        # ยอดเงินรวม
    r_score = Column(Integer, default=1)         # คะแนน R (1-5)
    f_score = Column(Integer, default=1)         # คะแนน F (1-5)
    m_score = Column(Integer, default=1)         # คะแนน M (1-5)
    segment = Column(String, default="General")  # กลุ่มลูกค้า (เช่น Champions, At Risk)
    updated_at = Column(DateTime, default=datetime.utcnow)