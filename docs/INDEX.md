# Beta-Trader Documentation Index

**Last Updated**: 2026-02-06

## Core Layer
- [Risk Engine](specs/core/risk_engine.md)
- [Execution](specs/core/execution.md)
- [Backtest](specs/core/backtest.md)
- [Portfolio](specs/core/portfolio.md)

## Intel Layer
- [Orchestrator](specs/intel/orchestrator.md)
- [Exa Source](specs/intel/exa_source.md)
- [Tavily Source](specs/intel/tavily_source.md)
- [Firecrawl Source](specs/intel/firecrawl_source.md)
- [Redis Cache](specs/intel/redis_cache.md)

## Signals Layer
- [LSTM Model](specs/signals/lstm.md)
- [N-BEATS Model](specs/signals/nbeats.md)
- [TFT Model](specs/signals/tft.md)
- [DeepAR Model](specs/signals/deepar.md)
- [TCN Model](specs/signals/tcn.md)
- [Ensemble Orchestrator](specs/signals/ensemble.md)
- [WASM Inference](specs/signals/wasm_inference.md)

## Routing Layer
- [Router](specs/routing/router.md)
- [Tier System](specs/routing/tier_system.md)
- [OpenRouter Client](specs/routing/openrouter_client.md)

## Adapters Layer
- [Polymarket Adapter](specs/adapters/polymarket.md)
- [Kalshi Adapter](specs/adapters/kalshi.md)

## Strategies Layer
- [Base Predictor](specs/strategies/base_predictor.md)
- [Polymarket Arbitrage](specs/strategies/polymarket_arb.md)
- [Crypto Momentum](specs/strategies/crypto_momentum.md)

---

## Architecture Decision Records
- [ADR-001: NautilusTrader Fork Strategy](adr/001-nautilus-fork.md)
- [ADR-002: Polymarket Adapter Architecture](adr/002-polymarket-adapter.md)
- [ADR-003: Kalshi Adapter Architecture](adr/003-kalshi-adapter.md)
- [ADR-004: Neural Model Selection](adr/004-neural-models.md)
- [ADR-005: Cost Routing Strategy](adr/005-cost-routing.md)
- [ADR-006: Deployment Architecture](adr/006-deployment.md)

---

## Shared Interfaces
- [Type Definitions](interfaces/types.md)
- [Error Handling Patterns](interfaces/errors.md)
- [Event Schemas](interfaces/events.md)
