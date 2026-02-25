"""Создание HTML лендинга для продукта."""

import json
import logging
from pathlib import Path

from infobiz_engine.state.state_manager import StateManager
from infobiz_engine.ai.copywriter import generate_landing_copy
from infobiz_engine.config import CONTENT_DIR

logger = logging.getLogger("producer.landing")

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "landing"
ICONS = ["📚", "🎯", "💡", "🚀", "⚡", "🔥", "💪", "🏆"]


async def run(product_id: str):
    """Создать HTML лендинг для продукта.

    Args:
        product_id: ID продукта из PRODUCER_PRODUCTS.json
    """
    sm = StateManager()

    product = sm.get_product(product_id)
    if not product:
        print(f"Продукт не найден: {product_id}")
        products = sm.load_products()
        if products.get("products"):
            print("Доступные продукты:")
            for p in products["products"]:
                print(f"  {p['id']} — {p.get('title', '?')} [{p.get('status', '?')}]")
        return

    course_dir = Path(product.get("course_dir", ""))
    course_json = course_dir / "course.json"

    if not course_json.exists():
        print(f"Файл курса не найден: {course_json}")
        print("Сначала выполни create_course для этой ниши.")
        return

    with open(course_json, "r", encoding="utf-8") as f:
        course = json.load(f)

    course_title = course.get("title", product.get("title", "Курс"))
    modules = course.get("modules", [])
    price_rub = product.get("price_rub", 4990)

    print(f"Генерирую лендинг для: {course_title}...")
    print()

    # Генерация copy через AI
    try:
        copy = await generate_landing_copy(
            course_title=course_title,
            course_subtitle=course.get("subtitle", ""),
            target_audience=course.get("target_audience", ""),
            modules=modules,
            price_rub=price_rub,
            learning_outcomes=course.get("learning_outcomes"),
        )
    except Exception as e:
        print(f"Ошибка AI: {e}")
        return

    if not copy:
        print("AI не вернул текст лендинга.")
        return

    # Прочитать шаблон
    template_path = TEMPLATE_DIR / "base.html"
    template = template_path.read_text(encoding="utf-8")

    # Заполнить шаблон (простая замена {{ }})
    benefits = copy.get("solution_section", {}).get("benefits", [])
    for i, b in enumerate(benefits):
        b["icon"] = ICONS[i % len(ICONS)]

    problem_section = copy.get("problem_section", {})
    author = copy.get("author_section", {})
    author_name = author.get("name", "Автор")
    initials = "".join(w[0] for w in author_name.split()[:2]).upper() if author_name else "AV"

    # Сборка HTML через string replace (без jinja2 dependency)
    html = template
    replacements = {
        "{{ hero_title }}": copy.get("hero_title") or course_title,
        "{{ hero_subtitle }}": copy.get("hero_subtitle") or "",
        "{{ course_title }}": course_title,
        "{{ cta_text }}": copy.get("cta_text") or "Начать обучение",
        "{{ problem_title }}": problem_section.get("title") or "Знакомо?",
        "{{ solution_title }}": copy.get("solution_section", {}).get("title") or "Что ты получишь",
        "{{ program_intro }}": copy.get("program_intro") or "",
        "{{ author_initials }}": initials,
        "{{ author_name }}": author_name,
        "{{ author_bio }}": author.get("bio") or "",
        "{{ price_rub }}": str(price_rub),
        "{{ guarantee_text }}": copy.get("guarantee_text") or "",
        "{{ payment_url }}": product.get("payment_url") or "",
    }

    for key, val in replacements.items():
        html = html.replace(key, str(val) if val is not None else "")

    # Генерация секций с циклами (problems, benefits, modules, testimonials, faq)
    html = _render_list_section(html, "problems", problem_section.get("problems", []))
    html = _render_benefits(html, benefits)
    html = _render_modules(html, modules)
    html = _render_testimonials(html, copy.get("testimonials", []))
    html = _render_author_credentials(html, author.get("credentials", []))
    html = _render_faq(html, copy.get("faq", []))

    # Сохранить HTML
    output_dir = course_dir / "landing"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "index.html"
    output_file.write_text(html, encoding="utf-8")

    # Обновить продукт
    sm.update_product(product_id, {"status": "landing_ready"})
    sm.record_action("build_landing")
    sm.update_pipeline_stage("landing", {"status": "active", "pages_built": 1})

    print(f"Лендинг создан: {output_file}")
    print(f"Откройте в браузере для предпросмотра.")
    print(f"Для деплоя: deploy_site {product_id}")

    sm.update_status(f"Лендинг создан: {course_title}")


