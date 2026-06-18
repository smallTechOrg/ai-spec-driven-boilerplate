"""Dataset + file-upload routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datachat.api._common import api_error, ok
from datachat.config.settings import get_settings
from datachat.data import engine
from datachat.data.ingest import ingest_csv
from datachat.db.models import Dataset, File
from datachat.db.session import get_session
from datachat.domain import DatasetCreate

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _file_dict(f: File) -> dict:
    return {
        "id": f.id,
        "dataset_id": f.dataset_id,
        "filename": f.filename,
        "duckdb_table": f.duckdb_table,
        "schema_columns": f.schema_json,
        "row_count": f.row_count,
        "created_at": f.created_at.isoformat(),
    }


def _dataset_dict(ds: Dataset, files: list[File]) -> dict:
    return {
        "id": ds.id,
        "name": ds.name,
        "created_at": ds.created_at.isoformat(),
        "files": [_file_dict(f) for f in files],
    }


async def _files_for(session: AsyncSession, dataset_id: str) -> list[File]:
    return list(
        (await session.execute(select(File).where(File.dataset_id == dataset_id)))
        .scalars()
        .all()
    )


@router.post("")
async def create_dataset(body: DatasetCreate, session: AsyncSession = Depends(get_session)):
    ds = Dataset(name=body.name)
    session.add(ds)
    await session.commit()
    await session.refresh(ds)
    return ok(_dataset_dict(ds, []), status=201)


@router.get("")
async def list_datasets(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Dataset).order_by(Dataset.created_at.desc()))).scalars().all()
    out = [_dataset_dict(ds, await _files_for(session, ds.id)) for ds in rows]
    return ok(out)


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, session: AsyncSession = Depends(get_session)):
    ds = await session.get(Dataset, dataset_id)
    if ds is None:
        raise api_error("NOT_FOUND", "Dataset not found.", status=404)
    return ok(_dataset_dict(ds, await _files_for(session, dataset_id)))


@router.post("/{dataset_id}/files")
async def upload_files(
    dataset_id: str,
    files: list[UploadFile],
    session: AsyncSession = Depends(get_session),
):
    ds = await session.get(Dataset, dataset_id)
    if ds is None:
        raise api_error("NOT_FOUND", "Dataset not found.", status=404)

    max_bytes = get_settings().max_upload_bytes
    created: list[dict] = []
    for upload in files:
        raw = await upload.read()
        if len(raw) > max_bytes:
            raise api_error("FILE_TOO_LARGE", f"{upload.filename} exceeds the size limit.", status=413)
        try:
            res = ingest_csv(dataset_id, upload.filename or "upload.csv", raw)
        except ValueError as exc:
            raise api_error("BAD_CSV", str(exc), status=422)

        rec = File(
            dataset_id=dataset_id,
            filename=upload.filename or "upload.csv",
            duckdb_table=res.duckdb_table,
            schema_json=res.schema_columns,
            sample_rows_json=res.sample_rows,
            row_count=res.row_count,
        )
        session.add(rec)
        await session.commit()
        await session.refresh(rec)
        created.append(_file_dict(rec))

    return ok({"dataset_id": dataset_id, "files": created}, status=201)


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str, session: AsyncSession = Depends(get_session)):
    ds = await session.get(Dataset, dataset_id)
    if ds is None:
        raise api_error("NOT_FOUND", "Dataset not found.", status=404)
    await session.delete(ds)
    await session.commit()
    engine.release(dataset_id)  # release the session-scoped DuckDB engine on deletion
    return ok({"deleted": dataset_id})
