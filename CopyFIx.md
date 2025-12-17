# Copy Trading Engine - Complete Fix Plan

## Problem Summary
The copy trading engine has components that exist but are **never wired together**. WebSocket connects but trades are dropped silently.

---

## Fyers v3 Response Format (Source of Truth)

```json
{
   "s": "ok",
   "trades": {
      "tradeNumber": "23080400089344-21726639",
      "orderNumber": "23080400089344",
      "tradedQty": 1,
      "tradePrice": 7.95,
      "productType": "INTRADAY",
      "clientId": "XV20986",
      "side": -1,
      "symbol": "NSE:IDEA-EQ",
      "exchange": 10,
      "segment": 10
   }
}
```

**Key insight:** Data is nested under `trades` key, NOT at root level.

---

## CRITICAL: AsyncSession Compatibility

**WARNING:** `AsyncSession` does NOT support `db.query()`. This will crash:
```python
trade = db.query(Trade).filter(Trade.id == 1).first()  # CRASHES!
```

Must use SQLAlchemy 2.0 async syntax:
```python
result = await db.execute(select(Trade).where(Trade.id == 1))
trade = result.scalar_one_or_none()
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/core/database.py` | Add async_session_maker |
| `backend/main.py` | Add lifespan startup, wire components |
| `backend/services/copy_trading/websocket_manager.py` | Fix callback, add client_id mapping, event loop |
| `backend/services/copy_trading/trade_handler.py` | Fix Fyers v3 parsing, async DB |
| `backend/services/copy_trading/copy_engine.py` | Fix placeholder + **refactor all queries to async** |
| `backend/services/copy_trading/executor.py` | Symbol `-EQ` suffix + **refactor all queries to async** |
| `backend/services/copy_trading/token_manager.py` | **Refactor all queries to async** |

---

## Implementation Steps

### Step 1: Add async_session_maker to database.py

**File:** `backend/core/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Async engine (convert postgresql:// to postgresql+asyncpg://)
ASYNC_DATABASE_URL = settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')

async_engine = create_async_engine(ASYNC_DATABASE_URL)

async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

---

### Step 2: Fix main.py (Add Startup Wiring)

**File:** `backend/main.py`

```python
import asyncio
from contextlib import asynccontextmanager
import redis.asyncio as redis
from backend.core.config import settings
from backend.services.copy_trading import (
    websocket_manager,
    trade_handler,
    copy_engine,
    executor
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    print("Starting TradeKnight Copy Trading Engine...")

    # 1. Initialize Redis
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )

    # 2. Initialize services with Redis
    await websocket_manager.initialize(redis_client)
    await trade_handler.initialize(redis_client)
    await copy_engine.initialize(redis_client, executor)

    # 3. CRITICAL: Wire the callback
    websocket_manager.set_trade_callback(trade_handler.process)

    # 4. Start copy engine background listener
    copy_task = asyncio.create_task(copy_engine.start())

    print("Copy Trading Engine Started")

    yield

    # SHUTDOWN
    print("Shutting down...")
    copy_task.cancel()
    await websocket_manager.shutdown()
    await redis_client.close()

# Update FastAPI app - add lifespan parameter
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)
```

---

### Step 3: Fix websocket_manager.py

**File:** `backend/services/copy_trading/websocket_manager.py`

#### 3a. Update __init__:

```python
def __init__(self):
    self._connections: Dict[int, TraderConnection] = {}
    self._redis: Optional[redis.Redis] = None
    self._on_trade_callback: Optional[Callable] = None
    self._is_running = False
    self._reconnect_tasks: Dict[int, asyncio.Task] = {}
    # NEW
    self._client_id_to_user_map: Dict[str, int] = {}
    self._loop: Optional[asyncio.AbstractEventLoop] = None
```

#### 3b. Update initialize():

```python
async def initialize(self, redis_client: redis.Redis):
    self._redis = redis_client
    self._is_running = True
    self._loop = asyncio.get_running_loop()
    logger.info("WebSocket manager initialized")
