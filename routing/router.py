from typing import Optional
from routing.openrouter.client import OpenRouterClient, CompletionResult

class ThreeTierRouter:
    """Router that selects execution tier based on prompt complexity."""
    
    def __init__(self, client: Optional[OpenRouterClient] = None):
        self.client = client or OpenRouterClient()
        
    async def route(self, prompt: str, complexity: Optional[str] = None) -> CompletionResult:
        """
        Route the prompt to appropriate model tier.
        
        Phase 1 Heuristic:
        - Tier 3 (Reasoning): Prompt > 500 chars OR contains 'analyze'/'explain'/'reason'
        - Tier 2 (General): Everything else
        - Tier 1 (WASM): Skipped for now
        """
        
        # Heuristic Logic
        use_tier_3 = False
        
        if complexity == "high":
            use_tier_3 = True
        elif len(prompt) > 500:
            use_tier_3 = True
        else:
            keywords = ["analyze", "explain", "reason"]
            if any(k in prompt.lower() for k in keywords):
                use_tier_3 = True
        
        # Routing
        if use_tier_3:
            # Tier 3 maps to "reasoning" models in OpenRouter
            return await self.client.complete(prompt, task_type="reasoning")
        else:
            # Tier 2 maps to "general" models
            return await self.client.complete(prompt, task_type="general")
