import json

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from api._common import api_error, ok
from db.models import Dataset
from db.session import get_session
from domain.models import DatasetSummary
from ingest.csv_loader import BadCsvError, EmptyFileError, ingest_csv

router = APIRouter()


def _dataset_summary(ds: Dataset) -> dict:
    columns = json.loads(ds.columns_json) if ds.columns_json else []
    return DatasetSummary(
        id=ds.id,
        name=ds.name,
        table_name=ds.table_name,
        row_count=ds.row_count,
        columns=columns,
        created_at=ds.created_at,
    ).model_dump(mode="json")


@router.post("/datasets")
async def create_dataset(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
) -> dict:
    raw = await file.read()
    display_name = (name or file.filename or "dataset.csv").strip() or "dataset.csv"
    try:
        summary = ingest_csv(raw, display_name)
    except EmptyFileError as exc:
        raise api_error("EMPTY_FILE", str(exc), 400)
    except BadCsvError as exc:
        raise api_error("BAD_CSV", str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        raise api_error("INGEST_FAILED", f"Failed to ingest CSV: {exc}", 500)

    return ok(
        DatasetSummary(
            id=summary["id"],
            name=summary["name"],
            table_name=summary["table_name"],
            row_count=summary["row_count"],
            columns=summary["columns"],
            created_at=summary["created_at"],
        ).model_dump(mode="json")
    )


@router.get("/datasets")
def list_datasets(session: Session = Depends(get_session)) -> dict:
    rows = session.execute(
        select(Dataset).order_by(Dataset.created_at.desc())
    ).scalars().all()
    return ok([_dataset_summary(d) for d in rows])


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str, session: Session = Depends(get_session)) -> dict:
    ds = session.get(Dataset, dataset_id)
    if ds is None:
        raise api_error("NOT_FOUND", f"Dataset {dataset_id} not found", 404)
    return ok(_dataset_summary(ds))
