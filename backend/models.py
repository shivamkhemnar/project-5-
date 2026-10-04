"""SQLAlchemy schemas for saved forecasts, anomaly logs, backtests."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import get_settings

Base = declarative_base()


class TickerQuery(Base):
    __tablename__ = "ticker_queries"
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), index=True)
    period = Column(String(10))
    rows = Column(Integer)
    synthetic = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class AnomalyLog(Base):
    __tablename__ = "anomaly_logs"
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), index=True)
    date = Column(String(20))
    price = Column(Float)
    severity = Column(String(20))
    type = Column(String(40))
    z_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class ForecastRecord(Base):
    __tablename__ = "forecasts"
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), index=True)
    model = Column(String(40))
    horizon = Column(Integer)
    direction = Column(String(20))
    rmse = Column(Float)
    mae = Column(Float)
    payload = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


engine = create_engine(get_settings().database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
