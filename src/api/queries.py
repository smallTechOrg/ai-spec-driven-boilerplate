import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api._common import api_error, ok
from db.models import Dataset, Query
from db.session import get_session
from domain.models import QueryRequest, QueryResult
from graph.runner import run_query

router = APIRouter()


def _query_result(q: Query) -> dict:
    return QueryResult(
        id=q.id,
        dataset_id=q.dataset_id,
        question=q.question,
        generated_sql=q.generated_sql,
        answer_text=q.answer_text,
        result_columns=json.loads(q.result_columns_json) if q.result_columns_json else None,
        result_rows=json.loads(q.result_rows_json) if q.result_rows_json else None,
        row_count=q.row_count,
        status=q.status,
        error=q.error_message,
        created_at=q.created_at,
    ).model_dump(mode="json")


@router.post("/queries")
def create_query(req: QueryRequest, session: Session = Depends(get_session)) -> dict:
    if not req.question or not req.question.strip():
        raise api_error("BAD_REQUEST", "Question must not be empty", 400)
    ds = session.get(Dataset, req.dataset_id)
    if ds is None:
        raise api_error("NOT_FOUND", f"Dataset {req.dataset_id} not found", 404)

    query_id = run_query(req.dataset_id, req.question.strip())

    q = session.get(Query, query_id)
    if q is None:
        raise api_error("INTERNAL", "Query not found after run", 500)
    return ok(_query_result(q))


@router.get("/queries")
def list_queries(
    dataset_id: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(Query).order_by(Query.created_at.desc())
    if dataset_id:
        stmt = stmt.where(Query.dataset_id == dataset_id)
    rows = session.execute(stmt).scalars().all()
    return ok([_query_result(q) for q in rows])
