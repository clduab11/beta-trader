# Redis Cache Specification

**Status**: Draft

## Purpose
The Redis Cache provides response caching for the Intel pipeline, reducing costs and latency for repeated or similar intelligence queries. It stores serialized `IntelResult` objects with configurable TTL per source and depth level.

## Dependencies
- **Internal**: [IntelResult](../../interfaces/types.md#intelresult), [IntelQuery](../../interfaces/types.md#intelquery)
- **External**: Redis (via `redis` Python package)

## Interface Contract

### Inputs
- `key` (str): Cache key derived from query parameters
- `value` (IntelResult): Result to cache
- `ttl_seconds` (int): Time-to-live for the cached entry

### Outputs
- `cached_result` (IntelResult | None): Cached result if present, `None` on cache miss

### Errors
- `APIError`: When Redis is unreachable

## Behavioral Requirements
1. Cache hits must be served in < 50 ms
2. TTL defaults: SHALLOW = 300 s, STANDARD = 180 s, DEEP = 600 s
3. Cache key must include query text hash and depth level
4. Must gracefully degrade on Redis unavailability (continue without cache)

## Test Specification
- **Unit**: Key generation, TTL handling, serialization/deserialization
- **Integration**: Redis round-trip with real Redis instance
- **Performance**: Cache hit latency < 50 ms

## Implementation Scaffolding
Located in `intel/cache/redis_cache.py`. Requires `REDIS_URL` environment variable.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
