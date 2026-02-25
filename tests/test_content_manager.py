"""
Тесты для AI-Контент-Менеджера
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from content_manager_bot.database.models import Post, PostStatus, PostType, ContentSchedule


class TestPostModel:
    """Тесты для модели Post"""
    
    @pytest.mark.asyncio
    async def test_create_post(self, test_session):
        """Тест создания поста"""
        post = Post(
            content="🌟 Новый продукт Energy Diet!\n\nОткройте для себя...",
            post_type="product",
            status="draft",
            ai_model="gigachat"
        )
        test_session.add(post)
        await test_session.commit()
        
        # Проверяем что пост создан
        result = await test_session.execute(
            select(Post).where(Post.post_type == "product")
        )
        saved_post = result.scalar_one()
        
        assert saved_post.content.startswith("🌟 Новый продукт")
        assert saved_post.status == "draft"
        assert saved_post.ai_model == "gigachat"
    
    @pytest.mark.asyncio
    async def test_post_status_change(self, test_session, test_post):
        """Тест изменения статуса поста"""
        # Меняем статус на approved
        test_post.status = "approved"
        test_post.approved_at = datetime.utcnow()
        await test_session.commit()
        
        # Проверяем изменения
        result = await test_session.execute(
            select(Post).where(Post.id == test_post.id)
        )
        updated_post = result.scalar_one()
        
        assert updated_post.status == "approved"
        assert updated_post.approved_at is not None
    
    @pytest.mark.asyncio
    async def test_post_scheduling(self, test_session):
        """Тест планирования поста"""
        scheduled_time = datetime.utcnow() + timedelta(hours=2)
        
        post = Post(
            content="Запланированный пост",
            post_type="motivation",
            status="scheduled",
            scheduled_for=scheduled_time
        )
        test_session.add(post)
        await test_session.commit()
        
        # Проверяем что пост запланирован
        result = await test_session.execute(
            select(Post).where(Post.status == "scheduled")
        )
        scheduled_post = result.scalar_one()
        
        assert scheduled_post.scheduled_for is not None
        assert scheduled_post.scheduled_for > datetime.utcnow()
    
    @pytest.mark.asyncio
    async def test_post_to_telegram_format(self, test_post):
        """Тест форматирования поста для Telegram"""
        formatted = test_post.to_telegram_format()
        
        assert formatted == test_post.content
        assert isinstance(formatted, str)


class TestContentSchedule:
    """Тесты для модели ContentSchedule"""
    
    @pytest.mark.asyncio
    async def test_create_schedule(self, test_session):
        """Тест создания расписания"""
        schedule = ContentSchedule(
            post_type="product",
            cron_expression="0 9 * * *",  # Каждый день в 9:00
            is_active=True
        )
        test_session.add(schedule)
        await test_session.commit()
        
        # Проверяем что расписание создано
        result = await test_session.execute(
            select(ContentSchedule).where(ContentSchedule.post_type == "product")
        )
        saved_schedule = result.scalar_one()
        
        assert saved_schedule.cron_expression == "0 9 * * *"
        assert saved_schedule.is_active is True
        assert saved_schedule.total_generated == 0
    
    @pytest.mark.asyncio
    async def test_schedule_statistics(self, test_session):
        """Тест обновления статистики расписания"""
        schedule = ContentSchedule(
            post_type="motivation",
            cron_expression="0 12 * * *",
            total_generated=5,
            total_published=3
        )
        test_session.add(schedule)
        await test_session.commit()
        
        # Увеличиваем счётчики
        schedule.total_generated += 1
        schedule.total_published += 1
        schedule.last_run = datetime.utcnow()
        await test_session.commit()
        
        # Проверяем обновления
        result = await test_session.execute(
            select(ContentSchedule).where(ContentSchedule.post_type == "motivation")
        )
        updated_schedule = result.scalar_one()
        
        assert updated_schedule.total_generated == 6
        assert updated_schedule.total_published == 4
        assert updated_schedule.last_run is not None


class TestPostFiltering:
    """Тесты для фильтрации постов"""
    
    @pytest.mark.asyncio
    async def test_filter_by_status(self, test_session):
        """Тест фильтрации постов по статусу"""
        # Создаём посты с разными статусами
        statuses = ["draft", "pending", "approved", "published"]
        for status in statuses:
            post = Post(
                content=f"Пост со статусом {status}",
                post_type="news",
                status=status
            )
            test_session.add(post)
        
        await test_session.commit()
        
        # Фильтруем только pending посты
        result = await test_session.execute(
            select(Post).where(Post.status == "pending")
        )
        pending_posts = result.scalars().all()
        
        assert len(pending_posts) == 1
        assert pending_posts[0].status == "pending"
    
    @pytest.mark.asyncio
    async def test_filter_by_type(self, test_session):
        """Тест фильтрации постов по типу"""
        # Создаём посты разных типов
        types = ["product", "motivation", "news"]
        for post_type in types:
            post = Post(
                content=f"Пост типа {post_type}",
                post_type=post_type,
                status="draft"
            )
            test_session.add(post)
        
        await test_session.commit()
        
        # Фильтруем только product посты
        result = await test_session.execute(
            select(Post).where(Post.post_type == "product")
        )
        product_posts = result.scalars().all()
        
        assert len(product_posts) == 1
        assert product_posts[0].post_type == "product"
