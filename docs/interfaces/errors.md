# Error Handling Patterns

**Last Updated**: 2026-02-06  
**Status**: Draft  
**Scope**: Shared error types, retry strategies, and circuit breaker patterns used across all layers

> Module-specific error handling details belong in the respective module specs. This document defines the **common error taxonomy** and **standard recovery patterns** that every module must follow.

---

## Error Base Structure

All errors in Beta-Trader extend a common base to ensure consistent logging, tracing, and error propagation.

### BaseError

**Structure**:
- `error_type` (str): One of the error category names defined below
- `message` (str): Human-readable error description
- `timestamp` (Timestamp): When the error occurred
- `source_module` (str): Module that raised the error (e.g. `"intel.exa"`, `"signals.lstm"`)
- `correlation_id` (str): Tracing ID linking to the originating request
- `retry_count` (int): Number of retries already attempted (starts at 0)
- `original_request` (dict | None): Serialized original request for replay (optional)
- `stack_trace` (str | None): Python traceback string (optional; included in `DEBUG` log level)

**References**:
- AGENTS.md: §9 Agent Behavioral Rules — proper error handling with retries

---

## Error Categories

### APIError

**When Thrown**: An external API (Exa.ai, Firecrawl, Tavily, Jina, OpenRouter, venue REST APIs) returns a non-2xx response or times out.

