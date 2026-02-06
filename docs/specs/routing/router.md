# Router Specification

**Status**: Draft

## Purpose
The Router is the central decision point in the 3-tier cost routing system. It evaluates signal complexity and cost constraints to route inference requests to the optimal tier: WASM (free/fast), Haiku (mid-cost), or Opus (high-cost/heavy reasoning).

## Dependencies
- **Internal**: [SignalOutput](../../interfaces/types.md#signaloutput), [EnsembleResult](../../interfaces/types.md#ensembleresult), WASM Tier, Haiku Tier, Opus Tier
- **External**: None (orchestration only)

## Interface Contract

### Inputs
- `request` (RoutingRequest): Signal request with complexity assessment and cost budget

### Outputs
- `response` (RoutingResponse): Routed result from the selected tier

### Errors
- `InferenceError`: When all tiers fail

## Behavioral Requirements
1. Tier 1 (WASM) must be attempted first for simple classifications
2. Tier 2 (Haiku) used for moderate complexity at $0.25/1M tokens
3. Tier 3 (Opus) reserved for complex reasoning at $15/1M tokens
4. Must respect per-request cost budgets
5. Must fall back to lower tiers on higher-tier failure

## Test Specification
- **Unit**: Tier selection logic, cost budget enforcement
- **Integration**: End-to-end routing with mocked tiers
- **Performance**: Routing decision overhead < 5 ms

## Implementation Scaffolding
Located in `routing/router.py`. See AGENTS.md §2 Architecture Overview — Routing Layer.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
