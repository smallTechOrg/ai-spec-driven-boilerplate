"""Shared response serializers mapping ORM rows to api.md response shapes."""
from __future__ import annotations

from db.models import AnalysisRun, Dataset, DatasetProfile
from domain.analysis import RunBody, Tokens
from domain.dataset import DatasetBody, DatasetWithProfile, ProfileBody


def dataset_with_profile(dataset: Dataset, profile: DatasetProfile) -> dict:
    body = DatasetWithProfile(
        dataset=DatasetBody(
            id=dataset.id,
            name=dataset.name,
            kind=dataset.kind,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
            size_bytes=dataset.size_bytes,
            created_at=dataset.created_at,
        ),
        profile=ProfileBody(
            columns=profile.columns,
            row_count=profile.row_count,
            quality_flags=profile.quality_flags,
        ),
    )
    return body.model_dump()


def run_body(run: AnalysisRun) -> dict:
    body = RunBody(
        id=run.id,
        dataset_id=run.dataset_id,
        question=run.question,
        answer=run.answer,
        code=run.code,
        result_summary=run.result_summary,
        tokens=Tokens(
            prompt=run.prompt_tokens,
            completion=run.completion_tokens,
            total=run.total_tokens,
        ),
        cost_usd=run.cost_usd,
        status=run.status,
        error_message=run.error_message,
        assumptions=run.assumptions,
        followups=run.followups,
        viz=run.viz,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )
    return body.model_dump()
