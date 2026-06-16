import os
import logging
from datetime import datetime
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PASSWORD = os.getenv("DB_PASSWORD")
WATCHLIST = ["NVDA", "AAPL", "TSLA"]
POLLING_INTERVAL_SECONDS = 10
if not DB_PASSWORD:
    logger.warning("DB_PASSWORD environment variable not set. Database connection may fail.")
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://root:{DB_PASSWORD}@{DB_HOST}:3306/stock_app"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ORM Model
class StockRecord(Base):
    __tablename__ = "stock_history"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), index=True)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
Base.metadata.create_all(bind=engine)

# Background Task
def fetch_and_store_data():
    db = SessionLocal() 
    try:
        for ticker in WATCHLIST:
            stock = yf.Ticker(ticker)
            price = stock.fast_info.last_price
            if price:
                record = StockRecord(ticker=ticker, price=price, timestamp=datetime.utcnow())
                db.add(record)
        db.commit()
    except Exception as e:
        logger.error(f"Background job failed: {e}")
        db.rollback()
    finally:
        db.close()

# Lifespan Management for APScheduler
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_store_data, 'interval', seconds=POLLING_INTERVAL_SECONDS)
    scheduler.start()
    logger.info("APScheduler started: Polling live equity metrics every 10 seconds.")
    yield
    scheduler.shutdown()
    logger.info("APScheduler stopped.")

# FastAPI App
app = FastAPI(title="Market Data REST API", lifespan=lifespan)

# Pydantic Schemas
class StockResponse(BaseModel):
    ticker: str
    price: float
    currency: str = "USD"
    saved_to_db: bool

class AnalysisResponse(BaseModel):
    ticker: str
    current_price: float
    sma_5: float 
    sma_20: float
    signal: str

# Dependency Injection
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def health_check():
    return {"status": "operational", "pipeline": "active"}

@app.get("/stock/{ticker}", response_model=StockResponse)
def get_stock_info(ticker: str, db: Session = Depends(get_db)):
    ticker = ticker.upper()
    try:
        stock = yf.Ticker(ticker)
        current_price = stock.fast_info.last_price 
        if not current_price: 
            raise ValueError("Price not available")

        db_record = StockRecord(ticker=ticker, price=current_price, timestamp=datetime.utcnow())
        db.add(db_record)
        db.commit()

        return {"ticker": ticker, "price": round(current_price, 2), "saved_to_db": True}
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        raise HTTPException(status_code=404, detail=f"Stock '{ticker}' data not found.")

@app.get("/stock/{ticker}/analysis", response_model=AnalysisResponse)
def analyze_stock(ticker: str, db: Session = Depends(get_db)):
    ticker = ticker.upper()
    
    # Fetch minimum 20 records for the calculation
    records = db.query(StockRecord).filter(StockRecord.ticker == ticker)\
                .order_by(StockRecord.id.desc()).limit(20).all()
    if len(records) < 20:
        raise HTTPException(status_code=400, detail="Insufficient time-series data for moving average calculation (20 records required).")

    # Time series
    data = [{"price": r.price, "timestamp": r.timestamp} for r in records]
    df = pd.DataFrame(data)
    
    # Sort
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    df['SMA_5'] = df['price'].rolling(window=5).mean()
    df['SMA_20'] = df['price'].rolling(window=20).mean()
    current_price = df['price'].iloc[-1] 
    sma_5 = df['SMA_5'].iloc[-1]
    sma_20 = df['SMA_20'].iloc[-1]
    
    # Signal 
    signal = "BUY" if sma_5 > sma_20 else "HOLD"
    return {
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "sma_5": round(sma_5, 2),
        "sma_20": round(sma_20, 2),
        "signal": signal
    }

