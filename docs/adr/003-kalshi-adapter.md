# ADR-003: Kalshi Adapter Architecture

**Status**: Proposed  
**Date**: 2026-02-06  
**Deciders**: @clduab11

## Context and Problem Statement
Beta-Trader needs to interact with the Kalshi prediction market for regulated event contracts. The adapter must handle Kalshi's specific contract model (event-based binary options with regulatory constraints) while integrating with NautilusTrader's adapter pattern.

## Decision Drivers
- NautilusTrader adapter compatibility
- Kalshi API structure and rate limits
- Regulatory compliance requirements (CFTC-regulated exchange)
- Event contract lifecycle management

## Considered Options
1. Custom standalone client
2. NautilusTrader adapter pattern with REST integration
3. Shared base class with Polymarket adapter

## Decision Outcome
**Chosen option**: Option 2 — NautilusTrader adapter pattern with REST integration

**Rationale**: Kalshi's API is REST-based and its contract model is sufficiently different from Polymarket to warrant a separate adapter. A shared base class would create unnecessary coupling given the different market mechanics.

### Positive Consequences
- Clean separation from Polymarket adapter
- Full compatibility with NautilusTrader execution pipeline
- Handles Kalshi-specific regulatory requirements independently

### Negative Consequences
- Some code duplication between Polymarket and Kalshi adapters
- Must maintain two separate adapter implementations

## Links
- [Kalshi Adapter Spec](../specs/adapters/kalshi.md)
- [ADR-002: Polymarket Adapter Architecture](002-polymarket-adapter.md)
