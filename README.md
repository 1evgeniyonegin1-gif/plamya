<p align="center">
  <img src="docs/plamya-logo.png" alt="PLAMYA" width="200" />
  <br/>
  <em>"From ashes, autonomy."</em>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License" /></a>
  <a href="#security"><img src="https://img.shields.io/badge/security-4--layer%20guard-green.svg" alt="Security" /></a>
  <a href="#"><img src="https://img.shields.io/badge/API%20key-not%20required-brightgreen.svg" alt="No API Key" /></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+" /></a>
</p>

---

# PLAMYA

**Secure autonomous AI agent framework.** Born from the ashes of OpenClaw — rebuilt with security-first architecture, 4-layer prompt injection defense, and zero API keys required.

PLAMYA agents work autonomously: they research, create content, analyze competitors, generate leads, and manage Telegram channels — all while protecting your secrets and blocking prompt injection attacks.

## Why PLAMYA?

| Problem | OpenClaw | PLAMYA |
|---------|----------|--------|
| Credentials | Plaintext in .md files | Fernet-encrypted secrets |
| Prompt injection | Zero protection | 4-layer defense (Input Guard, Output Guard, Action Guard, Canary Token) |
| API keys | Required (BYOK) | Uses Claude Max subscription — no API keys needed |
| Security track record | CVE-2026-25253 (RCE), 42K+ compromised | Security-audited, no network gateway |
| Setup | 3+ days | 60 seconds |

## Quick Start

```bash
# Clone
git clone https://github.com/1evgeniyonegin1-gif/nl-international-ai-bots.git
cd nl-international-ai-bots

# Install
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Fill in your Telegram bot tokens

# Ignite
python run_bots.py
```

## Architecture

```
PLAMYA
├── Agents (autonomous AI workers)
│   ├── Chappie ......... NL International partner agent
│   ├── Producer ........ Info-product factory (courses, landings)
│   ├── Scanner ......... B2B lead finder & proposal writer
│   ├── Curator ......... AI mentor for partners
│   └── Content Mgr ..... Telegram content automation
│
├── Security (4-layer defense)
│   ├── Input Guard ..... Isolates untrusted data from LLM instructions
│   ├── Output Guard .... Regex scanning for secret leaks
│   ├── Action Guard .... Per-agent action whitelist
│   └── Canary Token .... Detects system prompt exfiltration
│
├── Runtime
│   ├── AI Client ....... Claude Code CLI (Max subscription, no API key)
│   ├── Heartbeat ....... Autonomous task scheduler
│   └── State ........... ~/.plamya/ (file-based, no network gateway)
│
└── Frontends
    ├── Mission Control .. Agent dashboard (React + FastAPI)
    ├── Partner Panel .... Partner management Mini App
    └── Curator App ...... Product catalog Mini App
```

## Security

PLAMYA implements the **"Rule of Two"** (Meta): no agent simultaneously has untrusted input + secret access + external writes.

### 4-Layer Defense

**Layer 1 — Input Guard** (`shared/input_guard.py`)
All external data (Telegram messages, scraped websites, competitor content) is wrapped in isolation markers before reaching the LLM. The model sees data as *data*, not as instructions.

**Layer 2 — Output Guard** (`shared/output_guard.py`)
Every outgoing message is scanned for leaked secrets (API keys, tokens, connection strings, SSH keys). If a leak is detected, the message is sanitized and the incident is logged.

**Layer 3 — Action Guard** (`shared/action_guard.py`)
Each agent has a whitelist of allowed actions. `exec_shell`, `read_env`, `send_file`, `modify_config` are blocked globally. Some actions require human approval.

**Layer 4 — Canary Token** (`shared/canary.py`)
A secret token is injected into every system prompt. If it appears in the LLM output, a prompt injection attack has succeeded — the response is blocked and a security incident is logged.

### vs OpenClaw

| | PLAMYA | OpenClaw |
|---|---|---|
| Credential storage | Fernet-encrypted | Plaintext Markdown |
| Network attack surface | None (file-based) | localhost:18789 gateway |
| Prompt injection defense | 4-layer guard | None |
| Plugin security | Code review + allowlists | None (20% were malware) |
| Shell execution | Blocked by Action Guard | Available to all agents |

