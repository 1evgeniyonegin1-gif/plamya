"""
Comment Generator - AI генерация умных комментариев.

Использует YandexGPT для генерации релевантных комментариев
под постами в целевых каналах.
"""

import random
import time
from typing import Dict, List, Optional

import httpx
import jwt
from loguru import logger

from traffic_engine.config import settings


class YandexGPTClient:
    """Клиент для YandexGPT API"""

    def __init__(self):
        self.service_account_id = settings.yandex_service_account_id
        self.key_id = settings.yandex_key_id
        self.private_key = settings.yandex_private_key
        self.folder_id = settings.yandex_folder_id
        self.model = "yandexgpt-32k"
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1"
        self.iam_token = None
        self.token_expires_at = 0

    def _create_jwt_token(self) -> str:
        """Создание JWT токена для получения IAM токена"""
        now = int(time.time())
        payload = {
            'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            'iss': self.service_account_id,
            'iat': now,
            'exp': now + 3600
        }
        return jwt.encode(
            payload,
            self.private_key,
            algorithm='PS256',
            headers={'kid': self.key_id}
        )

    async def _get_iam_token(self, force_refresh: bool = False) -> str:
        """Получение IAM токена через JWT"""
        if self.iam_token and not force_refresh and time.time() < self.token_expires_at:
            return self.iam_token

        try:
            jwt_token = self._create_jwt_token()
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://iam.api.cloud.yandex.net/iam/v1/tokens',
                    json={'jwt': jwt_token}
                )
                response.raise_for_status()
                result = response.json()
                self.iam_token = result['iamToken']
                self.token_expires_at = time.time() + (11 * 3600)
                logger.info("YandexGPT IAM token obtained")
                return self.iam_token
        except Exception as e:
            logger.error(f"Error obtaining IAM token: {e}")
            raise

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.8,
        max_tokens: int = 200
    ) -> Optional[str]:
        """Генерирует текст через YandexGPT"""
        for attempt in range(2):
            try:
                iam_token = await self._get_iam_token(force_refresh=(attempt > 0))

                messages = [
                    {"role": "system", "text": system_prompt},
                    {"role": "user", "text": user_message}
                ]

                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/completion",
                        headers={
                            "Authorization": f"Bearer {iam_token}",
                            "Content-Type": "application/json",
                            "x-folder-id": self.folder_id
                        },
                        json={
                            "modelUri": f"gpt://{self.folder_id}/{self.model}/latest",
                            "completionOptions": {
                                "stream": False,
                                "temperature": temperature,
                                "maxTokens": str(max_tokens)
                            },
                            "messages": messages
                        }
                    )

                    if response.status_code in [401, 403] and attempt == 0:
                        logger.warning("YandexGPT token expired, refreshing...")
                        self.iam_token = None
                        self.token_expires_at = 0
                        continue

                    response.raise_for_status()
                    result = response.json()
                    return result["result"]["alternatives"][0]["message"]["text"]

            except httpx.HTTPStatusError as e:
                if e.response.status_code in [401, 403] and attempt == 0:
                    self.iam_token = None
                    self.token_expires_at = 0
                    continue
                logger.error(f"YandexGPT API error: {e}")
                return None
            except Exception as e:
                logger.error(f"YandexGPT error: {e}")
                return None

        return None


