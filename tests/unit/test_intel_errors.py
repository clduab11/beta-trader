"""Unit tests for Intel pipeline errors."""

from intel.errors import (
    APIError,
    BetaTraderError,
    CircuitOpenError,
    ConfigurationError,
    RateLimitError,
    ValidationError,
)


class TestBetaTraderError:
    def test_basic_error(self):
        err = BetaTraderError("something broke", source_module="test")
        assert str(err) == "something broke"
        assert err.error_type == "BetaTraderError"
        assert err.source_module == "test"
        assert err.retry_count == 0

    def test_to_dict(self):
        err = BetaTraderError("test", source_module="mod", correlation_id="c-123")
        d = err.to_dict()
        assert d["error_type"] == "BetaTraderError"
        assert d["message"] == "test"
        assert d["correlation_id"] == "c-123"
        assert "timestamp" in d


class TestAPIError:
    def test_fields(self):
        err = APIError(
            message="Exa returned 500",
            source_module="intel.exa",
            service_name="exa",
            http_status=500,
            endpoint="/search",
            request_duration_ms=150.0,
        )
        assert err.service_name == "exa"
        assert err.http_status == 500
        assert err.endpoint == "/search"
        assert err.request_duration_ms == 150.0


class TestRateLimitError:
    def test_fields(self):
        err = RateLimitError(
            message="rate limited",
            service_name="tavily",
            retry_after_seconds=5.0,
        )
        assert err.service_name == "tavily"
        assert err.retry_after_seconds == 5.0


class TestCircuitOpenError:
    def test_fields(self):
        err = CircuitOpenError(
            message="circuit open",
            service_name="exa",
            reopens_in_seconds=60.0,
        )
        assert err.service_name == "exa"
        assert err.reopens_in_seconds == 60.0


class TestValidationError:
    def test_fields(self):
        err = ValidationError(
            message="bad input",
            field_name="quantity",
            expected="float > 0",
            received="-1",
            validation_rule="positive_quantity",
        )
        assert err.field_name == "quantity"
        assert err.expected == "float > 0"


class TestConfigurationError:
    def test_fields(self):
        err = ConfigurationError(
            message="missing key",
            config_key="EXA_API_KEY",
        )
        assert err.config_key == "EXA_API_KEY"