```

#### 3c. Update connect_trader() - fetch profile to get client_id:

```python
async def connect_trader(self, trader_id: int, access_token: str) -> bool:
    if trader_id in self._connections:
        conn = self._connections[trader_id]
        if conn.status == ConnectionStatus.CONNECTED:
            return True

    conn = TraderConnection(trader_id, access_token)
    self._connections[trader_id] = conn

    try:
        conn.status = ConnectionStatus.CONNECTING

        # NEW: Fetch Fyers profile to get client_id mapping
        from fyers_apiv3 import fyersModel
        fyers = fyersModel.FyersModel(
            client_id=settings.FYERS_APP_ID,
            token=access_token,
            is_async=False
        )
        profile_response = fyers.get_profile()

        if profile_response.get('s') == 'ok':
            fyers_client_id = profile_response['data']['fy_id']
            self._client_id_to_user_map[fyers_client_id] = trader_id
            logger.info(f"Mapped Fyers client {fyers_client_id} to user {trader_id}")
        else:
            logger.error(f"Failed to get profile: {profile_response}")
            conn.status = ConnectionStatus.ERROR
            return False

        formatted_token = f"{settings.FYERS_APP_ID}:{access_token}"

        # CHANGED: Use method reference instead of lambda for on_trades
        socket = order_ws.FyersOrderSocket(
            access_token=formatted_token,
            write_to_file=False,
            log_path="",
            on_connect=lambda: self._handle_connect(trader_id),
            on_close=lambda: self._handle_close(trader_id),
            on_error=lambda error: self._handle_error(trader_id, error),
            on_general=lambda msg: self._handle_general(trader_id, msg),
            on_orders=lambda msg: self._handle_order(trader_id, msg),
            on_positions=lambda msg: self._handle_position(trader_id, msg),
            on_trades=self._handle_trade_event  # NO LAMBDA
        )

        conn.socket = socket
        socket.connect()

        await self._update_redis_state(trader_id, ConnectionStatus.CONNECTING)
        return True

    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        conn.status = ConnectionStatus.ERROR
        return False
```

#### 3d. Replace _handle_trade() with _handle_trade_event():

```python
def _handle_trade_event(self, message: dict):
    """Handle trade from Fyers - extracts user_id from clientId."""
    try:
        trade_data = message.get("trades", {})
        fyers_client_id = trade_data.get("clientId")

        if not fyers_client_id:
            logger.warning(f"No clientId in message: {message}")
            return

        user_id = self._client_id_to_user_map.get(fyers_client_id)
        if not user_id:
            logger.error(f"Unknown Fyers client: {fyers_client_id}")
            return

        logger.info(f"Trade event for user {user_id}")

        if user_id in self._connections:
            self._connections[user_id].last_message_at = datetime.now(timezone.utc)

        if self._on_trade_callback and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._on_trade_callback(user_id, message),
                self._loop
            )

    except Exception as e:
        logger.error(f"Error in _handle_trade_event: {e}")
```

---

### Step 4: Fix trade_handler.py

**File:** `backend/services/copy_trading/trade_handler.py`

#### 4a. Update process() - create own DB session:

```python
from backend.core.database import async_session_maker

async def process(self, user_id: int, message: dict) -> Optional[int]:
    """Process trade event - creates own DB session."""
    async with async_session_maker() as db:
        try:
            trade_data = message.get('trades')
            if not trade_data:
                return None

            broker_order_id = str(trade_data.get('orderNumber', ''))
            if not broker_order_id:
                return None

            cache_key = f"{user_id}:{broker_order_id}"
            if cache_key in self._processed_orders:
                return None

            # DB dedup - need async version
            exists = await db.execute(
                select(Trade).where(Trade.broker_order_id == broker_order_id)
            )
            if exists.scalar():
                self._add_to_cache(cache_key)
                return None

            trade = self._parse_trade(user_id, message)
            if not trade:
                return None

            db.add(trade)
            await db.commit()
            await db.refresh(trade)

            self._add_to_cache(cache_key)
            logger.info(f"Stored trade {trade.id}")

            await self._publish_trade(trade.id)
            return trade.id

        except Exception as e:
            logger.error(f"Error processing trade: {e}")
            await db.rollback()
            return None
