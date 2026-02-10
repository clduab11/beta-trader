import time
from typing import List, Set, TypedDict, Optional, Callable

class OpenRouterModel(TypedDict):
    id: str
    name: str
    context: int
    strength: str
    notes: str

OPENROUTER_FREE_MODELS: List[OpenRouterModel] = [
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

class ModelRotator:
    """Round-robin rotation with fallback on rate limits."""
    
    def __init__(self, wait_handler: Callable[[float], None] = time.sleep):
        self.models = OPENROUTER_FREE_MODELS
        self.current_index = 0
        self.rate_limited: Set[str] = set()
        self.wait_handler = wait_handler
    
    def get_next_model(self, task_type: str = "reasoning") -> str:
        """Get next available model, prioritizing task-appropriate ones."""
        # Filter out rate limited models
        candidates = [m for m in self.models 
                      if m["id"] not in self.rate_limited]
        
        # If all models are rate limited, reset the list (wait strategy is handled by caller/retry logic)
        # But for rotation logic, we might need to be careful. 
        # The spec says: "Rate-limited models must be temporarily excluded from rotation"
        # AGENTS.md implementation: "if not candidates: self.rate_limited.clear(); candidates = self.models"
        
        if not candidates:
            # All rate limited, wait and reset
            self.wait_handler(60.0)
            self.rate_limited.clear()
            candidates = self.models
        
        # Filter by strength if specified
        if task_type:
            preferred = [m for m in candidates if m["strength"] == task_type]
            if preferred:
                candidates = preferred
            # If no preferred models available (or all rate limited), fall back to any available candidates
        
        # Determine the model using round-robin index
        # Note: AGENTS.md logic uses a single global index. 
        # If candidates list changes, the index might point to a different model than expected 
        # relative to the full list, but it ensures rotation.
        
        model = candidates[self.current_index % len(candidates)]
        self.current_index += 1
        return model["id"]
    
    def mark_rate_limited(self, model_id: str):
        """Mark model as rate limited for rotation."""
        self.rate_limited.add(model_id)
