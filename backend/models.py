from pydantic import BaseModel, Field
from typing import Any, Literal
from intel.types import IntelDepth

class ErrorResponse(BaseModel):
    error: str
    request_id: str
    traceback: str | None = None

class IntelRequest(BaseModel):
    query: str
    depth: Literal["SHALLOW", "STANDARD", "DEEP"] | None = None

class IntelResponse(BaseModel):
    result: Any # Using Any for now as IntelResult structure is complex, or ideally reuse IntelResult
    cost: float

class DepthRequest(BaseModel):
    query: str

class DepthResponse(BaseModel):
    depth: IntelDepth
    reason: str = "Heuristic-based recommendation"

class LLMTestRequest(BaseModel):
    model: str = "openai/gpt-3.5-turbo"
    prompt: str = "Hello"

class LLMTestResponse(BaseModel):
    response: str
    latency_ms: float

class SettingsResponse(BaseModel):
    settings: dict[str, Any]

class SettingsUpdateRequest(BaseModel):
    settings: dict[str, Any]

class CouncilExportRequest(BaseModel):
    intel_result: dict[str, Any]
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None

class CouncilExportResponse(BaseModel):
    record_id: str
    query_id: str
