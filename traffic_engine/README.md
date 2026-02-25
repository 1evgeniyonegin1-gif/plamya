# Traffic Engine

> Multi-account Telegram traffic automation system: AI-powered commenting, story viewing, invites, and content posting via Telethon userbot accounts.

**Status:** Production (deployed on VPS as `apexflow-traffic.service`)
**Stack:** Python, Telethon, YandexGPT, Deepseek, PostgreSQL (asyncpg), SQLAlchemy, Pydantic, aiogram (notifications)

## What It Does

- **Auto-commenting** in target channels: monitors new posts, analyzes them with AI, generates contextual comments in a human persona style, posts via rotating userbot accounts
- **Story viewing + reactions**: views stories of target audience users, reacts with emojis (30% chance), tracks quality scores
- **Group invites**: invites target audience members into thematic event chats, publishes an offer when the member threshold is reached
- **Content posting**: auto-publishes AI-generated posts and stories to accounts' own thematic channels
- **Self-learning strategy selection**: Thompson Sampling (MAB) picks the best comment strategy (smart/supportive/funny/expert) per segment and channel, learns from replies and reactions

## Structure

```
traffic_engine/
├── main.py                          # TrafficEngine class, orchestrates all components
├── config.py                        # Settings from .env (Pydantic), segment definitions
├── __init__.py
│
├── core/
│   ├── account_manager.py           # Telethon client pool, rotation, warmup, cooldowns
│   ├── rate_limiter.py              # Per-action rate limits, FloodWait backoff
│   ├── human_simulator.py           # Working hours, typing/reading delays, breaks
│   └── strategy_selector.py         # Thompson Sampling MAB for comment strategies
│
├── channels/
│   ├── auto_comments/
│   │   ├── channel_monitor.py       # Watches target channels for new posts
│   │   ├── comment_generator.py     # YandexGPT: post analysis + comment generation
│   │   └── comment_poster.py        # Posts comment via Telethon, similarity check
│   ├── story_viewer/
│   │   ├── story_monitor.py         # Picks TA users, orchestrates viewing
│   │   ├── story_viewer.py          # Views stories via Telethon
│   │   └── story_reactor.py         # Sends emoji reactions to stories
│   ├── chat_inviter/
│   │   ├── invite_monitor.py        # Picks TA users, orchestrates invites
│   │   ├── chat_inviter.py          # Sends invite via Telethon
│   │   └── group_creator.py         # Creates thematic event groups
│   ├── own_channels/
│   │   └── channel_responder.py     # Replies to comments in own channels
│   ├── story_poster/
│   │   ├── story_poster.py          # Publishes stories from bot accounts
│   │   └── story_content.py         # Story text templates + AI generation
│   └── reply_checker.py             # Hourly: checks replies to our comments, feeds MAB
│
├── posting/
│   ├── auto_poster.py               # Publishes queued ChannelPost records
│   └── channel_content_generator.py # Deepseek: generates channel posts per segment
│
├── database/
│   ├── models.py                    # Tenant, UserBotAccount, TargetChannel, TrafficAction,
│   │                                #   TargetAudience, InviteChat, StrategyEffectiveness,
│   │                                #   ChannelPost
│   └── session.py                   # AsyncSession factory (asyncpg)
│
├── notifications/
│   └── telegram_notifier.py         # Alerts to admin via aiogram: errors, diagnosis,
│                                    #   aggregation, throttling, success notifications
└── analytics/                       # (reserved, empty)
```

## How to Run

```bash
# Activate virtualenv
cd "c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots"
venv\Scripts\activate

# Run via entry point script
python run_auto_comments.py

# Or as a module
python -m traffic_engine.main

# On VPS (systemd)
systemctl restart apexflow-traffic
journalctl -u apexflow-traffic -f
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `TELEGRAM_API_ID` | Yes | Telegram API ID from my.telegram.org |
| `TELEGRAM_API_HASH` | Yes | Telegram API Hash |
| `ADMIN_BOT_TOKEN` | No | Bot token for admin commands |
| `ADMIN_TELEGRAM_IDS` | No | Comma-separated admin Telegram IDs (default: `756877849`) |
| `YANDEX_SERVICE_ACCOUNT_ID` | Yes | YandexGPT service account |
| `YANDEX_KEY_ID` | Yes | YandexGPT key ID |
| `YANDEX_PRIVATE_KEY` | Yes | YandexGPT private key (or `YANDEX_PRIVATE_KEY_FILE`) |
| `YANDEX_FOLDER_ID` | Yes | YandexGPT folder ID |
| `ALERT_BOT_TOKEN` | No | Bot token for Telegram error alerts |
| `ALERT_ADMIN_ID` | No | Telegram user ID for alerts |
| `TRAFFIC_NOTIFY_SUCCESS` | No | `true` to get a notification on every successful action |
| `MAX_COMMENTS_PER_DAY` | No | Per-account daily comment limit (default: `15`) |
| `MAX_INVITES_PER_DAY` | No | Per-account daily invite limit (default: `8`) |
| `MAX_STORY_VIEWS_PER_DAY` | No | Per-account daily story view limit (default: `60`) |
| `MAX_STORY_REACTIONS_PER_DAY` | No | Per-account daily story reaction limit (default: `15`) |
| `ENCRYPTION_KEY` | No | Fernet key for encrypting session strings |

## Current Status

**Works:**
- Smart auto-commenting with post + comment analysis (YandexGPT)
- 4-segment routing: accounts comment only in their niche channels (zozh, mama, business, student)
- Thompson Sampling MAB for strategy selection (smart/supportive/funny/expert)
- Reply checker (hourly, feeds MAB with reply=1.0 / reaction=0.5 rewards)
- Story viewing + reactions (StoryReactor, 30% chance)
- Group invites with offer auto-publish at member threshold
- Auto-posting to thematic channels (Deepseek content generation)
- Own channel comment replies (OwnChannelMonitor)
- Story posting from bot accounts (StoryPoster, 1-3/day)
- Human simulation: working hours (9-23), night sleep, lunch slowdown, typing/reading delays, session breaks
- 14-day account warmup with graduated limits
- Telegram notifications with diagnosis, error aggregation, and throttling
- Cross-account safety checks and Jaccard similarity filter (>60% = blocked)
- Daily limit variance (+/-20%) for natural-looking activity

**In progress / TODO:**
- Switch comment generation from YandexGPT to Deepseek
- DM / private messages (needs 30-day warmup, planned March 2026+)
- Analytics module (reserved, empty)
