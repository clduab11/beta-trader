# Intel Orchestrator Specification

**Status**: Draft

## Purpose
The Intel Orchestrator is the central coordinator for the intelligence pipeline. It accepts `IntelQuery` requests, selects sources based on depth, executes parallel queries, merges and deduplicates results, and returns a unified `IntelResult`. It manages cost optimization by routing queries to the cheapest effective source first.

## Dependencies
- **Internal**: [IntelQuery](../../interfaces/types.md#intelquery), [IntelResult](../../interfaces/types.md#intelresult), [IntelDepth](../../interfaces/types.md#inteldepth), Exa Source, Tavily Source, Firecrawl Source, Redis Cache
- **External**: `httpx`, `redis`, `asyncio`

## Interface Contract

### Inputs
- `query` (IntelQuery): Standardized intelligence query

### Outputs
- `result` (IntelResult): Aggregated, deduplicated intelligence

### Errors
- `APIError`: When all sources fail for a given depth
- `RateLimitError`: When source rate limits are exhausted

## Behavioral Requirements
1. SHALLOW depth queries only Exa.ai
2. STANDARD depth queries Exa + Tavily in parallel
3. DEEP depth runs full pipeline: Exa → Firecrawl → Jina embeddings
4. Results are cached in Redis with configurable TTL
5. Cached results must be served without source queries

## Test Specification
- **Unit**: Source selection logic per depth, result merging, deduplication
- **Integration**: End-to-end query with mocked source APIs
- **Performance**: Cached query < 50 ms; SHALLOW < 300 ms; STANDARD < 500 ms

## Implementation Scaffolding
Located in `intel/orchestrator.py`. See AGENTS.md §6 for architecture details. Uses async patterns exclusively.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
