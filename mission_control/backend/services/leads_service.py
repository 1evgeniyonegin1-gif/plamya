"""
Leads Service — reads biz_scanner SQLite, generates AI dialog responses.

Connects to ~/.biz_scanner/biz_scanner.sqlite (same DB as biz_scanner pipeline).
"""

import json
import logging
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path.home() / ".biz_scanner" / "biz_scanner.sqlite"

# Claude Code CLI (подписка Max, без API ключа)
import platform as _platform
CLAUDE_CODE_CLI = os.getenv(
    "CLAUDE_CODE_CLI",
    "claude.cmd" if _platform.system() == "Windows" else "claude",
)
CLAUDE_CODE_TIMEOUT = 120

# Statuses that count as "leads" (have proposals ready)
LEAD_STATUSES = ("proposal_ready", "delivered", "contacted", "replied", "negotiating")

# Priority mapping from score
PRIORITY_THRESHOLDS = {"hot": 70, "warm": 40, "cold": 0}

# ── Services catalog with ROI (for AI dialog context) ──────────
SERVICES_BRIEF = """Каталог AI-услуг Данила (цена → окупаемость → экономия):
1. Сайт/лендинг — от 20K руб, 3-7 дней → окупаемость 2 мес, +15% заявок
2. Telegram-бот (запись + FAQ) — от 25K руб, 7-14 дней → окупаемость 1.5 мес, экономия 30K/мес vs администратор
3. AI-чатбот с RAG — от 40K руб, 14-21 день → окупаемость 2 мес, обработка 60% вопросов без человека
4. AI-контент для соцсетей — от 25K + 10K/мес → замена SMM-щика (40-60K/мес) в 4 раза дешевле
5. Email/SMS автоматика — от 15K руб → окупаемость 1 мес, -40% пропущенных записей
6. Настройка CRM — от 10K руб → окупаемость 1 мес, -30% потерянных клиентов
7. Бот записи с напоминаниями — от 25K руб → окупаемость 1.5 мес, no-shows с 15% до 5%

Пакеты:
- СТАРТ (сайт + бот + SEO): от 35K + 5K/мес → окупаемость 2 мес
- РОСТ (+ контент + email + аналитика): от 80K + 20K/мес → окупаемость 2-3 мес
- БИЗНЕС (+ CRM + AI-бот + Mini App): от 150K + 30K/мес → окупаемость 3-4 мес

КЛЮЧЕВОЕ: AI-бот стоит 3.5K/мес обслуживание, администратор — 35-45K/мес. Разница в 10 раз."""

DIALOG_SYSTEM_PROMPT = """Ты — Данил Лысенко, специалист по AI-автоматизации малого бизнеса из Краснодара.
Пишешь от первого лица ("я", "меня"). Не говоришь "мы" и "наша компания" — ты один.

КОНТЕКСТ КЛИЕНТА:
- Название: {name}
- Город: {city}
- Категория: {category}
- Проблемы: {problems}
- Подобранные AI-услуги: {services}

{services_catalog}

ВОЗРАЖЕНИЯ И КАК ОТВЕЧАТЬ (всегда используй ROI-аргументы):
- "дорого" → "Понимаю. Бот стоит 25K разово и 3.5K/мес. Администратор — 40K/мес. Разница в 10 раз. Окупается за 1-2 месяца."
- "нам не нужно" → задай уточняющий вопрос: "А как сейчас клиенты записываются? Много пропущенных звонков?"
- "уже есть подрядчик" → "Отлично, значит понимаете ценность. Если захотите сравнить — буду рад. На связи!"
- "пришлите КП" → "Конечно! Подготовлю с расчётом окупаемости конкретно под ваш бизнес. Скину в течение часа."
- "подумаю" → "Конечно, без спешки. Могу написать через пару дней?"
- "а кто вы" → "Данил, делаю AI-автоматизацию для бизнесов. Работаю официально — договор + чек."
- "сколько стоит" → СНАЧАЛА назови экономию, ПОТОМ цену: "Бот экономит ~30K/мес. Стоит 25-40K разово + 3.5K/мес обслуживание."

ИСТОРИЯ ДИАЛОГА:
{history}

ПРАВИЛА:
- Отвечай коротко (2-4 предложения, max 100 слов)
- Разговорный тон, без канцелярита
- Говори о ДЕНЬГАХ КЛИЕНТА, не о технологии
- НЕ "AI с RAG", А "бот отвечает как администратор, только 24/7 и за 3.5K/мес"
- Цель: довести до встречи/звонка или получить "пришлите КП"
- Если клиент спрашивает цену — СНАЧАЛА экономия, ПОТОМ цена
- Если клиент негативен — вежливо завершай, не навязывайся
- НЕ пиши Subject, НЕ пиши "Здравствуйте", просто продолжай диалог

ОТВЕТ КЛИЕНТА: {client_message}

Напиши ТОЛЬКО ответ Данила (без пояснений):"""

