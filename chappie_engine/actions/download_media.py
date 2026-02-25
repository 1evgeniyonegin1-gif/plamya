"""Скачать медиа из сообщений группы/канала + транскрипция через Whisper.

Транскрипция через faster-whisper (локально, CPU).
Модель скачивается при первом запуске (~300MB).
"""

import json
import logging
import re
from pathlib import Path

from chappie_engine.client import PersonalAccountClient
from chappie_engine.state.state_manager import StateManager
from chappie_engine.safety import SafetyGuard

logger = logging.getLogger("chappie.download_media")

MEDIA_DIR = Path(__file__).parent.parent / "content" / "downloaded_media"

# Singleton для модели Whisper (тяжёлая, загружаем один раз)
_whisper_model = None


def _get_whisper_model():
    """Загрузить faster-whisper модель (lazy singleton)."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            logger.info("Загружаю faster-whisper модель (base)...")
            _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            logger.info("Модель загружена")
        except ImportError:
            logger.error("faster-whisper не установлен: pip install faster-whisper")
            return None
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            return None
    return _whisper_model


async def transcribe_audio(file_path: str) -> str | None:
    """Транскрибировать аудио/видео файл через faster-whisper (локально).

    Поддерживает: .ogg, .oga, .opus, .mp4, .mp3, .wav, .m4a
    Возвращает текст или None если не удалось.
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"Файл не найден для транскрипции: {file_path}")
        return None

    model = _get_whisper_model()
    if model is None:
        return None

    try:
        segments, info = model.transcribe(
            str(path),
            language="ru",
            beam_size=3,
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        if text:
            logger.info(f"Транскрибировано {path.name}: {len(text)} символов ({info.duration:.1f}с аудио)")
            return text
        return None
    except Exception as e:
        logger.error(f"Ошибка транскрипции {path.name}: {e}")
        return None


async def run(group_identifier: str, limit: int = 10, media_types: str = "photo,voice",
              transcribe: bool = True):
    """Скачать медиа из группы/канала и транскрибировать голосовые.

    Args:
        group_identifier: Username или ID группы
        limit: Сколько сообщений просканировать (макс 20)
        media_types: Типы медиа через запятую (photo, voice, video, document)
        transcribe: Транскрибировать голосовые/видео через Whisper
    """
    sm = StateManager()
    sg = SafetyGuard(sm)

    can, reason = sg.can_perform("read")
    if not can:
        print(f"Нельзя: {reason}")
        return

    limit = min(limit, 20)
    wanted = set(media_types.split(","))
    group_identifier = group_identifier.lstrip("@")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Сканирую {group_identifier} на медиа ({media_types}), лимит {limit}...")

    try:
        async with PersonalAccountClient() as pac:
            client = pac.client

            try:
                entity = await client.get_entity(group_identifier)
            except Exception:
                try:
                    entity = await client.get_entity(int(group_identifier))
                except Exception:
                    print(f"Группа/чат {group_identifier} не найден")
                    return

            title = getattr(entity, 'title', group_identifier)
            downloaded = []

            async for message in client.iter_messages(entity, limit=limit):
                if not message.media:
                    continue

                media_type = _classify_media(message)
                if media_type not in wanted:
                    continue

                # Скачать
                safe_name = re.sub(r'[^\w\-]', '_', group_identifier)
                filename = f"{safe_name}_{message.id}"

                try:
                    path = await client.download_media(
                        message,
                        file=str(MEDIA_DIR / filename),
                    )
                    if path:
                        info = {
                            "id": message.id,
                            "type": media_type,
                            "path": str(path),
                            "date": message.date.strftime("%Y-%m-%d %H:%M"),
                            "caption": (message.text or "")[:200],
                        }
                        if media_type == "voice":
                            for attr in getattr(message.media.document, 'attributes', []):
                                if hasattr(attr, 'duration'):
                                    info["duration_sec"] = attr.duration
                                    break

                        # Транскрипция голосовых и видео
                        if transcribe and media_type in ("voice", "video"):
                            print(f"  Транскрибирую {media_type} (msg {message.id})...")
                            transcript = await transcribe_audio(path)
                            if transcript:
                                info["transcript"] = transcript
                                print(f"    Текст: {transcript[:150]}...")
                            else:
                                info["transcript"] = None
                                print(f"    Транскрипция не удалась")

                        downloaded.append(info)
                        print(f"  {media_type}: {Path(path).name}")
                except Exception as e:
                    logger.warning(f"Не удалось скачать медиа {message.id}: {e}")

            sg.record_action("read", success=True)

            print(f"\n--- Результат ---")
            print(f"Группа: {title}")
            print(f"Просканировано: {limit} сообщений")
            print(f"Скачано: {len(downloaded)} файлов")

            transcribed = [d for d in downloaded if d.get("transcript")]
            if transcribed:
                print(f"Транскрибировано: {len(transcribed)} файлов")

            if downloaded:
                # Сохранить метаданные
                meta_path = MEDIA_DIR / f"{re.sub(r'[^\\w\\-]', '_', group_identifier)}_meta.json"
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(downloaded, f, ensure_ascii=False, indent=2)
                print(f"Метаданные: {meta_path}")

                # Сохранить транскрипции в дневник
                if transcribed:
                    knowledge = sm.load_knowledge()
                    transcriptions = knowledge.get("transcriptions", [])
                    for t in transcribed:
                        transcriptions.append({
                            "group": group_identifier,
                            "msg_id": t["id"],
                            "type": t["type"],
                            "date": t["date"],
                            "text": t["transcript"],
                            "transcribed_at": _today_str(),
                        })
                    knowledge["transcriptions"] = transcriptions[-200:]  # Последние 200
                    sm.save_knowledge(knowledge)
                    print(f"Транскрипции сохранены в дневник ({len(transcribed)} шт)")

            sm.update_status(f"Скачано {len(downloaded)} медиа из {title}")

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        sg.record_action("read", success=False)

        error_msg = str(e).lower()
        if "flood" in error_msg:
            match = re.search(r"(\d+)", str(e))
            if match:
                sg.handle_flood_wait(int(match.group(1)))
        elif "ban" in error_msg or "forbidden" in error_msg:
            sg.handle_ban_error(str(e))

        print(f"Ошибка: {e}")


def _classify_media(message) -> str:
    """Определить тип медиа."""
    media = message.media
    type_name = type(media).__name__

    if "Photo" in type_name:
        return "photo"
    if "Document" in type_name:
        if hasattr(media, 'document') and media.document:
            mime = getattr(media.document, 'mime_type', '') or ''
            if 'audio/ogg' in mime or 'opus' in mime:
                return "voice"
            if 'video' in mime:
                return "video"
            if 'image' in mime:
                return "photo"
        return "document"
    return "other"


def _today_str() -> str:
    from datetime import datetime, timezone, timedelta
    msk = timezone(timedelta(hours=3))
    return datetime.now(msk).strftime("%Y-%m-%d")
