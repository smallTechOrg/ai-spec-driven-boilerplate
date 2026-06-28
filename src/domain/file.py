from datetime import datetime
from pydantic import BaseModel


class SchemaPreview(BaseModel):
    columns: list[str]
    dtypes: dict[str, str]
    sample_rows: list[list]


class UploadedFileResponse(BaseModel):
    file_id: str
    original_name: str
    source_type: str
    row_count: int | None
    file_size_bytes: int | None
    schema_preview: SchemaPreview
    created_at: datetime | None = None
