# Event Schemas

**Last Updated**: 2026-02-06  
**Status**: Draft  
**Scope**: Asynchronous event structures for inter-module communication across all layers

> Events are the primary mechanism for **loose coupling** between layers. Each layer emits events when it completes work; downstream layers subscribe to the events they need. This document defines the canonical event envelope and all event types.

---

## Event Envelope

Every event shares a common envelope structure. Payloads are type-specific and defined per event below.

### EventEnvelope

**Structure**:
- `event_id` (str): Unique identifier (UUID v4)
- `event_type` (str): One of the event type names defined below
- `timestamp` (Timestamp): When the event was emitted
- `source_module` (str): Module that emitted the event (e.g. `"intel.orchestrator"`)
- `correlation_id` (str): Tracing ID linking this event to the originating request chain
- `payload` (dict): Event-type-specific data (see individual schemas)

**Serialization**: Events are serialized as JSON for transport. All field names use `snake_case`.

**Example Envelope**:

```json
{
  "event_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "event_type": "IntelGathered",
  "timestamp": {
    "unix_nanos": 1770399000000000000,
    "iso8601": "2026-02-06T14:30:00.000000000Z"
  },
  "source_module": "intel.orchestrator",
  "correlation_id": "req-5678-abcd",
  "payload": { ... }
}
```

**References**:
- AGENTS.md: §2 Architecture Overview — inter-layer data flow

---

## Event Types

### IntelGathered

**Trigger**: Emitted by the Intel Orchestrator when an intelligence query completes (whether from cache or live sources).

**Payload Structure**:
- `query_id` (str): ID of the originating `IntelQuery`
- `depth_used` (str): `"SHALLOW"` | `"STANDARD"` | `"DEEP"`
- `source_count` (int): Number of sources consulted
- `total_cost_usd` (float): Aggregated cost of the query
- `latency_ms` (float): Total wall-clock time
- `cached` (bool): Whether result was served from Redis
- `result_summary` (str): Brief summary of the intel (first 200 chars of merged text)
- `has_embeddings` (bool): Whether Jina embeddings are available

**Consumers**: `signals/ensemble.py`, `strategies/base_predictor.py`

**Example Flow**:

```
Strategy                 Intel Orchestrator            Signal Layer
   │                            │                          │
   │── IntelQuery ──────────────▶                          │
   │                            │                          │
   │                            │── query Exa + Tavily     │
   │                            │── merge results          │
   │                            │                          │
   │                            │── emit IntelGathered ───▶│
   │                            │                          │
   │◀── IntelResult ────────────│                          │
   │                            │                    begin inference
```

**References**:
- AGENTS.md: §6 Intel Pipeline Architecture — `gather_intel()` return path

---

### SignalGenerated

**Trigger**: Emitted by the Ensemble Orchestrator (or an individual model during solo inference) when a prediction is ready.

**Payload Structure**:
- `ensemble_id` (str): ID of the ensemble run (or individual signal ID if solo)
- `instrument` (str): Target instrument
- `consensus_direction` (str): `"LONG"` | `"SHORT"` | `"NEUTRAL"`
- `consensus_confidence` (float): Overall confidence score 0.0–1.0
- `agreement_ratio` (float): Model agreement ratio 0.0–1.0
- `models_used` (list[str]): Names of models that contributed
- `models_failed` (list[str]): Names of models that failed (InferenceError)
- `total_inference_latency_ms` (float): Max latency across models
- `total_inference_cost_usd` (float): Sum of inference costs

**Consumers**: `routing/router.py`, `strategies/base_predictor.py`, `strategies/polymarket_arb.py`

**Example Flow**:

```
Intel Orchestrator       Ensemble Orchestrator        Routing Layer
   │                            │                          │
   │── IntelGathered ──────────▶│                          │
   │                            │                          │
   │                            │── run LSTM, TFT, N-BEATS │
   │                            │── aggregate signals      │
   │                            │                          │
   │                            │── emit SignalGenerated ──▶│
   │                            │                          │
   │                            │                   route to strategy
```

**References**:
- AGENTS.md: §3 Codebase Structure — `signals/ensemble.py`
- AGENTS.md: §2 Architecture Overview — Signal Layer → Routing Layer

---

### OrderPlaced

**Trigger**: Emitted by the Execution Layer after an order has been successfully submitted to a venue adapter and acknowledged by the venue.

**Payload Structure**:
- `order_id` (str): Client order ID
- `venue_order_id` (str | None): Venue-assigned order ID (if immediately available)
- `instrument` (str): Instrument being traded
- `venue` (str): Venue name (e.g. `"BINANCE"`, `"POLYMARKET"`)
- `side` (str): `"BUY"` | `"SELL"`
- `order_type` (str): `"MARKET"` | `"LIMIT"` | `"STOP_LIMIT"`
- `quantity` (float): Order quantity
- `price` (float | None): Limit price if applicable
- `strategy_id` (str): Originating strategy

**Consumers**: `strategies/base_predictor.py`, portfolio management, risk engine

**Example Flow**:

```
Strategy               Execution Engine             Venue Adapter
   │                        │                            │
   │── OrderRequest ───────▶│                            │
   │                        │── validate risk limits     │
   │                        │── submit to adapter ──────▶│
   │                        │                            │── ACK from venue
   │                        │◀── venue_order_id ─────────│
   │                        │                            │
   │◀── emit OrderPlaced ──│                            │
```

**References**:
- AGENTS.md: §2 Architecture Overview — Execution Layer (Order Management System)

---

### PositionUpdated

**Trigger**: Emitted by the Portfolio Manager when a position's state changes due to a fill, partial fill, close, or liquidation event.

