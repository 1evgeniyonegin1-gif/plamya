"""
Сервис аналитики и генерации отчетов
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from content_manager_bot.database.models import Post, PostAnalytics, PostType

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Сервис для анализа данных и генерации отчетов"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_overall_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Получает общую статистику за период

        Args:
            days: Количество дней для анализа

        Returns:
            Словарь с общими метриками
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Получаем все опубликованные посты за период
        result = await self.session.execute(
            select(Post).where(
                Post.status == "published",
                Post.published_at >= cutoff_date
            )
        )
        posts = result.scalars().all()

        total_posts = len(posts)
        total_views = sum(p.views_count or 0 for p in posts)
        total_reactions = sum(p.reactions_count or 0 for p in posts)
        total_forwards = sum(p.forwards_count or 0 for p in posts)

        avg_views = total_views / total_posts if total_posts > 0 else 0
        avg_reactions = total_reactions / total_posts if total_posts > 0 else 0
        avg_engagement = sum(p.engagement_rate or 0 for p in posts) / total_posts if total_posts > 0 else 0

        return {
            'period_days': days,
            'total_posts': total_posts,
            'total_views': total_views,
            'total_reactions': total_reactions,
            'total_forwards': total_forwards,
            'avg_views_per_post': round(avg_views, 2),
            'avg_reactions_per_post': round(avg_reactions, 2),
            'avg_engagement_rate': round(avg_engagement, 2)
        }

    async def get_stats_by_type(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """
        Получает статистику по типам контента

        Args:
            days: Количество дней для анализа

        Returns:
            Словарь со статистикой по каждому типу
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            select(Post).where(
                Post.status == "published",
                Post.published_at >= cutoff_date
            )
        )
        posts = result.scalars().all()

        stats_by_type = {}

        for post_type in PostType:
            type_posts = [p for p in posts if p.post_type == post_type.value]

            if not type_posts:
                continue

            total_count = len(type_posts)
            total_views = sum(p.views_count or 0 for p in type_posts)
            total_reactions = sum(p.reactions_count or 0 for p in type_posts)
            total_forwards = sum(p.forwards_count or 0 for p in type_posts)

            stats_by_type[post_type.value] = {
                'count': total_count,
                'total_views': total_views,
                'total_reactions': total_reactions,
                'total_forwards': total_forwards,
                'avg_views': round(total_views / total_count, 2),
                'avg_reactions': round(total_reactions / total_count, 2),
                'avg_engagement': round(
                    sum(p.engagement_rate or 0 for p in type_posts) / total_count, 2
                )
            }

        return stats_by_type

    async def get_top_posts(
        self,
        limit: int = 10,
        days: int = 30,
        sort_by: str = 'views'
    ) -> List[Dict[str, Any]]:
        """
        Получает топ постов по заданному критерию

        Args:
            limit: Количество постов
            days: Период для анализа
            sort_by: Критерий сортировки (views, reactions, engagement)

        Returns:
            Список постов с метриками
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            select(Post).where(
                Post.status == "published",
                Post.published_at >= cutoff_date
            )
        )
        posts = result.scalars().all()

        # Сортируем посты
        if sort_by == 'views':
            sorted_posts = sorted(posts, key=lambda p: p.views_count or 0, reverse=True)
        elif sort_by == 'reactions':
            sorted_posts = sorted(posts, key=lambda p: p.reactions_count or 0, reverse=True)
        elif sort_by == 'engagement':
            sorted_posts = sorted(posts, key=lambda p: p.engagement_rate or 0, reverse=True)
        else:
            sorted_posts = posts

        top_posts = []
        for post in sorted_posts[:limit]:
            top_posts.append({
                'id': post.id,
                'type': post.post_type,
                'published_at': post.published_at,
                'views': post.views_count or 0,
                'reactions': post.reactions_count or 0,
                'forwards': post.forwards_count or 0,
                'engagement_rate': post.engagement_rate or 0,
                'content_preview': post.content[:100] + '...' if len(post.content) > 100 else post.content
            })

        return top_posts

    async def get_reactions_distribution(self, days: int = 30) -> Dict[str, int]:
        """
        Получает распределение реакций по типам

        Args:
            days: Период для анализа

        Returns:
            Словарь с количеством каждой реакции
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            select(Post).where(
                Post.status == "published",
                Post.published_at >= cutoff_date,
                Post.reactions_breakdown.isnot(None)
            )
        )
        posts = result.scalars().all()

        all_reactions = {}
        for post in posts:
            if post.reactions_breakdown:
                for emoji, count in post.reactions_breakdown.items():
                    all_reactions[emoji] = all_reactions.get(emoji, 0) + count

        # Сортируем по популярности
        return dict(sorted(all_reactions.items(), key=lambda x: x[1], reverse=True))

    async def format_dashboard(self, days: int = 7) -> str:
        """
        Генерирует текстовый дашборд с основными метриками

        Args:
            days: Период для анализа

        Returns:
            Форматированная строка с дашбордом
        """
        overall = await self.get_overall_stats(days)
        by_type = await self.get_stats_by_type(days)
        top_posts = await self.get_top_posts(limit=5, days=days, sort_by='engagement')

        dashboard = f"""📊 **АНАЛИТИКА КОНТЕНТА** (за {days} дней)

📈 **Общая статистика:**
• Постов: {overall['total_posts']}
• Просмотров: {overall['total_views']:,}
• Реакций: {overall['total_reactions']:,}
• Пересылок: {overall['total_forwards']:,}

📊 **Средние показатели:**
• Просмотров на пост: {overall['avg_views_per_post']:.1f}
• Реакций на пост: {overall['avg_reactions_per_post']:.1f}
• Вовлеченность: {overall['avg_engagement_rate']:.2f}%"""

        if by_type:
            dashboard += "\n\n📑 **По типам контента:**"

            type_names = {
                'product': '🛍️ Продукты',
                'motivation': '💪 Мотивация',
                'news': '📰 Новости',
                'tips': '💡 Советы',
                'success_story': '⭐ Истории успеха',
                'promo': '🎁 Акции'
            }

            for post_type, stats in by_type.items():
                type_name = type_names.get(post_type, post_type)
                dashboard += f"\n\n{type_name}:"
                dashboard += f"\n  • Постов: {stats['count']}"
                dashboard += f"\n  • Ср. просмотров: {stats['avg_views']:.1f}"
                dashboard += f"\n  • Ср. реакций: {stats['avg_reactions']:.1f}"
                dashboard += f"\n  • Вовлеченность: {stats['avg_engagement']:.2f}%"

        if top_posts:
            dashboard += "\n\n🔥 **Топ-5 постов** (по вовлеченности):"
            type_names = {
                'product': '🛍️ Продукты',
                'motivation': '💪 Мотивация',
                'news': '📰 Новости',
                'tips': '💡 Советы',
                'success_story': '⭐ Истории',
                'promo': '🎁 Акции'
            }

            for i, post in enumerate(top_posts, 1):
                dashboard += f"\n\n{i}. [{type_names.get(post['type'], post['type'])}]"
                dashboard += f"\n   👁 {post['views']} | ❤️ {post['reactions']} | 📈 {post['engagement_rate']:.2f}%"
                dashboard += f"\n   \"{post['content_preview']}\""

        return dashboard.strip()
