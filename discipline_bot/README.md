# Discipline Bot — "Sergeant"

> A personal accountability tracker that messages you via a Telethon userbot account, enforcing daily habits, work plans, and evening reviews with a harsh AI drill-sergeant persona powered by Deepseek.

**Status:** Ready (not deployed)
**Stack:** Python, Telethon, Deepseek, SQLAlchemy, PostgreSQL

## What It Does

- Sends a morning wake-up ping at a seasonal time (05:00 Mar-Nov, 06:00 Dec-Feb) with 3-level escalation if no response
- Tracks daily habits (meditation, cold shower, planning, workout) with streak counting and time-window enforcement
- Manages a daily work plan with task completion tracking and an 18:00 reminder
- Runs an AI-powered evening review at 22:00 that scores the day and generates a brutal analysis via Deepseek
- Produces a weekly summary every Sunday with trend comparison to the previous week

## Structure

```
discipline_bot/
├── __init__.py
├── config.py                  # Constants, escalation messages, habit aliases
├── state.py                   # In-memory FSM (UserState) for dialog tracking
├── ai/
│   └── sergeant.py            # Deepseek "Tyrant" persona — evening/weekly reviews
├── database/
│   └── models.py              # 7 SQLAlchemy models (config, habits, logs, plans, tasks, reviews, checkins)
├── handler/
│   └── message_handler.py     # Text command router (morning confirm, habits, plan, stats)
└── scheduler/
    └── discipline_scheduler.py # Main 30-second loop — pings, escalations, reminders, reviews
```

**Migration:** `scripts/migrations/019_discipline_bot.sql`

## How to Run

The Discipline Bot is **not** a standalone service. It runs as a module inside Traffic Engine, sharing its Telethon client to avoid `AuthKeyDuplicatedError`.

Integration point in `traffic_engine/main.py`:

```python
from discipline_bot.scheduler import DisciplineScheduler

scheduler = DisciplineScheduler(account_manager=account_manager)
await scheduler.start()
```

The scheduler automatically picks the least-loaded Telethon account (or a fixed one from `discipline_config` table) and registers an incoming message handler for the admin user.

**Prerequisites:**
- Traffic Engine running with at least one active Telethon account
- PostgreSQL with migration `019_discipline_bot.sql` applied
- `DEEPSEEK_API_KEY` in `.env` (optional — falls back to template responses)

## Features

| Feature | Schedule | Details |
|---------|----------|---------|
| Morning ping | 05:00 / 06:00 MSK (seasonal) | Escalation at +5, +10, +20 min; fails at +30 min |
| Habit tracking | After morning confirm | By number (`1`), alias (`душ`), or name; streak + best streak |
| Habit windows | Configurable per habit | 20-min warning before window closes; streak reset on miss |
| Work plan | On demand (`план`) | Free-text tasks, close with `з1`, `з2`; reminder at 18:00 |
| Evening review | 22:00 MSK | Day score + AI analysis (Deepseek "Tyrant" persona) + tomorrow plan |
| Weekly summary | Sunday 23:00 MSK | Trend vs previous week, best/worst day, AI analysis |
| Statistics | On demand (`стат`) | Streaks, task progress, 7-day avg score |
| Quiet hours | 23:00-04:30 MSK (default) | No messages sent during this window |

### Text Commands

| Command | Action |
|---------|--------|
| `встал` | Confirm morning wake-up |
| `1`, `2`, `3`, `4` | Mark habit done by number |
| `медитация`, `душ`, `трен` | Mark habit done by alias |
| `план` | Show or create today's work plan |
| `з1`, `з2` | Close task by number |
| `стат` | Show statistics |
| `привычки` | List habits with streaks |
| `неделя` | Request weekly summary |
| `добавить <name>` | Add a new habit |
| `удалить <number>` | Deactivate a habit |

## Current Status

**Works (code-complete):**
- Morning protocol with 3-level escalation
- Habit tracking with streaks, windows, and aliases
- Daily work plan CRUD with task completion
- Evening review with Deepseek AI analysis + fallback templates
- Weekly summary with week-over-week trend comparison
- In-memory FSM for dialog state
- 7 database models with proper indexes
- Quiet hours enforcement
- Seasonal wake-up time (winter/summer)

**TODO:**
- Run migration `019_discipline_bot.sql` on VPS
- Deploy: `git push` + `systemctl restart apexflow-traffic`
- End-to-end test with a real Telethon account
- Admin must send an initial message to the bot account (Telethon needs entity resolution)
