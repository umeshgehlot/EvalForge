from typing import Optional
from sqlalchemy import ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AggregateMetrics(Base):
    __tablename__ = "aggregate_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("eval_runs.id", ondelete="CASCADE"))
    scorer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("scorers.id"), nullable=True
    )
    avg_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pass_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p95_latency: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    run: Mapped["EvalRun"] = relationship(back_populates="aggregate_metrics")
    scorer: Mapped[Optional["Scorer"]] = relationship(back_populates="aggregate_metrics")
