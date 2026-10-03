from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Text, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    rows: Mapped[list["DatasetRow"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    eval_runs: Mapped[list["EvalRun"]] = relationship(back_populates="dataset")


class DatasetRow(Base):
    __tablename__ = "dataset_rows"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE")
    )
    input: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[Any] = mapped_column(JSON, default=lambda: {})

    dataset: Mapped["Dataset"] = relationship(back_populates="rows")
    eval_run_items: Mapped[list["EvalRunItem"]] = relationship(back_populates="row")
