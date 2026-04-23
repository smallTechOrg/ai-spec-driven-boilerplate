import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from blogforge.agent.state import GenerationState
from blogforge.domain.models import Blog, Writer, Post

_NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _blog() -> Blog:
    return Blog(id=1, name="TestBlog", niche="productivity", themes=["focus"],
                created_at=_NOW, updated_at=_NOW)


def _writer() -> Writer:
    return Writer(id=1, name="Alice", persona_prompt="Write clearly.", bio="",
                  is_active=True, created_at=_NOW, updated_at=_NOW)


def _base_state(**overrides) -> GenerationState:
    state: GenerationState = {
        "run_id": 1,
        "blog": _blog(),
        "posts_count": 3,
        "topics": [],
        "assignments": [],
        "completed_posts": [],
        "failed_topics": [],
        "error": None,
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_topic_discovery_returns_topics():
    from blogforge.agent.nodes import node_topic_discovery

    with (
        patch("blogforge.agent.nodes.get_session") as mock_gs,
        patch("blogforge.agent.nodes.get_used_topics", new=AsyncMock(return_value=[])),
        patch("blogforge.agent.nodes.discover_topics", new=AsyncMock(return_value=["T1", "T2", "T3"])),
    ):
        mock_gs.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await node_topic_discovery(_base_state())

    assert result["topics"] == ["T1", "T2", "T3"]
    assert result["error"] is None


@pytest.mark.asyncio
async def test_topic_discovery_sets_error_on_empty():
    from blogforge.agent.nodes import node_topic_discovery

    with (
        patch("blogforge.agent.nodes.get_session") as mock_gs,
        patch("blogforge.agent.nodes.get_used_topics", new=AsyncMock(return_value=[])),
        patch("blogforge.agent.nodes.discover_topics", new=AsyncMock(return_value=[])),
    ):
        mock_gs.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await node_topic_discovery(_base_state())

    assert result["error"] is not None
    assert "topics" not in result or result.get("topics") is None or result.get("topics") == []


@pytest.mark.asyncio
async def test_writer_assignment_round_robin():
    from blogforge.agent.nodes import node_writer_assignment

    w1 = _writer()
    w2 = Writer(id=2, name="Bob", persona_prompt=".", bio="", is_active=True, created_at=_NOW, updated_at=_NOW)

    with (
        patch("blogforge.agent.nodes.get_session") as mock_gs,
        patch("blogforge.agent.nodes.get_writers", new=AsyncMock(return_value=[w1, w2])),
    ):
        mock_gs.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await node_writer_assignment(_base_state(topics=["T1", "T2", "T3"]))

    assignments = result["assignments"]
    assert len(assignments) == 3
    assert assignments[0][1].id == 1
    assert assignments[1][1].id == 2
    assert assignments[2][1].id == 1


@pytest.mark.asyncio
async def test_writer_assignment_no_writers_sets_error():
    from blogforge.agent.nodes import node_writer_assignment

    with (
        patch("blogforge.agent.nodes.get_session") as mock_gs,
        patch("blogforge.agent.nodes.get_writers", new=AsyncMock(return_value=[])),
    ):
        mock_gs.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await node_writer_assignment(_base_state(topics=["T1"]))

    assert result["error"] is not None
