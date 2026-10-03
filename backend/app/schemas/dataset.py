from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DatasetRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    row_count: int = 0

    model_config = {"from_attributes": True}


class DatasetRowRead(BaseModel):
    id: int
    dataset_id: int
    input: str
    expected_output: Optional[str] = None
    context: Optional[str] = None
    tags: Optional[str] = None
    metadata_json: Any = {}

    model_config = {"from_attributes": True}


class PaginatedRows(BaseModel):
    total: int
    page: int
    limit: int
    items: list[DatasetRowRead]
