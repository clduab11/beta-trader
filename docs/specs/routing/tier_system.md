# Tier System Specification

**Status**: Draft

## Purpose
The Tier System defines the three inference tiers used by the Router: WASM (local, free), Haiku (Claude Haiku, mid-cost), and Opus (Claude Opus, high-cost). Each tier provides a common interface so the Router can swap between them transparently.

## Dependencies
- **Internal**: [SignalOutput](../../interfaces/types.md#signaloutput), [InferenceError](../../interfaces/errors.md#inferenceerror), WASM Inference, OpenRouter Client
- **External**: Anthropic API (for Haiku/Opus tiers)

## Interface Contract

### Inputs
- `request` (TierRequest): Inference request with features and model configuration

### Outputs
- `response` (TierResponse): Inference result with cost and latency metadata

### Errors
- `InferenceError`: When inference fails at the selected tier
- `RateLimitError`: When API-based tiers are rate-limited

## Behavioral Requirements
1. All tiers must implement the same interface for hot-swapping
2. WASM tier: < 10 ms latency, $0 cost
3. Haiku tier: < 500 ms latency, $0.25/1M tokens
4. Opus tier: < 2 s latency, $15/1M tokens
5. Cost metadata must be reported per-request

## Test Specification
- **Unit**: Each tier independently with mocked backends
- **Integration**: Router → Tier selection → response
- **Performance**: Per-tier latency targets as specified above

## Implementation Scaffolding
Located in `routing/tiers/`. See AGENTS.md §3 — `routing/tiers/wasm_tier.py`, `haiku_tier.py`, `opus_tier.py`.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