TIPS_PROMPT = """Проанализируй ответ клиента и дай Данилу 1 совет (1 предложение).
Клиент написал: "{client_message}"
Контекст: {category}, {city}
Совет:"""


def _get_connection() -> sqlite3.Connection:
    """Get SQLite connection to biz_scanner DB."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _row_to_lead(row: sqlite3.Row) -> dict:
    """Convert DB row to lead dict for API response."""
    d = dict(row)

    # Parse audit_data JSON
    audit_data = {}
    if d.get("audit_data"):
        try:
            audit_data = json.loads(d["audit_data"])
        except (json.JSONDecodeError, TypeError):
            pass

    # Parse match_capabilities JSON
    capabilities = []
    if d.get("match_capabilities"):
        try:
            capabilities = json.loads(d["match_capabilities"])
        except (json.JSONDecodeError, TypeError):
            pass

    # Determine priority label from score
    score = d.get("priority_score", 0) or 0
    if score >= PRIORITY_THRESHOLDS["hot"]:
        priority_label = "hot"
    elif score >= PRIORITY_THRESHOLDS["warm"]:
        priority_label = "warm"
    else:
        priority_label = "cold"

    # Build contacts dict
    contacts = {}
    for field in ("phone", "email", "website", "telegram", "whatsapp", "vk", "instagram"):
        val = d.get(field)
        if val:
            contacts[field] = val

    # Problems from audit
    problems = audit_data.get("problems", [])
    if isinstance(problems, str):
        problems = [problems]

    return {
        "id": d["id"],
        "name": d.get("name", ""),
        "city": d.get("city", ""),
        "category": d.get("category", ""),
        "address": d.get("address", ""),
        "status": d.get("status", "new"),
        "priority": priority_label,
        "priority_score": score,
        "audit_score": d.get("audit_score", 0) or 0,
        "match_score": d.get("match_score", 0) or 0,
        "contacts": contacts,
        "problems": problems,
        "capabilities": capabilities,
        "proposal_telegram": d.get("proposal_telegram", ""),
        "proposal_email": d.get("proposal_email", ""),
        "proposal_phone_script": d.get("proposal_phone_script", ""),
        "estimated_check": d.get("estimated_check", ""),
        "contact_method": d.get("contact_method", ""),
        "contact_date": d.get("contact_date", ""),
        "reply_date": d.get("reply_date", ""),
        "notes": d.get("notes", ""),
        "created_at": d.get("created_at", ""),
        "updated_at": d.get("updated_at", ""),
    }


def get_leads(
    status: str = None,
    city: str = None,
    category: str = None,
    priority: str = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Get leads list from biz_scanner SQLite."""
    if not DB_PATH.exists():
        return {"leads": [], "total": 0}

    conn = _get_connection()
    try:
        conditions = []
        params = []

        # Default: only show leads with proposals
        if status:
            conditions.append("status = ?")
            params.append(status)
        else:
            placeholders = ",".join("?" for _ in LEAD_STATUSES)
            conditions.append(f"status IN ({placeholders})")
            params.extend(LEAD_STATUSES)

        if city:
            conditions.append("city = ?")
            params.append(city)
        if category:
            conditions.append("category LIKE ?")
            params.append(f"%{category}%")
        if priority:
            if priority == "hot":
                conditions.append(f"priority_score >= ?")
                params.append(PRIORITY_THRESHOLDS["hot"])
            elif priority == "warm":
                conditions.append(f"priority_score >= ? AND priority_score < ?")
                params.extend([PRIORITY_THRESHOLDS["warm"], PRIORITY_THRESHOLDS["hot"]])
            elif priority == "cold":
                conditions.append(f"priority_score < ?")
                params.append(PRIORITY_THRESHOLDS["warm"])

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Count total
        total = conn.execute(
            f"SELECT COUNT(*) FROM businesses {where}", params
        ).fetchone()[0]

        # Fetch page
        params.extend([limit, offset])
        rows = conn.execute(
            f"""SELECT * FROM businesses {where}
                ORDER BY priority_score DESC, audit_score DESC
                LIMIT ? OFFSET ?""",
            params,
        ).fetchall()

        leads = [_row_to_lead(r) for r in rows]
        return {"leads": leads, "total": total}

    finally:
        conn.close()


