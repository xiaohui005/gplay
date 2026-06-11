import urllib.parse

import requests
from fastapi import HTTPException

from src.models.notification_config import NotificationConfig


class BarkService:
    def __init__(self, config: NotificationConfig):
        self.config = config

    def send_test(self) -> dict:
        if not self.config.bark_enabled:
            raise HTTPException(status_code=400, detail="请先启用 Bark 推送")
        if not self.config.bark_server_url:
            raise HTTPException(status_code=400, detail="请填写 Bark 服务地址")
        if not self.config.bark_device_key:
            raise HTTPException(status_code=400, detail="请填写 Bark Device Key")

        title = "GPlay Bark 推送测试"
        body = "如果你收到这条消息，说明 GPlay Bark 推送配置已生效。"
        url = self._build_url(title, body)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Bark 推送失败: {exc}") from exc
        return {"status": "ok", "message": "测试推送已发送"}

    def _build_url(self, title: str, body: str) -> str:
        server_url = self.config.bark_server_url.rstrip("/")
        device_key = urllib.parse.quote(self.config.bark_device_key.strip(), safe="")
        encoded_title = urllib.parse.quote(title, safe="")
        encoded_body = urllib.parse.quote(body, safe="")
        return f"{server_url}/{device_key}/{encoded_title}/{encoded_body}"
