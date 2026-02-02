# AGENTS.md — Beta-Trader Platform

> **Optimized for**: OpenAI Codex 5.2 / GPT-5.1-Codex-Max  
> **Architecture**: NautilusTrader Core + Neural Inference + Prediction Markets  
> **Version**: 0.1.0-alpha

---

## 1. SYSTEM IDENTITY

You are an autonomous coding agent building **Beta-Trader**, a predictive betting and algorithmic trading platform. This system forks [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) as its execution core and integrates neural time-series forecasting for prediction market alpha.

### Primary Objectives
1. **Preserve** NautilusTrader's battle-tested risk engine and backtest capabilities
2. **Extend** with prediction market adapters (Polymarket, Kalshi)
3. **Integrate** neural forecasting models for signal generation
4. **Deploy** cost-efficiently on fly.io with ~$100 capital constraints

---

## 2. ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BETA-TRADER PLATFORM                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  INTEL LAYER    │    │  SIGNAL LAYER   │    │  ROUTING LAYER  │         │
│  │  ─────────────  │───▶│  ─────────────  │───▶│  ─────────────  │         │
│  │  • Exa.ai       │    │  • Neuro-Div    │    │  • WASM (fast)  │         │
│  │  • Firecrawl    │    │  • ruv-FANN     │    │  • Haiku (mid)  │         │
│  │  • Tavily       │    │  • LSTM/N-BEATS │    │  • Opus (heavy) │         │
│  │  • Jina.ai      │    │  • TFT/DeepAR   │    │                 │         │
│  └─────────────────┘    └─────────────────┘    └────────┬────────┘         │
│                                                          │                  │
│                         ┌────────────────────────────────▼────────────────┐ │
│                         │           EXECUTION LAYER (NautilusTrader)      │ │
│                         │  ──────────────────────────────────────────────  │ │
│                         │  • Risk Engine (position limits, drawdown)      │ │
│                         │  • Order Management System                       │ │
│                         │  • Backtest Engine (vectorized + event-driven)  │ │
│                         │  • Portfolio Management                          │ │
│                         └────────────────────────────────┬────────────────┘ │
│                                                          │                  │
│  ┌───────────────────────────────────────────────────────▼────────────────┐ │
│  │                         VENUE ADAPTERS                                  │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐               │ │
│  │  │ Binance  │  │  Kraken  │  │Polymarket│  │  Kalshi  │               │ │
│  │  │  (CEX)   │  │  (CEX)   │  │ (Predict)│  │ (Predict)│               │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. CODEBASE STRUCTURE

