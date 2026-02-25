"""PLAMYA AI Client — общий AI-клиент через Claude Code CLI.

Используется подписка Claude Max (без API ключей).
Встроены все 4 уровня защиты:
- Input Guard: изоляция внешних данных
- Output Guard: фильтрация утечек
- Canary Token: детекция prompt injection
- Action Guard: whitelist (на уровне вызывающего кода)

Fallback на Deepseek если CLI недоступен.
"""

import json
import logging
import os
import platform
import shutil
import subprocess
from typing import Optional

from shared.canary import check_canary, generate_canary, inject_canary
from shared.input_guard import detect_injection, wrap_untrusted
from shared.output_guard import guard_output

logger = logging.getLogger(__name__)

# Claude Code CLI
CLAUDE_CODE_CLI = os.getenv(
    "CLAUDE_CODE_CLI",
    "claude.cmd" if platform.system() == "Windows" else "claude",
)
CLAUDE_CODE_TIMEOUT = int(os.getenv("CLAUDE_CODE_TIMEOUT", "120"))

# Deepseek fallback
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def claude_call(
    prompt: str,
    agent: str = "unknown",
    system_prompt: str = "",
    untrusted_data: Optional[str] = None,
    untrusted_source: str = "external",
    max_turns: int = 1,
    timeout: Optional[int] = None,
) -> Optional[str]:
    """Вызов Claude через CLI с полной защитой.

    Args:
        prompt: основной промпт (инструкции)
        agent: имя агента (для логов и guards)
        system_prompt: системный промпт (будет prepend к prompt)
        untrusted_data: внешние данные для анализа (будут изолированы)
        untrusted_source: источник внешних данных
        max_turns: количество итераций Claude
        timeout: таймаут в секундах (по умолчанию CLAUDE_CODE_TIMEOUT)

    Returns:
        Ответ Claude (очищенный от секретов) или None при ошибке.
    """
    timeout = timeout or CLAUDE_CODE_TIMEOUT

    # --- Input Guard ---
    if untrusted_data:
        if detect_injection(untrusted_data):
            logger.warning(
                f"INPUT GUARD [{agent}]: обнаружена попытка prompt injection "
                f"в данных от '{untrusted_source}'"
            )
        wrapped_data = wrap_untrusted(untrusted_data, untrusted_source)
        prompt = f"{prompt}\n\n{wrapped_data}"

    # --- Canary Token ---
    canary = generate_canary()
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{inject_canary(system_prompt, canary)}\n\n{prompt}"
    else:
        full_prompt = inject_canary(prompt, canary)

    # --- Вызов Claude CLI ---
    result = _call_claude_cli(full_prompt, max_turns=max_turns, timeout=timeout)

    # Fallback на Deepseek
    if result is None and DEEPSEEK_API_KEY:
        logger.info(f"[{agent}] Claude CLI недоступен, fallback на Deepseek")
        result = _call_deepseek(full_prompt)

    if result is None:
        return None

    # --- Canary Check ---
    if not check_canary(result, canary, agent=agent):
        logger.critical(f"[{agent}] Prompt injection detected — ответ заблокирован")
        return "[Ответ заблокирован по безопасности]"

    # --- Output Guard ---
    result = guard_output(result, agent=agent)

    return result


def _call_claude_cli(
    prompt: str,
    max_turns: int = 1,
    timeout: int = 120,
) -> Optional[str]:
    """Низкоуровневый вызов Claude Code CLI."""
    if not shutil.which(CLAUDE_CODE_CLI):
        logger.warning("Claude Code CLI не найден в PATH")
        return None

    try:
        env = dict(os.environ)
        env.pop("CLAUDECODE", None)  # убираем для избежания nested session

        cmd = [
            CLAUDE_CODE_CLI, "-p", prompt,
            "--output-format", "json",
            "--max-turns", str(max_turns),
        ]

        # Windows .cmd требует cmd /c без shell=True
        if platform.system() == "Windows" and CLAUDE_CODE_CLI.endswith(".cmd"):
            cmd = ["cmd", "/c"] + cmd

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            env=env,
        )

        if result.returncode != 0:
            stderr = result.stderr[:300] if result.stderr else "no stderr"
            logger.warning(f"Claude CLI error (code {result.returncode}): {stderr}")
            return None

        stdout = result.stdout.strip()
        if not stdout:
            return None

        data = json.loads(stdout)
        text = data.get("result", "")
        return text.strip() if text else None

    except subprocess.TimeoutExpired:
        logger.warning(f"Claude CLI: таймаут ({timeout}с)")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Claude CLI: невалидный JSON: {e}")
        return None
    except Exception as e:
        logger.warning(f"Claude CLI exception: {e}")
        return None


def _call_deepseek(prompt: str) -> Optional[str]:
    """Fallback вызов Deepseek через httpx."""
    if not DEEPSEEK_API_KEY:
        return None

    try:
        import httpx
    except ImportError:
        logger.warning("httpx не установлен — Deepseek fallback недоступен")
        return None

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"Deepseek fallback error: {e}")
        return None