**Retry Strategy**:
- Max attempts: 3
- Backoff: Exponential — 1 s, 2 s, 4 s
- Circuit breaker: Yes (see [Circuit Breaker Pattern](#circuit-breaker-pattern))

**Required Context**:
- `service_name` (str): API service identifier (e.g. `"exa"`, `"tavily"`, `"binance"`)
- `http_status` (int | None): HTTP status code if available
- `endpoint` (str): API endpoint that was called
- `request_duration_ms` (float): How long the request took before failure

**Handling Example**:

```python
try:
    response = await httpx_client.get(url, timeout=10.0)
    response.raise_for_status()
except httpx.HTTPStatusError as exc:
    raise APIError(
        message=f"{service_name} returned {exc.response.status_code}",
        source_module="intel.exa",
        service_name="exa",
        http_status=exc.response.status_code,
        endpoint=url,
        request_duration_ms=elapsed,
        correlation_id=query.correlation_id,
    )
```

**References**:
- AGENTS.md: §6 Intel Pipeline Architecture — external API calls
- AGENTS.md: §4 Technology Stack — httpx for async HTTP

---

### RateLimitError

**When Thrown**: An external API returns HTTP 429 or the client detects a rate-limit header indicating quota exhaustion.

**Retry Strategy**:
- Max attempts: 5
- Backoff: Respect `Retry-After` header if present; otherwise exponential — 2 s, 4 s, 8 s, 16 s, 32 s
- Circuit breaker: Yes — after 3 consecutive rate limits, open circuit for 60 s

**Required Context**:
- `service_name` (str): API service identifier
- `retry_after_seconds` (float | None): Value from `Retry-After` header
- `quota_remaining` (int | None): Remaining quota if reported by API
- `quota_reset_at` (Timestamp | None): When quota resets

**Handling Example**:

```python
except httpx.HTTPStatusError as exc:
    if exc.response.status_code == 429:
        retry_after = float(exc.response.headers.get("Retry-After", 2.0))
        raise RateLimitError(
            message=f"{service_name} rate limited",
            source_module="intel.tavily",
            service_name="tavily",
            retry_after_seconds=retry_after,
            correlation_id=query.correlation_id,
        )
```

**Special Handling for OpenRouter Free Models**:
When a free model is rate-limited, the `ModelRotator` marks the model as rate-limited and rotates to the next available model **without** raising an error to the caller. Only if **all** free models are rate-limited simultaneously is a `RateLimitError` propagated.

**References**:
- AGENTS.md: §5 OpenRouter Free Model Rotation — `mark_rate_limited()`
- AGENTS.md: §4 Technology Stack — SDK best practices for 429 handling

---

### ValidationError

**When Thrown**: Input validation fails before processing. This covers malformed requests, missing required fields, out-of-range values, and schema violations.

**Retry Strategy**:
- Max attempts: 0 (not retryable — fix the input)
- Backoff: None
- Circuit breaker: No

**Required Context**:
- `field_name` (str): Name of the invalid field
- `expected` (str): Description of expected value/format
- `received` (str): Actual value received (sanitized)
- `validation_rule` (str): Rule that was violated

**Handling Example**:

```python
if order.quantity <= 0:
    raise ValidationError(
        message="Order quantity must be positive",
        source_module="strategies.base_predictor",
        field_name="quantity",
        expected="float > 0",
        received=str(order.quantity),
        validation_rule="positive_quantity",
        correlation_id=order.correlation_id,
    )
```

**References**:
- AGENTS.md: §4 Technology Stack — Pydantic for config validation
- AGENTS.md: §9 Agent Behavioral Rules — validate before trading

---

### ExecutionError

**When Thrown**: An order submission, amendment, or cancellation fails at the venue level. Covers rejected orders, insufficient balance, and venue connectivity issues.

**Retry Strategy**:
- Max attempts: 2 (only for transient failures like timeouts)
- Backoff: Linear — 500 ms, 1 s
- Circuit breaker: Yes — after 5 consecutive execution failures on a venue, pause trading on that venue for 5 minutes

**Required Context**:
- `venue` (Venue): Trading venue
- `order_id` (str): Client order ID
- `rejection_reason` (str | None): Venue-reported rejection reason
- `venue_error_code` (str | None): Venue-specific error code
- `is_transient` (bool): Whether the error is likely transient (e.g. timeout vs. insufficient balance)

**Handling Example**:

```python
try:
    await adapter.submit_order(order)
except VenueTimeoutError:
    raise ExecutionError(
        message="Order submission timed out",
        source_module="adapters.binance",
        venue=Venue.BINANCE,
        order_id=order.order_id,
        rejection_reason=None,
        is_transient=True,
        correlation_id=order.correlation_id,
    )
except VenueRejectionError as exc:
    raise ExecutionError(
        message=f"Order rejected: {exc.reason}",
        source_module="adapters.binance",
        venue=Venue.BINANCE,
        order_id=order.order_id,
        rejection_reason=exc.reason,
        venue_error_code=exc.code,
        is_transient=False,
        correlation_id=order.correlation_id,
    )
```

**References**:
- AGENTS.md: §9 Agent Behavioral Rules — escalation on unexpected venue responses
- AGENTS.md: §2 Architecture Overview — Execution Layer

---

### InferenceError

**When Thrown**: A neural model fails during inference. Covers model loading failures, tensor shape mismatches, WASM runtime errors, and timeout during prediction.

**Retry Strategy**:
- Max attempts: 2
- Backoff: Exponential — 500 ms, 1 s
- Circuit breaker: Yes — after 3 consecutive inference failures for the same model, exclude from ensemble for 10 minutes

**Required Context**:
- `model_name` (str): Name of the failing model (e.g. `"lstm"`, `"tft"`)
- `inference_tier` (str): `"wasm"` | `"haiku"` | `"opus"`
- `input_shape` (str | None): Shape of the input tensor if available
- `error_detail` (str): Low-level error message from the model runtime

**Handling Example**:

```python
try:
    output = await model.predict(features)
except WasmRuntimeError as exc:
    raise InferenceError(
        message=f"WASM inference failed for {model.name}",
        source_module="signals.lstm",
        model_name="lstm",
        inference_tier="wasm",
        error_detail=str(exc),
        correlation_id=correlation_id,
    )
```

**Ensemble Degradation**: When an individual model raises `InferenceError`, the ensemble orchestrator should:
1. Log the error with full context
2. Exclude the model from the current ensemble run
3. Continue with remaining models if at least 2 are healthy
4. Raise `InferenceError` only if fewer than 2 models are available

**References**:
- AGENTS.md: §3 Codebase Structure — `signals/wasm/`
- AGENTS.md: §2 Architecture Overview — Signal Layer

---

## Retry Patterns

### Exponential Backoff Strategy

The default retry strategy for transient errors. Each retry doubles the wait time up to a maximum.

```python
import asyncio
from random import uniform

async def retry_with_backoff(
    fn,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
):
    """Execute fn with exponential backoff on failure."""
    for attempt in range(max_attempts):
        try:
            return await fn()
        except (APIError, RateLimitError) as exc:
            if attempt == max_attempts - 1:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            if jitter:
                delay = uniform(delay * 0.5, delay * 1.5)
            log.warning(
                "Retrying",
                attempt=attempt + 1,
                delay=delay,
                error=str(exc),
            )
            await asyncio.sleep(delay)
```

**Parameters by Error Type**:

| Error Type | Max Attempts | Base Delay | Max Delay | Jitter |
|---|---|---|---|---|
| APIError | 3 | 1.0 s | 30 s | Yes |
| RateLimitError | 5 | 2.0 s | 60 s | Yes |
| ExecutionError (transient) | 2 | 0.5 s | 5 s | No |
| InferenceError | 2 | 0.5 s | 5 s | Yes |
| ValidationError | 0 | — | — | — |

---

### Circuit Breaker Pattern

Prevents cascading failures when a downstream service is persistently unhealthy. Beta-Trader uses a **three-state** circuit breaker.

**States**:
1. **CLOSED** (normal) — Requests flow through. Failures are counted.
2. **OPEN** (tripped) — All requests immediately fail with a `CircuitOpenError`. No calls to downstream.
3. **HALF-OPEN** (probing) — A single test request is allowed through. If it succeeds, transition to CLOSED. If it fails, transition back to OPEN.

**Configuration**:

| Service Category | Failure Threshold | Open Duration | Half-Open Probe Interval |
|---|---|---|---|
| Intel APIs (Exa, Tavily, Firecrawl) | 5 failures in 60 s | 120 s | 30 s |
| Neural Models | 3 failures in 60 s | 600 s (10 min) | 60 s |
| Venue Adapters | 5 failures in 120 s | 300 s (5 min) | 60 s |
| OpenRouter (per model) | 3 failures in 30 s | 60 s | 15 s |

**State Diagram**:

```
         success
    ┌────────────────┐
    │                │
    ▼                │
 CLOSED ──failure──▶ OPEN
    ▲    threshold   │
    │    exceeded     │ open_duration
    │                 │ expired
    │                 ▼
    └──success── HALF-OPEN
                     │
                failure
                     │
                     ▼
                   OPEN
```

**Implementation Sketch**:

```python
import time

class CircuitBreaker:
    def __init__(self, failure_threshold: int, open_duration: float):
        self.failure_threshold = failure_threshold
        self.open_duration = open_duration
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"
        self.opened_at = 0.0

    async def call(self, fn):
        if self.state == "OPEN":
            if time.monotonic() - self.opened_at >= self.open_duration:
                self.state = "HALF_OPEN"
            else:
                raise CircuitOpenError(f"Circuit open for {self.open_duration}s")

        try:
            result = await fn()
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as exc:
            self.failure_count += 1
            self.last_failure_time = time.monotonic()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.opened_at = time.monotonic()
            raise
```

**References**:
- AGENTS.md: §9 Agent Behavioral Rules — implement proper error handling with retries
- AGENTS.md: §9 Escalation Triggers — pause on unexpected API responses

---

## Error Propagation Rules

1. **Transient errors** (network timeouts, 5xx, rate limits) → retry with backoff, then circuit breaker
2. **Non-transient errors** (validation, auth, 4xx except 429) → fail immediately, log, and propagate
3. **Partial failures in ensemble** → degrade gracefully, continue with available models
4. **Risk engine errors** → **always escalate** to human review (AGENTS.md §9 Escalation Triggers)
5. **Capital-affecting errors** → log at `CRITICAL` level, halt trading on the affected venue

---

## Logging Standards

All errors must be logged with structured fields for observability:

```python
log.error(
    "Order execution failed",
    error_type="ExecutionError",
    venue="BINANCE",
    order_id=order.order_id,
    correlation_id=order.correlation_id,
    is_transient=True,
    retry_count=2,
    latency_ms=1500.0,
)
```

**Required Log Fields**: `error_type`, `source_module`, `correlation_id`, `timestamp`  
**Recommended Log Fields**: `retry_count`, `latency_ms`, venue/service-specific identifiers
