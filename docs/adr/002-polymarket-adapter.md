# ADR-002: Polymarket Adapter Architecture

**Status**: Proposed  
**Date**: 2026-02-06  
**Deciders**: @clduab11

## Context and Problem Statement
Beta-Trader needs to interact with the Polymarket prediction market for placing orders, tracking positions, and receiving real-time market data. The adapter must integrate with NautilusTrader's existing adapter pattern while accommodating Polymarket's unique market structure (binary event contracts, CLOB model).

## Decision Drivers
- NautilusTrader adapter compatibility
- Polymarket REST + WebSocket API requirements
- Real-time data streaming needs
- Binary event contract model (yes/no shares)

## Considered Options
1. Custom standalone client (bypass NautilusTrader adapter pattern)
2. NautilusTrader adapter pattern with REST-only integration
3. NautilusTrader adapter pattern with REST + WebSocket (full integration)

## Decision Outcome
**Chosen option**: Option 3 — Full NautilusTrader adapter with REST + WebSocket

**Rationale**: Preserves compatibility with NautilusTrader's execution and risk engines while supporting real-time data. REST-only would add unacceptable latency for price updates.

### Positive Consequences
- Full compatibility with NautilusTrader execution pipeline
- Real-time market data via WebSocket
- Consistent with existing Binance/Kraken adapter patterns

### Negative Consequences
- More complex implementation (WebSocket reconnection, state management)
- Must handle Polymarket-specific contract semantics within NautilusTrader types

## Links
- [Polymarket Adapter Spec](../specs/adapters/polymarket.md)
- [ADR-001: NautilusTrader Fork Strategy](001-nautilus-fork.md)