```
beta-trader/
├── AGENTS.md                    # THIS FILE - Agent instructions
├── README.md                    # Project overview
├── pyproject.toml               # Python dependencies (uv/poetry)
├── Cargo.toml                   # Rust workspace root
├── fly.toml                     # fly.io deployment config
│
├── core/                        # NautilusTrader fork (Rust + Cython)
│   ├── nautilus_core/           # Rust core library
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── risk/            # Risk engine (KEEP)
│   │   │   ├── execution/       # Order execution (KEEP)
│   │   │   ├── backtest/        # Backtest engine (KEEP)
│   │   │   └── portfolio/       # Portfolio mgmt (KEEP)
│   │   └── ffi/                 # Python FFI bindings
│   │
│   └── nautilus_trader/         # Python/Cython layer
│       ├── adapters/            # Venue adapters
│       │   ├── binance/         # EXISTS - Binance adapter
│       │   ├── kraken/          # EXISTS - Kraken adapter  
│       │   ├── polymarket/      # TO BUILD - Polymarket adapter
│       │   └── kalshi/          # TO BUILD - Kalshi adapter
│       ├── strategy/            # Strategy base classes
│       └── config/              # Configuration management
│
├── intel/                       # Intelligence pipeline
│   ├── __init__.py
│   ├── orchestrator.py          # Multi-source aggregator
│   ├── sources/
│   │   ├── exa.py               # Exa.ai neural search
│   │   ├── firecrawl.py         # Deep web scraping
│   │   ├── tavily.py            # News/general search
│   │   └── jina.py              # Embeddings pipeline
│   └── cache/
│       └── redis_cache.py       # Response caching
│
├── signals/                     # Neural inference layer
│   ├── __init__.py
│   ├── models/
│   │   ├── lstm.py              # LSTM forecaster
│   │   ├── nbeats.py            # N-BEATS forecaster
│   │   ├── tft.py               # Temporal Fusion Transformer
│   │   ├── deepar.py            # DeepAR probabilistic
│   │   └── tcn.py               # Temporal Convolutional Net
│   ├── ensemble.py              # Model ensemble orchestrator
│   └── wasm/                    # WASM-compiled fast inference
│       ├── Cargo.toml
│       └── src/lib.rs           # ruv-FANN integration
│
├── routing/                     # 3-tier cost routing
│   ├── __init__.py
│   ├── router.py                # Main routing logic
│   ├── tiers/
│   │   ├── wasm_tier.py         # Tier 1: Local WASM (free)
│   │   ├── haiku_tier.py        # Tier 2: Claude Haiku ($0.25/1M)
│   │   └── opus_tier.py         # Tier 3: Claude Opus ($15/1M)
│   └── openrouter/              # Free model rotation
│       ├── client.py            # OpenRouter API client
│       └── models.py            # Model definitions & rotation
│
├── strategies/                  # Trading strategies
│   ├── __init__.py
│   ├── base_predictor.py        # Base prediction strategy
│   ├── polymarket_arb.py        # Polymarket arbitrage
│   ├── kalshi_event.py          # Kalshi event trading
│   └── crypto_momentum.py       # Crypto momentum signals
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── backtest/
│
└── scripts/
    ├── setup.sh                 # Environment setup
    ├── backtest.py              # Run backtests
    └── deploy.py                # fly.io deployment
```

---

## 4. TECHNOLOGY STACK

### Core Languages
| Layer | Language | Rationale |
|-------|----------|-----------|
| Execution Engine | **Rust** | NautilusTrader core, memory safety, speed |
| Trading Logic | **Python 3.12+** | NautilusTrader Python layer, ML libs |
| Fast Inference | **Rust → WASM** | ruv-FANN, sub-ms signal classification |
| Adapters | **Python/Cython** | NautilusTrader adapter pattern |

### Key Dependencies
```toml
# Python (pyproject.toml)
[project.dependencies]
nautilus_trader = ">=1.200.0"
polars = ">=1.0.0"           # Fast dataframes
torch = ">=2.2.0"            # Neural networks
httpx = ">=0.27.0"           # Async HTTP
redis = ">=5.0.0"            # Caching
pydantic = ">=2.6.0"         # Config validation

# Rust (Cargo.toml)
[dependencies]
ruv-fann = "0.1"             # Neural network inference
tokio = "1.0"                # Async runtime
wasm-bindgen = "0.2"         # WASM bindings
```

### External APIs
| Service | Purpose | Cost |
|---------|---------|------|
| OpenRouter | Free reasoning models | $0 (with $10 credit) |
| Exa.ai | Neural web search | $2.50/1k searches |
| Firecrawl | Deep web scraping | Pay-per-page |
| Tavily | News search | $0.01/search |
| Jina.ai | Embeddings | Free tier available |

---

## 5. OPENROUTER FREE MODEL ROTATION

### Available Models (128K+ Context, Reasoning-Focused)

