"""
Posts API — CRUD, generate, moderate, edit, regenerate.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..api.auth import get_current_user
from ..schemas import (
    PostOut, PostListResponse, GenerateRequest, ModerateRequest,
    EditContentRequest, RegenerateRequest, AiEditRequest, UserInfo,
)
from ..services.post_service import (
    get_posts, get_post_by_id, generate_post,
    moderate_post, update_post_content, regenerate_post, ai_edit_post,
)

router = APIRouter(prefix="/posts", tags=["Posts"])


def _post_to_out(p) -> PostOut:
    return PostOut(
        id=p.id,
        content=p.content,
        post_type=p.post_type,
        status=p.status,
        segment=p.segment,
        views_count=p.views_count or 0,
        reactions_count=p.reactions_count or 0,
        forwards_count=p.forwards_count or 0,
        engagement_rate=p.engagement_rate,
        generated_at=p.generated_at,
        published_at=p.published_at,
        scheduled_for=p.scheduled_for,
        ai_model=p.ai_model,
    )


@router.get("", response_model=PostListResponse)
async def list_posts(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None, alias="type"),
    segment: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    posts, total = await get_posts(db, status=status, post_type=type, segment=segment, limit=limit, offset=offset)
    return PostListResponse(posts=[_post_to_out(p) for p in posts], total=total)


@router.get("/{post_id}", response_model=PostOut)
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    post = await get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return _post_to_out(post)


@router.post("/generate", response_model=PostOut)
async def generate(
    req: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    post = await generate_post(
        db, admin_id=user.telegram_id,
        post_type=req.post_type, custom_topic=req.custom_topic, segment=req.segment,
    )
    return _post_to_out(post)


@router.patch("/{post_id}", response_model=PostOut)
async def moderate(
    post_id: int,
    req: ModerateRequest,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    post = await get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    try:
        post = await moderate_post(db, post, admin_id=user.telegram_id, action=req.action, scheduled_at=req.scheduled_at)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return _post_to_out(post)


@router.patch("/{post_id}/content", response_model=PostOut)
async def edit_content(
    post_id: int,
    req: EditContentRequest,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    post = await get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post = await update_post_content(db, post, content=req.content, admin_id=user.telegram_id)
    return _post_to_out(post)


@router.post("/{post_id}/regenerate", response_model=PostOut)
async def regenerate(
    post_id: int,
    req: RegenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    post = await get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post = await regenerate_post(db, post, feedback=req.feedback, admin_id=user.telegram_id)
    return _post_to_out(post)


@router.post("/{post_id}/ai-edit", response_model=PostOut)
async def ai_edit(
    post_id: int,
    req: AiEditRequest,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    post = await get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post = await ai_edit_post(db, post, instructions=req.instructions, admin_id=user.telegram_id)
    return _post_to_out(post)