def get_lead(lead_id: int) -> Optional[dict]:
    """Get single lead by ID."""
    if not DB_PATH.exists():
        return None

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM businesses WHERE id = ?", (lead_id,)
        ).fetchone()
        if not row:
            return None
        return _row_to_lead(row)
    finally:
        conn.close()


def update_lead_status(lead_id: int, status: str, notes: str = "") -> bool:
    """Update lead status."""
    if not DB_PATH.exists():
        return False

    conn = _get_connection()
    try:
        fields = {"status": status, "updated_at": datetime.utcnow().isoformat()}
        if notes:
            fields["notes"] = notes
        if status == "contacted":
            fields["contact_date"] = datetime.utcnow().isoformat()
        elif status == "replied":
            fields["reply_date"] = datetime.utcnow().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [lead_id]
        conn.execute(f"UPDATE businesses SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return True
    finally:
        conn.close()


def get_dialog_history(lead_id: int) -> list[dict]:
    """Get dialog history from outreach_log."""
    if not DB_PATH.exists():
        return []

    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM outreach_log
               WHERE business_id = ?
               ORDER BY sent_at ASC""",
            (lead_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_dialog_message(
    lead_id: int,
    platform: str,
    direction: str,
    message_text: str,
    ai_classification: str = "",
) -> None:
    """Save a message to outreach_log."""
    if not DB_PATH.exists():
        return

    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO outreach_log
               (business_id, platform, direction, message_text, ai_classification)
               VALUES (?, ?, ?, ?, ?)""",
            (lead_id, platform, direction, message_text, ai_classification),
        )
        conn.commit()
    finally:
        conn.close()


async def generate_dialog_response(
    lead_id: int,
    client_message: str,
    platform: str = "telegram",
) -> dict:
    """Generate AI response for client message.

    1. Save client message to outreach_log
    2. Build context from lead data + history
    3. Call AI (PLAMYA gateway)
    4. Save AI response to outreach_log
    5. Return AI response + tips
    """
    lead = get_lead(lead_id)
    if not lead:
        return {"error": "Lead not found"}

    # Save client message
    save_dialog_message(lead_id, platform, "incoming", client_message)

    # Build history text
    history = get_dialog_history(lead_id)
    history_lines = []
    for msg in history:
        role = "Данил" if msg["direction"] == "outgoing" else "Клиент"
        history_lines.append(f"{role}: {msg['message_text']}")
    history_text = "\n".join(history_lines[-20:])  # Last 20 messages

    # Build problems text
    problems_text = ", ".join(lead["problems"][:5]) if lead["problems"] else "не выявлены"

    # Build services text
    services_text = ""
    if lead["capabilities"]:
        for cap in lead["capabilities"][:3]:
            name = cap.get("name", str(cap)) if isinstance(cap, dict) else str(cap)
            services_text += f"- {name}\n"

    # Build AI prompt
    prompt = DIALOG_SYSTEM_PROMPT.format(
        name=lead["name"],
        city=lead["city"],
        category=lead["category"] or "не указана",
        problems=problems_text,
        services=services_text or "общая автоматизация",
        services_catalog=SERVICES_BRIEF,
        history=history_text or "(первый контакт — предложение уже отправлено)",
        client_message=client_message,
    )

    # Call AI
    ai_response = await _ai_call(prompt, temperature=0.7, max_tokens=300)

    if not ai_response or ai_response == "AI unavailable":
        ai_response = _template_response(client_message, lead)

    # Save AI response
    save_dialog_message(lead_id, platform, "outgoing", ai_response, "ai_generated")

    # Generate tip
    tip = await _generate_tip(client_message, lead)

    return {
        "ai_response": ai_response,
        "tips": tip,
        "history_count": len(history) + 2,  # +2 for the new messages
    }


