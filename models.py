from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    password = Column(String, nullable=False)
    role = Column(String, default="customer")

class Product(Base):
    __tablename__ = "products"
    product_id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, nullable=False)
    cost_price = Column(Float, nullable=False)
    selling_price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0)
    image_url = Column(String, nullable=True)

class Order(Base):
    __tablename__ = "orders"
    sale_id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    payment_method = Column(String, default="PromptPay")
    total_amount = Column(Float, default=0.0)
    status = Column(String, default="Paid")
    
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    item_id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("orders.sale_id"))
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    subtotal = Column(Float, default=0.0)
    image_url = Column(String, nullable=True)

    order = relationship("Order", back_populates="items")

class Promotion(Base):
    __tablename__ = "promotions"
    promo_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    promo_type = Column(String, nullable=False) # bundle, cross_sell, coupon
    discount_text = Column(String, nullable=False)
    condition_summary = Column(String, nullable=False)
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)