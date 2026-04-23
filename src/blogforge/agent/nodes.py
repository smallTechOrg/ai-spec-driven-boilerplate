import logging

from blogforge.agent.state import GenerationState
from blogforge.db.repository import (
    add_used_topic,
    create_post,
    get_used_topics,
    get_writers,
    update_post,
    update_run,
)
from blogforge.db.session import get_session
from blogforge.tools.image_generation import generate_image
from blogforge.tools.post_generation import generate_post
from blogforge.tools.topic_discovery import discover_topics

logger = logging.getLogger(__name__)


async def node_topic_discovery(state: GenerationState) -> dict:
    try:
        async with get_session() as session:
            used = await get_used_topics(session)
        topics = await discover_topics(
            niche=state["blog"].niche,
            themes=state["blog"].themes,
            used_topics=used,
        )
        if not topics:
            return {"error": "No topics discovered after deduplication"}
        logger.info("topic_discovery.done", extra={"count": len(topics)})
        return {"topics": topics, "error": None}
    except Exception as exc:
        logger.exception("topic_discovery.fatal")
        return {"error": str(exc)}


async def node_writer_assignment(state: GenerationState) -> dict:
    try:
        async with get_session() as session:
            writers = await get_writers(session)
        active = [w for w in writers if w.is_active]
        if not active:
            return {"error": "No active writers configured"}
        topics = state["topics"][: state["posts_count"]]
        assignments = [(topic, active[i % len(active)]) for i, topic in enumerate(topics)]
        logger.info("writer_assignment.done", extra={"pairs": len(assignments)})
        return {"assignments": assignments, "error": None}
    except Exception as exc:
        logger.exception("writer_assignment.fatal")
        return {"error": str(exc)}


async def node_post_generation(state: GenerationState) -> dict:
    completed: list = list(state.get("completed_posts", []))
    failed: list = list(state.get("failed_topics", []))
    for topic, writer in state["assignments"]:
        try:
            post_data = await generate_post(
                topic=topic,
                writer=writer,
                blog_name=state["blog"].name,
                blog_niche=state["blog"].niche,
            )
            async with get_session() as session:
                post = await create_post(
                    session,
                    run_id=state["run_id"],
                    writer_id=writer.id,
                    topic=topic,
                    **post_data,
                )
                await add_used_topic(session, topic, post.id)
            completed.append(post)
            logger.info("post_generation.saved", extra={"post_id": post.id, "topic": topic})
        except Exception as exc:
            logger.error("post_generation.failed", extra={"topic": topic, "error": str(exc)})
            failed.append(topic)
    return {"completed_posts": completed, "failed_topics": failed}


async def node_image_generation(state: GenerationState) -> dict:
    for post in state.get("completed_posts", []):
        try:
            image_path = await generate_image(post_id=post.id, title=post.title)
            async with get_session() as session:
                await update_post(session, post.id, cover_image_path=image_path)
            logger.info("image_generation.saved", extra={"post_id": post.id, "path": image_path})
        except Exception as exc:
            logger.warning("image_generation.skipped", extra={"post_id": post.id, "error": str(exc)})
    return {}


async def node_handle_error(state: GenerationState) -> dict:
    error = state.get("error", "unknown error")
    logger.error("run.failed", extra={"run_id": state["run_id"], "error": error})
    async with get_session() as session:
        await update_run(session, state["run_id"], status="failed", error_message=error)
    return {}


async def node_finalize(state: GenerationState) -> dict:
    async with get_session() as session:
        await update_run(session, state["run_id"], status="completed")
    logger.info(
        "run.completed",
        extra={
            "run_id": state["run_id"],
            "topics": len(state.get("topics", [])),
            "posts_ok": len(state.get("completed_posts", [])),
            "posts_failed": len(state.get("failed_topics", [])),
        },
    )
    return {}
