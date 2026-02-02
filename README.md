# Beta-Trader

> **Predictive Betting & Algorithmic Trading Platform**  
> *NautilusTrader Core • Neural Forecasting • Prediction Markets*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Rust](https://img.shields.io/badge/rust-1.75+-orange.svg)](https://www.rust-lang.org/)

---

## 🎯 Vision

Beta-Trader is an AI-powered predictive trading platform that combines:

- **[NautilusTrader](https://github.com/nautechsystems/nautilus_trader)** — Production-grade execution engine (Rust core + Python)
- **Neural Forecasting** — Time-series models (LSTM, N-BEATS, TFT, DeepAR) for signal generation
- **Prediction Markets** — Polymarket & Kalshi adapters for event-driven trading
- **Intelligent Research** — Multi-source intel pipeline (Exa.ai, Firecrawl, Tavily)
- **Cost-Optimized LLMs** — OpenRouter free model rotation for research at scale

Built for deployment on **fly.io** with minimal capital (~$100 starting).

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BETA-TRADER PLATFORM                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   INTEL LAYER          SIGNAL LAYER          ROUTING LAYER                 │
│   ───────────          ────────────          ─────────────                 │
│   • Exa.ai      ───▶   • LSTM         ───▶   • WASM (free)                 │
│   • Firecrawl          • N-BEATS             • Haiku (cheap)               │
│   • Tavily             • TFT                 • Opus (quality)              │
│   • Jina.ai            • DeepAR                                            │
│                                                      │                      │
│                    ┌─────────────────────────────────▼────────────────┐    │
│                    │         EXECUTION ENGINE (NautilusTrader)        │    │
│                    │  • Risk Engine  • Order Management  • Backtest   │    │
│                    └─────────────────────────────────┬────────────────┘    │
│                                                      │                      │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│   │ Binance  │  │  Kraken  │  │Polymarket│  │  Kalshi  │                   │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Features

### Execution Engine
- **Risk Management** — Position limits, drawdown controls, stop-loss enforcement
- **Backtest Engine** — Vectorized + event-driven simulation with realistic fills
- **Multi-Venue** — Unified interface for CEX (Binance/Kraken) and prediction markets

### Neural Forecasting
- **Neuro-Divergent Models** — LSTM, N-BEATS, TFT, DeepAR, TCN implementations
- **WASM Inference** — Sub-10ms signal classification via ruv-FANN
- **Ensemble Orchestration** — Combine multiple models with confidence weighting

### Intelligence Pipeline
- **Exa.ai** — Neural semantic search ($2.50/1k queries)
- **Firecrawl** — Deep web scraping for full content extraction
- **Tavily** — Real-time news and event monitoring ($0.01/search)
- **Jina.ai** — Embeddings for similarity search (free tier)

### Cost Optimization
- **3-Tier Routing** — WASM → Haiku → Opus (saves ~75% on LLM costs)
- **OpenRouter Free Models** — Rotate between 7+ free reasoning models
- **Redis Caching** — Cache expensive API responses

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Rust 1.75+
- uv (Python package manager)
- Redis (local or cloud)

### Installation

```bash
# Clone repository
git clone https://github.com/clduab11/beta-trader.git
cd beta-trader

# Install Python dependencies
uv sync

# Build Rust core
cargo build --release

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

```bash
# Required API Keys
OPENROUTER_API_KEY=      # Free models access
EXA_API_KEY=             # Intel pipeline
POLYMARKET_API_KEY=      # Prediction market
BINANCE_API_KEY=         # Crypto trading
```

### Run Backtest

```bash
python scripts/backtest.py \
  --strategy=polymarket_arb \
  --period=90d \
  --capital=100
```

### Deploy to fly.io

```bash
fly deploy --app beta-trader
```

---

## 📁 Project Structure

```
beta-trader/
├── AGENTS.md              # Codex agent instructions
├── README.md              # This file
├── pyproject.toml         # Python dependencies
├── Cargo.toml             # Rust workspace
├── fly.toml               # Deployment config
│
├── core/                  # NautilusTrader fork
│   ├── nautilus_core/     # Rust execution engine
│   └── nautilus_trader/   # Python trading layer
│       └── adapters/      # Venue adapters
│
├── intel/                 # Intelligence pipeline
│   ├── orchestrator.py    # Multi-source aggregation
│   └── sources/           # Exa, Firecrawl, Tavily, Jina
│
├── signals/               # Neural forecasting
│   ├── models/            # LSTM, N-BEATS, TFT, etc.
│   └── wasm/              # Fast inference
│
├── routing/               # Cost-optimized LLM routing
│   ├── router.py          # 3-tier routing logic
│   └── openrouter/        # Free model rotation
│
├── strategies/            # Trading strategies
│   ├── polymarket_arb.py
│   ├── kalshi_event.py
│   └── crypto_momentum.py
│
├── tests/
└── scripts/
```

---

## 🤖 OpenRouter Free Models

Rotating between these 128K+ context reasoning models:

| Model | Context | Best For |
|-------|---------|----------|
| DeepSeek R1 0528 | 164K | Deep reasoning |
| NVIDIA Nemotron 3 Nano | 256K | Agentic tasks |
| GPT-OSS 120B | 131K | Tool use, CoT |
| Llama 3.3 70B | 131K | General |
| Qwen3 Coder 480B | 262K | Code generation |
| Hermes 3 405B | 131K | Complex tasks |
| GLM-4.5 Air | 131K | Multilingual |

See [AGENTS.md](./AGENTS.md) for rotation implementation.

---

## 📊 Supported Venues

### Crypto Exchanges
| Exchange | Status | Features |
|----------|--------|----------|
| Binance | ✅ Ready | Spot, Futures, WebSocket |
| Kraken | ✅ Ready | Spot, Margin |

### Prediction Markets
| Market | Status | Features |
|--------|--------|----------|
| Polymarket | 🔨 Building | Event contracts, CLOB |
| Kalshi | 🔨 Building | Regulated events |

---

## 💰 Cost Breakdown (Monthly Estimate)

| Service | Usage | Cost |
|---------|-------|------|
| fly.io (shared-cpu-1x) | 24/7 | ~$5-10 |
| OpenRouter | Free tier | $0 |
| Exa.ai | ~500 queries | ~$1.25 |
| Tavily | ~100 queries | ~$1 |
| Redis (Upstash) | Free tier | $0 |
| **Total** | | **~$8-15/mo** |

---

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit -v

# Integration tests (requires API keys)
pytest tests/integration -v --api

# Backtest validation
pytest tests/backtest -v

# Coverage report
pytest --cov=. --cov-report=html
```

---

## 📚 Documentation

- [AGENTS.md](./AGENTS.md) — AI agent instructions (Codex optimized)
- [docs/architecture.md](./docs/architecture.md) — Detailed system design
- [docs/adapters.md](./docs/adapters.md) — Venue adapter guide
- [docs/strategies.md](./docs/strategies.md) — Strategy development

---

## 🛣️ Roadmap

### Phase 1: Foundation ← *Current*
- [x] Repository structure
- [x] AGENTS.md for Codex
- [ ] NautilusTrader fork & strip
- [ ] Intel pipeline (Exa + Tavily + Firecrawl)
- [ ] OpenRouter client with rotation

### Phase 2: Neural Layer
- [ ] LSTM forecaster port
- [ ] ruv-FANN WASM integration
- [ ] Model ensemble orchestrator

### Phase 3: Prediction Markets
- [ ] Polymarket adapter (REST + WS)
- [ ] Kalshi adapter
- [ ] Paper trading validation

### Phase 4: Strategies & Deploy
- [ ] Polymarket arbitrage strategy
- [ ] Crypto momentum strategy
- [ ] fly.io deployment
- [ ] Live trading ($100 capital)

---

## ⚠️ Risk Disclaimer

This software is for **educational and research purposes**. Trading cryptocurrencies and prediction markets involves substantial risk of loss. Never trade with funds you cannot afford to lose. The authors are not responsible for any financial losses incurred.

---

## 🤝 Contributing

This is a personal project by [@clduab11](https://github.com/clduab11). While not accepting external contributions at this time, feel free to fork and adapt for your own use.

---

## 📄 License

MIT License — see [LICENSE](./LICENSE) for details.

---

## 🙏 Acknowledgments

- [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) — Execution engine foundation
- [rUv's Claude-Flow](https://github.com/ruvnet/claude-flow) — Multi-agent orchestration patterns
- [ruv-FANN](https://github.com/ruvnet/ruv-FANN) — Neural inference & Neuro-Divergent models
- [OpenRouter](https://openrouter.ai) — Free model access

---

**Status**: 🟡 Active Development  
**Last Updated**: February 2026
