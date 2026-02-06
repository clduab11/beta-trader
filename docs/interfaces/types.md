# Shared Type Definitions

**Last Updated**: 2026-02-06  
**Status**: Draft  
**Scope**: Cross-layer data structures used by two or more modules

> All types defined here are the **single source of truth**. Module-specific types belong in their respective specs under `docs/specs/<layer>/`.

---

## Intel Layer Types

### IntelQuery

**Description**: Standardized query structure submitted to the Intel Orchestrator. Encapsulates the user's information need along with cost/depth preferences.

**Structure**:
- `query_id` (str): Unique identifier for this query (UUID v4)
- `text` (str): Natural language query string
- `depth` (IntelDepth): Search depth controlling source selection and cost
- `max_sources` (int): Upper bound on sources to consult (default: 10)
- `cache_ttl_seconds` (int | None): Override default cache TTL; `None` uses per-source defaults
- `correlation_id` (str): ID for tracing this query across layers
- `timestamp` (Timestamp): When the query was created

**Usage Example**:
Used by: `intel/orchestrator.py`, `strategies/base_predictor.py`

```python
query = IntelQuery(
    query_id=uuid4(),
    text="Will Bitcoin ETF approval happen before March 2026?",
    depth=IntelDepth.STANDARD,
    max_sources=10,
    correlation_id=correlation_id,
    timestamp=Timestamp.now(),
)
result = await orchestrator.gather_intel(query)
```

**References**:
- AGENTS.md: §6 Intel Pipeline Architecture — `IntelOrchestrator.gather_intel()`

---

### IntelDepth

**Description**: Enum controlling how many sources the Intel Orchestrator queries and at what cost.

**Structure**:
- `SHALLOW` — Exa.ai semantic search only (~$0.0025/query, ~200 ms)
- `STANDARD` — Parallel Exa + Tavily (~$0.0125/query, ~300 ms)
- `DEEP` — Full pipeline: Exa → Firecrawl → Jina embeddings (~$0.01–0.05/query, ~1–2 s)

**Usage Example**:
Used by: `intel/orchestrator.py`, `routing/router.py`

```python
if market_volatility > HIGH_THRESHOLD:
    depth = IntelDepth.DEEP
else:
    depth = IntelDepth.SHALLOW
```

**References**:
- AGENTS.md: §6 Intel Pipeline Architecture — depth parameter in `gather_intel()`

---

### IntelResult

**Description**: Aggregated intelligence output from one or more sources. Returned by the Intel Orchestrator after merging, deduplicating, and optionally embedding search results.

**Structure**:
- `query_id` (str): Matches the originating `IntelQuery.query_id`
- `correlation_id` (str): For cross-layer tracing
- `sources` (list[IntelSource]): Individual source results
- `merged_text` (str): Deduplicated, ranked text summary
- `embeddings` (list[list[float]] | None): Jina embeddings when depth is `DEEP`
- `depth_used` (IntelDepth): Actual depth that was executed
- `total_cost_usd` (float): Aggregated cost of all source calls
- `latency_ms` (float): Wall-clock time for the full pipeline
- `timestamp` (Timestamp): When the result was assembled
- `cached` (bool): Whether the result was served from Redis cache

**Nested Type — IntelSource**:
- `source_name` (str): e.g. `"exa"`, `"tavily"`, `"firecrawl"`
- `url` (str | None): Source URL if applicable
- `title` (str): Title or heading of the result
- `snippet` (str): Relevant text excerpt
- `relevance_score` (float): 0.0–1.0 relevance ranking
- `cost_usd` (float): Cost of this individual call
- `latency_ms` (float): Source-specific latency

**Usage Example**:
Used by: `signals/ensemble.py`, `strategies/base_predictor.py`

```python
result: IntelResult = await orchestrator.gather_intel(query)
if result.cached:
    log.info("Served from cache", cost=result.total_cost_usd)
for source in result.sources:
    log.debug(f"{source.source_name}: {source.relevance_score:.2f}")
```

**References**:
- AGENTS.md: §6 Intel Pipeline Architecture — return type of `gather_intel()`

---

## Signal Layer Types

### SignalOutput

**Description**: Prediction output from a single neural forecasting model. Represents the model's directional view, confidence, and metadata.

**Structure**:
- `signal_id` (str): Unique identifier (UUID v4)
- `model_name` (str): Identifier of the producing model (e.g. `"lstm"`, `"tft"`)
- `instrument` (str): Target instrument or market (e.g. `"BTC-USD"`, `"POLYMARKET:will-btc-hit-100k"`)
- `direction` (str): `"LONG"` | `"SHORT"` | `"NEUTRAL"`
- `magnitude` (float): Predicted magnitude of move (model-specific units)
- `confidence` (ModelConfidence): Confidence breakdown
- `horizon_seconds` (int): Forecast horizon in seconds
- `features_used` (list[str]): Feature names the model consumed
- `inference_latency_ms` (float): Time to run inference
- `inference_tier` (str): `"wasm"` | `"haiku"` | `"opus"` — which routing tier was used
- `timestamp` (Timestamp): When the signal was generated
- `correlation_id` (str): Tracing ID linking back to the originating Intel query

