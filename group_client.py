from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests


@dataclass
class GroupClient:
    base_url: str
    token: str
    session: requests.Session = field(default_factory=requests.Session)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def list_groups(self) -> List[Dict[str, Any]]:
        r = self.session.get(f"{self.base_url}/groups/mine", headers=self._headers(), timeout=20)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else data.get("items", data)

    def create_group(self, name: Optional[str], member_user_ids: Optional[List[str]], is_open: Optional[bool]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if name:
            payload["name"] = name
        if member_user_ids:
            payload["memberUserIds"] = member_user_ids
        if is_open is not None:
            payload["isOpen"] = is_open
        r = self.session.post(f"{self.base_url}/groups", json=payload, headers=self._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    def list_mine(self) -> Dict[str, Any]:
        r = self.session.get(f"{self.base_url}/groups/mine", headers=self._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    def list_members(self, group_id: str) -> Dict[str, Any]:
        r = self.session.get(
            f"{self.base_url}/groups/members",
            params={"groupId": group_id},
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def delete_group(self, group_id: str) -> None:
        r = self.session.delete(f"{self.base_url}/groups/{group_id}", headers=self._headers(), timeout=20)
        r.raise_for_status()

    def join_group(self, group_id: str) -> Dict[str, Any]:
        r = self.session.post(f"{self.base_url}/groups/{group_id}/join", headers=self._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    def accept_request(self, group_id: str, user_id: str) -> Dict[str, Any]:
        r = self.session.post(
            f"{self.base_url}/groups/{group_id}/requests/{user_id}/accept",
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def reject_request(self, group_id: str, user_id: str) -> Dict[str, Any]:
        r = self.session.post(
            f"{self.base_url}/groups/{group_id}/requests/{user_id}/reject",
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def leave_group(self, group_id: str) -> Dict[str, Any]:
        r = self.session.post(f"{self.base_url}/groups/{group_id}/leave", headers=self._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    # Group mailbox operations
    def group_push(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = self.session.post(
            f"{self.base_url}/group-mailbox/push",
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def group_pull(self, group_id: str, cursor: Optional[str], limit: int) -> Dict[str, Any]:
        r = self.session.get(
            f"{self.base_url}/group-mailbox/pull",
            params={"cursor": cursor, "limit": limit, "groupId": group_id},
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def group_ack_delivered(self, ids: List[str]) -> None:
        if not ids:
            return
        r = self.session.post(
            f"{self.base_url}/group-mailbox/ack/delivered",
            json={"ids": ids},
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()

    def group_ack_read(self, ids: List[str]) -> None:
        if not ids:
            return
        r = self.session.post(
            f"{self.base_url}/group-mailbox/ack/read",
            json={"ids": ids},
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()

    def group_delete(self, ids: List[str]) -> None:
        if not ids:
            return
        r = self.session.post(
            f"{self.base_url}/group-mailbox/delete",
            json={"ids": ids},
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
