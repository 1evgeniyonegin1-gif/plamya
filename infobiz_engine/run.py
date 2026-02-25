"""CLI точка входа для Infobiz Engine (ПРОДЮСЕР).

Использование:
    python -m infobiz_engine <action> [args]

Действия:
    get_status                          — Показать статус пайплайна
    research_niche [query]              — Найти и оценить ниши
    analyze_competitors <niche_slug>    — Проанализировать конкурентов в нише
    create_course <niche_slug>          — Сгенерировать курс (структура + уроки)
    build_landing <product_id>          — Создать HTML лендинг
    deploy_site <product_id>            — Задеплоить лендинг на VPS
    setup_payment <product_id> <price>  — Создать ссылку на оплату
    check_sales                         — Проверить продажи
    publish_promo <product_id>          — Сгенерировать промо-контент
    escalate <type> <description>       — Эскалировать в INBOX (feature_request/bug/permission/question)
"""

import asyncio
import io
import sys

# Windows encoding fix - ДОЛЖЕН БЫТЬ ПЕРВЫМ
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Fix: platform/ directory in project shadows stdlib platform module.
_project_dir = str(__import__("pathlib").Path(__file__).parent.parent)
sys.path = [p for p in sys.path if p != _project_dir]
sys.path.append(_project_dir)

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        return

    action = args[0]

    if action == "get_status":
        from infobiz_engine.actions.get_status import run
        asyncio.run(run())

    elif action == "research_niche":
        query = args[1] if len(args) > 1 else ""
        from infobiz_engine.actions.research_niche import run
        asyncio.run(run(query=query))

    elif action == "analyze_competitors":
        if len(args) < 2:
            print("Использование: analyze_competitors <niche_slug>")
            print("Пример: analyze_competitors telegram-bots")
            return
        niche_slug = args[1]
        from infobiz_engine.actions.analyze_competitors import run
        asyncio.run(run(niche_slug=niche_slug))

    elif action == "create_course":
        if len(args) < 2:
            print("Использование: create_course <niche_slug>")
            print("Пример: create_course telegram-bots")
            return
        niche_slug = args[1]
        from infobiz_engine.actions.create_course import run
        asyncio.run(run(niche_slug=niche_slug))

    elif action == "build_landing":
        if len(args) < 2:
            print("Использование: build_landing <product_id>")
            return
        product_id = args[1]
        from infobiz_engine.actions.build_landing import run
        asyncio.run(run(product_id=product_id))

    elif action == "deploy_site":
        if len(args) < 2:
            print("Использование: deploy_site <product_id>")
            return
        product_id = args[1]
        from infobiz_engine.actions.deploy_site import run
        asyncio.run(run(product_id=product_id))

    elif action == "setup_payment":
        if len(args) < 3:
            print("Использование: setup_payment <product_id> <price_rub>")
            print("Пример: setup_payment prod_001 4990")
            return
        product_id = args[1]
        price_rub = int(args[2])
        from infobiz_engine.actions.setup_payment import run
        asyncio.run(run(product_id=product_id, price_rub=price_rub))

    elif action == "check_sales":
        from infobiz_engine.actions.check_sales import run
        asyncio.run(run())

    elif action == "publish_promo":
        if len(args) < 2:
            print("Использование: publish_promo <product_id>")
            return
        product_id = args[1]
        from infobiz_engine.actions.publish_promo import run
        asyncio.run(run(product_id=product_id))

    elif action == "escalate":
        if len(args) < 3:
            print("Использование: escalate <type> <description> [--why ...] [--priority ...]")
            print("Типы: feature_request, permission, bug, question")
            return

        esc_type = args[1]
        description = args[2]

        why = ""
        priority = "medium"
        i = 3
        while i < len(args):
            if args[i] == "--why" and i + 1 < len(args):
                why = args[i + 1]
                i += 2
            elif args[i] == "--priority" and i + 1 < len(args):
                priority = args[i + 1]
                i += 2
            else:
                i += 1

        from infobiz_engine.actions.escalate import run
        asyncio.run(run(
            escalation_type=esc_type,
            description=description,
            why_needed=why,
            priority=priority,
        ))

    else:
        print(f"Неизвестное действие: {action}")
        print(__doc__)


if __name__ == "__main__":
    main()
