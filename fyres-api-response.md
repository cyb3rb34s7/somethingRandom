Here is the **Definitive "Source of Truth" Data Dictionary** for your Copy Trading Engine.

These JSON samples are based strictly on **Fyers API v3 Standards** and the **actual logs** your developer captured. Use these to verify your system's behavior step-by-step.

---

### Step 1: Trade Detection (Input)

**Context:** The Master Trader buys 50 shares of IDEA on NSE.
**Source:** Fyers WebSocket (`order_ws`)
**Event:** `on_trades` callback.

#### 🔴 The "OnTrades" Packet (What Fyers Sends)

*Critique for Testing:* Your code **MUST** handle the nested `trades` dictionary.

```json
{
  "s": "ok",
  "trades": {
    "tradeNumber": "75849302-21726639",
    "orderNumber": "23080400089344", 
    "tradedQty": 50,
    "tradePrice": 14.50,
    "tradeValue": 725.00,
    "productType": "INTRADAY",
    "clientId": "XV20986",
    "exchangeOrderNo": "1100000009596016",
    "orderType": 2,
    "side": 1,
    "symbol": "NSE:IDEA-EQ",
    "orderDateTime": "17-12-2025 10:12:58",
    "fyToken": "101000000014366",
    "exchange": 10,
    "segment": 10
  }
}

```

**Key Fields to Parse:**

* `trades.orderNumber`: Maps to your `broker_order_id`.
* `trades.clientId`: Used to identify `user_id` (via mapping).
* `trades.symbol`: `NSE:IDEA-EQ` (Note the suffix).
* `trades.side`: `1` = BUY, `-1` = SELL.

---

### Step 2: Trader Identification (Setup)

**Context:** Before receiving trades, your system calls `get_profile` to know who owns the token.
**Source:** HTTP GET `https://api-t1.fyers.in/api/v3/profile`

#### 🔵 Profile Response (What you use for Mapping)

```json
{
  "s": "ok",
  "code": 200,
  "message": "",
  "data": {
    "fy_id": "XV20986",
    "name": "Rajesh Kumar",
    "image": null,
    "email_id": "rajesh@example.com",
    "pin_change_date": "21-11-2024 10:10:10",
    "mobile_number": "9876543210",
    "totp": true,
    "pwd_change_date": "20-11-2024 12:00:00",
    "pan": "ABCDE1234F",
    "aadhaar": "XXXX-XXXX-1234"
  }
}

```

**Logic:** Store `data.fy_id` ("XV20986") mapped to your internal `user_id`.

---

### Step 3: Execution Request (Action)

**Context:** Your `Executor` sends an order for the **Client** to copy the trade.
**Source:** HTTP POST `https://api-t1.fyers.in/api/v3/orders/sync`
**Library Call:** `fyers.place_order(data=...)`

#### 📤 The Request Payload (What YOU Send)

*Critique:* Ensure `symbol` has `-EQ` and `type` is an integer.

```json
{
  "symbol": "NSE:IDEA-EQ",
  "qty": 50,
  "type": 2,
  "side": 1,
  "productType": "INTRADAY",
  "limitPrice": 0,
  "stopPrice": 0,
  "validity": "DAY",
  "disclosedQty": 0,
  "offlineOrder": false,
  "stopLoss": 0,
  "takeProfit": 0
}

```

**Field Reference:**

* `type: 2`: Market Order.
* `side: 1`: BUY.
* `productType`: Must match the master (INTRADAY/CNC).

---

### Step 4: Execution Response (Output)

**Context:** Immediate response from Fyers after you try to place the order.

#### ✅ Scenario A: Success (Market Open)

```json
{
  "s": "ok",
  "code": 1101,
  "message": "Order submitted successfully",
  "id": "123456789012"
}

```

**Logic:**

* `s == 'ok'`: Mark database status as `SUCCESS`.
* `id`: Save this as `client_broker_order_id`.

#### ❌ Scenario B: Failure (Market Closed / Test Tonight)

```json
{
  "s": "error",
  "code": -400,
  "message": "Market is closed. Please place an AMO order.",
  "id": ""
}

```

**Logic:**

* `s == 'error'`: Mark database status as `FAILED`.
* `message`: Save to `error_message` column.

#### ❌ Scenario C: Token Error (Expired)

```json
{
  "s": "error",
  "code": -16,
  "message": "Access token is expired or invalid",
  "id": ""
}

```

**Logic:** Trigger `TokenManager` to refresh the token and retry.

---

### How to Manually Verify

1. **Run your `simulate_trade.py**`.
2. **Check your Database:**
* If you see `Status: SUCCESS` -> Your mock worked.
* If you see `Status: FAILED` and `Error: Market is closed` -> **REAL API SUCCESS.** Your system successfully talked to Fyers.
* If you see `Status: RETRY` and `Error: Invalid Symbol` -> Your symbol formatting logic is broken.



This JSON set is the absolute standard. If your code produces or parses anything different, it is wrong.
