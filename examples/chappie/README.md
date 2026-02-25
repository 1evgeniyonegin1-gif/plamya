# Chappie — Example PLAMYA Agent

An autonomous Telegram agent that studies products, monitors channels, and creates content.

This example shows how to build an agent using PLAMYA's framework components.

## What Chappie Does

- **Studies products** from a knowledge base and summarizes them
- **Monitors Telegram channels** for relevant content
- **Creates posts** for a personal brand channel
- **Runs autonomously** on a schedule via Heartbeat

## Architecture

```
examples/chappie/
├── config.py          # Agent configuration (paths, limits, schedule)
├── run.py             # Entry point — registers tasks with Heartbeat
└── actions/
    ├── __init__.py
    ├── study_products.py   # Reads files → AI summary
    └── read_channel.py     # Reads Telegram → AI analysis (with Input Guard)
```

## How It Uses PLAMYA

```python
from shared.ai_client_cli import claude_call
from shared.heartbeat import Heartbeat

# AI call with all 4 security layers built in
result = claude_call(
    prompt="Summarize this product for a social media post",
    agent="chappie",
    untrusted_data=channel_message,      # Input Guard wraps this
    untrusted_source="telegram_group",
)

# Autonomous scheduling
hb = Heartbeat()
hb.register("chappie", "study_products", interval_minutes=120)
hb.register("chappie", "read_channels", interval_minutes=30)
await hb.run_forever()
```

## Key Patterns

1. **All external data** (Telegram messages, web content) goes through `untrusted_data` parameter — Input Guard isolates it from LLM instructions
2. **All AI responses** are automatically scanned by Output Guard for leaked secrets
3. **Agent actions** are validated against Action Guard whitelists
4. **Canary tokens** detect prompt injection attempts

## Running

```bash
# Configure
cp ../../.env.example .env
# Set TELEGRAM_API_ID, TELEGRAM_API_HASH

# Run
python run.py
```
