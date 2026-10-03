import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.scorer import Scorer
from app.scorers import get_scorer
from app.scorers.registry import SCORER_REGISTRY
from app.schemas.scorer import (
    ScorerCreate,
    ScorerRead,
    ScorerTestRequest,
    ScorerTestResult,
)

router = APIRouter(prefix="/scorers", tags=["scorers"])


@router.get("", response_model=list[ScorerRead])
async def list_scorers(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Scorer).order_by(Scorer.id))
    return result.scalars().all()


@router.post("", response_model=ScorerRead, status_code=201)
async def create_scorer(
    body: ScorerCreate, session: AsyncSession = Depends(get_async_session)
):
    if body.scorer_type not in SCORER_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scorer_type '{body.scorer_type}'. "
            f"Valid types: {list(SCORER_REGISTRY.keys())}",
        )
    s = Scorer(
        name=body.name,
        scorer_type=body.scorer_type,
        config_json=body.config_json,
        prompt_template=body.prompt_template,
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


@router.get("/{scorer_id}", response_model=ScorerRead)
async def get_scorer_by_id(
    scorer_id: int, session: AsyncSession = Depends(get_async_session)
):
    s = await session.get(Scorer, scorer_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scorer not found")
    return s


@router.delete("/{scorer_id}", status_code=204)
async def delete_scorer(
    scorer_id: int, session: AsyncSession = Depends(get_async_session)
):
    s = await session.get(Scorer, scorer_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scorer not found")
    await session.delete(s)
    await session.commit()


@router.post("/{scorer_id}/test", response_model=ScorerTestResult)
async def test_scorer(
    scorer_id: int,
    body: ScorerTestRequest,
    session: AsyncSession = Depends(get_async_session),
):
    s = await session.get(Scorer, scorer_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scorer not found")

    scorer_instance = get_scorer(s.scorer_type, s.config_json or {})

    # Scorers are synchronous (Celery-compatible); run in thread pool for FastAPI
    result = await asyncio.to_thread(
        scorer_instance.score,
        body.input,
        body.output,
        body.expected,
        body.context,
        body.retrieved_chunks,
    )

    return ScorerTestResult(
        score=result.score,
        passed=result.passed,
        label=result.label,
        reasoning=result.reasoning,
        raw=result.raw,
    )
