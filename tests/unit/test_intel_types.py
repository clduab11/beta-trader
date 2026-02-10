"""Unit tests for Intel pipeline types."""

from intel.types import (
    IntelDepth,
    IntelQuery,
    IntelResult,
    IntelSource,
    ScrapedContent,
    SearchResult,
    Timestamp,
)


class TestTimestamp:
    def test_now(self):
        ts = Timestamp.now()
        assert ts.unix_nanos > 0
        assert "T" in ts.iso8601

    def test_from_epoch_seconds(self):
        ts = Timestamp.from_epoch_seconds(1700000000.0)
        assert ts.unix_nanos == 1700000000000000000


class TestIntelDepth:
    def test_values(self):
        assert IntelDepth.SHALLOW == "SHALLOW"
        assert IntelDepth.STANDARD == "STANDARD"
        assert IntelDepth.DEEP == "DEEP"


class TestIntelQuery:
    def test_defaults(self):
        q = IntelQuery(text="test query")
        assert q.text == "test query"
        assert q.depth == IntelDepth.STANDARD
        assert q.max_sources == 10
        assert q.query_id
        assert q.correlation_id.startswith("req-")

    def test_custom_depth(self):
        q = IntelQuery(text="test", depth=IntelDepth.DEEP)
        assert q.depth == IntelDepth.DEEP


class TestIntelSource:
    def test_creation(self):
        source = IntelSource(
            source_name="exa",
            url="https://example.com",
            title="Test",
            snippet="Some content",
            relevance_score=0.85,
            cost_usd=0.001,
        )
        assert source.source_name == "exa"
        assert source.relevance_score == 0.85


class TestIntelResult:
    def test_creation(self):
        result = IntelResult(
            query_id="test-id",
            correlation_id="req-123",
            depth_used=IntelDepth.STANDARD,
            total_cost_usd=0.05,
        )
        assert result.query_id == "test-id"
        assert result.cached is False
        assert result.sources == []

    def test_with_sources(self):
        sources = [
            IntelSource(source_name="exa", title="R1", snippet="S1"),
            IntelSource(source_name="tavily", title="R2", snippet="S2"),
        ]
        result = IntelResult(
            query_id="test",
            correlation_id="req-123",
            sources=sources,
            depth_used=IntelDepth.STANDARD,
        )
        assert len(result.sources) == 2


class TestSearchResult:
    def test_defaults(self):
        r = SearchResult()
        assert r.url is None
        assert r.title == ""
        assert r.source_name == ""


class TestScrapedContent:
    def test_creation(self):
        sc = ScrapedContent(
            url="https://example.com",
            title="Test Page",
            content="<html>...</html>",
            markdown="# Test",
        )
        assert sc.url == "https://example.com"
        assert sc.markdown == "# Test"
