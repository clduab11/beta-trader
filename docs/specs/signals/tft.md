# TFT Model Specification

**Status**: Draft

## Purpose
The Temporal Fusion Transformer (TFT) model provides multi-horizon forecasting with attention-based feature importance. It excels at incorporating both static covariates and time-varying inputs, making it well-suited for prediction market event modeling.

## Dependencies
- **Internal**: [SignalOutput](../../interfaces/types.md#signaloutput), [ModelConfidence](../../interfaces/types.md#modelconfidence), [InferenceError](../../interfaces/errors.md#inferenceerror)
- **External**: PyTorch (`torch`)

## Interface Contract

### Inputs
- `features` (Tensor): Input feature tensor (time-varying and static covariates)

### Outputs
- `signal` (SignalOutput): Prediction with direction, magnitude, and confidence

### Errors
- `InferenceError`: When model fails during prediction

## Behavioral Requirements
1. Must produce directional signal (LONG/SHORT/NEUTRAL) with confidence score
2. Must provide attention-based feature importance scores
3. Must support multi-horizon predictions
4. Must gracefully degrade from ensemble when inference fails

## Test Specification
- **Unit**: Forward pass, attention weight extraction
- **Integration**: Feature pipeline → TFT → SignalOutput
- **Performance**: Inference < 200 ms

## Implementation Scaffolding
Located in `signals/models/tft.py`. Part of Phase 2 (Neural Layer).

## Template Compliance Checklist
- [x] Purpose section complete
- [x] Dependencies identified (internal and external)
- [x] Interface contract defined (inputs/outputs/errors)
- [x] Behavioral requirements with acceptance criteria
- [x] Test specification included (unit/integration/performance)
- [x] Implementation scaffolding provided
