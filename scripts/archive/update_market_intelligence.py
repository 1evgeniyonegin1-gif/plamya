#!/usr/bin/env python3
"""
Скрипт автоматического обновления маркетинговой аналитики.

Запускается раз в день (через cron/systemd timer).
Собирает:
- Новости NL International
- Информацию о конкурентах
- Тренды в нутрициологии и MLM
- Актуальные акции и промо

Добавляет данные в RAG базу знаний с метаданными о свежести.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict
import sys
from pathlib import Path
import aiohttp
from bs4 import BeautifulSoup
import re

# Добавляем корневую директорию в путь для импорта модулей
sys.path.append(str(Path(__file__).parent.parent))

from shared.config.settings import settings
from shared.rag.vector_store import VectorStore

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/market_intelligence.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MarketIntelligenceCollector:
    """Сборщик маркетинговой аналитики"""

    def __init__(self):
        self.vector_store = VectorStore()
        self.today = datetime.now().strftime("%Y-%m-%d")

        # Источники для мониторинга
        self.sources = {
            "nl_official": {
                "name": "NL International официальный сайт",
                "url": "https://nl-international.ru/news/",
                "enabled": True
            },
            "competitors": [
                {
                    "name": "Herbalife Russia",
                    "keywords": ["herbalife", "гербалайф"],
                    "enabled": True
                },
                {
                    "name": "Siberian Wellness",
                    "keywords": ["siberian wellness", "сибирское здоровье"],
                    "enabled": True
                },
                {
                    "name": "Oriflame Wellness",
                    "keywords": ["oriflame wellness", "орифлейм"],
                    "enabled": True
                }
            ],
            "trends": [
                "нутрициология тренды 2026",
                "функциональное питание новости",
                "сетевой маркетинг россия",
                "БАДы исследования"
            ]
        }

    async def collect_all(self) -> Dict[str, List[str]]:
        """
        Собирает все данные из источников

        Returns:
            Dict со списками собранных документов по категориям
        """
        logger.info(f"🚀 Начало сбора маркетинговой аналитики {self.today}")

        results = {
            "nl_news": [],
            "competitor_insights": [],
            "industry_trends": [],
            "errors": []
        }

        try:
            # 1. Новости NL International
            logger.info("📰 Сбор новостей NL International...")
            nl_news = await self._collect_nl_news()
            results["nl_news"] = nl_news

            # 2. Анализ конкурентов
            logger.info("🔍 Анализ конкурентов...")
            competitor_data = await self._collect_competitor_insights()
            results["competitor_insights"] = competitor_data

            # 3. Отраслевые тренды
            logger.info("📊 Сбор трендов индустрии...")
            trends = await self._collect_industry_trends()
            results["industry_trends"] = trends

        except Exception as e:
            logger.error(f"❌ Ошибка при сборе данных: {e}")
            results["errors"].append(str(e))

        return results

    async def _collect_nl_news(self) -> List[str]:
        """Собирает новости с официального сайта NL"""
        news_items = []

        try:
            url = self.sources["nl_official"]["url"]

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status != 200:
                            logger.warning(f"⚠️ Не удалось получить страницу NL: статус {response.status}")
                            return self._get_nl_news_fallback()

                        html = await response.text()
                        soup = BeautifulSoup(html, 'lxml')

                        # Ищем новости на странице
                        news_blocks = soup.find_all(['article', 'div'], class_=re.compile(r'news|article|post', re.I), limit=10)

                        if not news_blocks:
                            news_blocks = soup.find_all(['div'], class_=re.compile(r'item|card|entry', re.I), limit=10)

                        for block in news_blocks:
                            try:
                                title_elem = block.find(['h1', 'h2', 'h3', 'h4', 'a'])
                                title = title_elem.get_text(strip=True) if title_elem else ""

                                text_block = block.get_text(separator=' ', strip=True)
                                if title:
                                    text_block = text_block.replace(title, '', 1)

                                description = text_block[:500].strip() if text_block else ""

                                link_elem = block.find('a', href=True)
                                link = ""
                                if link_elem:
                                    href = link_elem['href']
                                    if href.startswith('/'):
                                        link = f"https://nl-international.ru{href}"
                                    elif href.startswith('http'):
                                        link = href

                                if title and len(title) > 10:
                                    news_doc = f"""