```

#### 4b. Update _parse_trade() for Fyers v3 fields:

```python
def _parse_trade(self, trader_id: int, message: dict) -> Optional[Trade]:
    try:
        trade_data = message.get('trades', {})
        if not trade_data:
            return None

        full_symbol = trade_data.get('symbol', '')
        exchange, symbol = self._parse_symbol(full_symbol)

        side_code = trade_data.get('side', 0)
        side = 'BUY' if side_code == 1 else 'SELL'

        quantity = trade_data.get('tradedQty', 0)
        price = Decimal(str(trade_data.get('tradePrice', 0)))

        trade = Trade(
            trader_id=trader_id,
            broker_order_id=str(trade_data.get('orderNumber')),
            symbol=symbol,
            exchange=exchange,
            side=side,
            quantity=quantity,
            price=price,
            order_type=self._map_order_type(trade_data.get('orderType', 2)),
            product_type=trade_data.get('productType', 'CNC'),
            executed_qty=quantity,
            remaining_qty=0,
            status='SUCCESS',
            executed_at=datetime.now(timezone.utc),
            detected_at=datetime.now(timezone.utc),
            segment=self._map_segment(trade_data.get('segment', 10)),
            raw_response=message
        )
        return trade

    except Exception as e:
        logger.error(f"Parse error: {e}")
        return None

def _map_order_type(self, code: int) -> str:
    return {1: 'LIMIT', 2: 'MARKET', 3: 'SL-MARKET', 4: 'SL-LIMIT'}.get(code, 'MARKET')

def _map_segment(self, code: int) -> str:
    return {10: 'EQUITY', 11: 'FNO', 12: 'COMMODITY'}.get(code, 'EQUITY')
```

---

### Step 5: Fix copy_engine.py (CRITICAL: Use SQLAlchemy 2.0 Async Syntax)

**File:** `backend/services/copy_trading/copy_engine.py`

**WARNING:** `AsyncSession` does NOT support `db.query()`. Must use `await db.execute(select(...))`.

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database import async_session_maker

async def _on_trade_received(self, trade_id: int):
    """Actually process the trade - was a placeholder before."""
    try:
        async with async_session_maker() as db:
            logger.info(f"Processing copy trades for trade_id: {trade_id}")
            await self.process_trade(trade_id, db)
    except Exception as e:
        logger.error(f"Error in _on_trade_received: {e}")

async def _listen_for_trades(self):
    if not self._redis:
        return

    try:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self.REDIS_TRADE_CHANNEL)

        async for message in pubsub.listen():
            if not self._is_running:
                break

            if message['type'] == 'message':
                trade_id = int(message['data'])
                await self._on_trade_received(trade_id)

    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(self.REDIS_TRADE_CHANNEL)

# CRITICAL: Refactor process_trade() for AsyncSession
async def process_trade(self, trade_id: int, db: AsyncSession) -> List[CopyTrade]:
    """Process a trade - REFACTORED FOR ASYNC."""
    if not market_hours.is_market_open():
        logger.warning(f"Market closed, skipping trade {trade_id}")
        return []

    # OLD: trade = db.query(Trade).filter(Trade.id == trade_id).first()
    # NEW: Use select() + execute()
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()

    if not trade:
        logger.error(f"Trade {trade_id} not found")
        return []

    # Get eligible clients (also refactored for async)
    eligible_relationships = await self._get_eligible_clients(
        trade.trader_id, trade.symbol, trade.segment, db
    )

    if not eligible_relationships:
        logger.info(f"No eligible clients for trade {trade_id}")
        return []

    # Create copy trades
    copy_trades = []
    for relationship in eligible_relationships:
        copy_trade = await self._create_copy_trade(trade, relationship, db)
        if copy_trade:
            copy_trades.append(copy_trade)

    if copy_trades:
        await db.commit()  # ASYNC COMMIT
        logger.info(f"Created {len(copy_trades)} copy trades for trade {trade_id}")

        if self._executor:
            await self._executor.execute_all(copy_trades, db)

    return copy_trades

# CRITICAL: Refactor _get_eligible_clients() for AsyncSession
async def _get_eligible_clients(
    self, trader_id: int, symbol: str, segment: str, db: AsyncSession
) -> List[TraderClientRelationship]:
    """Get eligible clients - REFACTORED FOR ASYNC."""

    # OLD: relationships = db.query(TraderClientRelationship).filter(...).all()
    # NEW:
    result = await db.execute(
        select(TraderClientRelationship).where(
            TraderClientRelationship.trader_id == trader_id,
            TraderClientRelationship.status == 'approved',
            TraderClientRelationship.auto_copy_enabled == True
        )
    )
    relationships = result.scalars().all()

    eligible = []

    for rel in relationships:
        if not rel.accepts_segment(segment):
            continue
        if rel.is_symbol_blacklisted(symbol):
            continue

        # Check broker connection - ASYNC
        broker_result = await db.execute(
            select(BrokerCredential).where(
                BrokerCredential.user_id == rel.client_id,
                BrokerCredential.broker_name == 'FYERS',
                BrokerCredential.is_active == True
            )
        )
        broker_cred = broker_result.scalar_one_or_none()

        if not broker_cred or not broker_cred.is_connected():
            continue

        eligible.append(rel)

    return eligible

# CRITICAL: Refactor _create_copy_trade() for AsyncSession
async def _create_copy_trade(
    self, trade: Trade, relationship: TraderClientRelationship, db: AsyncSession
) -> Optional[CopyTrade]:
    """Create copy trade - REFACTORED FOR ASYNC."""
    copy_qty = self._calculate_quantity(trade, relationship)

    if copy_qty <= 0:
        return None

    copy_trade = CopyTrade(
        original_trade_id=trade.id,
        client_id=relationship.client_id,
        relationship_id=relationship.id,
        quantity=copy_qty,
        status='PENDING',
        max_retries=3,
        calculated_from_ratio=str(relationship.copy_ratio),
        created_at=datetime.now(timezone.utc)
    )

    db.add(copy_trade)
    return copy_trade
```

