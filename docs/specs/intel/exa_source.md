# Exa Source Specification

**Status**: Draft

## Purpose
The Exa Source adapter provides neural/semantic web search via the Exa.ai API. It is the primary intelligence source for all depth levels and specializes in finding semantically relevant content rather than keyword matches.

## Dependencies
- **Internal**: [IntelSource](../../interfaces/types.md#intelresult) (nested type), [APIError](../../interfaces/errors.md#apierror), [RateLimitError](../../interfaces/errors.md#ratelimiterror)
- **External**: Exa.ai API, `httpx`

## Interface Contract

### Inputs
- `query` (str): Natural language search query
- `num_results` (int): Maximum number of results to return

### Outputs
- `results` (list[IntelSource]): Ranked search results with relevance scores

### Errors
- `APIError`: When Exa.ai returns non-2xx response
- `RateLimitError`: When Exa.ai rate limit is exceeded

## Behavioral Requirements
1. Cost per query: ~$2.50/1k searches
2. Expected latency: ~200 ms
3. Must handle rate limits with exponential backoff
4. Results must include relevance scores for ranking

## Test Specification
- **Unit**: Response parsing, error handling
- **Integration**: Mocked Exa.ai API round-trip
- **Performance**: Single query latency < 500 ms (including network)

## Implementation Scaffolding
Located in `intel/sources/exa.py`. Requires `EXA_API_KEY` environment variable.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
