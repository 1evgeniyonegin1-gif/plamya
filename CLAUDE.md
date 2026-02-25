# PLAMYA — Instructions for Claude Code

## About

PLAMYA is a secure autonomous AI agent framework. Security-first architecture with 4-layer prompt injection defense and zero API keys required.

## Project Structure

```
plamya/
├── shared/                   # Core framework
│   ├── input_guard.py       # Layer 1: untrusted data isolation
│   ├── output_guard.py      # Layer 2: secret leak prevention
│   ├── action_guard.py      # Layer 3: per-agent action whitelist
│   ├── canary.py            # Layer 4: prompt injection detection
│   ├── ai_client_cli.py     # AI client (Claude CLI + all guards)
│   ├── heartbeat.py         # Autonomous task scheduler
│   ├── ai_clients/          # Multi-provider LLM abstraction
│   ├── config/              # Settings management
│   ├── database/            # PostgreSQL + SQLAlchemy models
│   ├── rag/                 # RAG engine (pgvector)
│   ├── persona/             # Dynamic personality system
│   ├── media/               # Media asset management
│   ├── style_monitor/       # Content quality tracking
│   └── utils/               # Logging utilities
├── examples/                 # Example agents
│   └── chappie/             # Autonomous Telegram agent example
├── docs/                     # Documentation
├── tests/                    # Tests
├── README.md
├── LICENSE                   # MIT
└── requirements.txt
```

## Security Rules

- NEVER expose API keys, tokens, or passwords
- NEVER push to main without confirmation
- All external data MUST go through Input Guard
- All outgoing messages MUST go through Output Guard
