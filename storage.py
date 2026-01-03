from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Tuple

from nacl.signing import SigningKey

from crypto_utils import derive_user_id, signing_key_from_b64
from models import KeyMaterial


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_json_secure(path: Path, payload: Dict[str, Any]) -> None:
    ensure_parent_dir(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_config(path: Path, base_url: str) -> None:
    _write_json_secure(path, {"base_url": base_url})


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_key_material(path: Path, material: KeyMaterial, store_mnemonic: bool = False) -> None:
    payload = asdict(material)
    if not store_mnemonic:
        payload.pop("mnemonic", None)
    _write_json_secure(path, payload)


def load_key_material(path: Path) -> KeyMaterial:
    if not path.exists():
        raise FileNotFoundError(f"key file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return KeyMaterial(
        signing_key_b64=data["signing_key_b64"],
        public_key_b64=data["public_key_b64"],
        user_id=data["user_id"],
        mnemonic=data.get("mnemonic"),
    )


def signing_key_from_file(path: Path) -> Tuple[SigningKey, KeyMaterial]:
    material = load_key_material(path)
    signing_key = signing_key_from_b64(material.signing_key_b64)
    pk = signing_key.verify_key.encode()
    derived_user_id = derive_user_id(pk)
    if derived_user_id != material.user_id:
        raise RuntimeError("Stored key mismatch: derived userId does not match stored userId")
    return signing_key, material
