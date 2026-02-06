# Kalshi Adapter Specification

**Status**: Draft

## Purpose
The Kalshi Adapter connects Beta-Trader's execution engine to the Kalshi prediction market. It implements the Kalshi REST API for order management, position tracking, and market data following NautilusTrader's adapter pattern.

## Dependencies
- **Internal**: [OrderRequest](../../interfaces/types.md#orderrequest), [PositionState](../../interfaces/types.md#positionstate), [Venue](../../interfaces/types.md#venue), [ExecutionError](../../interfaces/errors.md#executionerror), Execution Engine
- **External**: Kalshi API, `httpx`

## Interface Contract

### Inputs
- `order` (OrderRequest): Order to submit to Kalshi

### Outputs
- `order_status` (OrderStatus): Venue-reported order state
- `market_data` (MarketData): Event contract prices and volumes

### Errors
- `ExecutionError`: When order submission fails
- `APIError`: When Kalshi API is unreachable

## Behavioral Requirements
1. Must follow NautilusTrader adapter pattern for compatibility
2. Must support Kalshi's event contract model
3. Must handle Kalshi-specific order types (yes/no contracts, binary events)
4. Must map Kalshi events to NautilusTrader order/position types

## Test Specification
- **Unit**: Order mapping, event parsing, contract normalization
- **Integration**: Mocked Kalshi API order lifecycle
- **Performance**: Order submission latency < 100 ms (excluding network)

## Implementation Scaffolding
Located in `core/nautilus_trader/adapters/kalshi/`. To be built in Phase 3. See AGENTS.md §8 and ADR-003.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