def _template_response(client_message: str, lead: dict) -> str:
    """Template fallback when AI is unavailable. С ROI-аргументами."""
    msg = client_message.lower().strip()

    if any(w in msg for w in ("скольк", "цен", "стоит", "прайс", "стоимость")):
        return (
            f"AI-бот экономит ~30K руб/мес по сравнению с администратором, при этом работает 24/7. "
            f"Базовый пакет (сайт + бот + SEO) — от 35K руб, окупается за 2 месяца. "
            f"Могу подготовить расчёт конкретно под {lead['name']}. Когда удобно обсудить?"
        )

    if any(w in msg for w in ("дорог", "денег нет", "бюджет")):
        return (
            f"Понимаю. Давайте начнём с минимума — один AI-бот записи за 25K. "
            f"Он заменяет администратора (35-45K/мес) и работает 24/7. "
            f"Окупается буквально за месяц. Или можем обсудить рассрочку."
        )

    if any(w in msg for w in ("не нужн", "не интерес", "не надо", "нет")):
        return "Понял, спасибо за ответ! Если что-то изменится — буду на связи."

    if any(w in msg for w in ("подробн", "расскаж", "как это", "что именно")):
        problems = lead["problems"][:2] if lead["problems"] else ["автоматизация процессов"]
        return (
            f"Если коротко: AI-бот решает проблему с {problems[0].lower() if problems else 'автоматизацией'}. "
            f"Работает 24/7, стоит в 10 раз дешевле сотрудника. Делаю под ключ за 1-3 недели. "
            f"Удобнее созвониться на 15 минут или в переписке?"
        )

    if any(w in msg for w in ("кп", "предложен", "коммерческ")):
        return (
            f"Отлично! Подготовлю персональное предложение с расчётом окупаемости "
            f"под {lead['name']}. Скину в течение часа."
        )

    if any(w in msg for w in ("подума", "позже", "потом")):
        return "Конечно, без спешки. Могу написать через пару дней — вдруг появятся вопросы?"

    if any(w in msg for w in ("договор", "оформл", "официальн", "чек")):
        return (
            f"Работаю официально — самозанятый, договор подряда + чек через 'Мой налог'. "
            f"Гарантия 60 дней на все работы. Оплата поэтапная: 30% предоплата, 40% после сдачи."
        )

    # Default
    return (
        f"Спасибо за ответ! Если интересно — могу подготовить конкретное предложение "
        f"с расчётом окупаемости под {lead['name']}. Или ответить на вопросы."
    )


async def _generate_tip(client_message: str, lead: dict) -> str:
    """Generate a tip for Danil about the client's response."""
    prompt = TIPS_PROMPT.format(
        client_message=client_message,
        category=lead.get("category", ""),
        city=lead.get("city", ""),
    )

    tip = await _ai_call(prompt, temperature=0.3, max_tokens=100)
    if not tip or tip == "AI unavailable":
        # Template tips с ROI-подсказками
        msg = client_message.lower()
        if any(w in msg for w in ("скольк", "цен", "стоит")):
            return "Клиент спрашивает цену — отлично! Сначала назови экономию (~30K/мес), потом цену."
        if any(w in msg for w in ("дорог", "денег", "бюджет")):
            return "Возражение 'дорого'. Покажи ROI: бот 3.5K/мес vs администратор 40K/мес. Предложи минимальный вариант."
        if any(w in msg for w in ("не нужн", "не интерес")):
            return "Клиент отказывает. Не навязывайся, но спроси: 'А как сейчас клиенты записываются?'"
        if any(w in msg for w in ("подробн", "расскаж")):
            return "Клиент просит подробности — отличный знак! Предложи 15-минутный звонок."
        if any(w in msg for w in ("кп", "предложен")):
            return "Просят КП — горячий лид! Быстро подготовь предложение с расчётом окупаемости."
        if any(w in msg for w in ("договор", "оформл")):
            return "Спрашивают про оформление — почти сделка! Скажи: самозанятый, договор + чек."
        return "Продолжай разговор. Цель: звонок на 15 минут или запрос КП."

    return tip


