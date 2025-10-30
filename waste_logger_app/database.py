# waste_logger_app/database.py

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime


# Always create the database inside the waste_logger_app directory, regardless of where the app is run from
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'waste_log.db')}"  # Changed to absolute path

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# WasteLog model
class WasteLog(Base):
    __tablename__ = "waste_logs"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String)
    confidence = Column(Float)
    material = Column(String)
    recyclable = Column(Boolean)
    co2_estimate = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    username = Column(String, default="guest")  
    filename = Column(String)
# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Automatically initialize the database when this module is loaded
Base.metadata.create_all(bind=engine)
