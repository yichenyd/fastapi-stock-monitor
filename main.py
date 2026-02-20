from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import yfinance as yf
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
import time
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password_here") 

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://root:{DB_PASSWORD}@{DB_HOST}:3306/stock_app"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class StockRecord(Base):
    __tablename__ = "stock_history"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), index=True)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def fetch_and_store_data():
    print(f"[{datetime.now()}] ⏰ Background Task Started...")
    watchlist = ["NVDA", "AAPL", "TSLA"]
    db = SessionLocal() 
    try:
        for ticker in watchlist:
            stock = yf.Ticker(ticker)
            price = stock.fast_info.last_price
            if price:
                record = StockRecord(ticker=ticker, price=price, timestamp=datetime.now())
                db.add(record)
                print(f"   -> Saved {ticker}: {round(price, 2)}")
        db.commit()
        print("✅ Batch update completed.")
    except Exception as e:
        print(f"❌ Job failed: {e}")
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(fetch_and_store_data, 'interval', seconds=10)
scheduler.start()

app = FastAPI(title="Quant Market Data API (Level 3: Analytics)")

class StockResponse(BaseModel):
    ticker: str
    price: float
    currency: str = "USD"
    saved_to_db: bool

class AnalysisResponse(BaseModel):
    ticker: str
    current_price: float
    average_price_5: float 
    price_change: float 
    signal: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home():
    return {"message": "Quant System Running. Analysis endpoint ready."}

@app.get("/stock/{ticker}", response_model=StockResponse)
def get_stock_info(ticker: str, db: Session = Depends(get_db)):
    try:
        stock = yf.Ticker(ticker)
        current_price = stock.fast_info.last_price 
        if not current_price: raise ValueError("Price not found")

        db_record = StockRecord(ticker=ticker.upper(), price=current_price, timestamp=datetime.now())
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        return {"ticker": ticker.upper(), "price": round(current_price, 2), "saved_to_db": True}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Stock '{ticker}' not found.")


@app.get("/stock/{ticker}/analysis", response_model=AnalysisResponse)
def analyze_stock(ticker: str, db: Session = Depends(get_db)):

    ticker = ticker.upper()
    
    records = db.query(StockRecord).filter(StockRecord.ticker == ticker)\
                .order_by(StockRecord.id.desc()).limit(10).all()
    
    if len(records) < 2:
        raise HTTPException(status_code=400, detail="Not enough data to analyze. Wait for scheduler.")

    
    data = [{"price": r.price, "time": r.timestamp} for r in records]
    df = pd.DataFrame(data)
    
    
    current_price = df['price'].iloc[0] 
    avg_price = df['price'].mean() 
    
    if current_price < avg_price:
        signal = "BUY (Below Average)"
    else:
        signal = "HOLD (Above Average)"

    change_percent = ((current_price - avg_price) / avg_price) * 100

    return {
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "average_price_5": round(avg_price, 2),
        "price_change": round(change_percent, 2),
        "signal": signal
    }


