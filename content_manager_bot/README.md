# Content Manager Bot

> AI-powered Telegram content generation and publishing bot with moderation, scheduling, analytics, and multi-channel funnel support.

**Status:** Production
**Stack:** Python, aiogram 3, Deepseek (primary) / Claude (fallback) / YandexGPT (fallback), PostgreSQL, SQLAlchemy

## What It Does

- Generates Telegram posts via a 3-stage AI pipeline (Planner -> Writer -> Critic) with anti-AI-word validation and post memory (last 15 published) to avoid repetition
- Admin moderation flow: generate -> preview -> approve/edit/reject/schedule -> publish to channel
- Automated scheduling with per-type intervals (product daily, motivation daily, tips every 2 days, etc.) and thematic channel routing by segment (zozh, business, mama, student)
- Two-tier channel funnel: public channels get regular content + time-limited invite-teasers with auto-expiring links to a private VIP channel
- AI Content Director: editorial planning, self-review every 10 posts, competitor analysis, trend detection, performance analytics (LinUCB contextual bandit), and channel memory

## Structure

```
content_manager_bot/
|-- main.py                       # Entry point: bot + dispatcher + scheduler
|-- ai/
|   |-- content_generator.py      # 3-stage pipeline (Planner/Writer/Critic)
|   |-- prompts.py                # Legacy prompts + FunnelPrompts
|   |-- prompts_v2.py             # V2 prompt system (POST_TYPES, validators)
|   |-- style_dna.py              # Persona, anti-AI words, segment overlays
|   |-- series_manager.py         # Multi-part series with cliffhangers
|-- handlers/
|   |-- admin.py                  # Commands: /generate, /pending, /stats, /traffic, /plan, /diary
|   |-- callbacks.py              # Inline buttons: publish, edit, reject, schedule, images
|   |-- channel_admin.py          # Channel management handlers
|   |-- vip_welcome.py            # VIP channel join handler (ChatMemberUpdated)
|-- scheduler/
|   |-- content_scheduler.py      # Auto-generation loop, scheduled publishing, invite posts, daily TE report, Director tasks
|-- database/
|   |-- models.py                 # Post, ContentSchedule, AdminAction, DiaryEntry, ContentSeries, MediaAsset
|   |-- funnel_models.py          # ChannelTier, InviteLink (funnel)
|   |-- director_models.py        # AI Director DB models
|-- director/
|   |-- performance_analyzer.py   # LinUCB contextual bandit + scoring
|   |-- editorial_planner.py      # AI weekly content plan
|   |-- channel_memory.py         # Structured channel state (Mem0/A.U.D.N.)
|   |-- self_reviewer.py          # AI self-review every 10 posts
|   |-- reflection_engine.py      # Learning from edits/rejections
|   |-- competitor_analyzer.py    # Competitor channel analysis
|   |-- trend_detector.py         # Trending topic detection
|-- routing/
|   |-- channel_router.py         # Route posts to correct channel (public/VIP/thematic)
|-- invites/
|   |-- invite_manager.py         # Temporary invite link creation + cleanup
|-- verification/
|   |-- partner_verifier.py       # VIP channel join verification
|-- analytics/
|   |-- analytics_service.py      # Dashboard, top posts, engagement metrics
|   |-- stats_collector.py        # Fetch views/reactions from Telegram API
|-- utils/
|   |-- keyboards.py              # Inline + Reply keyboards
|   |-- image_helpers.py          # Image utilities
|   |-- product_reference.py      # Product photo lookup (legacy)
|   |-- leader_topics.py          # Leader topic pools
```

## How to Run

```bash
# Activate venv
cd "c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots"
venv\Scripts\activate

# Run standalone
python -m content_manager_bot.main

# Or together with curator bot
python run_bots.py
```

Required `.env` variables:
```
CONTENT_MANAGER_BOT_TOKEN=...
ANTHROPIC_API_KEY=...          # or DEEPSEEK_API_KEY
CHANNEL_USERNAME=@channel
ADMIN_TELEGRAM_IDS=123456789
DATABASE_URL=postgresql+asyncpg://...
```

## Key Commands

| Command | Description |
|---------|-------------|
| `/start` | Show main menu (admin only) |
| `/generate [type]` | Generate a post (random type if omitted) |
| `/pending` | Show posts awaiting moderation |
| `/stats` | Post counts by status |
| `/analytics [days]` | Detailed analytics dashboard |
| `/top [metric] [count] [days]` | Top posts by views/reactions/engagement |
| `/schedule` | Auto-posting settings per content type |
| `/update_stats` | Pull latest metrics from Telegram |
| `/traffic` | Traffic Engine status (accounts, actions, errors) |
| `/accounts` | Traffic Engine account details |
| `/errors` | Traffic Engine errors (24h, grouped by type) |
| `/plan [segment]` | AI editorial content plan |
| `/review [segment]` | AI self-review of recent posts |
| `/insights [segment]` | Performance insights (LinUCB) |
| `/competitors [segment]` | Competitor channel analysis |
| `/diary` | Personal diary (used as AI context) |
| `/help` | Help text |

Post types: `product`, `motivation`, `news`, `tips`, `success_story`, `promo`, `invite_teaser`, `vip_content`

## Current Status

**Working:**
- 3-stage AI generation pipeline (Deepseek primary, Claude/YandexGPT fallback)
- Post moderation (approve, reject, edit via AI, manual edit, regenerate with feedback)
- Publishing to Telegram channels with image support (product photos, testimonials)
- Auto-scheduling by content type with configurable intervals
- Thematic channel support (segment-based routing)
- Post analytics (views, reactions, engagement rate, top posts)
- Admin diary as generation context
- Serial content with cliffhangers
- AI Director: editorial planner, self-reviewer, reflection engine, trend detector
- Traffic Engine monitoring commands
- Daily TE report at 23:00 MSK

**In progress:**
- Channel funnel invite posts (code exists, needs Telethon for real invite links)
- Competitor analyzer (needs Telethon API keys)

**TODO:**
- Connect Telethon for real invite link creation
- Improve prompts to reduce hallucination rate (currently ~23%)
- Fix `/schedule` button handlers (partially broken)
