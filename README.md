# 📈 Stock Monitor & Analysis API

## 📖 Overview

This is a backend API built to track and analyze stock market data. It automatically fetches real-time prices, stores them in a MySQL database, and uses Pandas to calculate simple moving averages. 

## 🚀 What It Does (Features)

* **Auto-Tracking (`APScheduler`)**: It runs a background job that automatically fetches live stock prices from Yahoo Finance every few seconds.
* **Database Storage (`MySQL` & `SQLAlchemy`)**: It permanently saves all the price history into a local MySQL database.
* **Basic Analytics (`Pandas`)**: It reads the recent prices from the database, calculates the average price, and tells you if the current price is above or below that average (BUY/HOLD signal).
* **Safe Configuration**: It uses `.env` files to hide real database password.

## 🛠️ Tech Stack

* **Language**: Python
* **Web Framework**: FastAPI & Uvicorn
* **Database**: MySQL & SQLAlchemy
* **Data Math**: Pandas
* **Automation**: APScheduler
* **API Data**: Yahoo Finance (`yfinance`)

## 💻 Installation & Setup

1. **Install required libraries:** `pip install -r requirements.txt`
2. **Setup the Database:** Create a file named `.env` in the same folder and add your local MySQL password like this: 
   `DB_PASSWORD=your_actual_local_password`
3. **Run the API:** `uvicorn main:app --reload`

## 📝 Sample Response

When you request the analysis endpoint (`GET /stock/NVDA/analysis`), you will get:
```json
{
  "ticker": "NVDA",
  "current_price": 182.81,
  "average_price_5": 181.50,
  "price_change": 0.72,
  "signal": "HOLD (Above Average)"
}