**Usage Example**:
Used by: `signals/ensemble.py`, `routing/router.py`, `strategies/base_predictor.py`

```python
signal = await lstm_model.predict(features)
if signal.confidence.overall >= 0.7:
    ensemble.add_signal(signal)
```

**References**:
- AGENTS.md: §2 Architecture Overview — Signal Layer
- AGENTS.md: §3 Codebase Structure — `signals/models/`

---

### ModelConfidence

**Description**: Granular confidence breakdown for a neural model's prediction. Separates model certainty from data quality and ensemble agreement.

**Structure**:
- `overall` (float): Composite confidence score 0.0–1.0
- `model_certainty` (float): Model's self-assessed certainty 0.0–1.0
- `data_quality` (float): Quality of input features 0.0–1.0
- `sample_size` (int): Number of training/calibration samples considered
- `calibration_score` (float | None): Historical calibration accuracy if available

**Usage Example**:
Used by: `signals/ensemble.py`, `strategies/base_predictor.py`

```python
if confidence.model_certainty > 0.8 and confidence.data_quality > 0.6:
    action = "execute"
elif confidence.overall < 0.3:
    action = "skip"
else:
    action = "reduce_size"
```

**References**:
- AGENTS.md: §2 Architecture Overview — Signal Layer confidence thresholds

---

### EnsembleResult

**Description**: Combined output from the model ensemble orchestrator. Aggregates multiple `SignalOutput` instances into a consensus view with weighted scoring.

**Structure**:
- `ensemble_id` (str): Unique identifier (UUID v4)
- `instrument` (str): Target instrument
- `signals` (list[SignalOutput]): Individual model signals included
- `consensus_direction` (str): `"LONG"` | `"SHORT"` | `"NEUTRAL"`
- `consensus_magnitude` (float): Weighted average magnitude
- `consensus_confidence` (ModelConfidence): Aggregated confidence
- `agreement_ratio` (float): Fraction of models that agree on direction (0.0–1.0)
- `model_weights` (dict[str, float]): Weights applied to each model
- `total_inference_cost_usd` (float): Sum of inference costs across all models
- `total_inference_latency_ms` (float): Max latency across parallel model calls
- `timestamp` (Timestamp): When the ensemble result was produced
- `correlation_id` (str): Tracing ID

**Usage Example**:
Used by: `routing/router.py`, `strategies/base_predictor.py`, `strategies/polymarket_arb.py`

```python
ensemble = await ensemble_orchestrator.run(instrument="BTC-USD", features=features)
if ensemble.agreement_ratio >= 0.6 and ensemble.consensus_confidence.overall >= 0.65:
    order = build_order(ensemble)
```

**References**:
- AGENTS.md: §3 Codebase Structure — `signals/ensemble.py`

---

## Execution Layer Types

### OrderRequest

**Description**: Standardized order structure submitted to the NautilusTrader execution engine. Bridges the signal/strategy layer with venue adapters.

**Structure**:
- `order_id` (str): Client-assigned unique order ID (UUID v4)
- `instrument` (str): Target instrument identifier
- `venue` (Venue): Target trading venue
- `side` (str): `"BUY"` | `"SELL"`
- `order_type` (str): `"MARKET"` | `"LIMIT"` | `"STOP_LIMIT"`
- `quantity` (float): Order quantity in base units
- `price` (float | None): Limit price; `None` for market orders
- `stop_price` (float | None): Stop trigger price
- `time_in_force` (str): `"GTC"` | `"IOC"` | `"FOK"` | `"DAY"`
- `reduce_only` (bool): If true, only reduces an existing position
- `strategy_id` (str): Originating strategy identifier
- `risk_limits` (RiskLimits): Risk constraints to validate before submission
- `correlation_id` (str): Tracing ID
- `timestamp` (Timestamp): When the order was created

**Usage Example**:
Used by: `strategies/base_predictor.py`, `strategies/polymarket_arb.py`, core execution engine

```python
order = OrderRequest(
    order_id=uuid4(),
    instrument="BTC-USD",
    venue=Venue.BINANCE,
    side="BUY",
    order_type="LIMIT",
    quantity=0.001,
    price=95000.00,
    time_in_force="GTC",
    reduce_only=False,
    strategy_id="crypto_momentum_v1",
    risk_limits=default_risk_limits,
    correlation_id=ensemble.correlation_id,
    timestamp=Timestamp.now(),
)
```

**References**:
- AGENTS.md: §2 Architecture Overview — Execution Layer (NautilusTrader)
- AGENTS.md: §3 Codebase Structure — `core/nautilus_trader/`

---

### PositionState

**Description**: Current state of a position held on a specific venue. Updated after fills, partial fills, and close events.

**Structure**:
- `position_id` (str): Unique position identifier
- `instrument` (str): Instrument being held
- `venue` (Venue): Venue where the position is held
- `side` (str): `"LONG"` | `"SHORT"` | `"FLAT"`
- `quantity` (float): Current position size
- `avg_entry_price` (float): Volume-weighted average entry price
- `unrealized_pnl` (float): Current unrealized P&L in quote currency
- `realized_pnl` (float): Total realized P&L for this position
- `margin_used` (float): Margin allocated to this position
- `opened_at` (Timestamp): When the position was first opened
- `updated_at` (Timestamp): Last state change timestamp
- `strategy_id` (str): Strategy that owns this position
- `correlation_id` (str): Tracing ID

