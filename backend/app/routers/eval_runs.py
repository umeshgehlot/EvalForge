import os
from typing import Optional

from celery import Celery
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_async_session
from app.models.dataset import Dataset, DatasetRow
from app.models.app_version import AppVersion
from app.models.eval_run import EvalRun, EvalRunItem
from app.models.metrics import AggregateMetrics
from app.models.scorer import Scorer
from app.models.trace import TraceSpan
from app.schemas.eval_run import (
    AggregateMetricRead,
    BenchmarkMetric,
    BenchmarkPoint,
    EvalRunCreate,
    EvalRunItemEnrichedRead,
    EvalRunRead,
    EvalRunStatusRead,
    MetricDelta,
    PaginatedRunItemsEnriched,
    RunComparisonItem,
    RunComparisonRead,
    TraceSpanRead,
)

router = APIRouter(prefix="/runs", tags=["eval_runs"])


def _celery_client() -> Celery:
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return Celery(broker=redis_url, backend=redis_url)


def _enrich(item: EvalRunItem) -> dict:
    row = item.row
    return {
        "id": item.id,
        "run_id": item.run_id,
        "row_id": item.row_id,
        "row_input": row.input if row else "",
        "row_expected": row.expected_output if row else None,
        "row_context": row.context if row else None,
        "row_tags": row.tags if row else None,
        "output": item.output,
        "latency_ms": item.latency_ms,
        "token_in": item.token_in,
        "token_out": item.token_out,
        "pass_fail": item.pass_fail,
        "scorer_results_json": item.scorer_results_json or {},
        "retrieved_chunks_json": item.retrieved_chunks_json or [],
    }


