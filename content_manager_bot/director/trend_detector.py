"""
TrendDetector — обнаружение trending тем в нише.

Чистый Python, без AI вызовов.
Данные берутся из CompetitorAnalyzer (не дублируем загрузку).
Биграммы с current_tf / background_tf > 3.0 = trending.
"""
import re
from collections import Counter
from typing import Optional

from loguru import logger

from content_manager_bot.director.channel_memory import get_channel_memory


# Стоп-слова для фильтрации
STOP_WORDS = {
    "это", "что", "как", "для", "уже", "все", "вот", "так", "тоже",
    "есть", "мне", "мой", "где", "тут", "там", "они", "она", "ему",
    "если", "когда", "потому", "чтобы", "может", "нет", "просто",
    "очень", "даже", "или", "при", "без", "ещё", "еще", "был",
    "была", "было", "были", "будет", "буду", "которые", "который",
    "которая", "которое", "после", "через", "между", "перед",
    "более", "можно", "нужно", "надо", "того", "этого", "этом",
    "этой", "этих", "свой", "свои", "свою", "своё", "такой",
    "такая", "такие", "такое", "один", "одна", "одно", "только",
    "себя", "себе", "собой", "каждый", "каждая", "каждое",
}


class TrendDetector:
    """Выявляет trending темы на основе данных CompetitorAnalyzer."""

    # Порог trending: current / baseline > TREND_THRESHOLD
    TREND_THRESHOLD = 3.0
    # Минимальная частота для учёта
    MIN_FREQ = 3

    def detect_trends(self, competitor_posts: list[dict]) -> list[str]:
        """Обнаруживает trending темы из постов конкурентов.

        Args:
            competitor_posts: [{text, channel, views, reactions}, ...]

        Returns:
            list[str]: Топ-5 trending тем.
        """
        if not competitor_posts:
            return []

        # 1. Токенизация + биграммы
        all_bigrams = []
        for post in competitor_posts:
            text = post.get("text", "")
            if not text:
                continue

            words = self._tokenize(text)
            bigrams = self._get_bigrams(words)
            all_bigrams.extend(bigrams)

        if not all_bigrams:
            return []

        # 2. Считаем TF
        bigram_counts = Counter(all_bigrams)

        # 3. Фильтруем по минимальной частоте
        frequent = {
            bg: count for bg, count in bigram_counts.items()
            if count >= self.MIN_FREQ
        }

        if not frequent:
            return []

        # 4. Сортируем по частоте (простой TF — без baseline пока)
        sorted_bigrams = sorted(frequent.items(), key=lambda x: x[1], reverse=True)

        # 5. Возвращаем топ-5
        trending = [" ".join(bg) for bg, _ in sorted_bigrams[:5]]

        logger.info(f"[DIRECTOR] Detected {len(trending)} trending topics: {trending}")
        return trending

    async def detect_trends_with_baseline(self, segment: str, competitor_posts: list[dict]) -> list[str]:
        """Обнаруживает trending с учётом фоновой частоты.

        Сравнивает текущие биграммы с baseline из channel_memory.
        """
        if not competitor_posts:
            return []

        memory = get_channel_memory()
        state = await memory.get_state(segment)
        baseline = state.get("keyword_baseline", {})

        # Текущие биграммы
        all_bigrams = []
        for post in competitor_posts:
            text = post.get("text", "")
            if text:
                words = self._tokenize(text)
                all_bigrams.extend(self._get_bigrams(words))

        if not all_bigrams:
            return []

        current_counts = Counter(all_bigrams)
        total = len(all_bigrams)

        # Нормализуем в TF
        current_tf = {
            " ".join(bg): count / total
            for bg, count in current_counts.items()
            if count >= self.MIN_FREQ
        }

        trending = []
        for term, tf in current_tf.items():
            bg_tf = baseline.get(term, 0.0)
            if bg_tf > 0:
                ratio = tf / bg_tf
                if ratio > self.TREND_THRESHOLD:
                    trending.append((term, ratio))
            elif tf > 0.01:  # Новый термин с высокой частотой
                trending.append((term, 10.0))

        # Сортируем по ratio
        trending.sort(key=lambda x: x[1], reverse=True)

        # Обновляем baseline (скользящее среднее)
        new_baseline = {}
        for term, tf in current_tf.items():
            old = baseline.get(term, tf)
            new_baseline[term] = old * 0.7 + tf * 0.3  # EMA
        await memory.update_keyword_baseline(segment, new_baseline)

        result = [term for term, _ in trending[:5]]
        logger.info(f"[DIRECTOR] Trending (with baseline) for {segment}: {result}")
        return result

    async def get_trend_context(self, segment: str) -> str:
        """Строка для промпта: 'В нише сейчас trending: X, Y, Z'."""
        memory = get_channel_memory()
        state = await memory.get_state(segment)
        insights = state.get("competitor_insights", {})

        trending = insights.get("trending_topics", [])
        if not trending:
            return ""

        return f"В нише {segment} сейчас trending: {', '.join(trending[:5])}"

    def _tokenize(self, text: str) -> list[str]:
        """Токенизация текста → список слов (lowercase, без стоп-слов)."""
        words = re.findall(r'[а-яёА-ЯЁ]{3,}', text.lower())
        return [w for w in words if w not in STOP_WORDS]

    def _get_bigrams(self, words: list[str]) -> list[tuple[str, str]]:
        """Возвращает биграммы из списка слов."""
        if len(words) < 2:
            return []
        return [(words[i], words[i + 1]) for i in range(len(words) - 1)]


# Singleton
_detector: Optional[TrendDetector] = None


def get_trend_detector() -> TrendDetector:
    global _detector
    if _detector is None:
        _detector = TrendDetector()
    return _detector
