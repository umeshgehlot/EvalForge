from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AppVersion(Base):
    __tablename__ = "app_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    model_name: Mapped[str] = mapped_column(String(255))
    endpoint_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    prompt_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retriever_config: Mapped[Any] = mapped_column(JSON, default=lambda: {})
    git_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    eval_runs: Mapped[list["EvalRun"]] = relationship(back_populates="app_version")
