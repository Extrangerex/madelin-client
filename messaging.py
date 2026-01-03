from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

import requests

from crypto_utils import b64d, b64e

_COLORS = ["\033[32m", "\033[36m", "\033[35m", "\033[33m", "\033[34m"]


def _color_for_user(user_id: str) -> str:
    if not user_id:
        return _COLORS[0]
    h = hashlib.sha1(user_id.encode("utf-8")).digest()
    idx = h[0] % len(_COLORS)
    return _COLORS[idx]


@dataclass
class MailboxClient:
    base_url: str
    token: str
    session: requests.Session = field(default_factory=requests.Session)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def pull(self, cursor: Optional[str], limit: int) -> Dict[str, Any]:
        r = self.session.get(
            f"{self.base_url}/mailbox/pull",
            params={"cursor": cursor, "limit": limit},
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def ack_delivered(self, ids: List[str]) -> None:
        if not ids:
            return
        r = self.session.post(
            f"{self.base_url}/mailbox/ack/delivered",
            json={"ids": ids},
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()

    def ack_read(self, ids: List[str]) -> None:
        if not ids:
            return
        r = self.session.post(
            f"{self.base_url}/mailbox/ack/read",
            json={"ids": ids},
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()

    def delete(self, ids: List[str]) -> None:
        if not ids:
            return
        r = self.session.post(
            f"{self.base_url}/mailbox/delete",
            json={"ids": ids},
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()

    def push(self, recipient_user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = {"recipientUserId": recipient_user_id, **payload}
        r = self.session.post(
            f"{self.base_url}/mailbox/push",
            json=body,
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()


def make_plaintext_payload(text: str, ttl_seconds: int, crypto_suite: int = 0) -> Dict[str, Any]:
    nonce = b64e(uuid4().bytes)
    ciphertext = b64e(text.encode("utf-8"))
    message_id = b64e(uuid4().bytes)
    thread_id = b64e(uuid4().bytes)
    return {
        "messageId": message_id,
        "threadId": thread_id,
        "nonce": nonce,
        "ciphertext": ciphertext,
        "aad": "",
        "cryptoSuite": crypto_suite,
        "ttlSeconds": ttl_seconds,
    }


def process_pull_items(items: List[Dict[str, Any]]) -> List[str]:
    ids = []
    for idx, item in enumerate(items):
        ids.append(item.get("id"))
        ciphertext = item.get("ciphertext")
        text = ""
        if ciphertext:
            try:
                text = b64d(ciphertext).decode("utf-8", errors="replace")
            except Exception:
                text = "<unable to decode>"
        sender = item.get("senderUserId", "unknown")
        prefix = "\n" if idx == 0 else ""
        color = _color_for_user(sender)
        print(f"{prefix}{color}{sender}> {text}\033[0m", end="")
    return [i for i in ids if i]


def process_group_pull_items(items: List[Dict[str, Any]]) -> List[str]:
    ids = []
    for idx, item in enumerate(items):
        ids.append(item.get("id"))
        ciphertext = item.get("ciphertext")
        text = ""
        if ciphertext:
            try:
                text = b64d(ciphertext).decode("utf-8", errors="replace")
            except Exception:
                text = "<unable to decode>"
        sender = item.get("senderUserId", "unknown")
        prefix = "\n" if idx == 0 else ""
        color = _color_for_user(sender)
        print(f"{prefix}{color}{sender}> {text}\033[0m")
    return [i for i in ids if i]