---

### Step 6: Fix executor.py (CRITICAL: Use SQLAlchemy 2.0 Async Syntax)

**File:** `backend/services/copy_trading/executor.py`

**WARNING:** `AsyncSession` does NOT support `db.query()`. Must use `await db.execute(select(...))`.

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def execute_all(self, copy_trades: List[CopyTrade], db: AsyncSession):
    """Execute all copy trades in parallel - REFACTORED FOR ASYNC."""
    tasks = [self._execute_single(ct, db) for ct in copy_trades]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

async def _execute_single(self, copy_trade: CopyTrade, db: AsyncSession):
    """Execute single copy trade - REFACTORED FOR ASYNC."""
    async with self._semaphore:
        start = time.time()

        try:
            # Update status to EXECUTING
            copy_trade.status = 'EXECUTING'
            await db.commit()

            # Get client's access token
            access_token = await token_manager.get_valid_token(copy_trade.client_id, db)

            # OLD: original_trade = db.query(Trade).filter(Trade.id == copy_trade.original_trade_id).first()
            # NEW: Use select() + execute()
            result = await db.execute(
                select(Trade).where(Trade.id == copy_trade.original_trade_id)
            )
            original_trade = result.scalar_one_or_none()

            if not original_trade:
                raise ValueError(f"Original trade {copy_trade.original_trade_id} not found")

            # Build order params with -EQ suffix fix
            order_params = self._build_order_params(original_trade, copy_trade)

            # Place order on Fyers
            response = await self._place_order(access_token, order_params)

            elapsed = (time.time() - start) * 1000

            if response.get('s') == 'ok':
                copy_trade.status = 'SUCCESS'
                copy_trade.broker_order_id = response.get('id')
                copy_trade.executed_at = datetime.now(timezone.utc)
            else:
                copy_trade.status = 'RETRY'
                copy_trade.error_message = response.get('message', 'Unknown error')
                copy_trade.attempts += 1

            copy_trade.execution_time_ms = int(elapsed)
            await db.commit()

        except Exception as e:
            logger.error(f"Execution error for copy_trade {copy_trade.id}: {e}")
            copy_trade.status = 'RETRY'
            copy_trade.error_message = str(e)
            copy_trade.attempts += 1
            await db.commit()

