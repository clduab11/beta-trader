"""Unit tests for CouncilRecord schema and validation."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from council.types import CouncilRecord


class TestCouncilRecordValidation:
    """Pydantic validation rules for CouncilRecord."""

    def test_valid_record_minimal(self):
        record = CouncilRecord(
            query_id="q-1",
            merged_text="some intel text",
        )
        assert record.query_id == "q-1"
        assert record.merged_text == "some intel text"
        assert record.embedding_vector == []
        assert record.source_names == []
        assert record.depth_used == "STANDARD"
        assert record.total_cost_usd == 0.0

    def test_valid_record_full(self):
        vec = [0.1] * 768
        record = CouncilRecord(
            query_id="q-2",
            correlation_id="corr-abc",
            merged_text="full record",
            embedding_vector=vec,
            source_names=["exa", "tavily"],
            depth_used="DEEP",
            total_cost_usd=0.005,
            tags=["crypto", "news"],
            metadata={"foo": "bar"},
        )
        assert len(record.embedding_vector) == 768
        assert record.source_names == ["exa", "tavily"]
        assert record.tags == ["crypto", "news"]

    def test_merged_text_empty_raises(self):
        with pytest.raises(ValidationError, match="merged_text must not be empty"):
            CouncilRecord(query_id="q-3", merged_text="")

    def test_merged_text_whitespace_raises(self):
        with pytest.raises(ValidationError, match="merged_text must not be empty"):
            CouncilRecord(query_id="q-4", merged_text="   ")

    def test_embedding_wrong_dimensions_raises(self):
        with pytest.raises(ValidationError, match="768 dimensions"):
            CouncilRecord(
                query_id="q-5",
                merged_text="text",
                embedding_vector=[0.1] * 100,
            )

    def test_embedding_empty_allowed(self):
        record = CouncilRecord(query_id="q-6", merged_text="text", embedding_vector=[])
        assert record.embedding_vector == []

    def test_negative_cost_raises(self):
        with pytest.raises(ValidationError):
            CouncilRecord(
                query_id="q-7",
                merged_text="text",
                total_cost_usd=-1.0,
            )

    def test_uuid_auto_generated(self):
        r1 = CouncilRecord(query_id="q-8", merged_text="a")
        r2 = CouncilRecord(query_id="q-9", merged_text="b")
        assert r1.id != r2.id

    def test_created_at_default(self):
        record = CouncilRecord(query_id="q-10", merged_text="text")
        assert isinstance(record.created_at, datetime)
        assert record.created_at.tzinfo is not None