```python
OPENROUTER_FREE_MODELS = [
    {
        "id": "deepseek/deepseek-r1-0528:free",
        "name": "DeepSeek R1 0528",
        "context": 164_000,
        "strength": "reasoning",
        "notes": "o1-tier reasoning, fully open-source"
    },
    {
        "id": "nvidia/nemotron-3-nano-30b-a3b:free",
        "name": "NVIDIA Nemotron 3 Nano",
        "context": 256_000,
        "strength": "agentic",
        "notes": "Best for agentic AI, MoE architecture"
    },
    {
        "id": "openai/gpt-oss-120b:free",
        "name": "GPT-OSS 120B",
        "context": 131_000,
        "strength": "reasoning",
        "notes": "OpenAI open-weight, tool use, chain-of-thought"
    },
    {
        "id": "meta-llama/llama-3.3-70b-instruct:free",
        "name": "Llama 3.3 70B",
        "context": 131_000,
        "strength": "general",
        "notes": "GPT-4 tier performance"
    },
    {
        "id": "qwen/qwen3-coder-480b-a35b:free",
        "name": "Qwen3 Coder 480B",
        "context": 262_000,
        "strength": "coding",
        "notes": "Best for code generation, agentic tasks"
    },
    {
        "id": "nous/hermes-3-405b:free",
        "name": "Hermes 3 405B",
        "context": 131_000,
        "strength": "complex",
        "notes": "Fine-tuned Llama 405B, instruction following"
    },
    {
        "id": "z.ai/glm-4.5-air:free",
        "name": "GLM-4.5 Air",
        "context": 131_000,
        "strength": "multilingual",
        "notes": "Strong multilingual support"
    }
]
```

### Rotation Strategy
```python
class ModelRotator:
    """Round-robin rotation with fallback on rate limits."""
    
    def __init__(self):
        self.models = OPENROUTER_FREE_MODELS
        self.current_index = 0
        self.rate_limited = set()
    
    def get_next_model(self, task_type: str = "reasoning") -> str:
        """Get next available model, prioritizing task-appropriate ones."""
        # Filter by strength if specified
        candidates = [m for m in self.models 
                      if m["id"] not in self.rate_limited]
        
        if task_type:
            preferred = [m for m in candidates if m["strength"] == task_type]
            if preferred:
                candidates = preferred
        
        if not candidates:
            # All rate limited, wait and reset
            self.rate_limited.clear()
            candidates = self.models
        
        model = candidates[self.current_index % len(candidates)]
        self.current_index += 1
        return model["id"]
    
    def mark_rate_limited(self, model_id: str):
        """Mark model as rate limited for rotation."""
        self.rate_limited.add(model_id)
```

---

## 6. INTEL PIPELINE ARCHITECTURE

### Multi-Source Orchestration

```python
class IntelOrchestrator:
    """
    Cost-optimized intelligence gathering.
    
    Priority Order:
    1. Exa.ai (neural search) - $2.50/1k, best for semantic queries
    2. Tavily (news) - $0.01/search, real-time news
    3. Firecrawl (deep scrape) - per-page, when full content needed
    """
    
    async def gather_intel(self, query: str, depth: str = "standard") -> IntelResult:
        match depth:
            case "shallow":
                # Quick semantic search only
                return await self.exa.search(query, num_results=5)
            
            case "standard":
                # Parallel: Exa + Tavily
                exa_task = self.exa.search(query, num_results=10)
                tavily_task = self.tavily.search(query, max_results=5)
                results = await asyncio.gather(exa_task, tavily_task)
                return self.merge_results(results)
            
            case "deep":
                # Full pipeline with Firecrawl
                semantic = await self.exa.search(query, num_results=10)
                urls_to_scrape = self.extract_high_value_urls(semantic)
                scraped = await self.firecrawl.batch_scrape(urls_to_scrape)
                embeddings = await self.jina.embed(scraped)
                return IntelResult(semantic, scraped, embeddings)
```

### Cost Comparison
| Source | Use Case | Cost | Latency |
|--------|----------|------|---------|
| Exa.ai | Semantic/neural search | $2.50/1k | ~200ms |
| Tavily | News, real-time events | $0.01/search | ~300ms |
| Firecrawl | Full page scraping | ~$0.001/page | ~1-2s |
| Jina.ai | Embeddings | Free tier | ~100ms |

---

## 7. DEVELOPMENT GUIDELINES

### Code Style
- **Python**: Black formatter, Ruff linter, type hints required
- **Rust**: rustfmt, clippy with `-D warnings`
- **Docstrings**: Google style for Python, `///` for Rust

