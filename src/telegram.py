from loguru import logger
import re
from typing import Any, Literal, Self
from httpx import Client
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

class TelegramSettings(BaseSettings):
    bot_token: str
    chat_id: str

    model_config = SettingsConfigDict(
        extra = 'ignore',
        env_prefix = 'TELEGRAM_',
        env_file = '.env',
        env_file_encoding = 'utf-8',
    )

class Telegram:
    escape_pattern = re.compile(rf'([{re.escape(r"\_*[]()~`>#+-=|{}.!")}])')

    def __init__(self) -> None:
        self._settings = TelegramSettings()

    def __enter__(self) -> Self:
        self._client = Client(base_url='https://api.telegram.org', http2=True, timeout=60)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._client.close()

    def send_message(
        self,
        text: str,
        *,
        parse_mode: Literal['HTML', 'MarkdownV2'] | None = None,
        preview: bool = False,
    ) -> Any:
        logger.info("Prepare to send message")
        if parse_mode == 'MarkdownV2':
            text = re.sub(self.escape_pattern, r'\\\1', text)
        path = f'/bot{self._settings.bot_token}/sendMessage'
        payload = {
            'chat_id': self._settings.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': not preview,
        }

        resp = self._client.post(path, data=payload)
        logger.info("Already send message")

        if not resp.is_success:
            resp.raise_for_status()
        return resp.json()

    def send_photo(
        self,
        photo: bytes,
        caption: str,
        *,
        parse_mode: Literal['HTML', 'MarkdownV2'] | None = None,
    ) -> Any:
        if parse_mode == 'MarkdownV2':
            caption = re.sub(self.escape_pattern, r'\\\1', caption)
        path = f'/bot{self._settings.bot_token}/sendPhoto'
        payload = {
            'chat_id': self._settings.chat_id,
            'caption': caption,
            'parse_mode': parse_mode,
        }
        files = {'photo': photo}
        resp = self._client.post(path, data=payload, files=files)
        if not resp.is_success:
            resp.raise_for_status()
        return resp.json()

    def send_group_media(
        self,
        photos: list[bytes],
        captions: list[str] | None = None,
        *,
        parse_mode: Literal['HTML', 'MarkdownV2'] | None = None,
    ) -> Any:
        logger.info("Prepare to send group media")
        if captions and parse_mode == 'MarkdownV2':
            captions = [re.sub(self.escape_pattern, r'\\\1', c) for c in captions]

        path = f'/bot{self._settings.bot_token}/sendMediaGroup'

        # Build the attach payloads: photo1 -> 'attach://photo0', etc.
        media = []
        files = {}
        for idx, photo_bytes in enumerate(photos):
            file_name = f'photo{idx}.jpg'  # telegram just needs a filename extension
            media.append({
                'type': 'photo',
                'media': f'attach://{file_name}',
                'caption': captions[idx] if captions and idx < len(captions) else None,
                'parse_mode': parse_mode,
            })
            files[file_name] = photo_bytes

        payload = {
            'chat_id': self._settings.chat_id,
            'media': json.dumps(media),
        }

        resp = self._client.post(path, data=payload, files=files)
        logger.info("Already sent group media")
        if not resp.is_success:
            resp.raise_for_status()
        return resp.json()
