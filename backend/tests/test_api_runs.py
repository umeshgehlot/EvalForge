"""Integration tests for app-versions, scorers, and eval-run endpoints."""
import json
import io
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.app_version import AppVersion
from app.models.dataset import Dataset, DatasetRow
from app.models.eval_run import EvalRun, EvalRunItem
from app.models.metrics import AggregateMetrics
from app.models.scorer import Scorer
from app.models.trace import TraceSpan


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _create_dataset(client, name="Test DS") -> int:
    r = await client.post("/datasets", json={"name": name})
    ds_id = r.json()["id"]
    csv = "input,expected_output\nWhat is AI?,Artificial intelligence.\n"
    await client.post(
        f"/datasets/{ds_id}/rows/upload",
        files={"file": ("d.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    return ds_id


async def _create_app_version(client) -> int:
    r = await client.post("/app-versions", json={
        "name": "v1.0", "model_name": "gpt-3.5-turbo", "endpoint_url": "http://demo:8000",
    })
    return r.json()["id"]


async def _create_scorer(client) -> int:
    r = await client.post("/scorers", json={
        "name": "KW Test", "scorer_type": "keyword_coverage",
        "config_json": {"threshold": 0.7},
    })
    return r.json()["id"]


# ── App Version endpoints ─────────────────────────────────────────────────────

async def test_create_app_version(client):
    r = await client.post("/app-versions", json={
        "name": "v1.0",
        "model_name": "gpt-4",
        "endpoint_url": "http://app:8000",
        "git_note": "initial",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "v1.0"
    assert data["model_name"] == "gpt-4"
    assert "id" in data


async def test_list_app_versions(client):
    await client.post("/app-versions", json={"name": "v1", "model_name": "gpt-3.5-turbo", "endpoint_url": "http://a"})
    await client.post("/app-versions", json={"name": "v2", "model_name": "gpt-4", "endpoint_url": "http://b"})
    r = await client.get("/app-versions")
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_get_app_version_not_found(client):
    r = await client.get("/app-versions/9999")
    assert r.status_code == 404


async def test_delete_app_version(client):
    av_id = (await client.post("/app-versions", json={
        "name": "del", "model_name": "m", "endpoint_url": "http://x",
    })).json()["id"]
    r = await client.delete(f"/app-versions/{av_id}")
    assert r.status_code == 204
    assert (await client.get(f"/app-versions/{av_id}")).status_code == 404


# ── Scorer endpoints ──────────────────────────────────────────────────────────

async def test_create_scorer(client):
    r = await client.post("/scorers", json={
        "name": "Exact", "scorer_type": "exact_match", "config_json": {"threshold": 1.0},
    })
    assert r.status_code == 201
    assert r.json()["scorer_type"] == "exact_match"


async def test_create_scorer_invalid_type(client):
    r = await client.post("/scorers", json={
        "name": "Bad", "scorer_type": "nonexistent_type", "config_json": {},
    })
    assert r.status_code == 400


async def test_list_scorers(client):
    await client.post("/scorers", json={"name": "S1", "scorer_type": "exact_match", "config_json": {}})
    await client.post("/scorers", json={"name": "S2", "scorer_type": "keyword_coverage", "config_json": {"threshold": 0.7}})
    r = await client.get("/scorers")
    assert len(r.json()) == 2


async def test_test_scorer_endpoint(client):
    sid = (await client.post("/scorers", json={
        "name": "Exact", "scorer_type": "exact_match", "config_json": {"threshold": 1.0},
    })).json()["id"]

    r = await client.post(f"/scorers/{sid}/test", json={
        "input": "q", "output": "hello", "expected": "hello",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["passed"] is True
    assert body["score"] == 1.0


async def test_test_scorer_not_found(client):
    r = await client.post("/scorers/9999/test", json={"input": "q", "output": "a"})
    assert r.status_code == 404


# ── Eval run creation ─────────────────────────────────────────────────────────

@patch("app.routers.eval_runs._celery_client")
async def test_create_run(mock_celery, client):
    mock_celery.return_value = MagicMock(
        send_task=MagicMock(return_value=MagicMock(id="mock-task-id"))
    )
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)

    r = await client.post("/runs", json={
        "dataset_id": ds_id, "app_version_id": av_id, "scorer_ids": [sc_id],
    })
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["dataset_id"] == ds_id
    assert data["scorer_ids"] == [sc_id]
    assert data["celery_task_id"] == "mock-task-id"


@patch("app.routers.eval_runs._celery_client")
async def test_create_run_no_scorers(mock_celery, client):
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    r = await client.post("/runs", json={
        "dataset_id": ds_id, "app_version_id": av_id, "scorer_ids": [],
    })
    assert r.status_code == 400


@patch("app.routers.eval_runs._celery_client")
async def test_list_runs(mock_celery, client):
    mock_celery.return_value = MagicMock(send_task=MagicMock(return_value=MagicMock(id="t")))
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)

    await client.post("/runs", json={"dataset_id": ds_id, "app_version_id": av_id, "scorer_ids": [sc_id]})
    r = await client.get("/runs")
    assert r.status_code == 200
    assert len(r.json()) == 1


# ── Run status ────────────────────────────────────────────────────────────────

@patch("app.routers.eval_runs._celery_client")
async def test_run_status(mock_celery, client):
    mock_celery.return_value = MagicMock(send_task=MagicMock(return_value=MagicMock(id="t")))
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)

    run_id = (await client.post("/runs", json={
        "dataset_id": ds_id, "app_version_id": av_id, "scorer_ids": [sc_id],
    })).json()["id"]

    r = await client.get(f"/runs/{run_id}/status")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pending"
    assert body["items_total"] == 1   # dataset has 1 row
    assert body["items_done"] == 0
    assert body["progress"] == 0.0


# ── Run results with items ────────────────────────────────────────────────────

async def _make_completed_run(db_engine, ds_id: int, av_id: int, sc_id: int) -> int:
    """Insert a completed run with 2 items (1 pass, 1 fail) directly into the DB."""
    SM = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    # Add a second dataset row so we have 2 items
    async with SM() as s:
        row2 = DatasetRow(dataset_id=ds_id, input="Q2", expected_output="A2")
        s.add(row2)
        await s.flush()
        row2_id = row2.id

        run = EvalRun(
            dataset_id=ds_id,
            app_version_id=av_id,
            status="completed",
            scorer_ids=[sc_id],
            completed_at=datetime.now(timezone.utc),
        )
        s.add(run)
        await s.flush()
        run_id = run.id

        rows = (await s.execute(__import__("sqlalchemy").select(DatasetRow).where(DatasetRow.dataset_id == ds_id))).scalars().all()
        for i, row in enumerate(rows):
            pf = (i == 0)  # first row passes, second fails
            item = EvalRunItem(
                run_id=run_id, row_id=row.id,
                output=f"Answer {i}",
                latency_ms=300 + i * 100,
                token_in=100, token_out=50,
                pass_fail=pf,
                scorer_results_json={str(sc_id): {"score": 0.9 if pf else 0.3, "passed": pf, "label": "pass" if pf else "fail", "reasoning": "test"}},
            )
            s.add(item)
        await s.flush()

        metric = AggregateMetrics(run_id=run_id, scorer_id=sc_id, avg_score=0.6, pass_rate=0.5, p95_latency=400.0, total_cost=0.001)
        s.add(metric)
        await s.commit()
        return run_id


async def test_run_results(client, db_engine):
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)
    run_id = await _make_completed_run(db_engine, ds_id, av_id, sc_id)

    r = await client.get(f"/runs/{run_id}/results")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


async def test_run_results_filter_pass(client, db_engine):
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)
    run_id = await _make_completed_run(db_engine, ds_id, av_id, sc_id)

    r = await client.get(f"/runs/{run_id}/results?pass_fail=true")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["pass_fail"] is True


async def test_run_results_filter_fail(client, db_engine):
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)
    run_id = await _make_completed_run(db_engine, ds_id, av_id, sc_id)

    r = await client.get(f"/runs/{run_id}/results?pass_fail=false")
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["pass_fail"] is False


async def test_run_metrics(client, db_engine):
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)
    run_id = await _make_completed_run(db_engine, ds_id, av_id, sc_id)

    r = await client.get(f"/runs/{run_id}/metrics")
    assert r.status_code == 200
    metrics = r.json()
    assert len(metrics) == 1
    assert metrics[0]["pass_rate"] == 0.5
    assert metrics[0]["p95_latency"] == 400.0