def _build_order_params(self, trade: Trade, copy_trade: CopyTrade) -> dict:
    """Build Fyers order params - add -EQ suffix for equity."""
    symbol = f"{trade.exchange}:{trade.symbol}"
    if trade.segment == 'EQUITY' and '-EQ' not in symbol:
        symbol = f"{symbol}-EQ"

    return {
        "symbol": symbol,
        "qty": copy_trade.quantity,
        "side": 1 if trade.side == 'BUY' else -1,
        "type": 2,  # Market order
        "productType": trade.product_type or "CNC",
        "validity": "DAY",
        "offlineOrder": False,
        "disclosedQty": 0
    }
```

---

### Step 7: Fix token_manager.py (CRITICAL: Use SQLAlchemy 2.0 Async Syntax)

**File:** `backend/services/copy_trading/token_manager.py`

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_valid_token(self, user_id: int, db: AsyncSession) -> str:
    """Get valid access token - REFACTORED FOR ASYNC."""
    # Check cache first
    if user_id in self._token_cache:
        cached = self._token_cache[user_id]
        if cached['expires_at'] > datetime.now(timezone.utc):
            return cached['token']

    # OLD: credential = db.query(BrokerCredential).filter(...).first()
    # NEW:
    result = await db.execute(
        select(BrokerCredential).where(
            BrokerCredential.user_id == user_id,
            BrokerCredential.broker_name == 'FYERS',
            BrokerCredential.is_active == True
        )
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise TokenExpiredError(f"No active broker credential for user {user_id}")

    # Check if needs refresh
    if credential.needs_refresh():
        if credential.refresh_token:
            await self._refresh_token(credential, db)
        else:
            raise TokenExpiredError("Token expired, no refresh token")

    # Decrypt and cache
    decrypted = self._decrypt_token(credential.access_token)
    self._token_cache[user_id] = {
        'token': decrypted,
        'expires_at': credential.expires_at or datetime.now(timezone.utc) + timedelta(hours=1)
    }

    return decrypted

async def _refresh_token(self, credential: BrokerCredential, db: AsyncSession):
    """Refresh token - REFACTORED FOR ASYNC."""
    # ... refresh logic ...
    await db.commit()
```

---

## Execution Order

1. `backend/core/database.py` - Add async_session_maker
2. `backend/services/copy_trading/websocket_manager.py` - All changes (client_id mapping, event loop)
3. `backend/services/copy_trading/trade_handler.py` - Fyers v3 parsing + async DB
4. `backend/services/copy_trading/copy_engine.py` - Fix placeholder + **refactor to SQLAlchemy 2.0 async**
5. `backend/services/copy_trading/executor.py` - Symbol fix + **refactor to SQLAlchemy 2.0 async**
6. `backend/services/copy_trading/token_manager.py` - **Refactor to SQLAlchemy 2.0 async**
7. `backend/main.py` - Add lifespan wiring
8. Test locally

---

## Dependencies to Add

```
asyncpg  # For async PostgreSQL
```

---

## Key SQLAlchemy 2.0 Async Patterns

| Old Sync Pattern | New Async Pattern |
|------------------|-------------------|
| `db.query(Model).filter(...).first()` | `result = await db.execute(select(Model).where(...)); result.scalar_one_or_none()` |
| `db.query(Model).filter(...).all()` | `result = await db.execute(select(Model).where(...)); result.scalars().all()` |
| `db.commit()` | `await db.commit()` |
| `db.rollback()` | `await db.rollback()` |
| `db.refresh(obj)` | `await db.refresh(obj)` |
| `exists().where(...)` | `select(exists().where(...))` then `result.scalar()` |

---

## Flow After Fix

```
Fyers WebSocket
       ↓ on_trades callback
_handle_trade_event(message)
       ↓ Extract clientId from message['trades']
       ↓ Look up user_id
trade_handler.process(user_id, message)
       ↓ Parse using trades['orderNumber'], trades['tradedQty']
       ↓ Save to DB
       ↓ Publish to Redis
copy_engine._on_trade_received(trade_id)
       ↓ process_trade(trade_id, db)
       ↓ Get eligible clients
       ↓ Create CopyTrade records
executor.execute_all(copy_trades, db)
       ↓ Place orders on Fyers for each client
```
