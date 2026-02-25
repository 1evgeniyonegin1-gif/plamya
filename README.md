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

Build agents that work autonomously: research, create content, analyze competitors, generate leads, manage Telegram channels — all while protecting your secrets and blocking prompt injection attacks.

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
git clone https://github.com/1evgeniyonegin1-gif/plamya.git
cd plamya

# Install
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Fill in your Telegram bot token

# Try the example agent
cd examples/chappie
python run.py
```

## Architecture

```
PLAMYA
├── Core Framework (shared/)
│   ├── AI Client ......... Claude Code CLI (Max subscription, no API key)
│   ├── Input Guard ....... Isolates untrusted data from LLM instructions
│   ├── Output Guard ...... Regex scanning for secret leaks
│   ├── Action Guard ...... Per-agent action whitelist
│   ├── Canary Token ...... Detects system prompt exfiltration
│   ├── Heartbeat ......... Autonomous task scheduler
│   ├── RAG Engine ........ pgvector-based retrieval
│   ├── Persona System .... Dynamic personality injection
│   └── AI Clients ........ Multi-provider (Claude, Deepseek, OpenAI, YandexGPT, GigaChat)
│
├── Runtime
│   ├── State ............. ~/.plamya/ (file-based, no network gateway)
│   ├── Embers ............ Agent configs (embers = glowing coals)
│   └── Secrets ........... Fernet-encrypted credentials
│
└── Examples
    └── Chappie ........... Autonomous Telegram agent example
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

## Building an Agent

```python
from shared.ai_client_cli import claude_call
from shared.heartbeat import Heartbeat

# 1. Make AI calls with all security layers built in
result = claude_call(
    prompt="Analyze this data and suggest next steps",
    agent="my_agent",
    untrusted_data=external_input,       # Input Guard isolates this
    untrusted_source="telegram_message",
)

# 2. Schedule autonomous tasks
hb = Heartbeat()
hb.register("my_agent", "check_messages", interval_minutes=30, callback=check_messages)
hb.register("my_agent", "daily_report", interval_minutes=1440, callback=daily_report)
await hb.run_forever()
```

See [examples/chappie/](examples/chappie/) for a complete working agent.

## Project Structure

```
plamya/
├── shared/                    # Core framework
│   ├── ai_client_cli.py      # Claude Code CLI client with all guards
│   ├── input_guard.py        # Layer 1: untrusted data isolation
│   ├── output_guard.py       # Layer 2: secret leak prevention
│   ├── action_guard.py       # Layer 3: per-agent action whitelist
│   ├── canary.py             # Layer 4: prompt injection detection
│   ├── heartbeat.py          # Autonomous task scheduler
│   ├── ai_clients/           # Multi-provider LLM abstraction
│   ├── config/               # Settings management
│   ├── database/             # PostgreSQL + SQLAlchemy models
│   ├── rag/                  # RAG engine (pgvector embeddings)
│   ├── persona/              # Dynamic personality system
│   └── utils/                # Logging utilities
├── examples/                  # Example agents
│   └── chappie/              # Autonomous Telegram agent
├── docs/                      # Documentation
└── tests/                     # Tests
```

## State Directory

```
~/.plamya/                     # The Forge
├── embers/                    # Agent configs (embers = glowing coals)
│   ├── chappie.json
│   └── my_agent.json
├── chappie/                   # Agent state
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