# ── Item detail + traces ──────────────────────────────────────────────────────

async def _add_trace(db_engine, run_id: int) -> int:
    SM = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    import sqlalchemy as sa
    async with SM() as s:
        item = (await s.execute(sa.select(EvalRunItem).where(EvalRunItem.run_id == run_id))).scalars().first()
        span = TraceSpan(run_item_id=item.id, span_name="rag.total", start_ms=0, end_ms=300, metadata_json={"model": "gpt-4"})
        s.add(span)
        await s.flush()
        root_id = span.id
        child = TraceSpan(run_item_id=item.id, span_name="rag.retrieval", parent_id=root_id, start_ms=5, end_ms=90, metadata_json={})
        s.add(child)
        await s.commit()
        return item.id


async def test_run_item_detail(client, db_engine):
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)
    run_id = await _make_completed_run(db_engine, ds_id, av_id, sc_id)

    results = (await client.get(f"/runs/{run_id}/results")).json()["items"]
    item_id = results[0]["id"]

    r = await client.get(f"/runs/{run_id}/items/{item_id}")
    assert r.status_code == 200
    body = r.json()
    assert "row_input" in body
    assert "scorer_results_json" in body


async def test_run_item_traces(client, db_engine):
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)
    run_id = await _make_completed_run(db_engine, ds_id, av_id, sc_id)
    item_id = await _add_trace(db_engine, run_id)

    r = await client.get(f"/runs/{run_id}/items/{item_id}/traces")
    assert r.status_code == 200
    spans = r.json()
    assert len(spans) == 2
    names = {s["span_name"] for s in spans}
    assert "rag.total" in names
    assert "rag.retrieval" in names
    # child has parent_id set
    retrieval = next(s for s in spans if s["span_name"] == "rag.retrieval")
    assert retrieval["parent_id"] is not None


