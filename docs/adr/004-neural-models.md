# ADR-004: Neural Model Selection

**Status**: Proposed  
**Date**: 2026-02-06  
**Deciders**: @clduab11

## Context and Problem Statement
Beta-Trader needs a set of neural time-series forecasting models for the Signal Layer. The models must balance accuracy, latency, interpretability, and deployment cost. The ensemble approach requires diverse model architectures to reduce correlation between predictions.

## Decision Drivers
- Prediction accuracy on financial time-series data
- Inference latency (target < 100 ms per model)
- Model diversity for ensemble robustness
- WASM compatibility for Tier 1 local inference
- PyTorch ecosystem compatibility

## Considered Options
1. Single large transformer model
2. Ensemble of 3 models (LSTM, TFT, N-BEATS)
3. Ensemble of 5 models (LSTM, N-BEATS, TFT, DeepAR, TCN)

## Decision Outcome
**Chosen option**: Option 3 — Ensemble of 5 diverse models

**Rationale**: Maximizes prediction diversity and ensemble robustness. Each model captures different aspects of time-series dynamics: LSTM (sequential), N-BEATS (decomposition), TFT (attention/covariates), DeepAR (probabilistic), TCN (convolutional). The ensemble orchestrator degrades gracefully when individual models fail.

### Positive Consequences
- High model diversity reduces correlation risk
- Graceful degradation (ensemble works with ≥ 2 models)
- Each model brings unique strengths
- LSTM and TCN can be compiled to WASM for fast inference

### Negative Consequences
- Higher total inference cost and latency
- More complex model management and weight tuning
- Larger deployment footprint

## Links
- [LSTM Spec](../specs/signals/lstm.md)
- [N-BEATS Spec](../specs/signals/nbeats.md)
- [TFT Spec](../specs/signals/tft.md)
- [DeepAR Spec](../specs/signals/deepar.md)
- [TCN Spec](../specs/signals/tcn.md)
- [Ensemble Orchestrator Spec](../specs/signals/ensemble.md)
