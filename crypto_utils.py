from __future__ import annotations

import base64
import hashlib
from typing import Optional, Tuple

import base58
from nacl.signing import SigningKey

from settings import PREFIX


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def derive_user_id(public_key_32: bytes) -> str:
    """sha256(publicKey) -> bs58.encode(hash)"""
    if len(public_key_32) != 32:
        raise ValueError("public_key must be 32 bytes")
    h = hashlib.sha256(public_key_32).digest()
    return base58.b58encode(h).decode("ascii")


def build_payload(user_id: str, challenge_id: str, nonce_32: bytes) -> bytes:
    """Match backend payload: prefix + userId + challengeId + nonce."""
    if len(nonce_32) != 32:
        raise ValueError("nonce must be 32 bytes")
    return b"".join([
        PREFIX,
        user_id.encode("utf-8"),
        challenge_id.encode("utf-8"),
        nonce_32,
    ])


def get_mnemonic_lib():
    try:
        from mnemonic import Mnemonic  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency notice
        raise RuntimeError("Dependency missing: install 'mnemonic' (pip install mnemonic)") from exc
    return Mnemonic


def generate_signing_key_from_mnemonic(mnemonic: Optional[str] = None) -> Tuple[str, bytes, SigningKey]:
    Mnemonic = get_mnemonic_lib()
    helper = Mnemonic("english")
    phrase = mnemonic or helper.generate(strength=256)
    if not helper.check(phrase):
        raise ValueError("Invalid mnemonic phrase")
    seed = helper.to_seed(phrase)
    signing_key = SigningKey(seed[:32])  # Ed25519 uses 32-byte seed
    return phrase, seed, signing_key


def signing_key_from_b64(seed_b64: str) -> SigningKey:
    seed = b64d(seed_b64)
    if len(seed) != 32:
        raise ValueError("signing key seed must be 32 bytes")
    return SigningKey(seed)
