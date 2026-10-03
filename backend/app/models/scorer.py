from typing import Optional, Any
from sqlalchemy import String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Scorer(Base):
    __tablename__ = "scorers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    scorer_type: Mapped[str] = mapped_column(String(50))  # deterministic | programmatic | llm_judge
    config_json: Mapped[Any] = mapped_column(JSON, default=lambda: {})
    prompt_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    aggregate_metrics: Mapped[list["AggregateMetrics"]] = relationship(
        back_populates="scorer"
    )
