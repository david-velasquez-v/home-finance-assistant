from typing import Any

import httpx


class TelegramClient:
    def __init__(self, token: str) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self._file_base = f"https://api.telegram.org/file/bot{token}"

    def get_updates(self, offset: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        r = httpx.get(f"{self._base}/getUpdates", params=params, timeout=10)
        r.raise_for_status()
        return r.json()["result"]

    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: int | None = None,
    ) -> None:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        r = httpx.post(f"{self._base}/sendMessage", json=payload, timeout=10)
        r.raise_for_status()

    def download_file(self, file_id: str) -> bytes:
        r = httpx.get(f"{self._base}/getFile", params={"file_id": file_id}, timeout=10)
        r.raise_for_status()
        file_path = r.json()["result"]["file_path"]
        r2 = httpx.get(f"{self._file_base}/{file_path}", timeout=60)
        r2.raise_for_status()
        return r2.content