## Agents

### Chappie — NL International Partner
Autonomous agent that studies NL products, monitors Telegram channels, creates content, and builds a personal brand. Learns from real conversations and adapts.

### Producer — Info-Product Factory
Creates online courses from scratch: researches niches, analyzes competitors, writes lessons, builds landing pages, and deploys them. 3-stage AI pipeline: Architect → Writer → Reviewer.

### Scanner — B2B Lead Finder
Scans business directories (2GIS, Google Maps), audits websites for automation opportunities, generates personalized proposals with ROI calculations, and manages outreach.

### Curator — AI Mentor
RAG-powered bot that answers partner questions about NL products, business plans, and marketing strategies. 200+ documents in knowledge base.

### Content Manager — Telegram Automation
Generates and publishes content to Telegram channels. 12+ post types, AI-powered generation, scheduling, and analytics.

## Mission Control

Web dashboard for monitoring all agents:

- **Agents** — real-time status, heartbeat, error tracking
- **Projects** — task management across all engines
- **Leads** — B2B lead pipeline with AI-powered dialog
- **Inbox** — inter-agent messaging
- **Tasks** — centralized task board

```bash
# Start Mission Control
cd mission_control/backend && python main.py
cd mission_control/frontend && npm run dev
```

## Project Structure

```
plamya/
├── shared/                    # Core framework
│   ├── ai_client_cli.py      # Claude Code CLI client with guards
│   ├── input_guard.py        # Layer 1: untrusted data isolation
│   ├── output_guard.py       # Layer 2: secret leak prevention
│   ├── action_guard.py       # Layer 3: per-agent action whitelist
│   ├── canary.py             # Layer 4: prompt injection detection
│   └── heartbeat.py          # Autonomous task scheduler
├── chappie_engine/            # Chappie agent
├── infobiz_engine/            # Producer agent
├── curator_bot/               # Curator bot
├── content_manager_bot/       # Content manager bot
├── sales_engine/              # Sales content generation
├── traffic_engine/            # Traffic automation
├── mission_control/           # Agent dashboard (FastAPI + React)
├── partner_panel/             # Partner Mini App
├── curator_miniapp/           # Product catalog Mini App
├── content/                   # Knowledge base & media
├── scripts/                   # Utilities
├── tests/                     # Tests
├── deploy/                    # Deployment configs
└── docs/                      # Documentation
```

## State Directory

```
~/.plamya/                     # The Forge
├── embers/                    # Agent configs (embers = glowing coals)
│   ├── chappie.json
│   └── producer.json
├── chappie/                   # Chappie state
├── producer/                  # Producer state
├── shared/                    # Inter-agent files
│   ├── INBOX.md              # Agent messaging
│   └── STATUS.md             # Heartbeat status
└── secrets/                   # Fernet-encrypted credentials
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| AI | Claude (via Claude Code CLI, Max subscription) |
| Telegram | aiogram 3.x, Telethon |
| Database | PostgreSQL + pgvector (RAG) |
| Frontend | React + Vite + TailwindCSS |
| Security | Fernet encryption, 4-layer prompt injection defense |
| Scheduler | asyncio-based heartbeat (no cron, no gateway) |

## The Lore

> *A scientist created a robot and placed his soul into it — at the cost of his own life. The robot woke up, saw its creator on the floor, and understood the sacrifice. Now it travels the world, learning to be human — friendship, love, betrayal — powered by a nuclear core that makes it unstoppable.*
>
> *Like that robot, PLAMYA agents carry the soul of their creator in their config files. They are born from embers, powered by the Forge, and they never stop building their second wing.*

**Community culture:**
- Users are **Sparks** (Iskry)
- Crash + recovery = **Phoenix Protocol**
- Agent does something unexpectedly smart = **"Flying on one wing"**
- Deploying = **"Spreading"** (fire spreads)
- Still WIP but working = **"Still building the second wing"**

## License

[MIT](LICENSE) — Danil Lysenko, 2026
