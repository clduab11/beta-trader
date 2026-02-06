# Base Predictor Strategy Specification

**Status**: Draft

## Purpose
The Base Predictor is the foundational trading strategy class that all Beta-Trader strategies extend. It defines the standard lifecycle: gather intelligence → generate signals → evaluate ensemble → submit orders. It integrates with NautilusTrader's strategy base class while adding prediction market and neural inference capabilities.

## Dependencies
- **Internal**: [IntelQuery](../../interfaces/types.md#intelquery), [IntelResult](../../interfaces/types.md#intelresult), [EnsembleResult](../../interfaces/types.md#ensembleresult), [OrderRequest](../../interfaces/types.md#orderrequest), [RiskLimits](../../interfaces/types.md#risklimits), Intel Orchestrator, Ensemble Orchestrator, Risk Engine
- **External**: NautilusTrader strategy base class

## Interface Contract

### Inputs
- `market_event` (MarketEvent): Incoming market data trigger
- `config` (StrategyConfig): Strategy-specific configuration

### Outputs
- `orders` (list[OrderRequest]): Zero or more orders to submit

### Errors
- `ValidationError`: When strategy configuration is invalid

## Behavioral Requirements
1. Must extend NautilusTrader's strategy base class
2. Must implement stop-loss logic on every position (AGENTS.md §9)
3. Must validate all orders against RiskLimits before submission
4. Must log all trading decisions with rationale
5. Must support backtest mode without live venue connections

## Test Specification
- **Unit**: Signal-to-order conversion, stop-loss placement, risk check
- **Integration**: Full strategy lifecycle with mocked intel and signals
- **Performance**: Decision loop < 500 ms end-to-end

## Implementation Scaffolding
Located in `strategies/base_predictor.py`. To be built in Phase 4. See AGENTS.md §8.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
