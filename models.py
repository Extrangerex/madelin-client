from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from nacl.signing import SigningKey

from crypto_utils import b64e, derive_user_id


@dataclass
class KeyMaterial:
    signing_key_b64: str
    public_key_b64: str
    user_id: str
    mnemonic: Optional[str] = None

    @classmethod
    def from_signing_key(cls, signing_key: SigningKey, mnemonic: Optional[str] = None) -> "KeyMaterial":
        pk = signing_key.verify_key.encode()
        return cls(
            signing_key_b64=b64e(signing_key.encode()),
            public_key_b64=b64e(pk),
            user_id=derive_user_id(pk),
            mnemonic=mnemonic,
        )