[НОВОСТЬ NL] {self.today}
Заголовок: {title}

{description}

Источник: NL International
URL: {link if link else 'https://nl-international.ru/news/'}
Категория: Новости компании
Актуальность: Высокая
                                    """.strip()

                                    news_items.append(news_doc)

                            except Exception as e:
                                logger.debug(f"Ошибка при обработке блока новости: {e}")
                                continue

                        if not news_items:
                            logger.warning("⚠️ Не удалось извлечь новости из HTML, используем fallback")
                            return self._get_nl_news_fallback()

                except asyncio.TimeoutError:
                    logger.warning("⚠️ Таймаут при загрузке страницы NL, используем fallback")
                    return self._get_nl_news_fallback()
                except aiohttp.ClientError as e:
                    logger.warning(f"⚠️ Ошибка сети при загрузке NL: {e}, используем fallback")
                    return self._get_nl_news_fallback()

        except Exception as e:
            logger.error(f"❌ Ошибка при сборе новостей NL: {e}")
            return self._get_nl_news_fallback()

        logger.info(f"✅ Собрано {len(news_items)} новостей NL")
        return news_items

    def _get_nl_news_fallback(self) -> List[str]:
        """Возвращает fallback данные если парсинг не удался"""
        return [
            f"""
[НОВОСТЬ NL] {self.today}
Источник: Официальный сайт NL International

Примечание: Автоматический сбор новостей временно недоступен.
Рекомендуется проверить официальный сайт nl-international.ru/news/

Категория: Новости компании
Актуальность: Низкая (fallback)
            """.strip()
        ]

    async def _collect_competitor_insights(self) -> List[str]:
        """Собирает информацию о конкурентах"""
        insights = []

        async with aiohttp.ClientSession() as session:
            for competitor in self.sources["competitors"]:
                if not competitor["enabled"]:
                    continue

                try:
                    competitor_name = competitor["name"]
                    keywords = competitor["keywords"]

                    # Формируем поисковый запрос для Яндекс Новостей
                    search_query = "+".join(keywords[:2])  # Берем первые 2 ключевых слова
                    search_url = f"https://yandex.ru/news/search?text={search_query}"

                    try:
                        async with session.get(
                            search_url,
                            timeout=aiohttp.ClientTimeout(total=20),
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                        ) as response:
                            if response.status == 200:
                                html = await response.text()
                                soup = BeautifulSoup(html, 'lxml')

                                # Ищем заголовки новостей
                                news_titles = []
                                for title_elem in soup.find_all(['h2', 'h3', 'a'], limit=5):
                                    title_text = title_elem.get_text(strip=True)
                                    if title_text and len(title_text) > 20:
                                        # Проверяем что в заголовке есть хотя бы одно ключевое слово
                                        if any(kw.lower() in title_text.lower() for kw in keywords):
                                            news_titles.append(title_text)

                                if news_titles:
                                    news_summary = "\n- ".join(news_titles[:3])
                                    insight = f"""
[КОНКУРЕНТ: {competitor_name}] {self.today}

Последние упоминания в новостях:
- {news_summary}

Анализ: Мониторинг активности конкурента в сегменте MLM нутрициологии.
Ключевые слова: {', '.join(keywords)}

Категория: Конкурентная аналитика
Актуальность: Средняя
                                    """.strip()
                                else:
                                    insight = self._get_competitor_fallback(competitor_name, keywords)

                            else:
                                logger.debug(f"Не удалось получить данные о {competitor_name}: статус {response.status}")
                                insight = self._get_competitor_fallback(competitor_name, keywords)

                    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                        logger.debug(f"Ошибка при сборе данных о {competitor_name}: {e}")
                        insight = self._get_competitor_fallback(competitor_name, keywords)

                    insights.append(insight)

                except Exception as e:
                    logger.warning(f"❌ Ошибка при анализе конкурента {competitor.get('name', 'unknown')}: {e}")
                    continue

        logger.info(f"✅ Собрано {len(insights)} инсайтов о конкурентах")
        return insights if insights else [self._get_competitor_fallback("Общий анализ", [])]

    def _get_competitor_fallback(self, competitor_name: str, keywords: List[str]) -> str:
        """Возвращает fallback данные для конкурента"""
        return f"""
