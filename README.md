# Stock Monitor

* It runs a background job that automatically fetches live stock prices from Yahoo Finance every few seconds.
* It permanently saves all the price history into a local MySQL database.
* It reads the recent prices from the database, calculates the average price, and tells you if the current price is above or below that average (BUY/HOLD signal).
* It uses `.env` files to hide real database password.

1. Install: `pip install -r requirements.txt`
2. Setup: Create a file named `.env` in the same folder and add MySQL password, for example: `DB_PASSWORD=your_actual_local_password`
3. Run: `uvicorn main:app --reload`

* Sample Response:
When you request the analysis endpoint (`GET /stock/NVDA/analysis`), you will get:
```json
{
  "ticker": "NVDA",
  "current_price": 182.81,
  "average_price_5": 181.50,
  "price_change": 0.72,
  "signal": "HOLD (Above Average)"
}
