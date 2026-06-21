import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.datasets.ingest import ingest_file
from src.db.connection import get_db

router = APIRouter(prefix="/datasets", tags=["datasets"])
UPLOAD_DIR = Path("data/uploads")


@router.post("/")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    conn = get_db()
    try:
        result = ingest_file(conn, str(dest), name)
        conn.close()
        return result
    except ValueError as e:
        conn.close()
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        conn.close()
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_datasets():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, file_type, row_count, created_at FROM datasets ORDER BY created_at"
    ).fetchdf()
    conn.close()
    return rows.to_dict(orient="records")
