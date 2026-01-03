from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey

from api_client import MadelinClient
from crypto_utils import b64d, b64e, build_payload, derive_user_id, generate_signing_key_from_mnemonic
from models import KeyMaterial
from storage import save_key_material


def login_flow(base_url: str, signing_key: SigningKey) -> Dict[str, Any]:
    """
    Full flow:
      - given Ed25519 keypair
      - register (idempotent)
      - createChallenge
      - sign exact payload
      - verifyChallenge -> JWT
    """
    client = MadelinClient(base_url=base_url)
    pk = signing_key.verify_key.encode()
    public_key_b64 = b64e(pk)

    client.register(public_key_b64)

    ch = client.create_challenge(public_key_b64)
    user_id = ch["userId"]
    challenge_id = ch["challengeId"]
    nonce = b64d(ch["nonce"])

    derived = derive_user_id(pk)
    if derived != user_id:
        raise RuntimeError(f"userId mismatch: derived={derived} server={user_id}")

    payload = build_payload(user_id, challenge_id, nonce)
    signature = signing_key.sign(payload).signature  # detached signature (64 bytes)
    if len(signature) != 64:
        raise RuntimeError(f"signature must be 64 bytes, got {len(signature)}")

    signature_b64 = b64e(signature)

    try:
        signing_key.verify_key.verify(payload, signature)
    except BadSignatureError as e:
        raise RuntimeError("local signature verification failed") from e

    result = client.verify_challenge(public_key_b64, challenge_id, signature_b64)
    return {
        "keys": {
            "publicKeyB64": public_key_b64,
            "userId": user_id,
        },
        "auth": result,
    }


def register_flow(base_url: str, key_path: Path, mnemonic: Optional[str], store_mnemonic: bool) -> Dict[str, Any]:
    phrase, seed, signing_key = generate_signing_key_from_mnemonic(mnemonic)
    material = KeyMaterial.from_signing_key(signing_key, mnemonic=phrase if store_mnemonic else None)

    client = MadelinClient(base_url=base_url)
    client.register(material.public_key_b64)

    save_key_material(key_path, material, store_mnemonic=store_mnemonic)
    return {
        "mnemonic": phrase,
        "seedHex": seed.hex(),
        "keys": asdict(material),
        "privateKeyB64": material.signing_key_b64,
        "storedAt": str(key_path),
    }
