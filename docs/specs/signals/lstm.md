# LSTM Model Specification

**Status**: Draft

## Purpose
The LSTM (Long Short-Term Memory) model provides time-series forecasting for price direction and magnitude. It is one of the core neural models in the Signal Layer ensemble, specializing in capturing sequential dependencies in financial data.

## Dependencies
- **Internal**: [SignalOutput](../../interfaces/types.md#signaloutput), [ModelConfidence](../../interfaces/types.md#modelconfidence), [InferenceError](../../interfaces/errors.md#inferenceerror)
- **External**: PyTorch (`torch`), NumPy

## Interface Contract

### Inputs
- `features` (Tensor): Input feature tensor (time-series data)

### Outputs
- `signal` (SignalOutput): Prediction with direction, magnitude, and confidence

### Errors
- `InferenceError`: When model fails during prediction (shape mismatch, runtime error)

## Behavioral Requirements
1. Must produce directional signal (LONG/SHORT/NEUTRAL) with confidence score
2. Must support WASM-compiled inference for sub-10 ms latency
3. Must gracefully degrade from ensemble when inference fails
4. Model weights must be loadable from file system

## Test Specification
- **Unit**: Forward pass with known input/output pairs
- **Integration**: Feature pipeline → LSTM → SignalOutput
- **Performance**: WASM inference < 10 ms; PyTorch inference < 100 ms

## Implementation Scaffolding
Located in `signals/models/lstm.py`. Part of Phase 2 (Neural Layer). See AGENTS.md §8 Phase 2.

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
