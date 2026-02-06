# Ticket: ADRs - NautilusTrader Fork & Deployment

<!-- Status is tracked in the roadmap: Todo | In Progress | Blocked | Done | Won't Do -->
**Phase**: 1  
**Dependencies**: None

## Objective
Produce initial Architecture Decision Records for the NautilusTrader fork strategy and deployment architecture, capturing scope, rationale, and trade-offs so implementation tickets can proceed with shared context.

## Linked Specifications
- [Spec: docs/specs/core/README.md]
- [Spec: docs/specs/routing/README.md]
- [ADR: docs/adr/001-nautilus-fork.md]
- [ADR: docs/adr/006-deployment.md]

## Acceptance Criteria
1. ADR for NautilusTrader fork is created using ADR template with context, drivers, options, outcome, and links.
2. ADR for deployment architecture is created using ADR template with context, drivers, options, outcome, and links.
3. Ticket links and references updated to ensure discoverability from docs index/roadmap.

## Implementation Notes
- Keep ADRs concise but specific to fork scope (risk/backtest preservation, adapter hooks) and deployment slices (trading vs. intel/inference vs. scheduled jobs) targeting ~$100 fly.io budget.
- Align terminology with Beta-Trader layers (core, intel, signals, routing).

## Blocker Log
<!-- BLOCKED (YYYY-MM-DD): Reason and impact. -->

## Completion Evidence
<!-- DONE (YYYY-MM-DD): Commit hash, validation reference. -->
