import os
import asyncio
import httpx
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from intel.errors import APIError, RateLimitError, ConfigurationError, CircuitOpenError
from intel.circuit_breaker import CircuitBreaker, OPENROUTER_CONFIG
from intel.events import get_event_bus
from routing.openrouter.models import ModelRotator

class LLMUsage(BaseModel):
    """Token usage and cost information."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0

class CompletionResult(BaseModel):
    """Standardized LLM response."""
    content: str
    model: str
    usage: LLMUsage
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Alias for backward compatibility
LLMResponse = CompletionResult

class OpenRouterClient:
    """Client for OpenRouter API with model rotation and cost tracking."""
    
    def __init__(self, api_key: str | None = None):
        """Initialize OpenRouter client.
        
        Args:
            api_key: Optional API key. If not provided, reads from OPENROUTER_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.rotator = ModelRotator()
        self.base_url = "https://openrouter.ai/api/v1"
        self.session_cost = 0.0
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.event_bus = get_event_bus()
        
    @property
    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise ConfigurationError(
                "OPENROUTER_API_KEY not found", 
                source_module="openrouter_client", 
                config_key="OPENROUTER_API_KEY"
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://beta-trader.platform",
            "X-Title": "Beta-Trader",
            "Content-Type": "application/json"
        }

    async def complete(
        self, 
        prompt: str, 
        task_type: str = "reasoning",
        max_tokens: int = 4096
    ) -> CompletionResult:
        """Generate completion with resilience patterns."""
        attempt = 0
        max_attempts = 10 
        
        while attempt < max_attempts:
            model_id = self.rotator.get_next_model(task_type)
            
            if model_id not in self.breakers:
                self.breakers[model_id] = CircuitBreaker(
                    service_name=model_id,
                    config=OPENROUTER_CONFIG,
                    source_module="openrouter_client"
                )
            breaker = self.breakers[model_id]

            try:
                result = await breaker.call(
                    self._execute_with_backoff,
                    prompt, model_id, max_tokens
                )
                
                await self.event_bus.emit(
                    "CompletionGenerated", 
                    {"model": result.model, "usage": result.usage.dict()},
                    source_module="openrouter_client"
                )
                return result

            except (RateLimitError, CircuitOpenError) as e:
                self.rotator.mark_rate_limited(model_id)
                await self.event_bus.emit(
                    "RateLimitHit", 
                    {"model": model_id, "error": str(e)}, 
                    source_module="openrouter_client"
                )
                await self.event_bus.emit(
                    "ModelRotated", 
                    {"previous_model": model_id},
                    source_module="openrouter_client"
                )
                attempt += 1
                continue
            
            except APIError as e:
                await self.event_bus.emit(
                    "ModelError",
                    {"model": model_id, "error": str(e)},
                    source_module="openrouter_client"
                )
                attempt += 1
                continue
                
        raise APIError(
            "Failed to generate completion: all models exhausted or max attempts reached", 
            source_module="openrouter_client"
        )

    async def generate_completion(
        self, 
        prompt: str, 
        task_type: str = "reasoning",
        max_retries: int = 3
    ) -> CompletionResult:
        """Wrapper for backward compatibility."""
        return await self.complete(prompt, task_type=task_type)

    async def _execute_with_backoff(self, prompt: str, model_id: str, max_tokens: int) -> CompletionResult:
        """Execute request with exponential backoff for transient errors."""
        backoffs = [0.5, 1.0, 2.0]
        
        for i, delay in enumerate(backoffs + [None]):
            try:
                return await self._make_request(prompt, model_id, max_tokens)
            except RateLimitError:
                raise
            except APIError as e:
                if delay is None:
                    raise e
                await asyncio.sleep(delay)

    async def _make_request(self, prompt: str, model_id: str, max_tokens: int) -> CompletionResult:
        """Execute single API request."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers,
                    json={
                        "model": model_id,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens
                    },
                    timeout=30.0
                )
                
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    retry_seconds = float(retry_after) if retry_after else 5.0
                    
                    raise RateLimitError(
                        "OpenRouter rate limit exceeded",
                        source_module="openrouter_client",
                        service_name="OpenRouter",
                        endpoint="/chat/completions",
                        retry_after_seconds=retry_seconds
                    )
                
                if response.status_code != 200:
                    raise APIError(
                        f"OpenRouter API error: {response.text}",
                        source_module="openrouter_client",
                        service_name="OpenRouter",
                        http_status=response.status_code,
                        endpoint="/chat/completions"
                    )
                
                data = response.json()
                return self._parse_response(data, model_id)

            except httpx.RequestError as e:
                raise APIError(
                    f"Request failed: {str(e)}",
                    source_module="openrouter_client",
                    service_name="OpenRouter"
                )

    def _parse_response(self, data: Dict[str, Any], model_id: str) -> CompletionResult:
        """Parse raw API response into CompletionResult."""
        if not data.get("choices"):
             raise APIError(
                "Invalid response format: no choices",
                source_module="openrouter_client",
                service_name="OpenRouter"
            )
            
        content = data["choices"][0]["message"]["content"]
        usage_data = data.get("usage", {})
        
        # Calculate cost
        request_cost = 0.0 
        
        self.session_cost += request_cost
        
        return CompletionResult(
            content=content,
            model=model_id,
            usage=LLMUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
                cost=request_cost
            ),
            metadata=data
        )