async def _ai_call(prompt: str, temperature: float = 0.3, max_tokens: int = 300) -> str:
    """Call Claude via Claude Code CLI (uses Max subscription, no API key needed)."""
    if not shutil.which(CLAUDE_CODE_CLI):
        logger.warning("Claude Code CLI не найден в PATH")
        return "AI unavailable"

    try:
        env = dict(os.environ)
        env.pop("CLAUDECODE", None)  # убираем чтобы не было ошибки nested session

        cmd = [CLAUDE_CODE_CLI, "-p", prompt, "--output-format", "json", "--max-turns", "1"]
        # На Windows .cmd файлы требуют cmd /c, но без shell=True (безопасность)
        if _platform.system() == "Windows" and CLAUDE_CODE_CLI.endswith(".cmd"):
            cmd = ["cmd", "/c"] + cmd

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=CLAUDE_CODE_TIMEOUT,
            env=env,
        )

        if result.returncode != 0:
            stderr = result.stderr[:300] if result.stderr else "no stderr"
            logger.warning(f"Claude Code CLI error (code {result.returncode}): {stderr}")
            return "AI unavailable"

        stdout = result.stdout.strip()
        if not stdout:
            logger.warning("Claude Code CLI: пустой stdout")
            return "AI unavailable"

        data = json.loads(stdout)
        text = data.get("result", "")
        return text.strip() if text else "AI unavailable"

    except subprocess.TimeoutExpired:
        logger.warning(f"Claude Code CLI: таймаут ({CLAUDE_CODE_TIMEOUT}с)")
        return "AI unavailable"
    except json.JSONDecodeError as e:
        logger.warning(f"Claude Code CLI: невалидный JSON: {e}")
        return "AI unavailable"
    except Exception as e:
        logger.warning(f"Claude Code CLI exception: {e}")
        return "AI unavailable"


def get_leads_stats() -> dict:
    """Get leads statistics."""
    if not DB_PATH.exists():
        return {"total": 0, "statuses": {}, "cities": {}, "categories": {}}

    conn = _get_connection()
    try:
        # Total leads (with proposals)
        placeholders = ",".join("?" for _ in LEAD_STATUSES)
        total = conn.execute(
            f"SELECT COUNT(*) FROM businesses WHERE status IN ({placeholders})",
            LEAD_STATUSES,
        ).fetchone()[0]

        # By status
        statuses = {}
        for row in conn.execute(
            f"""SELECT status, COUNT(*) as cnt FROM businesses
                WHERE status IN ({placeholders})
                GROUP BY status""",
            LEAD_STATUSES,
        ).fetchall():
            statuses[row["status"]] = row["cnt"]

        # By city
        cities = {}
        for row in conn.execute(
            f"""SELECT city, COUNT(*) as cnt FROM businesses
                WHERE status IN ({placeholders})
                GROUP BY city ORDER BY cnt DESC LIMIT 10""",
            LEAD_STATUSES,
        ).fetchall():
            cities[row["city"]] = row["cnt"]

        # By priority
        hot = conn.execute(
            f"SELECT COUNT(*) FROM businesses WHERE status IN ({placeholders}) AND priority_score >= ?",
            (*LEAD_STATUSES, PRIORITY_THRESHOLDS["hot"]),
        ).fetchone()[0]
        warm = conn.execute(
            f"SELECT COUNT(*) FROM businesses WHERE status IN ({placeholders}) AND priority_score >= ? AND priority_score < ?",
            (*LEAD_STATUSES, PRIORITY_THRESHOLDS["warm"], PRIORITY_THRESHOLDS["hot"]),
        ).fetchone()[0]
        cold = total - hot - warm

        return {
            "total": total,
            "statuses": statuses,
            "cities": cities,
            "priorities": {"hot": hot, "warm": warm, "cold": cold},
        }
    finally:
        conn.close()
