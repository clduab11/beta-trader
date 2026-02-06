# ADR-006: Deployment Architecture

**Status**: Proposed  
**Date**: 2026-02-06  
**Deciders**: @clduab11

## Context and Problem Statement
Beta-Trader must deploy a cost-efficient, globally reachable service with both compute-heavy neural inference and latency-sensitive trading execution. Budget is ~$100 on fly.io, so we need a lightweight architecture that separates hot-path execution from auxiliary tasks, keeps secrets safe, and supports rollbacks.

## Decision Drivers
- Minimize run-rate cost while keeping low-latency access to exchanges/prediction markets.
- Simple rollback and blue/green releases for safety.
- Isolation between inference workloads and trading OMS to prevent noisy-neighbor issues.
- Clear observability (logs/metrics/traces) with minimal operational overhead.

## Considered Options
1. Single all-in-one fly.io app (trading + inference + intel) with horizontal autoscale.
2. Two-process split: trading core + background worker in one app, inference external.
3. Three-slice split: trading core app, intel/inference worker app, and scheduled jobs; shared Redis for state and queueing.

## Decision Outcome
**Chosen option**: Option 3 — Three-slice split on fly.io.

**Rationale**: Separating trading from intel/inference reduces blast radius and lets us scale each slice independently within budget. A small Redis instance handles caching/queues. Scheduled jobs run in a minimal worker process, simplifying releases and rollbacks.

### Positive Consequences
- Independent scaling for trading vs. intel/inference; predictable spend.
- Lower risk of trading latency spikes from heavy inference workloads.
- Clear deployment artifacts per slice; simpler blue/green and rollbacks.

### Negative Consequences
- More deployment units to manage and monitor.
- Cross-service coordination (Redis queues) adds failure modes.

## Links
- Ticket: docs/tickets/phase-1/adrs-nautilus-fork-deployment.md
- Related spec: docs/specs/routing/README.md (routing to inference)
- Related spec: docs/specs/intel/README.md (intel worker)
