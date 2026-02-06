# OpenRouter Client Specification

**Status**: Draft

## Purpose
The OpenRouter Client provides access to free and paid LLM models via the OpenRouter API. It implements round-robin model rotation across free models, automatic fallback on rate limits, and task-type-aware model selection.

## Dependencies
- **Internal**: [RateLimitError](../../interfaces/errors.md#ratelimiterror), [APIError](../../interfaces/errors.md#apierror)
- **External**: OpenRouter API, `httpx`

## Interface Contract

### Inputs
- `prompt` (str): LLM prompt
- `task_type` (str): Task category for model selection (`"reasoning"`, `"coding"`, `"agentic"`, `"general"`)

### Outputs
- `response` (LLMResponse): Model response with content and usage metadata

### Errors
- `APIError`: When OpenRouter returns non-2xx response
- `RateLimitError`: When all free models are rate-limited simultaneously

## Behavioral Requirements
1. Must implement round-robin rotation across free models (see AGENTS.md §5)
2. Rate-limited models must be temporarily excluded from rotation
3. Must prioritize models by task type (reasoning, coding, agentic, general)
4. Must track cost per request and cumulative session cost
5. Must support 128K+ context models

## Test Specification
- **Unit**: Model rotation, rate limit exclusion, task-type filtering
- **Integration**: Mocked OpenRouter API round-trip
- **Performance**: Model selection overhead < 1 ms

## Implementation Scaffolding
Located in `routing/openrouter/client.py` and `routing/openrouter/models.py`. See AGENTS.md §5.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
