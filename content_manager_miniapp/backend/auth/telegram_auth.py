"""
Telegram Mini App Authentication Service

Validates initData from Telegram WebApp.
Reuses the same pattern as partner_panel.
"""
import hashlib
import hmac
import json
from datetime import datetime
from urllib.parse import parse_qs, unquote
from typing import Optional
from dataclasses import dataclass

from ..config import settings


@dataclass
class TelegramUser:
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: bool = False
    photo_url: Optional[str] = None


@dataclass
class WebAppInitData:
    user: TelegramUser
    auth_date: datetime
    hash: str
    query_id: Optional[str] = None
    start_param: Optional[str] = None


class TelegramAuthService:
    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or settings.bot_token

    def validate_init_data(self, init_data: str) -> Optional[WebAppInitData]:
        try:
            parsed = parse_qs(init_data)
            received_hash = parsed.get("hash", [None])[0]
            if not received_hash:
                return None

            data_check_string = "\n".join(
                f"{key}={unquote(parsed[key][0])}"
                for key in sorted(parsed.keys())
                if key != "hash"
            )

            secret_key = hmac.new(
                b"WebAppData",
                self.bot_token.encode(),
                hashlib.sha256,
            ).digest()

            calculated_hash = hmac.new(
                secret_key,
                data_check_string.encode(),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(calculated_hash, received_hash):
                return None

            user_data = json.loads(unquote(parsed.get("user", ["{}"])[0]))
            user = TelegramUser(
                id=user_data.get("id"),
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name"),
                username=user_data.get("username"),
                language_code=user_data.get("language_code"),
                is_premium=user_data.get("is_premium", False),
                photo_url=user_data.get("photo_url"),
            )

            auth_date = datetime.utcfromtimestamp(
                int(parsed.get("auth_date", ["0"])[0])
            )

            return WebAppInitData(
                user=user,
                auth_date=auth_date,
                hash=received_hash,
                query_id=parsed.get("query_id", [None])[0],
                start_param=parsed.get("start_param", [None])[0],
            )

        except Exception as e:
            print(f"Error validating init_data: {e}")
            return None

    def is_data_fresh(self, init_data: WebAppInitData, max_age_seconds: int = 86400) -> bool:
        age = (datetime.utcnow() - init_data.auth_date).total_seconds()
        return age < max_age_seconds
