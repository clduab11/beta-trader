# Backtest Engine Specification

**Status**: Draft

## Purpose
The Backtest Engine provides both vectorized and event-driven backtesting of trading strategies against historical data. It enables validation of strategies before live deployment, supporting accurate P&L simulation, slippage modeling, and performance metrics. This is a core NautilusTrader component that Beta-Trader preserves without modification.

## Dependencies
- **Internal**: Strategies, Portfolio, Risk Engine, [PositionState](../../interfaces/types.md#positionstate)
- **External**: NautilusTrader core (`nautilus_core/src/backtest/`), Polars for data handling

## Interface Contract

### Inputs
- `strategy` (Strategy): Strategy instance to backtest
- `data` (BacktestData): Historical price/event data
- `config` (BacktestConfig): Simulation parameters (fees, slippage, initial capital)

### Outputs
- `results` (BacktestResults): P&L curve, trade log, performance metrics

### Errors
- `ValidationError`: When configuration or data is invalid

## Behavioral Requirements
1. Must support both vectorized (fast) and event-driven (accurate) modes
2. Backtest of 1 year of daily data should complete in < 30 seconds
3. All strategies must pass backtest validation before live deployment (AGENTS.md §9)
4. Must report maximum drawdown and flag if > 20%

## Test Specification
- **Unit**: Data ingestion, fee calculation, slippage modeling
- **Integration**: Full strategy backtest with known expected outcomes
- **Performance**: 1-year daily data backtest < 30 s

## Implementation Scaffolding
Preserved from NautilusTrader core. See ADR-001 for fork strategy. Located in `core/nautilus_core/src/backtest/`.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
