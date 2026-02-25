"""Позволяет запускать как python -m chappie_engine.run.

ВАЖНО: Фикс platform/ конфликта должен быть ДО любых импортов.
Директория platform/ в проекте затеняет stdlib platform модуль,
что ломает aiohttp → multidict → platform.python_implementation().
"""

import sys
from pathlib import Path

# Fix: убираем проект из начала sys.path чтобы stdlib platform
# имел приоритет перед нашей директорией platform/
_project_dir = str(Path(__file__).parent.parent)
_project_dir_lower = _project_dir.lower().replace("\\", "/")

_clean_path = []
_project_entries = []
for p in sys.path:
    if p.lower().replace("\\", "/") == _project_dir_lower:
        _project_entries.append(p)
    else:
        _clean_path.append(p)

# Ставим проект в конец — после stdlib
sys.path = _clean_path + _project_entries

from chappie_engine.run import main

main()
