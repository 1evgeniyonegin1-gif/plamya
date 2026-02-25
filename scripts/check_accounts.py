"""Проверка всех Telegram аккаунтов на VPS.

Подключается по SSH к VPS, запускает проверку каждого session файла.
Результат: JSON со статусами (alive/dead/banned/expired).

Использование:
    python scripts/check_accounts.py
"""

import json
import subprocess
import sys

VPS_HOST = "root@194.87.86.103"
SESSIONS_DIR = "/opt/traffic-engine/sessions"

# Скрипт который будет запущен НА VPS
REMOTE_SCRIPT = r'''
import json
import sys
import os
import sqlite3
import asyncio

sys.path.insert(0, "/root/nl-international-ai-bots")

SESSIONS_DIR = "/opt/traffic-engine/sessions"
API_ID = 2496
API_HASH = "8da85b0d5bfe62527e5b244c209159c3"

results = []

def check_session_file(path):
    """Проверить session файл через SQLite — без подключения к Telegram."""
    info = {
        "file": os.path.basename(path),
        "path": path,
        "status": "unknown",
        "dc_id": None,
        "entities": [],
    }
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        # Проверить таблицу sessions
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]

        if "sessions" in tables:
            cursor.execute("SELECT dc_id, server_address, auth_key FROM sessions LIMIT 1")
            row = cursor.fetchone()
            if row:
                info["dc_id"] = row[0]
                info["server"] = row[1]
                info["has_auth_key"] = len(row[2]) > 0 if row[2] else False
                info["status"] = "has_session" if info["has_auth_key"] else "no_auth_key"

        # Проверить entities — кто этот аккаунт
        if "entities" in tables:
            cursor.execute("""
                SELECT id, phone, username, name
                FROM entities
                WHERE phone IS NOT NULL AND phone != ''
                LIMIT 5
            """)
            for row in cursor.fetchall():
                info["entities"].append({
                    "id": row[0],
                    "phone": row[1],
                    "username": row[2],
                    "name": row[3],
                })

        conn.close()
    except Exception as e:
        info["status"] = "error"
        info["error"] = str(e)

    return info


async def test_connection(session_path):
    """Попробовать подключиться к Telegram через session файл."""
    try:
        from telethon import TelegramClient
        from telethon.sessions import SQLiteSession

        client = TelegramClient(
            session_path.replace(".session", ""),
            API_ID,
            API_HASH,
        )
        await client.connect()

        if await client.is_user_authorized():
            me = await client.get_me()
            result = {
                "status": "alive",
                "user_id": me.id,
                "phone": me.phone,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
            }
        else:
            result = {"status": "unauthorized"}

        await client.disconnect()
        return result

    except Exception as e:
        err = str(e)
        if "AuthKeyDuplicated" in err:
            return {"status": "auth_key_duplicated", "error": err[:200]}
        elif "ban" in err.lower() or "forbidden" in err.lower():
            return {"status": "banned", "error": err[:200]}
        elif "flood" in err.lower():
            return {"status": "flood_wait", "error": err[:200]}
        else:
            return {"status": "error", "error": err[:200]}


# Собрать все session файлы
session_files = []
for f in sorted(os.listdir(SESSIONS_DIR)):
    if f.endswith(".session"):
        session_files.append(os.path.join(SESSIONS_DIR, f))

# Фаза 1: быстрая проверка через SQLite (без подключения)
for path in session_files:
    info = check_session_file(path)
    results.append(info)

# Фаза 2: реальное подключение к Telegram (только именованные аккаунты)
named_sessions = [
    "account1.session",
    "karina.session",
    "ua_account1.session",
    "ua_account2.session",
    "ua_account3.session",
    "test_usa.session",
]

connection_results = {}
loop = asyncio.new_event_loop()
for name in named_sessions:
    path = os.path.join(SESSIONS_DIR, name)
    if os.path.exists(path):
        try:
            conn_result = loop.run_until_complete(test_connection(path))
            connection_results[name] = conn_result
        except Exception as e:
            connection_results[name] = {"status": "error", "error": str(e)[:200]}
loop.close()

# Также проверим Чаппи session string
chappie_config_path = os.path.expanduser("~/.plamya/shared/chappie_config.json")
chappie_result = {"status": "no_config"}
if os.path.exists(chappie_config_path):
    try:
        with open(chappie_config_path) as f:
            cfg = json.load(f)
        session_string = cfg.get("session_string", "")
        if session_string:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            client = TelegramClient(
                StringSession(session_string),
                cfg.get("api_id", API_ID),
                cfg.get("api_hash", API_HASH),
            )
            chappie_result = loop.run_until_complete(test_connection_string(client))
    except:
        pass

async def test_connection_string(client):
    try:
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            return {
                "status": "alive",
                "user_id": me.id,
                "phone": me.phone,
                "username": me.username,
                "first_name": me.first_name,
            }
        return {"status": "unauthorized"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}
    finally:
        await client.disconnect()

output = {
    "session_files": results,
    "connection_tests": connection_results,
    "chappie": chappie_result,
    "summary": {
        "total_sessions": len(results),
        "with_auth_key": sum(1 for r in results if r.get("has_auth_key")),
        "alive": sum(1 for r in connection_results.values() if r.get("status") == "alive"),
        "dead": sum(1 for r in connection_results.values() if r.get("status") != "alive"),
    }
}

print("===JSON_START===")
print(json.dumps(output, ensure_ascii=False, indent=2))
print("===JSON_END===")
'''


