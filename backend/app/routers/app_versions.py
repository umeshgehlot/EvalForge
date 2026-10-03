from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.app_version import AppVersion
from app.schemas.app_version import AppVersionCreate, AppVersionRead

router = APIRouter(prefix="/app-versions", tags=["app-versions"])


@router.get("", response_model=list[AppVersionRead])
async def list_app_versions(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(AppVersion).order_by(AppVersion.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=AppVersionRead, status_code=201)
async def create_app_version(
    body: AppVersionCreate,
    session: AsyncSession = Depends(get_async_session),
):
    av = AppVersion(
        name=body.name,
        model_name=body.model_name,
        endpoint_url=body.endpoint_url,
        prompt_template=body.prompt_template,
        retriever_config=body.retriever_config or {},
        git_note=body.git_note,
    )
    session.add(av)
    await session.commit()
    await session.refresh(av)
    return av


@router.get("/{version_id}", response_model=AppVersionRead)
async def get_app_version(
    version_id: int, session: AsyncSession = Depends(get_async_session)
):
    av = await session.get(AppVersion, version_id)
    if not av:
        raise HTTPException(status_code=404, detail="App version not found")
    return av


@router.delete("/{version_id}", status_code=204)
async def delete_app_version(
    version_id: int, session: AsyncSession = Depends(get_async_session)
):
    av = await session.get(AppVersion, version_id)
    if not av:
        raise HTTPException(status_code=404, detail="App version not found")
    await session.delete(av)
    await session.commit()
