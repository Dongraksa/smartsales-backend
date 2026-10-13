import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ดึง URL ของ PostgreSQL จาก Environment Variable (Render จะเจนให้อัตโนมัติ)
# ถ้าหาไม่เจอจะ fallback ไปใช้ SQLite ท้องถิ่นเพื่อความสะดวกในการทดสอบ local
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./smartsales.db"
)

# Render จะให้ URL ขึ้นต้นด้วย postgres:// แต่ SQLAlchemy v2 ต้องการ postgresql://
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()