**Usage Example**:
Used by: `strategies/base_predictor.py`, core portfolio management, risk engine

```python
position = portfolio.get_position("BTC-USD", Venue.BINANCE)
if position.side == "LONG" and position.unrealized_pnl < -max_loss:
    await close_position(position)
```

**References**:
- AGENTS.md: §2 Architecture Overview — Execution Layer
- AGENTS.md: §3 Codebase Structure — `core/nautilus_core/src/portfolio/`

---

### RiskLimits

**Description**: Risk management constraints evaluated by the NautilusTrader risk engine before order submission. These are per-strategy or global limits.

**Structure**:
- `max_position_size` (float): Maximum allowed position quantity
- `max_order_size` (float): Maximum single order quantity
- `max_notional_usd` (float): Maximum notional value in USD
- `max_drawdown_pct` (float): Maximum drawdown percentage before circuit breaker triggers (0.0–1.0)
- `max_open_positions` (int): Maximum concurrent open positions
- `max_daily_loss_usd` (float): Daily loss limit in USD
- `max_leverage` (float): Maximum leverage ratio
- `allowed_venues` (list[Venue]): Venues permitted for this strategy
- `stop_loss_required` (bool): Whether every order must have a stop-loss (default: `True`)

**Usage Example**:
Used by: `strategies/base_predictor.py`, core risk engine

```python
risk_limits = RiskLimits(
    max_position_size=0.01,
    max_order_size=0.005,
    max_notional_usd=100.0,  # $100 capital constraint
    max_drawdown_pct=0.20,
    max_open_positions=3,
    max_daily_loss_usd=20.0,
    max_leverage=1.0,
    allowed_venues=[Venue.BINANCE, Venue.POLYMARKET],
    stop_loss_required=True,
)
```

**References**:
- AGENTS.md: §9 Agent Behavioral Rules — stop-loss requirement
- AGENTS.md: §2 Architecture Overview — Risk Engine (position limits, drawdown)

---

## Common Types

### Timestamp

**Description**: Standardized time representation used throughout the platform. All timestamps are UTC, stored as nanosecond-precision Unix epochs for NautilusTrader compatibility plus an ISO 8601 string for human readability.

**Structure**:
- `unix_nanos` (int): Nanoseconds since Unix epoch (UTC)
- `iso8601` (str): ISO 8601 formatted string (e.g. `"2026-02-06T14:30:00.000Z"`)

**Usage Example**:
Used by: All layers

```python
ts = Timestamp.now()
print(ts.iso8601)   # "2026-02-06T14:30:00.000000000Z"
print(ts.unix_nanos) # 1770399000000000000
```

**References**:
- AGENTS.md: §4 Technology Stack — NautilusTrader uses nanosecond timestamps

---

### Currency

**Description**: Representation of a currency or digital asset. Supports both fiat (USD, EUR) and crypto (BTC, ETH) plus prediction market tokens.

**Structure**:
- `code` (str): ISO 4217 code for fiat or ticker symbol for crypto (e.g. `"USD"`, `"BTC"`, `"POLY"`)
- `precision` (int): Number of decimal places for this currency
- `currency_type` (str): `"FIAT"` | `"CRYPTO"` | `"PREDICTION_TOKEN"`

**Usage Example**:
Used by: `core/`, `strategies/`, venue adapters

```python
btc = Currency(code="BTC", precision=8, currency_type="CRYPTO")
usd = Currency(code="USD", precision=2, currency_type="FIAT")
```

**References**:
- AGENTS.md: §3 Codebase Structure — Venue Adapters (Binance, Kraken, Polymarket, Kalshi)

---

### Venue

**Description**: Enum identifying a supported trading venue. Each venue maps to a specific adapter in the adapters layer.

**Structure**:
- `BINANCE` — Binance CEX
- `KRAKEN` — Kraken CEX
- `POLYMARKET` — Polymarket prediction market
- `KALSHI` — Kalshi prediction market

**Usage Example**:
Used by: All layers that handle venue-specific logic

```python
if venue == Venue.POLYMARKET:
    adapter = PolymarketAdapter(config)
elif venue == Venue.BINANCE:
    adapter = BinanceAdapter(config)
```

**References**:
- AGENTS.md: §2 Architecture Overview — Venue Adapters
- AGENTS.md: §3 Codebase Structure — `core/nautilus_trader/adapters/`

---

## Cross-Layer Type Flow

```
IntelQuery ─► IntelOrchestrator ─► IntelResult
                                        │
                                        ▼
                              SignalOutput (per model)
                                        │
                                        ▼
                              EnsembleResult (aggregated)
                                        │
                                        ▼
                              OrderRequest ─► Risk Engine ─► Venue Adapter
                                                                 │
                                                                 ▼
                                                          PositionState
```
