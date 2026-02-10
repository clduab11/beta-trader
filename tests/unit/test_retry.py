"""Unit tests for retry with backoff."""

from unittest.mock import AsyncMock

import pytest

from intel.errors import APIError, RateLimitError
from intel.retry import retry_with_backoff


class TestRetryWithBackoff:
    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        fn = AsyncMock(return_value="ok")
        result = await retry_with_backoff(fn, max_attempts=3, base_delay=0.01)
        assert result == "ok"
        fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_on_second_try(self):
        fn = AsyncMock(
            side_effect=[
                APIError("fail", service_name="test"),
                "ok",
            ]
        )
        result = await retry_with_backoff(fn, max_attempts=3, base_delay=0.01)
        assert result == "ok"
        assert fn.call_count == 2

    @pytest.mark.asyncio
    async def test_exhausts_all_attempts(self):
        fn = AsyncMock(side_effect=APIError("fail", service_name="test"))
        with pytest.raises(APIError, match="fail"):
            await retry_with_backoff(fn, max_attempts=3, base_delay=0.01)
        assert fn.call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_exception_raises_immediately(self):
        fn = AsyncMock(side_effect=ValueError("not retryable"))
        with pytest.raises(ValueError, match="not retryable"):
            await retry_with_backoff(fn, max_attempts=3, base_delay=0.01)
        fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_respects_retry_after(self):
        fn = AsyncMock(
            side_effect=[
                RateLimitError("limited", service_name="test", retry_after_seconds=0.01),
                "ok",
            ]
        )
        result = await retry_with_backoff(
            fn,
            max_attempts=3,
            base_delay=0.001,
            jitter=False,
        )
        assert result == "ok"
        assert fn.call_count == 2

    @pytest.mark.asyncio
    async def test_on_retry_callback(self):
        callback = AsyncMock()
        fn = AsyncMock(
            side_effect=[
                APIError("fail1", service_name="test"),
                APIError("fail2", service_name="test"),
                "ok",
            ]
        )
        result = await retry_with_backoff(
            fn,
            max_attempts=3,
            base_delay=0.01,
            on_retry=callback,
        )
        assert result == "ok"
        assert callback.call_count == 2

    @pytest.mark.asyncio
    async def test_custom_retryable_exceptions(self):
        fn = AsyncMock(
            side_effect=[
                ValueError("retry me"),
                "ok",
            ]
        )
        result = await retry_with_backoff(
            fn,
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,),
        )
        assert result == "ok"
        assert fn.call_count == 2
