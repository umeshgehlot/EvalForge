"""Eval runner — Phase 5 + Phase 6 (OTel trace capture)."""
import json
import os
import time
from datetime import datetime, timezone

import numpy as np
import psycopg2
import psycopg2.extras
import requests

from celery_app import celery_app
from app.scorers.registry import get_scorer

_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:password@postgres:5432/evalforge"
)

# Cost coefficients for gpt-4o-mini (per million tokens)
_COST_PER_M_IN = 0.15
_COST_PER_M_OUT = 0.60


def _conn():
    return psycopg2.connect(_DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def _set_status(cur, run_id: int, status: str) -> None:
    cur.execute("UPDATE eval_runs SET status = %s WHERE id = %s", (status, run_id))


def _insert_spans(cur, item_id: int, spans: list[dict]) -> None:
    """Insert OTel spans for a run item, resolving parent_id from otel IDs."""
    if not spans:
        return

    # Pass 1: insert all spans, collect otel_span_id → db_id mapping
    otel_to_db: dict[str, int] = {}
    for span in spans:
        cur.execute(
            """
            INSERT INTO trace_spans (run_item_id, span_name, start_ms, end_ms, metadata_json)
            VALUES (%s, %s, %s, %s, %s::jsonb)
            RETURNING id
            """,
            (
                item_id,
                span["span_name"],
                span["start_ms"],
                span["end_ms"],
                json.dumps(span.get("metadata", {})),
            ),
        )
        db_id = cur.fetchone()["id"]
        otel_to_db[span["otel_span_id"]] = db_id

    # Pass 2: update parent_id where we have a parent mapping
    for span in spans:
        parent_otel = span.get("otel_parent_id")
        if parent_otel and parent_otel in otel_to_db:
            cur.execute(
                "UPDATE trace_spans SET parent_id = %s WHERE id = %s",
                (otel_to_db[parent_otel], otel_to_db[span["otel_span_id"]]),
            )


@celery_app.task(bind=True, name="tasks.eval_runner.run_eval")
def run_eval(self, run_id: int) -> dict:
    conn = _conn()
    try:
        cur = conn.cursor()

        # ── 1. Load run ──────────────────────────────────────────────────────
        cur.execute(
            "SELECT id, dataset_id, app_version_id, scorer_ids FROM eval_runs WHERE id = %s",
            (run_id,),
        )
        run = cur.fetchone()
        if not run:
            raise ValueError(f"EvalRun {run_id} not found")

        _set_status(cur, run_id, "running")
        conn.commit()

        dataset_id = run["dataset_id"]
        app_version_id = run["app_version_id"]
        scorer_ids: list[int] = run["scorer_ids"] or []

        # ── 2. Load dataset rows ─────────────────────────────────────────────
        cur.execute(
            "SELECT id, input, expected_output, context FROM dataset_rows "
            "WHERE dataset_id = %s ORDER BY id",
            (dataset_id,),
        )
        rows = cur.fetchall()

        # ── 3. Load scorers ──────────────────────────────────────────────────
        if scorer_ids:
            cur.execute(
                "SELECT id, name, scorer_type, config_json FROM scorers WHERE id = ANY(%s)",
                (scorer_ids,),
            )
            scorer_records = cur.fetchall()
        else:
            scorer_records = []

        # ── 4. Load app version endpoint ─────────────────────────────────────
        cur.execute(
            "SELECT endpoint_url FROM app_versions WHERE id = %s",
            (app_version_id,),
        )
        av = cur.fetchone()
        endpoint_url = (av["endpoint_url"] or "http://demo-app:8000").rstrip("/")

        # ── 5. Process each row ───────────────────────────────────────────────
        latencies: list[float] = []
        total_token_in = 0
        total_token_out = 0

        for row in rows:
            t0 = time.time()
            output = ""
            token_in = 0
            token_out = 0
            retrieved_chunks: list[dict] = []
            spans: list[dict] = []

            try:
                resp = requests.post(
                    f"{endpoint_url}/ask",
                    json={"question": row["input"], "top_k": 5},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                output = data.get("answer", "")
                token_in = data.get("tokens", {}).get("input", 0)
                token_out = data.get("tokens", {}).get("output", 0)
                retrieved_chunks = data.get("retrieved_chunks", [])
                spans = data.get("spans", [])
            except Exception as exc:
                output = f"[ERROR: {exc}]"

            latency_ms = int((time.time() - t0) * 1000)
            latencies.append(latency_ms)
            total_token_in += token_in
            total_token_out += token_out

            # Run every scorer
            scorer_results: dict = {}
            all_passed: list[bool] = []

            for sr in scorer_records:
                try:
                    instance = get_scorer(sr["scorer_type"], sr["config_json"] or {})
                    result = instance.score(
                        input=row["input"],
                        output=output,
                        expected=row["expected_output"],
                        context=row["context"],
                        retrieved_chunks=retrieved_chunks,
                    )
                    scorer_results[str(sr["id"])] = {
                        "score": result.score,
                        "passed": result.passed,
                        "label": result.label,
                        "reasoning": result.reasoning,
                    }
                    all_passed.append(result.passed)
                except Exception as exc:
                    scorer_results[str(sr["id"])] = {
                        "score": 0.0,
                        "passed": False,
                        "label": "error",
                        "reasoning": str(exc),
                    }
                    all_passed.append(False)

            pass_fail = all(all_passed) if all_passed else None

            # Insert run item, capture DB id for span association
            cur.execute(
                """
                INSERT INTO eval_run_items
                  (run_id, row_id, output, latency_ms, token_in, token_out,
                   pass_fail, scorer_results_json, retrieved_chunks_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                RETURNING id
                """,
                (
                    run_id,
                    row["id"],
                    output,
                    latency_ms,
                    token_in,
                    token_out,
                    pass_fail,
                    json.dumps(scorer_results),
                    json.dumps(retrieved_chunks),
                ),
            )
            item_id = cur.fetchone()["id"]

            # Insert OTel trace spans
            _insert_spans(cur, item_id, spans)
            conn.commit()

        # ── 6. Aggregate metrics ─────────────────────────────────────────────
        cur.execute(
            "SELECT scorer_results_json, latency_ms FROM eval_run_items WHERE run_id = %s",
            (run_id,),
        )
        items = cur.fetchall()

        p95_latency = float(np.percentile(latencies, 95)) if latencies else None
        total_cost = (
            total_token_in * _COST_PER_M_IN + total_token_out * _COST_PER_M_OUT
        ) / 1_000_000

        for sr in scorer_records:
            sid = str(sr["id"])
            scores = []
            passed_flags = []
            for item in items:
                res_map = item["scorer_results_json"] or {}
                if sid in res_map:
                    scores.append(float(res_map[sid].get("score", 0.0)))
                    passed_flags.append(bool(res_map[sid].get("passed", False)))

            avg_score = sum(scores) / len(scores) if scores else None
            pass_rate = sum(passed_flags) / len(passed_flags) if passed_flags else None

            cur.execute(
                """
                INSERT INTO aggregate_metrics
                  (run_id, scorer_id, avg_score, pass_rate, p95_latency, total_cost)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (run_id, sr["id"], avg_score, pass_rate, p95_latency, total_cost),
            )

        # ── 7. Mark complete ─────────────────────────────────────────────────
        cur.execute(
            "UPDATE eval_runs SET status = 'completed', completed_at = %s WHERE id = %s",
            (datetime.now(timezone.utc), run_id),
        )
        conn.commit()

        return {"run_id": run_id, "items": len(rows)}

    except Exception:
        try:
            conn.rollback()
            cur2 = conn.cursor()
            cur2.execute(
                "UPDATE eval_runs SET status = 'failed' WHERE id = %s", (run_id,)
            )
            conn.commit()
        except Exception:
            pass
        raise
    finally:
        conn.close()
