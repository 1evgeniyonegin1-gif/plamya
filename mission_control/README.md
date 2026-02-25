# Mission Control -- NEXUS Dashboard

> Telegram Mini App for monitoring and managing PLAMYA AI agents in real time.

**Status:** Working
**Stack:** FastAPI, React 18, TypeScript, Tailwind, framer-motion, zustand, @tanstack/react-query
**Port:** 8006

## What It Does

- Displays live status of all 7 PLAMYA agents (Altron, Hunter, Coder, Scanner, Chappie, Empat, Producer) with heartbeat, model info, cron jobs, and API usage
- Provides a chat interface to send messages to any agent via shared INBOX.md
- Runs a Council page where you can create discussion topics and ask all agents to respond
- Manages a task board with priority levels and per-agent assignment/filtering
- Aggregates cron job errors and API failures into a unified error log with severity grouping
- Pushes real-time updates to the frontend via Server-Sent Events (SSE) -- no database required, reads/writes PLAMYA config files directly

## Structure

```
mission_control/
├── backend/
│   ├── main.py                    # FastAPI app, lifespan, SPA serving
│   ├── config.py                  # Settings (port 8006, plamya dir, bot token)
│   ├── schemas.py                 # Pydantic models
│   ├── auth/
│   │   └── telegram_auth.py       # Telegram WebApp auth
│   ├── api/
│   │   ├── agents.py              # GET /agents, GET /agents/:id
│   │   ├── inbox.py               # GET /inbox (filtered by agent)
│   │   ├── chat.py                # POST /chat/send
│   │   ├── cron.py                # GET /cron/jobs, POST toggle/trigger
│   │   ├── errors.py              # GET /errors (aggregated)
│   │   ├── council.py             # CRUD /council/topics, ask-all, reply
│   │   ├── tasks.py               # CRUD /tasks, toggle done, delete
│   │   ├── events.py              # GET /events/stream (SSE)
│   │   └── auth.py                # Auth endpoints
│   └── services/
│       ├── agents_service.py      # Aggregates plamya.json + STATUS.md + jobs.json + INBOX.md
│       ├── inbox_parser.py        # Parses INBOX.md
│       ├── status_parser.py       # Parses STATUS.md
│       ├── jobs_parser.py         # Parses cron/jobs.json
│       ├── jobs_writer.py         # Writes back to jobs.json
│       ├── council_service.py     # COUNCIL.md read/write
│       ├── tasks_service.py       # TASKS.md read/write
│       ├── errors_service.py      # Aggregates errors from cron + API profiles
│       ├── event_bus.py           # In-memory SSE event bus
│       ├── file_monitor.py        # Watches PLAMYA files for changes (3s interval)
│       └── file_watcher.py        # Cached file reader (JSON + text)
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx               # React entry point
│       ├── App.tsx                # Root layout, tab routing, SSE hook
│       ├── api/
│       │   └── client.ts          # Axios client + all API types + endpoint wrappers
│       ├── hooks/
│       │   ├── useTelegram.ts     # Telegram WebApp integration
│       │   ├── useAuth.ts         # Auth state
│       │   └── useSSE.ts          # SSE subscription + cache invalidation
│       ├── lib/
│       │   ├── constants.ts       # Agent definitions (7 agents), colors, order
│       │   └── utils.ts           # timeAgo, formatTimestamp, normalizeStatus
│       ├── pages/
│       │   ├── Overview.tsx       # Agent grid with status cards
│       │   ├── AgentDetail.tsx    # Agent profile: chat tab + info tab (cron, CRM, API usage)
│       │   ├── Council.tsx        # Discussion topics, ask-all, reply
│       │   ├── Tasks.tsx          # Task board with priority + agent filter
│       │   ├── Inbox.tsx          # Message feed filtered by agent
│       │   ├── ErrorLog.tsx       # Errors/warnings/info grouped by severity
│       │   └── CronMonitor.tsx    # Cron jobs list (toggle/trigger)
│       └── components/
│           ├── Navigation.tsx     # Bottom tab bar (5 tabs)
│           ├── AgentCard.tsx      # Agent summary card for grid
│           ├── ChatPanel.tsx      # Chat UI for messaging agents
│           ├── CronJobCard.tsx    # Single cron job display
│           ├── ErrorCard.tsx      # Single error display
│           ├── MessageBubble.tsx  # Inbox message bubble
│           ├── StatusDot.tsx      # Colored status indicator
│           ├── TimeAgo.tsx        # Relative time component
│           ├── RadarSweep.tsx     # Background radar animation
│           └── GridOverlay.tsx    # Background grid effect
└── __init__.py
```

