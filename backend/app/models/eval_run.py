from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    app_version_id: Mapped[int] = mapped_column(ForeignKey("app_versions.id"))
    # pending | running | completed | failed
    status: Mapped[str] = mapped_column(String(50), default="pending")
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scorer_ids: Mapped[Any] = mapped_column(JSON, default=lambda: [])
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    dataset: Mapped["Dataset"] = relationship(back_populates="eval_runs")
    app_version: Mapped["AppVersion"] = relationship(back_populates="eval_runs")
    items: Mapped[list["EvalRunItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    aggregate_metrics: Mapped[list["AggregateMetrics"]] = relationship(
        back_populates="run"
    )


class EvalRunItem(Base):
    __tablename__ = "eval_run_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("eval_runs.id", ondelete="CASCADE"))
    row_id: Mapped[int] = mapped_column(ForeignKey("dataset_rows.id"))
    output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_in: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_out: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pass_fail: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    scorer_results_json: Mapped[Any] = mapped_column(JSON, default=lambda: {})
    retrieved_chunks_json: Mapped[Any] = mapped_column(JSON, default=lambda: [])

    run: Mapped["EvalRun"] = relationship(back_populates="items")
    row: Mapped["DatasetRow"] = relationship(back_populates="eval_run_items")
    trace_spans: Mapped[list["TraceSpan"]] = relationship(
        back_populates="run_item", cascade="all, delete-orphan"
    )
