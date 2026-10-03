from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import List, Optional
from rag import RAGPipeline
import os
from dotenv import load_dotenv

load_dotenv()

_rag: Optional[RAGPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _rag
    _rag = RAGPipeline(
        db_url=os.environ["DATABASE_URL"],
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    )
    yield
    _rag = None


app = FastAPI(title="RAG Demo App — EvalForge", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class ChunkResult(BaseModel):
    text: str
    source: str
    score: Optional[float] = None


class TokenInfo(BaseModel):
    input: int
    output: int


class SpanData(BaseModel):
    span_name: str
    otel_span_id: str
    otel_parent_id: Optional[str] = None
    start_ms: int
    end_ms: int
    metadata: dict = {}


class AskResponse(BaseModel):
    question: str
    answer: str
    retrieved_chunks: List[ChunkResult]
    latency_ms: int
    tokens: TokenInfo
    spans: List[SpanData] = []


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    if _rag is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    result = _rag.ask(request.question, top_k=request.top_k)
    return AskResponse(question=request.question, **result)


@app.get("/health")
async def health():
    return {"status": "ok"}