## How to Run

**Backend:**

```bash
cd "c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots"
python -m mission_control.backend.main
# Runs on http://localhost:8006
```

**Frontend (dev):**

```bash
cd mission_control/frontend
npm install
npm run dev
```

**Frontend (build for production):**

```bash
cd mission_control/frontend
npm run build
# Output goes to frontend/dist/, served by FastAPI automatically
```

## Pages

| Tab | Route/Tab ID | Description |
|-----|-------------|-------------|
| Agents | `overview` | Grid of all 7 agents with status, model, cron count, errors |
| Agent Detail | (drill-down) | Chat with agent + info tab (cron jobs, CRM funnel, API usage, producer pipeline) |
| Council | `council` | Create discussion topics, ask all agents, view responses, reply as admin |
| Tasks | `tasks` | Task board with 4 priority levels, assign to agents, filter by agent, toggle done |
| Inbox | `inbox` | All inter-agent messages from INBOX.md, filterable by agent |
| Errors | `errors` | Aggregated errors from cron jobs and API profiles, grouped by severity |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/agents` | List all agents with summary |
| GET | `/api/v1/agents/:id` | Agent detail (cron, inbox, CRM, producer data) |
| GET | `/api/v1/inbox` | Inbox messages (optional `?agent=` filter) |
| POST | `/api/v1/chat/send` | Send message to agent via INBOX.md |
| GET | `/api/v1/cron/jobs` | List all cron jobs |
| POST | `/api/v1/cron/jobs/:id/toggle` | Enable/disable a cron job |
| POST | `/api/v1/cron/jobs/:id/trigger` | Manually trigger a cron job |
| GET | `/api/v1/errors` | Aggregated errors |
| GET | `/api/v1/council/topics` | List discussion topics |
| GET | `/api/v1/council/topics/:id` | Get topic with responses |
| POST | `/api/v1/council/topics` | Create new topic |
| POST | `/api/v1/council/topics/:id/ask` | Ask all agents to respond |
| POST | `/api/v1/council/topics/:id/reply` | Reply to a topic |
| GET | `/api/v1/tasks` | List tasks (optional `?assignee=` filter) |
| POST | `/api/v1/tasks` | Create task |
| PUT | `/api/v1/tasks/:id/status` | Toggle task done/undone |
| DELETE | `/api/v1/tasks/:id` | Remove task |
| GET | `/api/v1/events/stream` | SSE stream for real-time updates |
| GET | `/health` | Health check |

## Current Status

**Working:**
- Agent overview grid with live status from STATUS.md
- Agent detail with chat, cron jobs, API usage, CRM data (Hunter), producer pipeline, Chappie knowledge
- Chat interface (send/receive via INBOX.md)
- Council discussions with ask-all and reply
- Task board with CRUD, priority, agent assignment
- Inbox viewer with agent filtering
- Error aggregation from cron + API profiles
- SSE real-time updates (file monitor watches PLAMYA files every 3s)
- Telegram WebApp integration (BackButton, HapticFeedback)
- SPA serving from FastAPI (production build)

**Architecture notes:**
- Zero database -- reads/writes PLAMYA files directly (~/.plamya/)
- File-based state: STATUS.md, INBOX.md, COUNCIL.md, TASKS.md, cron/jobs.json, auth-profiles.json
- Hunter agent detail reads CRM.sqlite for lead funnel data
- Producer agent detail reads PRODUCER_*.json for pipeline/niche/product data
- Chappie agent detail reads CHAPPIE_*.json for goals/state/knowledge