# ── Compare runs ──────────────────────────────────────────────────────────────

async def _make_two_runs(db_engine, ds_id, av_id, sc_id):
    """Run A: row1=pass, row2=fail. Run B: row1=fail (regression), row2=pass (improvement)."""
    SM = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    import sqlalchemy as sa
    async with SM() as s:
        # Add a second row
        row2 = DatasetRow(dataset_id=ds_id, input="Q2", expected_output="A2")
        s.add(row2)
        await s.flush()

        rows = (await s.execute(sa.select(DatasetRow).where(DatasetRow.dataset_id == ds_id))).scalars().all()
        row_ids = [r.id for r in rows]

        now = datetime.now(timezone.utc)
        run_a = EvalRun(dataset_id=ds_id, app_version_id=av_id, status="completed", scorer_ids=[sc_id], completed_at=now - timedelta(hours=2))
        run_b = EvalRun(dataset_id=ds_id, app_version_id=av_id, status="completed", scorer_ids=[sc_id], completed_at=now)
        s.add(run_a); s.add(run_b)
        await s.flush()

        # Run A: row0=pass, row1=fail
        s.add(EvalRunItem(run_id=run_a.id, row_id=row_ids[0], output="A0", pass_fail=True, scorer_results_json={}, latency_ms=400, token_in=100, token_out=50))
        s.add(EvalRunItem(run_id=run_a.id, row_id=row_ids[1], output="A1", pass_fail=False, scorer_results_json={}, latency_ms=400, token_in=100, token_out=50))
        # Run B: row0=fail (regression!), row1=pass (improvement!)
        s.add(EvalRunItem(run_id=run_b.id, row_id=row_ids[0], output="B0", pass_fail=False, scorer_results_json={}, latency_ms=500, token_in=110, token_out=55))
        s.add(EvalRunItem(run_id=run_b.id, row_id=row_ids[1], output="B1", pass_fail=True, scorer_results_json={}, latency_ms=500, token_in=110, token_out=55))

        for run, pr in [(run_a, 0.5), (run_b, 0.5)]:
            s.add(AggregateMetrics(run_id=run.id, scorer_id=sc_id, avg_score=pr, pass_rate=pr, p95_latency=450.0, total_cost=0.001))

        await s.commit()
        return run_a.id, run_b.id