[КОНКУРЕНТ: {competitor_name}] {self.today}

Анализ конкурента в сегменте MLM нутрициологии.
Автоматический сбор данных временно недоступен.

Рекомендуется мониторить: {', '.join(keywords) if keywords else 'новости компании'}

Категория: Конкурентная аналитика
Актуальность: Низкая (fallback)
        """.strip()

    async def _collect_industry_trends(self) -> List[str]:
        """Собирает тренды индустрии"""
        trends = []

        async with aiohttp.ClientSession() as session:
            for trend_query in self.sources["trends"]:
                try:
                    # Формируем URL для поиска в Яндекс Новостях
                    search_query = trend_query.replace(" ", "+")
                    search_url = f"https://yandex.ru/news/search?text={search_query}"

                    try:
                        async with session.get(
                            search_url,
                            timeout=aiohttp.ClientTimeout(total=20),
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                        ) as response:
                            if response.status == 200:
                                html = await response.text()
                                soup = BeautifulSoup(html, 'lxml')

                                # Извлекаем заголовки новостей
                                trend_headlines = []
                                for elem in soup.find_all(['h2', 'h3', 'a'], limit=10):
                                    headline = elem.get_text(strip=True)
                                    if headline and len(headline) > 25 and len(headline) < 200:
                                        # Фильтруем релевантные заголовки
                                        query_keywords = trend_query.lower().split()
                                        if any(word in headline.lower() for word in query_keywords[:3]):
                                            trend_headlines.append(headline)

                                if trend_headlines:
                                    # Берем топ-3 заголовка
                                    top_headlines = trend_headlines[:3]
                                    headlines_text = "\n- ".join(top_headlines)

                                    trend = f"""
[ТРЕНД: {trend_query}] {self.today}

Актуальные новости по теме:
- {headlines_text}

Анализ: Мониторинг трендов в нутрициологии и сетевом маркетинге.
Источник: Яндекс Новости

Категория: Отраслевые тренды
Актуальность: Средняя
                                    """.strip()
                                else:
                                    trend = self._get_trend_fallback(trend_query)

                            else:
                                logger.debug(f"Не удалось получить тренды для '{trend_query}': статус {response.status}")
                                trend = self._get_trend_fallback(trend_query)

                    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                        logger.debug(f"Ошибка при сборе трендов для '{trend_query}': {e}")
                        trend = self._get_trend_fallback(trend_query)

                    trends.append(trend)

                except Exception as e:
                    logger.warning(f"❌ Ошибка при сборе тренда '{trend_query}': {e}")
                    trends.append(self._get_trend_fallback(trend_query))
                    continue

        logger.info(f"✅ Собрано {len(trends)} трендов")
        return trends if trends else [self._get_trend_fallback("Общие тренды")]

    def _get_trend_fallback(self, trend_query: str) -> str:
        """Возвращает fallback данные для тренда"""
        return f"""
[ТРЕНД: {trend_query}] {self.today}

Анализ трендов в нутрициологии и сетевом маркетинге.
Автоматический сбор данных временно недоступен.

Рекомендуется отслеживать актуальные публикации по теме: {trend_query}

