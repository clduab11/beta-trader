# Ensemble Orchestrator Specification

**Status**: Draft

## Purpose
The Ensemble Orchestrator runs multiple neural models in parallel, aggregates their predictions using weighted scoring, and produces a consensus `EnsembleResult`. It handles model failures gracefully by degrading to available models and adjusting weights dynamically.

## Dependencies
- **Internal**: [SignalOutput](../../interfaces/types.md#signaloutput), [EnsembleResult](../../interfaces/types.md#ensembleresult), [ModelConfidence](../../interfaces/types.md#modelconfidence), [InferenceError](../../interfaces/errors.md#inferenceerror), LSTM, N-BEATS, TFT, DeepAR, TCN
- **External**: PyTorch (`torch`), `asyncio`

## Interface Contract

### Inputs
- `instrument` (str): Target instrument to forecast
- `features` (dict): Feature data keyed by model name

### Outputs
- `result` (EnsembleResult): Aggregated consensus prediction

### Errors
- `InferenceError`: When fewer than 2 models are available for the ensemble

## Behavioral Requirements
1. Must run all available models in parallel
2. Must continue with ≥ 2 healthy models if some fail
3. Must weight models based on historical accuracy
4. Agreement ratio must be calculated as fraction of models agreeing on direction
5. Failed models must be logged and excluded from consensus

## Test Specification
- **Unit**: Weight calculation, consensus logic, degradation with N-1 models
- **Integration**: Full ensemble run with mocked model outputs
- **Performance**: Total ensemble latency < max(individual model latencies) + 50 ms overhead

## Implementation Scaffolding
Located in `signals/ensemble.py`. Part of Phase 2 (Neural Layer). See AGENTS.md §3.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