**Payload Structure**:
- `position_id` (str): Position identifier
- `instrument` (str): Instrument held
- `venue` (str): Venue name
- `side` (str): `"LONG"` | `"SHORT"` | `"FLAT"`
- `quantity` (float): Updated position size
- `avg_entry_price` (float): Updated VWAP entry
- `unrealized_pnl` (float): Current unrealized P&L
- `realized_pnl` (float): Cumulative realized P&L
- `change_reason` (str): `"FILL"` | `"PARTIAL_FILL"` | `"CLOSE"` | `"LIQUIDATION"` | `"STOP_LOSS"`
- `fill_price` (float | None): Price of the triggering fill
- `fill_quantity` (float | None): Quantity of the triggering fill
- `strategy_id` (str): Strategy that owns this position

**Consumers**: `strategies/base_predictor.py`, risk engine, portfolio dashboard

**Example Flow**:

```
Venue Adapter           Portfolio Manager            Strategy / Risk
   │                        │                            │
   │── Fill Report ────────▶│                            │
   │                        │── update position state    │
   │                        │── recalculate P&L          │
   │                        │                            │
   │                        │── emit PositionUpdated ───▶│
   │                        │                            │
   │                        │                     check stop-loss
   │                        │                     update drawdown
```

**References**:
- AGENTS.md: §3 Codebase Structure — `core/nautilus_core/src/portfolio/`
- AGENTS.md: §2 Architecture Overview — Portfolio Management

---

### RiskLimitBreached

**Trigger**: Emitted by the Risk Engine when a risk constraint is violated or about to be violated. This is a **critical** event that may trigger automatic position reduction or trading halt.

**Payload Structure**:
- `breach_id` (str): Unique identifier for this breach event
- `breach_type` (str): `"MAX_DRAWDOWN"` | `"MAX_POSITION_SIZE"` | `"MAX_DAILY_LOSS"` | `"MAX_LEVERAGE"` | `"MAX_OPEN_POSITIONS"`
- `severity` (str): `"WARNING"` (approaching limit) | `"CRITICAL"` (limit exceeded)
- `limit_name` (str): Human-readable limit name
- `limit_value` (float): The configured limit threshold
- `current_value` (float): The current value that breached/approaches the limit
- `venue` (str | None): Affected venue if venue-specific
- `strategy_id` (str | None): Affected strategy if strategy-specific
- `auto_action` (str | None): Action taken automatically: `"REDUCE_POSITION"` | `"HALT_TRADING"` | `"CANCEL_PENDING_ORDERS"` | `None`
- `requires_human_review` (bool): Whether this breach triggers an escalation (always `true` for `CRITICAL` severity)

**Consumers**: All strategies, portfolio management, alerting/monitoring

**Example Flow**:

```
Portfolio Manager          Risk Engine              Strategy / Alerting
   │                          │                          │
   │── PositionUpdated ──────▶│                          │
   │                          │── check drawdown         │
   │                          │── drawdown = 18%         │
   │                          │── limit = 20%            │
   │                          │                          │
   │                          │── emit RiskLimitBreached ▶│
   │                          │   (severity: WARNING)     │
   │                          │                          │
   │                          │                    reduce exposure
   │                          │                    alert human
```

**Escalation**: Per AGENTS.md §9, `CRITICAL` severity breaches **must** pause automated trading and request human review before resuming.

**References**:
- AGENTS.md: §9 Escalation Triggers — modifying risk management parameters, >20% drawdown
- AGENTS.md: §2 Architecture Overview — Risk Engine (position limits, drawdown)

---

## Event Flow: End-to-End Pipeline

The complete event chain for a single prediction cycle:

```
┌──────────────┐     IntelGathered     ┌──────────────┐    SignalGenerated    ┌──────────────┐
│  Intel Layer │ ────────────────────▶ │ Signal Layer │ ────────────────────▶ │Routing Layer │
└──────────────┘                       └──────────────┘                       └──────┬───────┘
                                                                                     │
                                                                              OrderRequest
                                                                                     │
                                                                                     ▼
┌──────────────┐    PositionUpdated    ┌──────────────┐     OrderPlaced      ┌──────────────┐
│  Strategies  │ ◀──────────────────── │  Portfolio   │ ◀──────────────────── │  Execution   │
└──────────────┘                       └──────┬───────┘                       └──────────────┘
                                              │
                                    RiskLimitBreached
                                       (if needed)
                                              │
                                              ▼
                                     ┌──────────────┐
                                     │ Risk Engine  │
                                     └──────────────┘
```

---

## Event Bus Design Principles

1. **At-least-once delivery**: Consumers must be idempotent — duplicate `event_id` values should be safely ignored.
2. **Ordered within correlation**: Events sharing a `correlation_id` should be processed in emission order.
3. **Fire-and-forget emission**: Producers emit events without waiting for consumer acknowledgment.
4. **Schema evolution**: New optional fields may be added to payloads without breaking existing consumers. Required fields are never removed.
5. **Observability**: Every event emission should be logged at `INFO` level with `event_type`, `event_id`, and `correlation_id`.

---

## Event Serialization

Events are serialized as JSON. The canonical format uses `snake_case` for all field names, ISO 8601 for timestamps, and string-encoded UUIDs.

```python
import json
from dataclasses import asdict

def serialize_event(event: EventEnvelope) -> str:
    """Serialize an event to JSON for transport."""
    return json.dumps(asdict(event), default=str)

def deserialize_event(data: str) -> EventEnvelope:
    """Deserialize JSON into an EventEnvelope."""
    raw = json.loads(data)
    return EventEnvelope(**raw)
```