def _render_list_section(html: str, tag: str, items: list) -> str:
    """Заменить {% for X in TAG %} ... {% endfor %} на повторённые блоки."""
    import re

    pattern = rf'{{% for \w+ in {tag} %}}(.*?){{% endfor %}}'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return html

    template_block = match.group(1)
    result_blocks = []
    for item in items:
        block = template_block.replace(f"{{{{ {tag[:-1] if tag.endswith('s') else tag} }}}}", str(item) if item is not None else "")
        # Handle {{ problem }} style
        block = block.replace("{{ problem }}", str(item) if item is not None else "")
        result_blocks.append(block)

    return html[:match.start()] + "\n".join(result_blocks) + html[match.end():]


def _render_benefits(html: str, benefits: list) -> str:
    import re
    pattern = r'{% for benefit in benefits %}(.*?){% endfor %}'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return html

    block = match.group(1)
    parts = []
    for b in benefits:
        p = block.replace("{{ benefit.icon }}", b.get("icon") or "💡")
        p = p.replace("{{ benefit.title }}", b.get("title") or "")
        p = p.replace("{{ benefit.description }}", b.get("description") or "")
        parts.append(p)

    return html[:match.start()] + "\n".join(parts) + html[match.end():]


def _render_modules(html: str, modules: list) -> str:
    import re
    outer = re.search(r'{% for module in modules %}(.*?){% endfor %}\s*</div>\s*</div>\s*</section>', html, re.DOTALL)
    if not outer:
        return html

    module_block = outer.group(1)
    parts = []

    for m in modules:
        p = module_block.replace("{{ module.module_num }}", str(m.get("module_num") or ""))
        p = p.replace("{{ module.title }}", m.get("title") or "")
        p = p.replace("{{ module.description }}", m.get("description") or "")

        # Render lessons inside module
        lesson_match = re.search(r'{% for lesson in module.lessons %}(.*?){% endfor %}', p, re.DOTALL)
        if lesson_match:
            lesson_block = lesson_match.group(1)
            lesson_parts = []
            for les in m.get("lessons", []):
                lp = lesson_block.replace("{{ lesson.lesson_num }}", str(les.get("lesson_num") or ""))
                lp = lp.replace("{{ lesson.title }}", les.get("title") or "")
                lp = lp.replace("{{ lesson.duration_min }}", str(les.get("duration_min") or 15))
                lesson_parts.append(lp)
            p = p[:lesson_match.start()] + "\n".join(lesson_parts) + p[lesson_match.end():]

        parts.append(p)

    return html[:outer.start()] + "\n".join(parts) + html[outer.end():]


def _render_testimonials(html: str, testimonials: list) -> str:
    import re
    # Handle {% if testimonials %} ... {% endif %}
    if_match = re.search(r'{% if testimonials %}(.*?){% endif %}', html, re.DOTALL)
    if not if_match:
        return html

    if not testimonials:
        return html[:if_match.start()] + html[if_match.end():]

    section = if_match.group(1)
    inner = re.search(r'{% for t in testimonials %}(.*?){% endfor %}', section, re.DOTALL)
    if not inner:
        return html

    block = inner.group(1)
    parts = []
    for t in testimonials:
        p = block.replace("{{ t.text }}", t.get("text") or "")
        p = p.replace("{{ t.name }}", t.get("name") or "")
        p = p.replace("{{ t.result }}", t.get("result") or "")
        parts.append(p)

    rendered_section = section[:inner.start()] + "\n".join(parts) + section[inner.end():]
    return html[:if_match.start()] + rendered_section + html[if_match.end():]


def _render_author_credentials(html: str, credentials: list) -> str:
    import re
    pattern = r'{% for cred in author_credentials %}(.*?){% endfor %}'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return html

    block = match.group(1)
    parts = [block.replace("{{ cred }}", c or "") for c in credentials]
    return html[:match.start()] + "\n".join(parts) + html[match.end():]


def _render_faq(html: str, faq: list) -> str:
    import re
    if_match = re.search(r'{% if faq %}(.*?){% endif %}', html, re.DOTALL)
    if not if_match:
        return html

    if not faq:
        return html[:if_match.start()] + html[if_match.end():]

    section = if_match.group(1)
    inner = re.search(r'{% for item in faq %}(.*?){% endfor %}', section, re.DOTALL)
    if not inner:
        return html

    block = inner.group(1)
    parts = []
    for item in faq:
        p = block.replace("{{ item.question }}", item.get("question") or "")
        p = p.replace("{{ item.answer }}", item.get("answer") or "")
        parts.append(p)

    rendered = section[:inner.start()] + "\n".join(parts) + section[inner.end():]
    return html[:if_match.start()] + rendered + html[if_match.end():]
