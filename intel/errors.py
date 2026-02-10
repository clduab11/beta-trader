"""Shared error types for Beta-Trader.

Implements error taxonomy from docs/interfaces/errors.md.
"""

from __future__ import annotations

from intel.types import Timestamp


class BetaTraderError(Exception):
    """Base exception for all Beta-Trader errors."""

    def __init__(
        self,
        message: str,
        source_module: str = "",
        correlation_id: str = "",
        retry_count: int = 0,
        original_request: dict | None = None,
        stack_trace: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = self.__class__.__name__
        self.message = message
        self.source_module = source_module
        self.correlation_id = correlation_id
        self.retry_count = retry_count
        self.original_request = original_request
        self.stack_trace = stack_trace
        self.timestamp = Timestamp.now()

    def to_dict(self) -> dict:
        """Serialize error for logging and transport."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "source_module": self.source_module,
            "correlation_id": self.correlation_id,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp.model_dump(),
        }


class APIError(BetaTraderError):
    """External API returned a non-2xx response or timed out."""

    def __init__(
        self,
        message: str,
        source_module: str = "",
        correlation_id: str = "",
        service_name: str = "",
        http_status: int | None = None,
        endpoint: str = "",
        request_duration_ms: float = 0.0,
        **kwargs,
    ) -> None:
        super().__init__(
            message,
            source_module=source_module,
            correlation_id=correlation_id,
            **kwargs,
        )
        self.service_name = service_name
        self.http_status = http_status
        self.endpoint = endpoint
        self.request_duration_ms = request_duration_ms


class RateLimitError(BetaTraderError):
    """External API returned HTTP 429 or rate-limit detected."""

    def __init__(
        self,
        message: str,
        source_module: str = "",
        correlation_id: str = "",
        service_name: str = "",
        retry_after_seconds: float | None = None,
        quota_remaining: int | None = None,
        quota_reset_at: Timestamp | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            message,
            source_module=source_module,
            correlation_id=correlation_id,
            **kwargs,
        )
        self.service_name = service_name
        self.retry_after_seconds = retry_after_seconds
        self.quota_remaining = quota_remaining
        self.quota_reset_at = quota_reset_at


class CircuitOpenError(BetaTraderError):
    """Circuit breaker is open — downstream service is unhealthy."""

    def __init__(
        self,
        message: str,
        source_module: str = "",
        correlation_id: str = "",
        service_name: str = "",
        reopens_in_seconds: float = 0.0,
        **kwargs,
    ) -> None:
        super().__init__(
            message,
            source_module=source_module,
            correlation_id=correlation_id,
            **kwargs,
        )
        self.service_name = service_name
        self.reopens_in_seconds = reopens_in_seconds


class ValidationError(BetaTraderError):
    """Input validation failed before processing."""

    def __init__(
        self,
        message: str,
        source_module: str = "",
        correlation_id: str = "",
        field_name: str = "",
        expected: str = "",
        received: str = "",
        validation_rule: str = "",
        **kwargs,
    ) -> None:
        super().__init__(
            message,
            source_module=source_module,
            correlation_id=correlation_id,
            **kwargs,
        )
        self.field_name = field_name
        self.expected = expected
        self.received = received
        self.validation_rule = validation_rule


class ConfigurationError(BetaTraderError):
    """Missing or invalid configuration (e.g. API key not set)."""

    def __init__(
        self,
        message: str,
        source_module: str = "",
        config_key: str = "",
        **kwargs,
    ) -> None:
        super().__init__(message, source_module=source_module, **kwargs)
        self.config_key = config_key
