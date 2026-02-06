# ADR-005: Cost Routing Strategy

**Status**: Proposed  
**Date**: 2026-02-06  
**Deciders**: @clduab11

## Context and Problem Statement
Beta-Trader operates under a ~$100 capital constraint and must minimize operational costs. Inference and reasoning tasks vary in complexity — some can be handled locally, while others require cloud LLM APIs. A tiered routing system is needed to optimize cost while maintaining prediction quality.

## Decision Drivers
- Capital constraint (~$100 total)
- Inference latency requirements (< 10 ms for simple, < 2 s for complex)
- Free model availability via OpenRouter
- Local WASM inference capability
- Cost per inference must be tracked and budgeted

## Considered Options
1. All cloud-based inference (single tier)
2. Two-tier: local WASM + cloud API
3. Three-tier: WASM (free) → Haiku (mid) → Opus (heavy)

## Decision Outcome
**Chosen option**: Option 3 — Three-tier routing with OpenRouter free model rotation

**Rationale**: The 3-tier system maximizes cost efficiency by handling simple signals locally for free, routing moderate complexity to low-cost Haiku, and reserving expensive Opus for complex reasoning. OpenRouter's free model rotation provides an additional cost buffer.

### Positive Consequences
- Majority of signals handled at zero cost (WASM)
- Graceful escalation through tiers
- Free model rotation via OpenRouter reduces cloud costs
- Per-request cost tracking enables budget enforcement

### Negative Consequences
- More complex routing logic
- Free models may have variable quality
- Three tiers require three different integration paths

## Links
- [Router Spec](../specs/routing/router.md)
- [Tier System Spec](../specs/routing/tier_system.md)
- [OpenRouter Client Spec](../specs/routing/openrouter_client.md)
- AGENTS.md §5: OpenRouter Free Model Rotation