def main():
    print("Проверяю аккаунты на VPS (194.87.86.103)...\n")

    # Отправляем скрипт на VPS и запускаем
    try:
        result = subprocess.run(
            [
                "ssh", VPS_HOST,
                "cd /root/nl-international-ai-bots && "
                "/root/nl-international-ai-bots/venv/bin/python3 -c "
                f"'''{REMOTE_SCRIPT}'''"
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        print("ОШИБКА: таймаут SSH (120 сек)")
        sys.exit(1)

    if result.returncode != 0:
        # Если не получилось через -c, попробуем через heredoc
        print("Прямой запуск не сработал, пробую через файл...")
        # Записать скрипт на VPS
        write_cmd = subprocess.run(
            ["ssh", VPS_HOST, f"cat > /tmp/check_accounts.py << 'PYEOF'\n{REMOTE_SCRIPT}\nPYEOF"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        result = subprocess.run(
            ["ssh", VPS_HOST,
             "cd /root/nl-international-ai-bots && "
             "/root/nl-international-ai-bots/venv/bin/python3 /tmp/check_accounts.py"],
            capture_output=True,
            text=True,
            timeout=120,
        )

    output = result.stdout
    if result.stderr:
        print(f"Warnings: {result.stderr[:500]}")

    # Извлечь JSON
    if "===JSON_START===" in output:
        json_str = output.split("===JSON_START===")[1].split("===JSON_END===")[0].strip()
        try:
            data = json.loads(json_str)
            print_report(data)
            # Сохранить результат
            with open("scripts/account_check_result.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\nРезультат сохранён: scripts/account_check_result.json")
        except json.JSONDecodeError:
            print(f"Ошибка парсинга JSON:\n{json_str[:500]}")
    else:
        print(f"Вывод скрипта:\n{output[:2000]}")
        if result.stderr:
            print(f"\nОшибки:\n{result.stderr[:1000]}")


def print_report(data):
    summary = data.get("summary", {})
    print(f"{'='*60}")
    print(f"ОТЧЁТ: Telegram аккаунты на VPS")
    print(f"{'='*60}")
    print(f"Всего session файлов: {summary.get('total_sessions', '?')}")
    print(f"С auth key: {summary.get('with_auth_key', '?')}")
    print(f"Живых (проверено): {summary.get('alive', '?')}")
    print(f"Мёртвых: {summary.get('dead', '?')}")

    # Результаты подключений
    conn = data.get("connection_tests", {})
    if conn:
        print(f"\n--- Именованные аккаунты ---")
        for name, info in conn.items():
            status = info.get("status", "?")
            if status == "alive":
                phone = info.get("phone", "?")
                username = info.get("username", "?")
                fname = info.get("first_name", "?")
                print(f"  ✅ {name}: {fname} (@{username}, +{phone})")
            else:
                error = info.get("error", "")[:100]
                print(f"  ❌ {name}: {status} — {error}")

    # Чаппи
    chappie = data.get("chappie", {})
    if chappie.get("status") == "alive":
        print(f"\n  ✅ Чаппи: {chappie.get('first_name', '?')} (@{chappie.get('username', '?')})")
    else:
        print(f"\n  ⚠️  Чаппи: {chappie.get('status', '?')}")

    # Entities из session файлов
    sessions = data.get("session_files", [])
    named = [s for s in sessions if not s["file"].startswith(("21", "+"))]
    if named:
        print(f"\n--- Детали session файлов ---")
        for s in named:
            entities = s.get("entities", [])
            if entities:
                ent = entities[0]
                print(f"  {s['file']}: {ent.get('name', '?')} (+{ent.get('phone', '?')})")


if __name__ == "__main__":
    main()
