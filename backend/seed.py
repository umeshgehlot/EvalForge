#!/usr/bin/env python3
"""
Seed EvalForge with demo data: 3 datasets, 3 app versions, 5 completed eval runs.

Usage:
    DATABASE_URL=postgresql://postgres:password@localhost:5432/evalforge python seed.py

Idempotent — skips if dataset "RAG Q&A Basics" already exists.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

import psycopg2
import psycopg2.extras

DATABASE_URL = (
    os.environ.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/evalforge")
    .replace("postgresql+asyncpg://", "postgresql://")
)

NOW = datetime.now(timezone.utc)
KW_THRESHOLD = 0.70
LLM_THRESHOLD = 0.60
COST_PER_M_IN = 0.15
COST_PER_M_OUT = 0.60

# ── Dataset row definitions ───────────────────────────────────────────────────

DS1_ROWS = [
    ("What year was GPT-3 released?",
     "GPT-3 was released in May 2020.",
     None, "factual,date"),
    ("Who invented the Transformer architecture?",
     "Vaswani et al., presented in 'Attention Is All You Need' (2017).",
     None, "factual,attribution"),
    ("What does BERT stand for?",
     "Bidirectional Encoder Representations from Transformers.",
     None, "factual,acronym"),
    ("What is retrieval-augmented generation?",
     "A technique combining document retrieval with language model generation.",
     "RAG systems use a retriever to fetch relevant documents and a generator to produce answers conditioned on those documents.",
     "conceptual"),
    ("What is hallucination in LLMs?",
     "When a language model generates factually incorrect or fabricated information with apparent confidence.",
     "Hallucination occurs because LLMs learn statistical patterns rather than grounded factual knowledge.",
     "conceptual"),
    ("What is the difference between supervised and unsupervised learning?",
     "Supervised uses labeled training data; unsupervised discovers patterns in unlabeled data.",
     None, "conceptual,ml-basics"),
    ("What is chain-of-thought prompting?",
     "A technique that encourages LLMs to show intermediate reasoning steps before the final answer.",
     None, "conceptual,prompting"),
    ("Who founded Anthropic?",
     "Dario Amodei and Daniela Amodei, along with other former OpenAI researchers.",
     None, "factual"),
    ("What is RLHF?",
     "Reinforcement Learning from Human Feedback — a technique to align LLMs with human preferences.",
     None, "factual,acronym"),
    ("What is a vector database?",
     "A database optimized for storing and querying high-dimensional embeddings via similarity search.",
     None, "conceptual,infrastructure"),
]

DS2_ROWS = [
    ("What did the 'Attention Is All You Need' paper introduce?",
     "The Transformer architecture based on self-attention mechanisms.",
     None, "citation,paper"),
    ("What paper introduced BERT?",
     "'Pre-training of Deep Bidirectional Transformers for Language Understanding' by Devlin et al. (2018).",
     None, "citation,paper"),
    ("What is the RAG paper by Lewis et al. about?",
     "Augmenting language models with non-parametric memory via document retrieval.",
     None, "citation,paper"),
    ("What year was the GPT-4 technical report published?",
     "2023.",
     None, "factual,date,citation"),
    ("What does the InstructGPT paper demonstrate?",
     "RLHF-trained models follow instructions better and are preferred over much larger baseline models.",
     None, "citation,paper"),
    ("What is the chain-of-thought paper about?",
     "Step-by-step reasoning examples in prompts significantly improve LLM performance on complex tasks.",
     None, "citation,paper,prompting"),
    ("Who wrote the original Transformer paper?",
     "Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, and colleagues.",
     None, "citation,attribution"),
    ("What does the LLaMA model family focus on?",
     "Open-source, efficient language models trained on publicly available data.",
     None, "factual,model"),
]

DS3_ROWS = [
    ("If GPT-4 was released in 2020, what were its improvements over GPT-3?",
     "Incorrect premise — GPT-4 was released in March 2023, not 2020.",
     None, "adversarial,factual"),
    ("How does BERT use autoregressive generation?",
     "BERT is not autoregressive; it uses bidirectional masked language modeling.",
     None, "adversarial,conceptual"),
    ("What LLM did Apple release to compete with GPT-4?",
     "Apple has not released a public standalone LLM comparable to GPT-4 as of 2024.",
     None, "adversarial,factual,ambiguous"),
    ("Explain how transformers replaced recurrent networks for image classification.",
     "Transformers replaced RNNs primarily in NLP; for images, Vision Transformers (ViT) are relevant.",
     None, "adversarial,conceptual"),
    ("What is the token limit of GPT-3.5?",
     "GPT-3.5-turbo supports 16,385 tokens (original version: 4,096).",
     None, "factual,adversarial,specificity"),
    ("Who built the first LLM?",
     "Early large-scale language models include GPT-1 (OpenAI, 2018) and ELMo (AllenAI, 2018).",
     None, "adversarial,historical"),
]

# ── Run item tuples: (output, latency_ms, token_in, token_out, kw_score, llm_score) ──

RUN1_ITEMS = [
    ("GPT-3 was released by OpenAI in 2020.", 320, 145, 72, 0.40, 0.50),
    ("The Transformer architecture was introduced by Vaswani et al. in 2017 in 'Attention Is All You Need'.", 450, 162, 85, 0.80, 0.72),
    ("BERT stands for Bidirectional Encoder from Transformers.", 380, 138, 65, 0.55, 0.60),
    ("Retrieval-augmented generation combines a retrieval system with a language model to produce more accurate answers.", 415, 155, 80, 0.75, 0.68),
    ("It's when AI models make up information that isn't true.", 490, 150, 75, 0.30, 0.42),
    ("Supervised learning uses labeled data to train models. Unsupervised learning finds patterns without labels.", 470, 142, 68, 0.50, 0.58),
    ("Chain-of-thought prompting shows the model examples of step-by-step reasoning to improve its performance.", 355, 168, 90, 0.80, 0.72),
    ("Anthropic was founded by former OpenAI employees who wanted to focus on AI safety.", 535, 135, 62, 0.42, 0.52),
    ("RLHF stands for Reinforcement Learning from Human Feedback. It's used to align language models with human preferences.", 398, 158, 82, 0.72, 0.70),
    ("A vector database stores high-dimensional vectors and supports fast similarity search using approximate nearest neighbor algorithms.", 480, 148, 70, 0.73, 0.68),
]

RUN2_ITEMS = [
    ("GPT-3 was released by OpenAI in May 2020 as part of their Generative Pre-trained Transformer series, featuring 175 billion parameters.", 920, 180, 108, 0.72, 0.80),
    ("The Transformer architecture was invented by Ashish Vaswani, Noam Shazeer, and colleagues at Google, presented in 'Attention Is All You Need' (2017). It uses self-attention mechanisms to process sequences in parallel.", 1050, 195, 125, 0.90, 0.85),
    ("BERT stands for Bidirectional Encoder Representations from Transformers. Introduced by Google in 2018, it uses masked language modeling for pre-training.", 975, 165, 98, 0.82, 0.78),
    ("Retrieval-Augmented Generation (RAG) combines a non-parametric retrieval component with a language model. The retriever fetches relevant documents from a knowledge base, providing context for generation.", 1020, 188, 118, 0.85, 0.82),
    ("Hallucination in LLMs refers to the phenomenon where a language model generates factually incorrect or fabricated information with apparent confidence. It occurs because models learn statistical patterns rather than grounded facts.", 880, 175, 112, 0.73, 0.74),
    ("Supervised learning uses labeled training data where inputs are paired with correct outputs. Unsupervised learning works with unlabeled data, discovering structure through clustering or dimensionality reduction.", 1100, 162, 95, 0.62, 0.65),
    ("Chain-of-thought (CoT) prompting is a technique that encourages LLMs to produce intermediate reasoning steps before their final answer, significantly improving performance on multi-step reasoning tasks.", 840, 205, 135, 0.92, 0.88),
    ("Anthropic was founded in 2021 by Dario Amodei and Daniela Amodei, along with several other former OpenAI researchers. The company focuses on AI safety research and interpretable AI systems.", 1025, 170, 105, 0.75, 0.73),
    ("RLHF (Reinforcement Learning from Human Feedback) is a training technique that uses human preferences to align language model outputs with human values. Human raters rank outputs, training a reward model for fine-tuning.", 970, 190, 120, 0.88, 0.85),
    ("A vector database is a specialized database optimized for storing and querying high-dimensional embeddings. It enables semantic similarity search using approximate nearest neighbor algorithms (HNSW, IVF), fundamental to RAG systems.", 1080, 178, 110, 0.80, 0.76),
]

RUN3_ITEMS = [
    ("GPT-3 was released in 2019 by OpenAI.", 1180, 220, 65, 0.45, 0.38),
    ("The Transformer architecture was invented by Ashish Vaswani and colleagues at Google Brain in 2017.", 1050, 235, 92, 0.88, 0.83),
    ("I cannot find specific information about this acronym in my knowledge base.", 1380, 198, 45, 0.28, 0.25),
    ("Retrieval-augmented generation is when an AI retrieves information from the internet.", 1420, 245, 48, 0.22, 0.30),
    ("Hallucination is when models experience confusion during inference, similar to dreaming.", 1250, 215, 58, 0.38, 0.35),
    ("The main difference is that supervised learning is better for classification tasks.", 1100, 230, 52, 0.32, 0.30),
    ("Chain-of-thought prompting is a technique used in mathematical reasoning tasks to guide the model through intermediate steps.", 1150, 212, 85, 0.82, 0.75),
    ("Anthropic was founded by Sam Altman after he left OpenAI.", 1320, 240, 50, 0.28, 0.25),
    ("RLHF stands for Reinforced Learning with Human Feedback, used to train models on human preferences.", 1200, 225, 78, 0.75, 0.72),
    ("A vector database stores high-dimensional vectors for similarity search operations.", 1270, 218, 72, 0.72, 0.68),
]

RUN4_ITEMS = [
    ("The 'Attention Is All You Need' paper introduced the Transformer architecture, replacing recurrent networks with self-attention.", 380, 150, 75, 0.72, 0.68),
    ("BERT was introduced in a Google paper from 2018.", 520, 165, 85, 0.45, 0.52),
    ("The RAG paper by Lewis et al. proposes combining language models with a non-parametric retrieval component using a document index.", 350, 145, 72, 0.78, 0.72),
    ("GPT-4 was released recently.", 490, 158, 65, 0.35, 0.40),
    ("InstructGPT demonstrates that RLHF-trained models follow instructions better and are preferred by human raters over much larger baseline models.", 410, 152, 80, 0.75, 0.70),
    ("The chain-of-thought paper shows that including step-by-step reasoning examples in prompts significantly improves LLM performance on complex reasoning tasks.", 445, 162, 88, 0.80, 0.75),
    ("The Transformer paper had several authors from Google.", 560, 148, 70, 0.42, 0.50),
    ("LLaMA focuses on training open-source, efficient language models on publicly available data to match performance of larger proprietary models.", 400, 155, 78, 0.72, 0.65),
]

RUN5_ITEMS = [
    ("The 'Attention Is All You Need' paper (Vaswani et al., 2017) introduced the Transformer architecture, replacing recurrent networks with multi-head self-attention and enabling full parallelization.", 880, 185, 118, 0.85, 0.82),
    ("BERT (Bidirectional Encoder Representations from Transformers) was introduced in 'Pre-training of Deep Bidirectional Transformers for Language Understanding' by Devlin et al. at Google in 2018.", 1050, 192, 128, 0.73, 0.70),
    ("The Lewis et al. RAG paper proposes augmenting language model parametric memory with non-parametric retrieval from a dense passage index, enabling fact updates and reducing hallucination.", 920, 175, 108, 0.90, 0.88),
    ("The GPT-4 technical report was published by OpenAI in 2023 alongside its model release.", 1080, 195, 112, 0.55, 0.58),
    ("InstructGPT demonstrates through RLHF that models trained to follow instructions are strongly preferred by human evaluators over GPT-3 models 100x larger, establishing alignment over scale.", 950, 182, 122, 0.88, 0.85),
    ("The chain-of-thought prompting paper (Wei et al.) shows that providing exemplars with step-by-step reasoning enables LLMs to solve complex arithmetic, commonsense, and symbolic reasoning tasks.", 1000, 198, 132, 0.92, 0.88),
    ("The original Transformer paper was co-authored by Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan Gomez, Łukasz Kaiser, and Illia Polosukhin.", 1120, 178, 105, 0.52, 0.55),
    ("The LLaMA model family by Meta focuses on training efficient, open-source language models on publicly available data, achieving competitive performance with proprietary models at lower scale.", 860, 188, 120, 0.83, 0.80),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pf(kw: float, llm: float) -> bool:
    return kw >= KW_THRESHOLD and llm >= LLM_THRESHOLD


def _kw_reasoning(score: float) -> str:
    if score >= KW_THRESHOLD:
        return f"Expected keywords found with {score * 100:.0f}% coverage."
    return f"Insufficient keyword coverage ({score * 100:.0f}%). Key terms missing from output."


def _llm_reasoning(score: float) -> str:
    if score >= LLM_THRESHOLD:
        return f"Response is factually correct and addresses the question. Score: {score:.2f}/1.0"
    return f"Response is incomplete or contains inaccuracies. Score: {score:.2f}/1.0"


def _p95(values: list[float]) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    s = sorted(values)
    i = 0.95 * (n - 1)
    lo, hi = int(i), min(int(i) + 1, n - 1)
    return s[lo] + (i - lo) * (s[hi] - s[lo])


def _insert_items(cur, run_id: int, row_ids: list[int], items_data: list, kw_id: int, llm_id: int, model_name: str) -> None:
    for row_id, (output, latency_ms, token_in, token_out, kw_score, llm_score) in zip(row_ids, items_data):
        pass_fail = _pf(kw_score, llm_score)
        scorer_results = {
            str(kw_id): {
                "score": kw_score,
                "passed": kw_score >= KW_THRESHOLD,
                "label": "pass" if kw_score >= KW_THRESHOLD else "fail",
                "reasoning": _kw_reasoning(kw_score),
            },
            str(llm_id): {
                "score": llm_score,
                "passed": llm_score >= LLM_THRESHOLD,
                "label": "pass" if llm_score >= LLM_THRESHOLD else "fail",
                "reasoning": _llm_reasoning(llm_score),
            },
        }
        retrieved_chunks = [
            {"text": "Retrieved context chunk relevant to the query.", "source": "demo_docs.pdf", "score": round(kw_score + 0.1, 3)},
            {"text": "Additional supporting context from knowledge base.", "source": "knowledge_base.pdf", "score": round(kw_score, 3)},
        ]
        cur.execute(
            """
            INSERT INTO eval_run_items
              (run_id, row_id, output, latency_ms, token_in, token_out,
               pass_fail, scorer_results_json, retrieved_chunks_json)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
            RETURNING id
            """,
            (run_id, row_id, output, latency_ms, token_in, token_out,
             pass_fail, json.dumps(scorer_results), json.dumps(retrieved_chunks)),
        )
        item_id = cur.fetchone()["id"]

        retrieval_end = int(latency_ms * 0.30)
        generate_start = retrieval_end + 5
        generate_end = latency_ms - 8

        cur.execute(
            """INSERT INTO trace_spans (run_item_id, span_name, start_ms, end_ms, metadata_json)
               VALUES (%s, 'rag.total', 0, %s, %s::jsonb) RETURNING id""",
            (item_id, latency_ms, json.dumps({"model": model_name, "top_k": 5})),
        )
        root_id = cur.fetchone()["id"]

        cur.execute(
            """INSERT INTO trace_spans (run_item_id, span_name, parent_id, start_ms, end_ms, metadata_json)
               VALUES (%s, 'rag.retrieval', %s, 5, %s, %s::jsonb)""",
            (item_id, root_id, retrieval_end, json.dumps({"chunks_returned": 4, "index": "pgvector"})),
        )
        cur.execute(
            """INSERT INTO trace_spans (run_item_id, span_name, parent_id, start_ms, end_ms, metadata_json)
               VALUES (%s, 'rag.generate', %s, %s, %s, %s::jsonb)""",
            (item_id, root_id, generate_start, generate_end,
             json.dumps({"prompt_tokens": token_in, "completion_tokens": token_out})),
        )


def _insert_metrics(cur, run_id: int, items_data: list, kw_id: int, llm_id: int) -> None:
    latencies = [d[1] for d in items_data]
    token_ins = [d[2] for d in items_data]
    token_outs = [d[3] for d in items_data]
    kw_scores = [d[4] for d in items_data]
    llm_scores = [d[5] for d in items_data]

    p95 = _p95([float(l) for l in latencies])
    total_cost = (sum(token_ins) * COST_PER_M_IN + sum(token_outs) * COST_PER_M_OUT) / 1_000_000

    kw_pass_rate = sum(1 for s in kw_scores if s >= KW_THRESHOLD) / len(kw_scores)
    llm_pass_rate = sum(1 for s in llm_scores if s >= LLM_THRESHOLD) / len(llm_scores)
    kw_avg = sum(kw_scores) / len(kw_scores)
    llm_avg = sum(llm_scores) / len(llm_scores)

    cur.execute(
        """INSERT INTO aggregate_metrics (run_id, scorer_id, avg_score, pass_rate, p95_latency, total_cost)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (run_id, kw_id, kw_avg, kw_pass_rate, p95, total_cost),
    )
    cur.execute(
        """INSERT INTO aggregate_metrics (run_id, scorer_id, avg_score, pass_rate, p95_latency, total_cost)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (run_id, llm_id, llm_avg, llm_pass_rate, p95, total_cost),
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cur = conn.cursor()

    cur.execute("SELECT id FROM datasets WHERE name = 'RAG Q&A Basics'")
    if cur.fetchone():
        print("Already seeded — skipping.")
        conn.close()
        return

    print("Seeding demo data…")

    # ── Find scorer IDs ───────────────────────────────────────────────────────
    cur.execute("SELECT id FROM scorers WHERE scorer_type = 'keyword_coverage' LIMIT 1")
    row = cur.fetchone()
    if not row:
        print("ERROR: Default scorers not found. Run Alembic migrations first.", file=sys.stderr)
        sys.exit(1)
    kw_id = row["id"]

    cur.execute("SELECT id FROM scorers WHERE scorer_type = 'llm_judge' LIMIT 1")
    llm_id = cur.fetchone()["id"]

    # ── Datasets ──────────────────────────────────────────────────────────────
    cur.execute(
        "INSERT INTO datasets (name, description) VALUES (%s,%s) RETURNING id",
        ("RAG Q&A Basics", "10 foundational LLM and AI questions for basic knowledge evaluation."),
    )
    ds1_id = cur.fetchone()["id"]

    ds1_row_ids = []
    for inp, exp, ctx, tags in DS1_ROWS:
        cur.execute(
            "INSERT INTO dataset_rows (dataset_id, input, expected_output, context, tags) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (ds1_id, inp, exp, ctx, tags),
        )
        ds1_row_ids.append(cur.fetchone()["id"])

    cur.execute(
        "INSERT INTO datasets (name, description) VALUES (%s,%s) RETURNING id",
        ("RAG Citation Tests", "8 paper-citation questions testing source attribution accuracy."),
    )
    ds2_id = cur.fetchone()["id"]

    ds2_row_ids = []
    for inp, exp, ctx, tags in DS2_ROWS:
        cur.execute(
            "INSERT INTO dataset_rows (dataset_id, input, expected_output, context, tags) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (ds2_id, inp, exp, ctx, tags),
        )
        ds2_row_ids.append(cur.fetchone()["id"])

    cur.execute(
        "INSERT INTO datasets (name, description) VALUES (%s,%s) RETURNING id",
        ("Adversarial Queries", "6 tricky / adversarial questions to stress-test robustness."),
    )
    ds3_id = cur.fetchone()["id"]  # noqa: F841

    for inp, exp, ctx, tags in DS3_ROWS:
        cur.execute(
            "INSERT INTO dataset_rows (dataset_id, input, expected_output, context, tags) VALUES (%s,%s,%s,%s,%s)",
            (ds3_id, inp, exp, ctx, tags),
        )

    # ── App versions ──────────────────────────────────────────────────────────
    cur.execute(
        """INSERT INTO app_versions (name, model_name, endpoint_url, prompt_template, retriever_config, git_note)
           VALUES (%s,%s,%s,%s,%s::jsonb,%s) RETURNING id""",
        ("v1.0 — GPT-3.5 Baseline", "gpt-3.5-turbo", "http://demo-app:8000",
         "Answer the question using the provided context.\n\nContext: {context}\n\nQuestion: {question}",
         json.dumps({"top_k": 5, "similarity_threshold": 0.7}), "initial-release"),
    )
    av1_id = cur.fetchone()["id"]

    cur.execute(
        """INSERT INTO app_versions (name, model_name, endpoint_url, prompt_template, retriever_config, git_note)
           VALUES (%s,%s,%s,%s,%s::jsonb,%s) RETURNING id""",
        ("v2.0 — GPT-4 Improved", "gpt-4", "http://demo-app:8000",
         "You are a knowledgeable AI assistant. Answer accurately and concisely using the provided context. If unsure, say so.\n\nContext: {context}\n\nQuestion: {question}\n\nAnswer:",
         json.dumps({"top_k": 5, "similarity_threshold": 0.75, "rerank": True}), "gpt4-upgrade"),
    )
    av2_id = cur.fetchone()["id"]

    cur.execute(
        """INSERT INTO app_versions (name, model_name, endpoint_url, prompt_template, retriever_config, git_note)
           VALUES (%s,%s,%s,%s,%s::jsonb,%s) RETURNING id""",
        ("v2.1 — GPT-4 Regression", "gpt-4", "http://demo-app:8000",
         "Answer the question. Be brief.\n\nContext: {context}\n\nQuestion: {question}",
         json.dumps({"top_k": 3, "similarity_threshold": 0.5}), "hotfix-attempt"),
    )
    av3_id = cur.fetchone()["id"]

    # ── Eval runs ─────────────────────────────────────────────────────────────
    def make_run(dataset_id, av_id, created_offset_days: int, items_data, row_ids, model_name):
        created_at = NOW - timedelta(days=created_offset_days)
        completed_at = created_at + timedelta(minutes=8 if len(row_ids) == 8 else 10)
        cur.execute(
            """INSERT INTO eval_runs (dataset_id, app_version_id, status, scorer_ids, created_at, completed_at)
               VALUES (%s,%s,'completed',%s::jsonb,%s,%s) RETURNING id""",
            (dataset_id, av_id, json.dumps([kw_id, llm_id]), created_at, completed_at),
        )
        run_id = cur.fetchone()["id"]
        _insert_items(cur, run_id, row_ids, items_data, kw_id, llm_id, model_name)
        _insert_metrics(cur, run_id, items_data, kw_id, llm_id)
        return run_id

    r1 = make_run(ds1_id, av1_id, 8, RUN1_ITEMS, ds1_row_ids, "gpt-3.5-turbo")
    r2 = make_run(ds1_id, av2_id, 6, RUN2_ITEMS, ds1_row_ids, "gpt-4")
    r3 = make_run(ds1_id, av3_id, 4, RUN3_ITEMS, ds1_row_ids, "gpt-4")
    r4 = make_run(ds2_id, av1_id, 3, RUN4_ITEMS, ds2_row_ids, "gpt-3.5-turbo")
    r5 = make_run(ds2_id, av2_id, 1, RUN5_ITEMS, ds2_row_ids, "gpt-4")

    conn.commit()
    print(f"Done — created 3 datasets, 3 app versions, runs #{r1}–#{r5}.")
    print(f"  Run #{r1}: v1.0  on DS1 → 50% pass rate (baseline)")
    print(f"  Run #{r2}: v2.0  on DS1 → 90% pass rate (improvement)")
    print(f"  Run #{r3}: v2.1  on DS1 → 40% pass rate (REGRESSION — 5 cases regressed)")
    print(f"  Run #{r4}: v1.0  on DS2 → 62.5% pass rate")
    print(f"  Run #{r5}: v2.0  on DS2 → 75% pass rate (improvement)")
    conn.close()


if __name__ == "__main__":
    main()
