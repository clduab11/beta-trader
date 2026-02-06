# N-BEATS Model Specification

**Status**: Draft

## Purpose
The N-BEATS (Neural Basis Expansion Analysis for Time Series) model provides interpretable time-series forecasting. It decomposes forecasts into trend and seasonality components, offering transparency into prediction drivers.

## Dependencies
- **Internal**: [SignalOutput](../../interfaces/types.md#signaloutput), [ModelConfidence](../../interfaces/types.md#modelconfidence), [InferenceError](../../interfaces/errors.md#inferenceerror)
- **External**: PyTorch (`torch`)

## Interface Contract

### Inputs
- `features` (Tensor): Input feature tensor (time-series data)

### Outputs
- `signal` (SignalOutput): Prediction with direction, magnitude, and confidence

### Errors
- `InferenceError`: When model fails during prediction

## Behavioral Requirements
1. Must produce directional signal (LONG/SHORT/NEUTRAL) with confidence score
2. Must decompose forecast into interpretable components
3. Must gracefully degrade from ensemble when inference fails

## Test Specification
- **Unit**: Forward pass with known input/output pairs
- **Integration**: Feature pipeline → N-BEATS → SignalOutput
- **Performance**: Inference < 100 ms

## Implementation Scaffolding
Located in `signals/models/nbeats.py`. Part of Phase 2 (Neural Layer).

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
