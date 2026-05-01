import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from food_tracker.api._common import render
from food_tracker.db.session import get_session
from food_tracker.graph.runner import run_pipeline

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/heic"}

log = structlog.get_logger()
router = APIRouter()


@router.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@router.get("/")
def upload_form(request: Request):
    return render(request, "upload.html")


@router.post("/analyze")
async def analyze(
    request: Request,
    photo: UploadFile,
    session: Session = Depends(get_session),
):
    if not photo or not photo.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    content_type = photo.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type}'. Please upload a JPEG, PNG, or HEIC image.",
        )

    image_bytes = await photo.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail="File exceeds the 10 MB limit. Please use a smaller image.",
        )
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    provider = request.app.state.provider
    log.info("analyze.request", filename=photo.filename, size=len(image_bytes))

    state = run_pipeline(
        image_bytes=image_bytes,
        image_filename=photo.filename,
        provider=provider,
        session=session,
    )

    if state["error"]:
        log.error("analyze.pipeline_error", error=state["error"])
        return render(request, "error.html", detail=state["error"])

    return render(
        request,
        "result.html",
        food_name=state["food_name"],
        calories_kcal=state["calories_kcal"],
        protein_g=state["protein_g"],
        carbs_g=state["carbs_g"],
        fat_g=state["fat_g"],
        provider=state["provider"],
        run_id=state["run_id"],
    )