### Commit Convention
```
<type>(<scope>): <description>

Types: feat, fix, docs, refactor, test, chore
Scopes: core, intel, signals, routing, adapters, strategies
```

### Testing Requirements
- Unit tests for all public functions
- Integration tests for API interactions (mocked)
- Backtest validation for all strategies
- Minimum 80% coverage on new code

### Performance Targets
| Operation | Target | Current |
|-----------|--------|---------|
| Signal inference (WASM) | <10ms | TBD |
| Intel query (cached) | <50ms | TBD |
| Order placement | <100ms | TBD |
| Backtest (1yr daily) | <30s | TBD |

---

## 8. PRIORITY TASK QUEUE

### Phase 1: Foundation (Current)
- [ ] Fork NautilusTrader, strip to core components
- [ ] Set up Rust/Python monorepo structure
- [ ] Implement Polymarket adapter skeleton
- [ ] Create Intel orchestrator with Exa.ai integration
- [ ] Build OpenRouter client with model rotation

### Phase 2: Neural Layer
- [ ] Port Neuro-Divergent LSTM model
- [ ] Integrate ruv-FANN for WASM inference
- [ ] Build model ensemble orchestrator
- [ ] Create signal-to-order pipeline

### Phase 3: Adapters
- [ ] Complete Polymarket adapter (REST + WebSocket)
- [ ] Build Kalshi adapter
- [ ] Test against paper trading accounts

### Phase 4: Strategies
- [ ] Implement base predictor strategy
- [ ] Build Polymarket event arbitrage
- [ ] Create crypto momentum strategy
- [ ] Backtest all strategies

### Phase 5: Deployment
- [ ] Configure fly.io deployment
- [ ] Set up Redis caching layer
- [ ] Implement monitoring/alerting
- [ ] Deploy with $100 capital

---

## 9. AGENT BEHAVIORAL RULES

### DO
- ✅ Read this file completely before starting any task
- ✅ Follow the architecture diagram strictly
- ✅ Use NautilusTrader patterns for adapters and strategies
- ✅ Implement proper error handling with retries
- ✅ Cache expensive API calls (Intel sources)
- ✅ Write tests alongside implementation
- ✅ Use type hints and validate with Pydantic
- ✅ Log all trading decisions with rationale

### DON'T
- ❌ Modify NautilusTrader core risk engine without explicit approval
- ❌ Make live trades without backtest validation
- ❌ Store API keys in code (use environment variables)
- ❌ Skip rate limit handling on external APIs
- ❌ Use synchronous HTTP calls in async contexts
- ❌ Implement strategies without stop-loss logic

### ESCALATION TRIGGERS
Pause and request human review when:
1. Modifying risk management parameters
2. Changing order sizing logic
3. Encountering unexpected API responses from venues
4. Backtest shows >20% drawdown
5. Any capital allocation decisions

---

## 10. QUICK REFERENCE

### Environment Variables Required
```bash
# Trading Venues
BINANCE_API_KEY=
BINANCE_SECRET_KEY=
KRAKEN_API_KEY=
KRAKEN_SECRET_KEY=
POLYMARKET_API_KEY=
KALSHI_API_KEY=

# Intel Sources
EXA_API_KEY=
FIRECRAWL_API_KEY=
TAVILY_API_KEY=
JINA_API_KEY=

# LLM Providers
OPENROUTER_API_KEY=
ANTHROPIC_API_KEY=

# Infrastructure
REDIS_URL=
FLY_API_TOKEN=
```

### Useful Commands
```bash
# Development
uv sync                          # Install Python deps
cargo build --release            # Build Rust core
pytest tests/ -v                 # Run tests

# Backtest
python scripts/backtest.py --strategy=polymarket_arb --period=90d

# Deploy
fly deploy --app beta-trader

# Model rotation test
python -c "from routing.openrouter.client import test_rotation; test_rotation()"
```

---

**Last Updated**: February 2026  
**Maintainer**: @clduab11  
**Status**: 🟡 Active Development
