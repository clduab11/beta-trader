# Copilot Instructions for Beta-Trader

## Project Identity

**Beta-Trader** is a predictive betting and algorithmic trading platform that combines neural time-series forecasting with prediction market integration. The platform uses a multi-layered architecture: Intel → Council → Routing → Execution.

## Primary Reference

**Always read `AGENTS.md` first** — it contains the authoritative project structure, architecture overview, and agent behavioral rules.

## Current Implementation Status (Phase 1)

### Implemented Modules
| Module | Directory | Purpose |
|--------|-----------|---------|
| Intel | `intel/` | Multi-source intelligence pipeline (Exa.ai, Firecrawl, Tavily, Jina) |
| Council | `council/` | Embedding-based council for decision aggregation |
| Routing | `routing/` | 3-tier LLM cost routing (OpenRouter free model rotation) |
| Backend | `backend/` | FastAPI server with SSE, depth analysis, settings management |
| Frontend | `frontend/` | Vite-based dashboard UI |

### Planned Modules (specs exist in `docs/specs/`)
| Module | Directory | Status |
|--------|-----------|--------|
| Core | `core/` | Not yet implemented — NautilusTrader execution engine |
| Signals | `signals/` | Not yet implemented — Neural inference layer |
| Strategies | `strategies/` | Not yet implemented — Trading strategy implementations |

## Documentation-First Workflow

1. Check `docs/INDEX.md` to discover existing specs
2. Read relevant specs before implementing
3. Use templates from `docs/templates/` for new documentation
4. Follow the spec lifecycle: Draft → Under Review → Approved
5. Check `docs/tickets/ROADMAP.md` for current phase and active tickets

## Key Directories

```
beta-trader/
├── AGENTS.md              # Architecture & agent instructions (primary reference)
├── CLAUDE.md              # Claude Code agent config
├── .gemini/               # Gemini agent config
├── pyproject.toml          # Python dependencies (uv package manager)
├── backend/               # FastAPI server (implemented)
├── intel/                 # Intelligence pipeline (implemented)
├── council/               # Decision council (implemented)
├── routing/               # LLM cost routing (implemented)
├── frontend/              # Vite dashboard UI (implemented)
├── tests/                 # Unit and integration tests
├── docs/                  # Specs, templates, setup guides
└── docker-compose.yml     # Local development services (Redis)
```

## Coding Conventions

- **Python 3.12+** with type hints on all function signatures
- **FastAPI** for HTTP endpoints; **httpx** for async HTTP clients
- **Pydantic v2** for configuration, validation, and serialization
- **Redis** for caching and state management
- **async/await** for all I/O operations
- **Ruff** for linting and formatting
- **Google-style docstrings** for Python
- **Conventional Commits**: `feat(scope)`, `fix(scope)`, `docs(scope)`, etc.

## Testing

- **pytest** with `pytest-asyncio` for async tests
- `asyncio_mode = "auto"` configured in `pyproject.toml`
- Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- Run: `uv run pytest tests/ -v`
- Lint: `uv run ruff check .`

## Security Rules

- **Never** hardcode secrets — use environment variables (see `.env.example`)
- **Never** modify risk engine parameters without explicit approval
- **Always** validate inputs with Pydantic
- **Always** implement retry logic with exponential backoff for external APIs

## References

- Architecture: `AGENTS.md` section 2
- Coding style: `.gemini/styleguide.md`
- Workflow: `docs/tickets/ROADMAP.md`
- Templates: `docs/templates/`
- Interfaces: `docs/interfaces/`
