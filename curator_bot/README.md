# AI Curator Bot

> Telegram bot that acts as a personal AI mentor for NL International partners -- answers product/business questions using RAG, runs a conversational sales funnel, and onboards new users through a 7-day checklist.

**Status:** Production
**Stack:** Python, aiogram 3, Deepseek/Claude/YandexGPT, PostgreSQL + pgvector, APScheduler

## What It Does

- Answers any question about NL International products, marketing plan, and business using a RAG knowledge base (200+ documents, pgvector search with 0.45 similarity threshold)
- Runs a DB-backed conversational sales funnel that detects user intent (product/business/skeptic), classifies lead temperature (hot/warm/cold), and naturally guides the conversation toward a CTA with referral links
- Onboards new partners with a 7-day interactive checklist (inline buttons to mark tasks done, proactive reminders for inactive users at 4h/12h/24h/48h/7d thresholds)
- Adapts tone per audience segment (zozh, mama, business, student) based on Traffic Engine deep-link source, including a swear filter for the mama segment
- Sends testimonial media (before/after photos, voice messages, check screenshots) from a 3775-message database when the user asks for proof or results

## Structure

```
curator_bot/
├── main.py                          # Entry point, registers routers, starts schedulers
├── ai/
│   ├── chat_engine.py               # CuratorChatEngine — generates AI responses with RAG + persona + funnel
│   ├── prompts.py                   # System prompts, onboarding context, topic-specific prompts
│   ├── curator_style.py             # Tone rules, forbidden patterns, AI-word replacement
│   ├── segment_styles.py            # Audience segment overlays (zozh/mama/business/student)
│   ├── media_responder.py           # MediaResponder — sends photos/videos/voice from testimonials DB
│   └── business_presenter.py        # Business presentation logic
├── handlers/
│   ├── commands.py                  # /start, /help, /progress, /goal, /menu, /catalog, /business, /diary, admin commands
│   ├── messages.py                  # Catch-all text handler — intent analysis, RAG retrieval, AI response
│   └── onboarding_callbacks.py      # Inline button handlers for onboarding checklist
├── database/
│   └── models.py                    # User, ConversationMessage, ConversationContext, KnowledgeBaseChunk, TrafficSource, UserOnboardingProgress
├── funnels/
│   ├── conversational_funnel.py     # ConversationalFunnel — 8-stage DB-backed sales funnel with lead temperature
│   ├── referral_links.py            # Product/business referral link mappings
│   ├── keyboards.py                 # Inline keyboards for funnel
│   └── messages.py                  # Funnel message templates, reminder texts
├── onboarding/
│   ├── onboarding_service.py        # OnboardingService — CRUD for 7-day progress tracking
│   ├── onboarding_scheduler.py      # OnboardingScheduler — background loop for reminders + event processing
│   └── proactive_tasks.py           # Day 1-7 task definitions, inactivity reminder messages
├── scheduler/
│   └── reminder_scheduler.py        # APScheduler — inactive user reminders (6h), hot lead alerts (1h)
├── analytics/
│   ├── funnel_stats.py              # Funnel conversion stats
│   └── lead_scoring.py              # Lead scoring and hot lead detection
├── events/
│   ├── event_consumer.py            # Processes system_events (e.g. new post notifications)
│   └── notification_service.py      # Notification dispatch
├── notifications/
│   └── lead_alerts.py               # Hot lead admin alerts
├── services/                        # Business logic services
├── utils/
│   ├── quiet_hours.py               # Blocks proactive messages outside 10:00-21:00 MSK
│   ├── webapp_keyboards.py          # Mini App keyboard builders (catalog, business)
│   └── product_photos.py            # Product photo helpers
└── knowledge_base/                  # Local knowledge base assets
```

## How to Run

```bash
cd "c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots"

# Activate venv
venv\Scripts\activate

# Run curator bot only
python -m curator_bot.main

# Or run both bots together
python run_bots.py
```

Required `.env` variables:

```
CURATOR_BOT_TOKEN=...
ANTHROPIC_API_KEY=...          # or DEEPSEEK_API_KEY
CURATOR_AI_MODEL=claude-3-5-sonnet-20241022
DATABASE_URL=postgresql+asyncpg://...
ADMIN_TELEGRAM_IDS=756877849
```

## Key Commands

| Command | Access | Description |
|---------|--------|-------------|
| `/start` | All | Register new user, start onboarding checklist |
| `/start <source_id>` | All | Register with Traffic Engine deep-link tracking |
| `/help` | All | Show available commands |
| `/progress` | All | Show qualification, days in business, current goal |
| `/goal` | All | Set a personal goal |
| `/menu` | All | Show Mini App buttons (catalog, business) |
| `/catalog` | All | Open product catalog (190 products) |
| `/business` | All | Open business section |
| `/support` | All | Contact info |
| `/diary` | Admin | Admin diary -- entries feed into AI context |
| `/funnel_stats [days]` | Admin | Sales funnel conversion stats |
| `/hot_leads` | Admin | List of hot leads needing attention |
| `/stats_traffic` | Admin | Traffic Engine source stats (clicks, registrations, conversions) |
| `/add_traffic_source` | Admin | Create a new traffic source with deep-link |

## Current Status

**Working:**
- AI responses via Deepseek (primary) / Claude (secondary) / YandexGPT (fallback)
- RAG with pgvector (min_similarity=0.45)
- Conversational sales funnel with DB persistence (survives restarts)
- Lead temperature classification (hot/warm/cold) with adaptive funnel speed
- 7-day onboarding with interactive checklist and proactive reminders
- Segment-aware tone adaptation (4 segments from Traffic Engine)
- Media responses from testimonials DB (photos, videos, voice)
- Quiet hours (no proactive messages 21:00-10:00 MSK)
- APScheduler: inactive user reminders every 6h, hot lead alerts every 1h
- AI-word post-processing (strips emoji, markdown, replaces 40+ AI-typical words)
- Admin diary entries injected into AI context
- Traffic source tracking with conversion analytics

**TODO:**
- Hallucination rate reduction (currently ~23.3%)
- Auto-posting schedule (`/schedule` partially broken)
- Add dates to top-20 RAG documents
