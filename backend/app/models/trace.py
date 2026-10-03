from typing import Optional, Any
from sqlalchemy import String, BigInteger, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TraceSpan(Base):
    __tablename__ = "trace_spans"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_item_id: Mapped[int] = mapped_column(
        ForeignKey("eval_run_items.id", ondelete="CASCADE")
    )
    span_name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    start_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    end_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    metadata_json: Mapped[Any] = mapped_column(JSON, default=lambda: {})

    run_item: Mapped["EvalRunItem"] = relationship(back_populates="trace_spans")
