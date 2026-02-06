# Risk Engine Specification

**Status**: Draft

## Purpose
The Risk Engine validates all order requests against configurable risk constraints before they reach the execution layer. It enforces position limits, drawdown thresholds, leverage caps, and stop-loss requirements to protect capital. This is a core NautilusTrader component that Beta-Trader preserves without modification.

## Dependencies
- **Internal**: [OrderRequest](../../interfaces/types.md#orderrequest), [RiskLimits](../../interfaces/types.md#risklimits), [PositionState](../../interfaces/types.md#positionstate)
- **External**: NautilusTrader core (`nautilus_core/src/risk/`)

## Interface Contract

### Inputs
- `order` (OrderRequest): Order to validate against risk limits
- `portfolio_state` (PortfolioState): Current portfolio positions and P&L

### Outputs
- `validated` (bool): Whether the order passes all risk checks
- `rejection_reason` (str | None): Reason if validation fails

### Errors
- `ValidationError`: When order fields are malformed
- `RiskLimitBreached`: When order would violate a risk constraint

## Behavioral Requirements
1. Every order must pass risk validation before venue submission
2. Stop-loss must be attached to every position when `stop_loss_required` is true
3. Drawdown exceeding `max_drawdown_pct` triggers automatic trading halt and human escalation
4. Daily loss exceeding `max_daily_loss_usd` halts all strategies for the remainder of the day

## Test Specification
- **Unit**: Validate each risk limit type independently
- **Integration**: End-to-end order flow through risk engine to venue adapter
- **Performance**: Risk check latency < 1 ms per order

## Implementation Scaffolding
Preserved from NautilusTrader core. See ADR-001 for fork strategy. Located in `core/nautilus_core/src/risk/`.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