@router.post("", response_model=EvalRunRead, status_code=201)
async def create_run(
    body: EvalRunCreate,
    session: AsyncSession = Depends(get_async_session),
):
    if not await session.get(Dataset, body.dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not await session.get(AppVersion, body.app_version_id):
        raise HTTPException(status_code=404, detail="App version not found")
    if not body.scorer_ids:
        raise HTTPException(status_code=400, detail="At least one scorer required")

    run = EvalRun(
        dataset_id=body.dataset_id,
        app_version_id=body.app_version_id,
        scorer_ids=body.scorer_ids,
        status="pending",
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    task = _celery_client().send_task("tasks.eval_runner.run_eval", args=[run.id])
    run.celery_task_id = task.id
    await session.commit()
    await session.refresh(run)
    return run


@router.get("", response_model=list[EvalRunRead])
async def list_runs(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(EvalRun).order_by(EvalRun.created_at.desc()))
    return result.scalars().all()


@router.get("/compare", response_model=RunComparisonRead)
async def compare_runs(
    run_a: int = Query(...),
    run_b: int = Query(...),
    session: AsyncSession = Depends(get_async_session),
):
    run_a_obj = await session.get(EvalRun, run_a)
    run_b_obj = await session.get(EvalRun, run_b)
    if not run_a_obj:
        raise HTTPException(status_code=404, detail=f"Run {run_a} not found")
    if not run_b_obj:
        raise HTTPException(status_code=404, detail=f"Run {run_b} not found")

    # Aggregate metrics for both runs, joined with scorer name
    rows_ma = (await session.execute(
        select(AggregateMetrics, Scorer)
        .outerjoin(Scorer, AggregateMetrics.scorer_id == Scorer.id)
        .where(AggregateMetrics.run_id == run_a)
    )).all()
    rows_mb = (await session.execute(
        select(AggregateMetrics, Scorer)
        .outerjoin(Scorer, AggregateMetrics.scorer_id == Scorer.id)
        .where(AggregateMetrics.run_id == run_b)
    )).all()

    ma = {metric.scorer_id: (metric, scorer) for metric, scorer in rows_ma}
    mb = {metric.scorer_id: (metric, scorer) for metric, scorer in rows_mb}

    all_scorer_ids = sorted(
        set(ma.keys()) | set(mb.keys()),
        key=lambda x: (x is not None, x or 0),
    )

    def _delta(va: Optional[float], vb: Optional[float]) -> Optional[float]:
        if va is None or vb is None:
            return None
        return vb - va

    metrics_delta = []
    for sid in all_scorer_ids:
        m_a, s_a = ma.get(sid, (None, None))
        m_b, s_b = mb.get(sid, (None, None))
        scorer = s_a or s_b
        metrics_delta.append(MetricDelta(
            scorer_id=sid,
            scorer_name=scorer.name if scorer else "Overall",
            avg_score_a=m_a.avg_score if m_a else None,
            avg_score_b=m_b.avg_score if m_b else None,
            avg_score_delta=_delta(
                m_a.avg_score if m_a else None,
                m_b.avg_score if m_b else None,
            ),
            pass_rate_a=m_a.pass_rate if m_a else None,
            pass_rate_b=m_b.pass_rate if m_b else None,
            pass_rate_delta=_delta(
                m_a.pass_rate if m_a else None,
                m_b.pass_rate if m_b else None,
            ),
            p95_latency_a=m_a.p95_latency if m_a else None,
            p95_latency_b=m_b.p95_latency if m_b else None,
            p95_latency_delta=_delta(
                m_a.p95_latency if m_a else None,
                m_b.p95_latency if m_b else None,
            ),
            total_cost_a=m_a.total_cost if m_a else None,
            total_cost_b=m_b.total_cost if m_b else None,
            total_cost_delta=_delta(
                m_a.total_cost if m_a else None,
                m_b.total_cost if m_b else None,
            ),
        ))

    # Eval run items keyed by row_id for regression/improvement detection
    items_a = {
        item.row_id: item
        for item in (await session.execute(
            select(EvalRunItem)
            .options(joinedload(EvalRunItem.row))
            .where(EvalRunItem.run_id == run_a)
        )).scalars().all()
    }
    items_b = {
        item.row_id: item
        for item in (await session.execute(
            select(EvalRunItem)
            .options(joinedload(EvalRunItem.row))
            .where(EvalRunItem.run_id == run_b)
        )).scalars().all()
    }

    regressions: list[RunComparisonItem] = []
    improvements: list[RunComparisonItem] = []
    for row_id in sorted(set(items_a.keys()) & set(items_b.keys())):
        a = items_a[row_id]
        b = items_b[row_id]
        if a.pass_fail is None or b.pass_fail is None:
            continue
        row_input = a.row.input if a.row else ""
        entry = RunComparisonItem(
            row_id=row_id,
            row_input=row_input,
            item_id_a=a.id,
            item_id_b=b.id,
            output_a=a.output,
            output_b=b.output,
        )
        if a.pass_fail and not b.pass_fail:
            regressions.append(entry)
        elif not a.pass_fail and b.pass_fail:
            improvements.append(entry)

    # Safe-to-ship: no regressions and no pass_rate drop > 5%
    significant_drops = [
        d.pass_rate_delta
        for d in metrics_delta
        if d.pass_rate_delta is not None and d.pass_rate_delta < -0.05
    ]
    safe_to_ship = len(regressions) == 0 and len(significant_drops) == 0
    if safe_to_ship:
        summary = f"Run #{run_b} looks safe to ship — no regressions detected."
    elif regressions:
        summary = (
            f"{len(regressions)} regression(s) detected. "
            f"Run #{run_b} is NOT safe to ship."
        )
    else:
        summary = (
            f"Pass rate dropped significantly (>{5}%). "
            f"Run #{run_b} is NOT safe to ship."
        )

    return RunComparisonRead(
        run_a=run_a_obj,
        run_b=run_b_obj,
        metrics_delta=metrics_delta,
        regressions=regressions,
        improvements=improvements,
        safe_to_ship=safe_to_ship,
        summary=summary,
    )


@router.get("/benchmark", response_model=list[BenchmarkPoint])
async def get_benchmark(
    dataset_id: int = Query(...),
    session: AsyncSession = Depends(get_async_session),
):
    runs_q = await session.execute(
        select(EvalRun)
        .where(EvalRun.dataset_id == dataset_id, EvalRun.status == "completed")
        .order_by(EvalRun.created_at)
    )
    runs = runs_q.scalars().all()
    if not runs:
        return []

    result: list[BenchmarkPoint] = []
    prev_rates: dict[Optional[int], float] = {}

    for run in runs:
        av = await session.get(AppVersion, run.app_version_id)
        av_name = av.name if av else f"App Version #{run.app_version_id}"

        metrics_q = await session.execute(
            select(AggregateMetrics, Scorer)
            .outerjoin(Scorer, AggregateMetrics.scorer_id == Scorer.id)
            .where(AggregateMetrics.run_id == run.id)
        )
        rows = metrics_q.all()

        bm_metrics: list[BenchmarkMetric] = []
        cur_rates: dict[Optional[int], float] = {}
        for metric, scorer in rows:
            bm_metrics.append(BenchmarkMetric(
                scorer_id=metric.scorer_id,
                scorer_name=scorer.name if scorer else "Overall",
                pass_rate=metric.pass_rate,
                avg_score=metric.avg_score,
            ))
            if metric.pass_rate is not None:
                cur_rates[metric.scorer_id] = metric.pass_rate

        has_regression = any(
            cur_rates.get(sid, 1.0) < prev_rates[sid] - 0.05
            for sid in prev_rates
            if sid in cur_rates
        )

        result.append(BenchmarkPoint(
            run_id=run.id,
            app_version_name=av_name,
            created_at=run.created_at,
            has_regression=has_regression,
            metrics=bm_metrics,
        ))
        prev_rates = cur_rates

    return result


@router.get("/{run_id}", response_model=EvalRunRead)
async def get_run(run_id: int, session: AsyncSession = Depends(get_async_session)):
    run = await session.get(EvalRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
    return run


@router.get("/{run_id}/status", response_model=EvalRunStatusRead)
async def get_run_status(
    run_id: int, session: AsyncSession = Depends(get_async_session)
):
    run = await session.get(EvalRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")

    total_q = await session.execute(
        select(func.count())
        .select_from(DatasetRow)
        .where(DatasetRow.dataset_id == run.dataset_id)
    )
    items_total = total_q.scalar() or 0

    done_q = await session.execute(
        select(func.count())
        .select_from(EvalRunItem)
        .where(EvalRunItem.run_id == run_id)
    )
    items_done = done_q.scalar() or 0

    progress = (items_done / items_total) if items_total > 0 else 0.0
    return EvalRunStatusRead(
        id=run.id,
        status=run.status,
        items_done=items_done,
        items_total=items_total,
        progress=progress,
    )


@router.get("/{run_id}/metrics", response_model=list[AggregateMetricRead])
async def get_run_metrics(
    run_id: int, session: AsyncSession = Depends(get_async_session)
):
    run = await session.get(EvalRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
    result = await session.execute(
        select(AggregateMetrics).where(AggregateMetrics.run_id == run_id)
    )
    return result.scalars().all()


@router.get("/{run_id}/results", response_model=PaginatedRunItemsEnriched)
async def get_run_results(
    run_id: int,
    page: int = 1,
    limit: int = 50,
    pass_fail: Optional[bool] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
):
    run = await session.get(EvalRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")

    # Base query with eager-loaded row
    base = (
        select(EvalRunItem)
        .options(joinedload(EvalRunItem.row))
        .where(EvalRunItem.run_id == run_id)
    )
    count_base = (
        select(func.count())
        .select_from(EvalRunItem)
        .where(EvalRunItem.run_id == run_id)
    )

    if pass_fail is not None:
        base = base.where(EvalRunItem.pass_fail == pass_fail)
        count_base = count_base.where(EvalRunItem.pass_fail == pass_fail)

    if tag:
        base = base.join(DatasetRow, EvalRunItem.row_id == DatasetRow.id).where(
            DatasetRow.tags.ilike(f"%{tag}%")
        )
        count_base = count_base.join(
            DatasetRow, EvalRunItem.row_id == DatasetRow.id
        ).where(DatasetRow.tags.ilike(f"%{tag}%"))

    total = (await session.execute(count_base)).scalar() or 0
    items_q = await session.execute(
        base.order_by(EvalRunItem.id).offset((page - 1) * limit).limit(limit)
    )
    items = items_q.scalars().all()

    return PaginatedRunItemsEnriched(
        items=[_enrich(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{run_id}/items/{item_id}", response_model=EvalRunItemEnrichedRead)
async def get_run_item(
    run_id: int,
    item_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(EvalRunItem)
        .options(joinedload(EvalRunItem.row))
        .where(EvalRunItem.id == item_id, EvalRunItem.run_id == run_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Run item not found")
    return _enrich(item)


@router.get("/{run_id}/items/{item_id}/traces", response_model=list[TraceSpanRead])
async def get_item_traces(
    run_id: int,
    item_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    item = await session.get(EvalRunItem, item_id)
    if not item or item.run_id != run_id:
        raise HTTPException(status_code=404, detail="Run item not found")

    result = await session.execute(
        select(TraceSpan)
        .where(TraceSpan.run_item_id == item_id)
        .order_by(TraceSpan.start_ms)
    )
    return result.scalars().all()


@router.delete("/{run_id}", status_code=204)
async def delete_run(run_id: int, session: AsyncSession = Depends(get_async_session)):
    run = await session.get(EvalRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
    await session.delete(run)
    await session.commit()
