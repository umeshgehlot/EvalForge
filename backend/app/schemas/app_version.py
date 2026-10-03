from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel


class AppVersionCreate(BaseModel):
    name: str
    model_name: str
    endpoint_url: str
    prompt_template: Optional[str] = None
    retriever_config: Any = {}
    git_note: Optional[str] = None


class AppVersionRead(BaseModel):
    id: int
    name: str
    model_name: str
    endpoint_url: Optional[str] = None
    prompt_template: Optional[str] = None
    retriever_config: Any = {}
    git_note: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
