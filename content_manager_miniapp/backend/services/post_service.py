"""
Post service — business logic for content posts.
Reuses ContentGenerator from content_manager_bot.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from content_manager_bot.database.models import Post, AdminAction


async def get_posts(
    db: AsyncSession,
    status: Optional[str] = None,
    post_type: Optional[str] = None,
    segment: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Post], int]:
    """Fetch posts with optional filters. Returns (posts, total_count)."""
    query = select(Post)

    if status:
        query = query.where(Post.status == status)
    if post_type:
        query = query.where(Post.post_type == post_type)
    if segment:
        query = query.where(Post.segment == segment)

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginated results
    query = query.order_by(desc(Post.created_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    posts = list(result.scalars().all())

    return posts, total


async def get_post_by_id(db: AsyncSession, post_id: int) -> Optional[Post]:
    result = await db.execute(select(Post).where(Post.id == post_id))
    return result.scalar_one_or_none()


async def generate_post(
    db: AsyncSession,
    admin_id: int,
    post_type: Optional[str] = None,
    custom_topic: Optional[str] = None,
    segment: Optional[str] = None,
) -> Post:
    """Generate a new post using ContentGenerator."""
    from content_manager_bot.ai.content_generator import ContentGenerator

    generator = ContentGenerator()
    content, prompt_used = await generator.generate_post(
        post_type=post_type or "motivation",
        custom_topic=custom_topic,
        segment=segment,
    )

    post = Post(
        content=content,
        post_type=post_type or "motivation",
        status="pending",
        generated_at=datetime.utcnow(),
        admin_id=admin_id,
        ai_model="deepseek",
        prompt_used=prompt_used,
        segment=segment,
    )
    db.add(post)

    action = AdminAction(
        admin_id=admin_id,
        action="generate",
        details={"post_type": post_type, "custom_topic": custom_topic, "segment": segment},
    )
    db.add(action)

    await db.commit()
    await db.refresh(post)
    return post


async def moderate_post(
    db: AsyncSession,
    post: Post,
    admin_id: int,
    action: str,
    scheduled_at: Optional[datetime] = None,
) -> Post:
    """Apply moderation action to a post. If 'publish', also sends to Telegram."""
    from loguru import logger
    now = datetime.utcnow()

    if action == "publish":
        # Actually send to Telegram channel
        from .telegram_publisher import publish_to_telegram
        try:
            message_id = await publish_to_telegram(
                post_content=post.content,
                post_id=post.id,
                segment=post.segment,
                image_base64=post.image_url,
            )
            post.channel_message_id = message_id
            logger.info(f"[MODERATE] Post #{post.id} published to Telegram, msg_id={message_id}")
        except Exception as e:
            logger.error(f"[MODERATE] Failed to publish post #{post.id} to Telegram: {e}")
            raise ValueError(f"Ошибка публикации в Telegram: {e}")

        post.status = "published"
        post.published_at = now
        post.approved_at = now
        post.admin_id = admin_id

        # Update AI Director channel memory
        try:
            from content_manager_bot.director import get_channel_memory
            memory = get_channel_memory()
            await memory.update_after_publish(
                segment=post.segment or "main",
                post_content=post.content,
                post_type=post.post_type,
                post_id=post.id,
                engagement_rate=post.engagement_rate,
            )
        except Exception as e:
            logger.warning(f"[MODERATE] ChannelMemory update failed: {e}")

    elif action == "reject":
        post.status = "rejected"
        post.admin_id = admin_id

        # Log rejection for AI Director
        try:
            from content_manager_bot.director import get_reflection_engine
            reflection = get_reflection_engine()
            await reflection.on_reject(
                segment=post.segment or "main",
                content=post.content,
                reason="Отклонён через Command Center",
                post_type=post.post_type or "unknown",
            )
        except Exception as e:
            logger.warning(f"[MODERATE] ReflectionEngine error: {e}")

    elif action == "schedule":
        post.status = "scheduled"
        post.scheduled_for = scheduled_at
        post.approved_at = now
        post.admin_id = admin_id
    else:
        raise ValueError(f"Unknown action: {action}")

    log = AdminAction(
        admin_id=admin_id,
        post_id=post.id,
        action=action,
        details={"scheduled_at": scheduled_at.isoformat() if scheduled_at else None},
    )
    db.add(log)
    await db.commit()
    await db.refresh(post)
    return post


async def update_post_content(db: AsyncSession, post: Post, content: str, admin_id: int) -> Post:
    """Manually edit post text."""
    post.content = content
    log = AdminAction(admin_id=admin_id, post_id=post.id, action="edit")
    db.add(log)
    await db.commit()
    await db.refresh(post)
    return post


async def regenerate_post(db: AsyncSession, post: Post, feedback: Optional[str], admin_id: int) -> Post:
    """Regenerate post with optional feedback."""
    from content_manager_bot.ai.content_generator import ContentGenerator

    generator = ContentGenerator()
    new_content = await generator.regenerate_post(
        original_post=post.content,
        feedback=feedback or "Перепиши по-другому",
        post_type=post.post_type,
    )

    post.content = new_content
    post.status = "pending"
    log = AdminAction(admin_id=admin_id, post_id=post.id, action="regenerate", details={"feedback": feedback})
    db.add(log)
    await db.commit()
    await db.refresh(post)
    return post


async def ai_edit_post(db: AsyncSession, post: Post, instructions: str, admin_id: int) -> Post:
    """AI-assisted edit of post content."""
    from content_manager_bot.ai.content_generator import ContentGenerator

    generator = ContentGenerator()
    new_content = await generator.edit_post(
        original_post=post.content,
        edit_instructions=instructions,
        post_type=post.post_type,
    )

    post.content = new_content
    log = AdminAction(admin_id=admin_id, post_id=post.id, action="ai_edit", details={"instructions": instructions})
    db.add(log)
    await db.commit()
    await db.refresh(post)
    return post
