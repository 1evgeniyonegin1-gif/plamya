import sys
# Remove project dir that shadows stdlib platform module, but keep venv
sys.path = [p for p in sys.path if not (
    ('nl-international-ai-bots' in p or 'apexflow' in p)
    and 'site-packages' not in p
    and 'venv' not in p
)]

import asyncio, os, json

API_ID = 2496
API_HASH = '8da85b0d5bfe62527e5b244c209159c3'
SESSIONS_DIR = '/opt/traffic-engine/sessions'

results = {}

async def check(name):
    path = os.path.join(SESSIONS_DIR, name)
    if not os.path.exists(path):
        results[name] = {'status': 'file_not_found'}
        return
    try:
        from telethon import TelegramClient
        c = TelegramClient(path.replace('.session',''), API_ID, API_HASH)
        await c.connect()
        if await c.is_user_authorized():
            me = await c.get_me()
            results[name] = {
                'status': 'alive',
                'user_id': me.id,
                'phone': me.phone,
                'username': me.username,
                'first_name': me.first_name,
                'last_name': me.last_name or '',
            }
        else:
            results[name] = {'status': 'unauthorized'}
        await c.disconnect()
    except Exception as e:
        err = str(e)
        if 'AuthKeyDuplicated' in err:
            results[name] = {'status': 'auth_key_duplicated'}
        elif 'ban' in err.lower():
            results[name] = {'status': 'banned'}
        elif 'flood' in err.lower():
            results[name] = {'status': 'flood_wait', 'error': err[:150]}
        else:
            results[name] = {'status': 'error', 'error': err[:150]}

async def main():
    targets = [
        'account1.session',
        'karina.session',
        'ua_account1.session',
        'ua_account2.session',
        'ua_account3.session',
        'test_usa.session',
    ]
    for t in targets:
        await check(t)
    print(json.dumps(results, ensure_ascii=False, indent=2))

asyncio.run(main())
