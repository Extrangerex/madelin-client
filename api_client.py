from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

import requests


@dataclass
class MadelinClient:
    base_url: str
    session: requests.Session = field(default_factory=requests.Session)

    def register(self, public_key_b64: str) -> Dict[str, Any]:
        r = self.session.post(
            f"{self.base_url}/auth/register",
            json={"publicKey": public_key_b64},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def create_challenge(self, public_key_b64: str) -> Dict[str, Any]:
        r = self.session.post(
            f"{self.base_url}/auth/challenge",
            json={"publicKey": public_key_b64},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def verify_challenge(self, public_key_b64: str, challenge_id: str, signature_b64: str) -> Dict[str, Any]:
        r = self.session.post(
            f"{self.base_url}/auth/verify",
            json={
                "publicKey": public_key_b64,
                "challengeId": challenge_id,
                "signature": signature_b64,
            },
            timeout=20,
        )
        r.raise_for_status()
        return r.json()
