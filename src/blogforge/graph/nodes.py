from uuid import UUID

from blogforge.db import repository as repo
from blogforge.db.session import new_session
from blogforge.graph.state import AgentState
from blogforge.llm.client import get_llm


def _prompt_outline(state: AgentState) -> str:
    return (
        "You are ghostwriting a blog post. Produce a 3-6 bullet outline.\n\n"
        f"Voice guidelines:\n{state['guidelines']}\n\n"
        f"Writer persona:\n{state['persona']}\n\n"
        f"Topic: {state['topic']}\n"
        f"Notes: {state.get('notes') or '(none)'}\n\n"
        "Return only the outline, markdown bullets."
    )


def _prompt_draft(state: AgentState) -> str:
    return (
        "Expand this outline into a full blog post in markdown, matching the voice and persona.\n\n"
        f"Voice:\n{state['guidelines']}\n\nPersona:\n{state['persona']}\n\n"
        f"Topic: {state['topic']}\n\nOutline:\n{state['outline']}\n"
    )


def _prompt_title(draft: str) -> str:
    return f"Give a short, catchy title (no quotes, no 'Title:' prefix) for:\n\n{draft[:2000]}"


def node_plan(state: AgentState) -> AgentState:
    try:
        outline = get_llm().generate(_prompt_outline(state))
        return {**state, "outline": outline}
    except Exception as e:
        return {**state, "error": f"plan: {e}"}


def node_draft(state: AgentState) -> AgentState:
    try:
        draft = get_llm().generate(_prompt_draft(state))
        return {**state, "draft": draft}
    except Exception as e:
        return {**state, "error": f"draft: {e}"}


def node_finalize(state: AgentState) -> AgentState:
    try:
        draft = state["draft"] or ""
        title = get_llm().generate(_prompt_title(draft)) or state["topic"][:80]
        title = title.strip().splitlines()[0][:200] if title.strip() else state["topic"][:80]

        with new_session() as db:
            article = repo.create_article(
                db,
                writer_id=UUID(state["writer_id"]),
                voice_id=UUID(state["voice_id"]),
                topic=state["topic"],
                title=title,
                body=draft,
            )
            repo.complete_run(db, UUID(state["run_id"]), article_id=article.id)
        return {**state, "title": title, "body": draft, "article_id": str(article.id)}
    except Exception as e:
        return {**state, "error": f"finalize: {e}"}


def node_handle_error(state: AgentState) -> AgentState:
    with new_session() as db:
        repo.fail_run(db, UUID(state["run_id"]), error_message=state.get("error") or "unknown error")
    return state