class CommentGenerator:
    """
    AI-генерация умных комментариев в стиле Данила.

    КОНТЕНТ-ЗАВОД: Все аккаунты = Данил, адаптированный под нишу.
    Стиль из реального интервью, не выдуманный.

    Стратегии:
    - smart: Анализ поста и релевантный ответ
    - supportive: Поддерживающий комментарий
    - funny: Уместный юмор
    - expert: Экспертное мнение
    """

    # =============================================
    # БАЗОВЫЙ СТИЛЬ ДАНИЛА (из реального интервью)
    # =============================================
    DANIL_BASE_STYLE = """Ты Данил, 21 год, партнёр NL International. Реальный человек.
Стиль общения:
- Разговорный, прямой, без воды
- Можно с маленькой буквы, без точки
- Сокращения: кст, имхо, хз, норм, оч, чёт
- НЕ пиши "отличный пост", "спасибо автору" — палево
- Можно не согласиться: "ну хз", "сомневаюсь", "а точно?"
- Без эмодзи (максимум 1)
- 1-3 предложения, не больше
- НЕ упоминай NL, продукты или бизнес в комментариях — вообще никогда
- Ты просто человек который шарит в теме и комментирует"""

    # =============================================
    # SEGMENT OVERLAYS — адаптация тона под нишу
    # =============================================
    SEGMENT_OVERLAYS: Dict[str, str] = {
        "zozh": """НИША: ЗОЖ/Питание. Адаптация:
- Экспертный тон про питание, макросы, добавки, энергию
- Можно упомянуть свой опыт с питанием: "я когда начал считать макросы..."
- Мат умеренный (блин, чёрт) — норм
- Вопросы: "а ты какой протеин юзаешь?", "сколько белка в день набираешь?"
- Темы-зацепки: коллаген, протеин, витамины, энергия, сон, вода""",

        "mama": """НИША: Мамы/Здоровье детей. Адаптация:
- Тёплый тон, БЕЗ мата вообще (блин максимум)
- Ссылайся на знакомых: "у знакомой с ребёнком 3 года..."
- Темы: детское питание, энергия для мам, усталость, здоровье семьи
- Сочувствие: "знаю как это бывает", "у всех так"
- НИКАКОГО снисхождения — ты общаешься на равных""",

        "business": """НИША: Бизнес/Доход. Адаптация:
- Деловой-неформальный тон, минимум мата
- Конкретика: цифры, сроки, результаты
- Опыт: "я за полгода выстроил систему..."
- Вопросы про масштабирование, автоматизацию, пассивный доход
- Темы: доп.доход, удалёнка, свобода, автоматизация""",

        "student": """НИША: Студенты/AI/Молодёжь. Адаптация:
- Как оригинальный стиль Данила — мат ок, юмор, мемы
- Темы: AI, нейросети, подработка, бюджет, философия
- Ирония и самоирония: "а потом удивляемся что денег нет"
- Сокращения и сленг по полной""",
    }

    # =============================================
    # СТРАТЕГИИ КОММЕНТИРОВАНИЯ
    # =============================================
    STRATEGY_PROMPTS: Dict[str, str] = {
        "smart": """Накидай коммент к посту — своё мнение, вопрос, или слегка спорное утверждение.
Добавь ПРОВОКАЦИИ или ИРОНИИ — живой коммент, не шаблон.
МОЖНО не согласиться или задать провокационный вопрос.

Пост:
{post_text}

{comments_context}

Коммент (только текст, без кавычек):""",

        "supportive": """Напиши короткую эмоциональную реакцию на пост — что откликнулось.
1-2 коротких предложения или одна фраза. Покажи ЭМОЦИЮ, не будь роботом.

Пост:
{post_text}

{comments_context}

Коммент:""",

        "funny": """Напиши что-то ироничное, саркастичное или с лёгкой провокацией по теме поста.
Юмор в тему, короткая фраза.

Пост:
{post_text}

{comments_context}

Коммент:""",

        "expert": """Добавь от себя полезную инфу или свой опыт по теме поста.
Делись как другу, 2-3 предложения макс. Не умничай.

Пост:
{post_text}

{comments_context}

Коммент:""",
    }

    def __init__(self, tenant_name: str = "nl_international"):
        """Initialize comment generator."""
        self.tenant_name = tenant_name
        self.client = YandexGPTClient()

    async def analyze_post(
        self,
        post_text: str,
        comments: Optional[List[str]] = None,
        channel_title: Optional[str] = None,
        segment: Optional[str] = None,
    ) -> Dict:
        """
        Анализирует пост + комменты перед комментированием.

        Returns:
            Dict с полями: topic, sentiment, relevance, discussion_mood,
            strategy, should_comment, avoid_topics, hook_opportunity
        """
        # Дефолтный результат если AI недоступен
        default_result = {
            "topic": "unknown",
            "sentiment": "neutral",
            "relevance": 0.5,
            "discussion_mood": "neutral",
            "strategy": "smart",
            "should_comment": True,
            "avoid_topics": [],
            "hook_opportunity": None,
        }

        if not post_text or len(post_text.strip()) < 30:
            default_result["should_comment"] = False
            default_result["relevance"] = 0.0
            return default_result

        # Формируем контекст комментариев
        comments_text = ""
        if comments:
            comments_text = "\n".join(f"- {c[:150]}" for c in comments[:15])

        segment_context = f"Аккаунт из сегмента: {segment}" if segment else ""

        prompt = f"""Проанализируй пост из Telegram канала "{channel_title or 'unknown'}".
{segment_context}

ПОСТ:
{post_text[:1000]}

{f'КОММЕНТАРИИ ПОД ПОСТОМ (последние):{chr(10)}{comments_text}' if comments_text else 'Комментариев нет.'}

Ответь СТРОГО в формате (каждое поле на новой строке):
topic: [тема поста в 3-5 словах]
sentiment: [вопрос/жалоба/совет/новость/обсуждение]
relevance: [0.0-1.0 насколько пост релевантен для комментирования по теме здоровья/питания/бизнеса/дохода]
discussion_mood: [friendly/hostile/curious/debate/dead]
strategy: [smart/supportive/funny/expert — лучшая стратегия для этого поста]
should_comment: [true/false — стоит ли комментировать]
avoid_topics: [темы которые уже обсудили в комментах, через запятую, или none]
hook: [зацепка для входа в обсуждение — чей-то вопрос/запрос, или none]"""

        try:
            response = await self.client.generate(
                system_prompt="Ты аналитик контента. Отвечай строго в указанном формате, без лишних слов.",
                user_message=prompt,
                temperature=0.3,
                max_tokens=300,
            )

            if not response:
                return default_result

            return self._parse_analysis(response, default_result)

        except Exception as e:
            logger.error(f"Post analysis failed: {e}")
            return default_result

    def _parse_analysis(self, response: str, default: Dict) -> Dict:
        """Парсит ответ AI в структурированный dict."""
        result = default.copy()

        for line in response.strip().split("\n"):
            line = line.strip()
            if ":" not in line:
                continue

            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()

            if key == "topic":
                result["topic"] = value
            elif key == "sentiment":
                result["sentiment"] = value
            elif key == "relevance":
                try:
                    result["relevance"] = max(0.0, min(1.0, float(value)))
                except ValueError:
                    pass
            elif key == "discussion_mood":
                if value in ("friendly", "hostile", "curious", "debate", "dead"):
                    result["discussion_mood"] = value
            elif key == "strategy":
                if value in ("smart", "supportive", "funny", "expert"):
                    result["strategy"] = value
            elif key == "should_comment":
                result["should_comment"] = value.lower() in ("true", "да", "yes", "1")
            elif key == "avoid_topics":
                if value.lower() not in ("none", "нет", "-"):
                    result["avoid_topics"] = [t.strip() for t in value.split(",") if t.strip()]
            elif key == "hook":
                if value.lower() not in ("none", "нет", "-"):
                    result["hook_opportunity"] = value

        return result

    async def generate(
        self,
        post_text: str,
        strategy: str = "smart",
        channel_title: Optional[str] = None,
        gender: Optional[str] = None,
        segment: Optional[str] = None,
        analysis: Optional[Dict] = None,
        comments: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Генерирует комментарий в стиле Данила с адаптацией под нишу.

        Args:
            post_text: Текст поста
            strategy: Стратегия (smart/supportive/funny/expert)
            channel_title: Название канала
            gender: Пол (для обратной совместимости, у Данила всегда male)
            segment: Сегмент аккаунта (zozh/mama/business/student)
            analysis: Результат analyze_post() если уже есть
            comments: Существующие комменты под постом

        Returns:
            Текст комментария или None
        """
        if not post_text or len(post_text.strip()) < 20:
            logger.warning("Post text too short, skipping")
            return None

        # Используем стратегию из анализа если есть
        if analysis and analysis.get("strategy"):
            strategy = analysis["strategy"]

        base_prompt = self.STRATEGY_PROMPTS.get(strategy, self.STRATEGY_PROMPTS["smart"])

        # Контекст комментариев для промпта
        comments_context = ""
        if comments:
            comments_snippet = "\n".join(f"  - {c[:100]}" for c in comments[:10])
            avoid = ""
            if analysis and analysis.get("avoid_topics"):
                avoid = f"\nНЕ ПОВТОРЯЙ темы: {', '.join(analysis['avoid_topics'])}"
            hook = ""
            if analysis and analysis.get("hook_opportunity"):
                hook = f"\nЗАЦЕПКА: {analysis['hook_opportunity']} — можно ответить на это"
            comments_context = f"Уже есть комменты:\n{comments_snippet}{avoid}{hook}"

        # Segment overlay
        segment_overlay = self.SEGMENT_OVERLAYS.get(segment or "", "")

        system_prompt = f"""{self.DANIL_BASE_STYLE}
{segment_overlay}

ВАЖНО:
- Пиши на русском, как живой человек
- Не упоминай что ты AI или бот
- Комментарий уникальный и в тему поста
- НЕ упоминай NL, продукты, бизнес, заработок — НИКОГДА"""

        user_prompt = base_prompt.format(
            post_text=post_text[:1500],
            comments_context=comments_context,
        )

        try:
            comment = await self.client.generate(
                system_prompt=system_prompt,
                user_message=user_prompt,
                temperature=random.uniform(0.7, 0.9),
                max_tokens=200,
            )

            if comment:
                comment = self._postprocess_comment(comment, segment)
                logger.debug(f"Generated comment ({strategy}, {segment}): {comment[:50]}...")
                return comment

            return None

        except Exception as e:
            logger.error(f"Failed to generate comment: {e}")
            return None

    def _postprocess_comment(self, comment: str, segment: Optional[str] = None) -> str:
        """Постобработка комментария."""
        comment = comment.strip('"\'')

        unwanted_prefixes = [
            "Комментарий:", "Мой комментарий:", "Вот комментарий:",
            "Коммент:", "Мой коммент:",
        ]
        for prefix in unwanted_prefixes:
            if comment.startswith(prefix):
                comment = comment[len(prefix):].strip()

        # Фильтр мата для mama-сегмента
        if segment == "mama":
            swear_replacements = {
                "бл*н": "блин", "блять": "блин", "бля": "блин",
                "пиздец": "ужас", "ппц": "кошмар", "нахуй": "нафиг",
                "хуй": "фиг", "сука": "жесть", "ёбаный": "жуткий",
            }
            comment_lower = comment.lower()
            for swear, replacement in swear_replacements.items():
                if swear in comment_lower:
                    # Case-insensitive replace
                    import re
                    comment = re.sub(re.escape(swear), replacement, comment, flags=re.IGNORECASE)

        if len(comment) > 500:
            comment = comment[:500]
            last_dot = comment.rfind('.')
            if last_dot > 200:
                comment = comment[:last_dot + 1]

        return comment

    async def should_comment(
        self,
        post_text: str,
        is_ad: bool = False,
        is_repost: bool = False,
        analysis: Optional[Dict] = None,
    ) -> bool:
        """Решает, стоит ли комментировать пост."""
        if is_ad:
            logger.debug("Skipping ad post")
            return False

        if is_repost:
            logger.debug("Skipping repost")
            return False

        if not post_text or len(post_text.strip()) < 50:
            logger.debug("Post too short")
            return False

        # Если есть анализ — используем его
        if analysis:
            if not analysis.get("should_comment", True):
                logger.info(f"AI analysis: skip (should_comment=false)")
                return False
            relevance = analysis.get("relevance", 0.5)
            if relevance < 0.4:
                logger.info(f"Skipped: low relevance ({relevance:.2f})")
                return False
            mood = analysis.get("discussion_mood", "neutral")
            if mood == "hostile":
                logger.info("Skipped: hostile discussion mood")
                return False
            return True

        # Fallback без анализа — старая логика
        bad_keywords = [
            "реклама", "промокод", "скидка 90%", "розыгрыш",
            "конкурс", "подписывайся", "переходи по ссылке",
        ]
        text_lower = post_text.lower()
        for keyword in bad_keywords:
            if keyword in text_lower:
                logger.debug(f"Post contains bad keyword: {keyword}")
                return False

        return random.random() < 0.7

    def get_random_strategy(self, weights: Optional[Dict[str, float]] = None) -> str:
        """Выбрать случайную стратегию (fallback если нет анализа)."""
        if weights is None:
            weights = {
                "smart": 0.35,
                "supportive": 0.25,
                "funny": 0.15,
                "expert": 0.25,
            }

        strategies = list(weights.keys())
        probs = list(weights.values())

        return random.choices(strategies, weights=probs, k=1)[0]