Категория: Отраслевые тренды
Актуальность: Низкая (fallback)
        """.strip()

    async def save_to_knowledge_base(self, data: Dict[str, List[str]]) -> int:
        """
        Сохраняет собранные данные в RAG базу знаний

        Args:
            data: Словарь с категориями и списками документов

        Returns:
            int: Количество сохраненных документов
        """
        total_saved = 0

        try:
            # Инициализируем RAG если нужно
            await self.vector_store.init_tables()

            logger.info(f"💾 Сохранение данных в RAG базу...")

            # Сохраняем новости NL
            for doc in data.get('nl_news', []):
                doc_id = await self.vector_store.add_document(
                    content=doc,
                    source="NL International",
                    category="market_intelligence_nl_news",
                    metadata={
                        "date": self.today,
                        "type": "nl_news",
                        "relevance": "high",
                        "auto_collected": True
                    }
                )
                if doc_id:
                    total_saved += 1
                    logger.debug(f"✅ Сохранена новость NL (ID: {doc_id})")

            # Сохраняем инсайты конкурентов
            for doc in data.get('competitor_insights', []):
                doc_id = await self.vector_store.add_document(
                    content=doc,
                    source="Competitor Analysis",
                    category="market_intelligence_competitors",
                    metadata={
                        "date": self.today,
                        "type": "competitor_insight",
                        "relevance": "medium",
                        "auto_collected": True
                    }
                )
                if doc_id:
                    total_saved += 1
                    logger.debug(f"✅ Сохранён инсайт конкурента (ID: {doc_id})")

            # Сохраняем тренды
            for doc in data.get('industry_trends', []):
                doc_id = await self.vector_store.add_document(
                    content=doc,
                    source="Industry Trends",
                    category="market_intelligence_trends",
                    metadata={
                        "date": self.today,
                        "type": "industry_trend",
                        "relevance": "medium",
                        "auto_collected": True
                    }
                )
                if doc_id:
                    total_saved += 1
                    logger.debug(f"✅ Сохранён тренд (ID: {doc_id})")

            logger.info(f"✅ Сохранено {total_saved} документов в RAG базу")

        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении в базу знаний: {e}", exc_info=True)

        return total_saved

    async def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Удаляет устаревшие данные из базы знаний

        Args:
            days_to_keep: Сколько дней хранить данные
        """
        from datetime import timedelta
        from sqlalchemy import delete

        logger.info(f"🧹 Очистка данных старше {days_to_keep} дней...")

        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            # Удаляем старые записи market_intelligence
            from shared.rag.vector_store import Document
            from shared.database.base import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                # Ищем документы с категорией market_intelligence старше cutoff_date
                stmt = delete(Document).where(
                    Document.category.like('market_intelligence%')
                ).where(
                    Document.created_at < cutoff_date
                )

                result = await session.execute(stmt)
                await session.commit()

                deleted_count = result.rowcount
                logger.info(f"✅ Удалено {deleted_count} устаревших документов")

        except Exception as e:
            logger.error(f"❌ Ошибка при очистке: {e}", exc_info=True)

    async def generate_summary(self, data: Dict[str, List[str]]) -> str:
        """
        Генерирует краткий отчет о собранных данных

        Args:
            data: Словарь с категориями и списками документов

        Returns:
            str: Текст отчета
        """
        summary = f"""
        📊 ОТЧЕТ О МАРКЕТИНГОВОЙ АНАЛИТИКЕ
        Дата: {self.today}

        ═══════════════════════════════════

        📰 Новости NL International: {len(data.get('nl_news', []))}
        🔍 Инсайты конкурентов: {len(data.get('competitor_insights', []))}
        📊 Отраслевые тренды: {len(data.get('industry_trends', []))}

        ❌ Ошибки: {len(data.get('errors', []))}

        ═══════════════════════════════════

        Всего собрано документов: {sum(len(v) for k, v in data.items() if k != 'errors')}
        """.strip()

        if data.get('errors'):
            summary += "\n\n⚠️ ОШИБКИ:\n"
            for error in data['errors']:
                summary += f"- {error}\n"

        return summary


async def main():
    """Главная функция"""
    try:
        collector = MarketIntelligenceCollector()

        # Собираем данные
        data = await collector.collect_all()

        # Сохраняем в базу знаний
        saved_count = await collector.save_to_knowledge_base(data)

        # Очищаем старые данные
        await collector.cleanup_old_data(days_to_keep=30)

        # Генерируем отчет
        summary = await collector.generate_summary(data)
        logger.info(f"\n{summary}")

        logger.info("✅ Обновление маркетинговой аналитики завершено")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
