# Tavily Source Specification

**Status**: Draft

## Purpose
The Tavily Source adapter provides real-time news and general web search via the Tavily API. It complements Exa.ai by focusing on time-sensitive, news-oriented content at low cost.

## Dependencies
- **Internal**: [IntelSource](../../interfaces/types.md#intelresult) (nested type), [APIError](../../interfaces/errors.md#apierror), [RateLimitError](../../interfaces/errors.md#ratelimiterror)
- **External**: Tavily API, `httpx`

## Interface Contract

### Inputs
- `query` (str): Search query string
- `max_results` (int): Maximum number of results to return

### Outputs
- `results` (list[IntelSource]): News and web search results

### Errors
- `APIError`: When Tavily returns non-2xx response
- `RateLimitError`: When Tavily rate limit is exceeded

## Behavioral Requirements
1. Cost per query: ~$0.01/search
2. Expected latency: ~300 ms
3. Used in STANDARD and DEEP depth queries
4. Must handle rate limits with exponential backoff

## Test Specification
- **Unit**: Response parsing, error handling
- **Integration**: Mocked Tavily API round-trip
- **Performance**: Single query latency < 600 ms (including network)

## Implementation Scaffolding
Located in `intel/sources/tavily.py`. Requires `TAVILY_API_KEY` environment variable.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
