# Firecrawl Source Specification

**Status**: Draft

## Purpose
The Firecrawl Source adapter provides deep web scraping for full-page content extraction. It is used in DEEP depth queries when semantic search results need to be enriched with complete page content.

## Dependencies
- **Internal**: [IntelSource](../../interfaces/types.md#intelresult) (nested type), [APIError](../../interfaces/errors.md#apierror), [RateLimitError](../../interfaces/errors.md#ratelimiterror)
- **External**: Firecrawl API, `httpx`

## Interface Contract

### Inputs
- `urls` (list[str]): URLs to scrape for full content

### Outputs
- `results` (list[IntelSource]): Scraped page content with metadata

### Errors
- `APIError`: When Firecrawl returns non-2xx response
- `RateLimitError`: When Firecrawl rate limit is exceeded

## Behavioral Requirements
1. Cost: ~$0.001/page
2. Expected latency: 1–2 seconds per page
3. Used only in DEEP depth queries
4. Must support batch scraping of multiple URLs
5. Must handle rate limits with exponential backoff

## Test Specification
- **Unit**: Response parsing, batch URL handling, error handling
- **Integration**: Mocked Firecrawl API batch scrape
- **Performance**: Batch of 5 URLs < 5 s

## Implementation Scaffolding
Located in `intel/sources/firecrawl.py`. Requires `FIRECRAWL_API_KEY` environment variable.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
