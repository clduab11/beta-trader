# ADR-001: NautilusTrader Fork Strategy

**Status**: Proposed  
**Date**: 2026-02-06  
**Deciders**: @clduab11

## Context and Problem Statement
Beta-Trader needs a robust execution core with proven risk controls while adding prediction-market adapters and neural inference. NautilusTrader provides a battle-tested risk and backtest engine, but upstream releases may diverge from our adapter and routing requirements. We must choose how to adopt NautilusTrader to balance stability, extensibility, and maintenance overhead.

## Decision Drivers
- Preserve NautilusTrader risk/backtest correctness with minimal regressions.
- Enable custom adapters (Polymarket, Kalshi) and routing without blocking on upstream timelines.
- Keep an upgrade path for upstream fixes while controlling churn.
- Maintain lean operational cost and build complexity for a small team.

## Considered Options
1. Full hard fork with deep customization and no upstream tracking.
2. Upstream-as-dependency only, extending purely via plugins/adapters (no fork).
3. Managed fork with upstream-tracking: minimal patches, adapters added in-tree, periodic rebases.

## Decision Outcome
**Chosen option**: Option 3 — Managed fork with upstream tracking.

**Rationale**: A managed fork lets us embed prediction-market adapters and routing hooks quickly while keeping the risk/backtest engine identical to upstream. Periodic rebases preserve access to upstream fixes. We avoid the brittleness of heavy divergence (Option 1) and the constraints of a plugin-only approach (Option 2) where required hooks may be missing.

### Positive Consequences
- Control over adapter integration and routing hooks without waiting on upstream approvals.
- Faster delivery for prediction-market venues while retaining upstream risk/backtest stability.
- Clear rebase workflow to import upstream security and performance fixes.

### Negative Consequences
- Ongoing rebase/merge overhead to track upstream releases.
- Risk of fork drift if rebases are delayed or patches are invasive.

## Links
- Ticket: docs/tickets/phase-1/adrs-nautilus-fork-deployment.md
- Related spec: docs/specs/core/README.md (fork scope)