async def test_compare_runs(client, db_engine):
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)
    run_a_id, run_b_id = await _make_two_runs(db_engine, ds_id, av_id, sc_id)

    r = await client.get(f"/runs/compare?run_a={run_a_id}&run_b={run_b_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["run_a"]["id"] == run_a_id
    assert body["run_b"]["id"] == run_b_id
    assert len(body["regressions"]) == 1
    assert len(body["improvements"]) == 1
    assert body["regressions"][0]["row_id"] is not None


async def test_compare_missing_run(client):
    r = await client.get("/runs/compare?run_a=9999&run_b=8888")
    assert r.status_code == 404


async def test_compare_safe_to_ship_summary(client, db_engine):
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)
    run_a_id, run_b_id = await _make_two_runs(db_engine, ds_id, av_id, sc_id)

    body = (await client.get(f"/runs/compare?run_a={run_a_id}&run_b={run_b_id}")).json()
    # run_b has a regression → NOT safe to ship
    assert body["safe_to_ship"] is False
    assert "regression" in body["summary"].lower() or "NOT safe" in body["summary"]


# ── Benchmark endpoint ────────────────────────────────────────────────────────

async def _make_benchmark_runs(db_engine, ds_id, av_id, sc_id):
    """3 runs on the same dataset with pass rates 0.8, 0.9, 0.4 (run3 = regression)."""
    SM = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    import sqlalchemy as sa
    async with SM() as s:
        now = datetime.now(timezone.utc)
        run_ids = []
        for i, (pr, delta_days) in enumerate([(0.8, 6), (0.9, 4), (0.4, 2)]):
            run = EvalRun(
                dataset_id=ds_id, app_version_id=av_id,
                status="completed", scorer_ids=[sc_id],
                created_at=now - timedelta(days=delta_days),
                completed_at=now - timedelta(days=delta_days) + timedelta(minutes=5),
            )
            s.add(run)
            await s.flush()
            s.add(AggregateMetrics(run_id=run.id, scorer_id=sc_id, avg_score=pr, pass_rate=pr, p95_latency=400.0, total_cost=0.001))
            run_ids.append(run.id)
        await s.commit()
        return run_ids


async def test_benchmark_returns_sorted_points(client, db_engine):
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)
    run_ids = await _make_benchmark_runs(db_engine, ds_id, av_id, sc_id)

    r = await client.get(f"/runs/benchmark?dataset_id={ds_id}")
    assert r.status_code == 200
    points = r.json()
    assert len(points) == 3
    # Should be sorted oldest→newest
    dates = [p["created_at"] for p in points]
    assert dates == sorted(dates)


async def test_benchmark_detects_regression(client, db_engine):
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)
    await _make_benchmark_runs(db_engine, ds_id, av_id, sc_id)

    points = (await client.get(f"/runs/benchmark?dataset_id={ds_id}")).json()
    # run3 (pass_rate=0.4) is a regression from run2 (pass_rate=0.9)
    regression_flags = [p["has_regression"] for p in points]
    assert regression_flags[0] is False   # first run — no previous to compare
    assert regression_flags[1] is False   # 0.9 > 0.8 — improvement
    assert regression_flags[2] is True    # 0.4 << 0.9 — regression


async def test_benchmark_empty_dataset(client):
    ds_id = (await client.post("/datasets", json={"name": "Empty DS"})).json()["id"]
    r = await client.get(f"/runs/benchmark?dataset_id={ds_id}")
    assert r.status_code == 200
    assert r.json() == []


# ── Delete run ────────────────────────────────────────────────────────────────

@patch("app.routers.eval_runs._celery_client")
async def test_delete_run(mock_celery, client):
    mock_celery.return_value = MagicMock(send_task=MagicMock(return_value=MagicMock(id="t")))
    ds_id = await _create_dataset(client)
    av_id = await _create_app_version(client)
    sc_id = await _create_scorer(client)

    run_id = (await client.post("/runs", json={
        "dataset_id": ds_id, "app_version_id": av_id, "scorer_ids": [sc_id],
    })).json()["id"]

    r = await client.delete(f"/runs/{run_id}")
    assert r.status_code == 204
    assert (await client.get(f"/runs/{run_id}")).status_code == 404
