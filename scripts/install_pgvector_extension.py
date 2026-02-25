"""
Установка расширения pgvector в PostgreSQL
"""
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import asyncpg


# Загружаем переменные окружения
load_dotenv()


async def install_pgvector():
    """Устанавливает расширение pgvector в PostgreSQL"""

    print("🔄 Подключаемся к базе данных...")

    # Получаем DATABASE_URL из переменных окружения
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("\n❌ Ошибка: DATABASE_URL не найден в .env файле")
        print("   Убедитесь что .env файл существует и содержит DATABASE_URL")
        return False

    # Преобразуем asyncpg URL в обычный PostgreSQL URL для psycopg2
    # asyncpg использует postgresql+asyncpg://, а нам нужен postgresql://
    db_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        # Подключаемся к базе через asyncpg
        conn = await asyncpg.connect(db_url)

        print("✅ Подключение к базе данных установлено")

        # Проверяем существующие расширения
        print("🔍 Проверяем наличие расширения pgvector...")
        existing = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'"
        )

        if existing:
            print("ℹ️  Расширение pgvector уже установлено")
        else:
            # Устанавливаем расширение pgvector
            print("📦 Устанавливаем расширение pgvector...")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("✅ Расширение pgvector успешно установлено!")

        # Проверяем что расширение установлено
        result = await conn.fetchrow(
            "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"
        )

        if result:
            print(f"✅ Расширение подтверждено: {result['extname']} (версия {result['extversion']})")
        
        await conn.close()

        print("\n🎉 Готово! Теперь можно использовать векторный поиск в RAG системе.")
        return True

    except asyncpg.InvalidCatalogNameError:
        print(f"\n❌ Ошибка: База данных не существует")
        print(f"   Создайте базу данных перед установкой расширения")
        return False

    except asyncpg.InsufficientPrivilegeError:
        print(f"\n❌ Ошибка: Недостаточно прав для установки расширения")
        print(f"   Убедитесь что пользователь имеет права CREATE EXTENSION")
        return False

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print(f"\n💡 Проверьте:")
        print(f"   1. DATABASE_URL в .env файле корректен")
        print(f"   2. PostgreSQL запущен и доступен")
        print(f"   3. База данных существует")
        return False


if __name__ == "__main__":
    import asyncio
    
    print("=" * 60)
    print("🚀 Установка расширения pgvector для PostgreSQL")
    print("=" * 60)
    print()

    try:
        success = asyncio.run(install_pgvector())

        if not success:
            print("\n⚠️  Исправьте ошибки и запустите скрипт снова")
            sys.exit(1)
        else:
            print("\n✅ Установка завершена успешно!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Установка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        sys.exit(1)
