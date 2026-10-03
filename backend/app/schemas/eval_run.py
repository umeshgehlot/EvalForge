from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel


class EvalRunCreate(BaseModel):
    dataset_id: int
    app_version_id: int
    scorer_ids: list[int]


class EvalRunRead(BaseModel):
    id: int
    dataset_id: int
    app_version_id: int
    status: str
    celery_task_id: Optional[str] = None
    scorer_ids: list[int] = []
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EvalRunStatusRead(BaseModel):
    id: int
    status: str
    items_done: int
    items_total: int
    progress: float


class EvalRunItemRead(BaseModel):
    id: int
    run_id: int
    row_id: int
    output: Optional[str] = None
    latency_ms: Optional[int] = None
    token_in: Optional[int] = None
    token_out: Optional[int] = None
    pass_fail: Optional[bool] = None
    scorer_results_json: Any = {}
    retrieved_chunks_json: Any = []

    model_config = {"from_attributes": True}


class EvalRunItemEnrichedRead(BaseModel):
    """EvalRunItem joined with its DatasetRow for the results table."""
    id: int
    run_id: int
    row_id: int
    # DatasetRow fields
    row_input: str
    row_expected: Optional[str] = None
    row_context: Optional[str] = None
    row_tags: Optional[str] = None
    # EvalRunItem fields
    output: Optional[str] = None
    latency_ms: Optional[int] = None
    token_in: Optional[int] = None
    token_out: Optional[int] = None
    pass_fail: Optional[bool] = None
    scorer_results_json: Any = {}
    retrieved_chunks_json: Any = []


class PaginatedRunItems(BaseModel):
    items: list[EvalRunItemRead]
    total: int
    page: int
    limit: int


class PaginatedRunItemsEnriched(BaseModel):
    items: list[EvalRunItemEnrichedRead]
    total: int
    page: int
    limit: int


class AggregateMetricRead(BaseModel):
    id: int
    run_id: int
    scorer_id: Optional[int] = None
    avg_score: Optional[float] = None
    pass_rate: Optional[float] = None
    p95_latency: Optional[float] = None
    total_cost: Optional[float] = None

    model_config = {"from_attributes": True}


class TraceSpanRead(BaseModel):
    id: int
    run_item_id: int
    span_name: str
    parent_id: Optional[int] = None
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    metadata_json: Any = {}

    model_config = {"from_attributes": True}


class RunComparisonItem(BaseModel):
    row_id: int
    row_input: str
    item_id_a: int
    item_id_b: int
    output_a: Optional[str] = None
    output_b: Optional[str] = None


class MetricDelta(BaseModel):
    scorer_id: Optional[int] = None
    scorer_name: str
    avg_score_a: Optional[float] = None
    avg_score_b: Optional[float] = None
    avg_score_delta: Optional[float] = None
    pass_rate_a: Optional[float] = None
    pass_rate_b: Optional[float] = None
    pass_rate_delta: Optional[float] = None
    p95_latency_a: Optional[float] = None
    p95_latency_b: Optional[float] = None
    p95_latency_delta: Optional[float] = None
    total_cost_a: Optional[float] = None
    total_cost_b: Optional[float] = None
    total_cost_delta: Optional[float] = None


class RunComparisonRead(BaseModel):
    run_a: EvalRunRead
    run_b: EvalRunRead
    metrics_delta: list[MetricDelta]
    regressions: list[RunComparisonItem]
    improvements: list[RunComparisonItem]
    safe_to_ship: bool
    summary: str


class BenchmarkMetric(BaseModel):
    scorer_id: Optional[int]
    scorer_name: str
    pass_rate: Optional[float]
    avg_score: Optional[float]


class BenchmarkPoint(BaseModel):
    run_id: int
    app_version_name: str
    created_at: datetime
    has_regression: bool
    metrics: list[BenchmarkMetric]
