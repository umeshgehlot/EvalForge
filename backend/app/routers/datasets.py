import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.dataset import Dataset, DatasetRow
from app.schemas.dataset import DatasetCreate, DatasetRead, DatasetRowRead, PaginatedRows

router = APIRouter(prefix="/datasets", tags=["datasets"])


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")  # strip BOM if present
    return list(csv.DictReader(io.StringIO(text)))


def _parse_jsonl(content: bytes) -> list[dict]:
    text = content.decode("utf-8").strip()
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


async def _get_dataset_or_404(dataset_id: int, session: AsyncSession) -> Dataset:
    ds = await session.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds


# ── routes ───────────────────────────────────────────────────────────────────

@router.get("", response_model=list[DatasetRead])
async def list_datasets(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(Dataset, func.count(DatasetRow.id).label("row_count"))
        .outerjoin(DatasetRow)
        .group_by(Dataset.id)
        .order_by(Dataset.created_at.desc())
    )
    return [
        DatasetRead(
            id=ds.id,
            name=ds.name,
            description=ds.description,
            created_at=ds.created_at,
            row_count=count or 0,
        )
        for ds, count in result.all()
    ]


@router.post("", response_model=DatasetRead, status_code=201)
async def create_dataset(
    body: DatasetCreate, session: AsyncSession = Depends(get_async_session)
):
    ds = Dataset(name=body.name, description=body.description)
    session.add(ds)
    await session.commit()
    await session.refresh(ds)
    return DatasetRead(
        id=ds.id,
        name=ds.name,
        description=ds.description,
        created_at=ds.created_at,
        row_count=0,
    )


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset(
    dataset_id: int, session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(Dataset, func.count(DatasetRow.id).label("row_count"))
        .outerjoin(DatasetRow)
        .where(Dataset.id == dataset_id)
        .group_by(Dataset.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    ds, count = row
    return DatasetRead(
        id=ds.id,
        name=ds.name,
        description=ds.description,
        created_at=ds.created_at,
        row_count=count or 0,
    )


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: int, session: AsyncSession = Depends(get_async_session)
):
    ds = await _get_dataset_or_404(dataset_id, session)
    await session.delete(ds)
    await session.commit()


@router.post("/{dataset_id}/rows/upload")
async def upload_rows(
    dataset_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
):
    await _get_dataset_or_404(dataset_id, session)

    content = await file.read()
    filename = file.filename or ""

    if filename.endswith(".json") or filename.endswith(".jsonl"):
        raw_rows = _parse_jsonl(content)
    else:
        raw_rows = _parse_csv(content)

    rows = []
    for r in raw_rows:
        metadata: dict = {}
        if r.get("difficulty"):
            metadata["difficulty"] = r["difficulty"]

        rows.append(
            DatasetRow(
                dataset_id=dataset_id,
                input=r.get("input", "").strip(),
                expected_output=r.get("expected_output") or None,
                context=r.get("context") or None,
                tags=r.get("tags") or None,
                metadata_json=metadata,
            )
        )

    session.add_all(rows)
    await session.commit()
    return {"inserted": len(rows)}


@router.get("/{dataset_id}/rows", response_model=PaginatedRows)
async def list_rows(
    dataset_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    tags: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    await _get_dataset_or_404(dataset_id, session)

    base = select(DatasetRow).where(DatasetRow.dataset_id == dataset_id)
    if tags:
        base = base.where(DatasetRow.tags.ilike(f"%{tags}%"))

    total = (
        await session.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    items = (
        await session.execute(base.offset((page - 1) * limit).limit(limit))
    ).scalars().all()

    return PaginatedRows(total=total, page=page, limit=limit, items=list(items))


@router.delete("/{dataset_id}/rows/{row_id}", status_code=204)
async def delete_row(
    dataset_id: int,
    row_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    row = await session.get(DatasetRow, row_id)
    if not row or row.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Row not found")
    await session.delete(row)
    await session.commit()
