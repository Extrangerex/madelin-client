from __future__ import annotations

import threading
from typing import Optional

import requests

from crypto_utils import derive_user_id, signing_key_from_b64
from flows import login_flow
from group_client import GroupClient
from messaging import make_plaintext_payload, process_group_pull_items
from storage import signing_key_from_file


def _load_signing_key(signing_key_b64: Optional[str], key_file):
    if signing_key_b64:
        return signing_key_from_b64(signing_key_b64), None
    return signing_key_from_file(key_file)


def run_group_chat_console(
    base_url: str,
    key_file,
    group_id: Optional[str],
    limit: int,
    poll_interval: float,
    ttl_seconds: int,
    crypto_suite: int,
    signing_key_b64: Optional[str],
    debug: bool = False,
) -> int:
    signing_key, material = _load_signing_key(signing_key_b64=signing_key_b64, key_file=key_file)
    login_out = login_flow(base_url, signing_key)
    user_id = login_out["keys"]["userId"]
    token = login_out["auth"]["accessToken"]

    if material:
        derived = derive_user_id(signing_key.verify_key.encode())
        if derived != material.user_id:
            raise RuntimeError("Stored key mismatch after load: derived userId does not match stored userId")

    if not group_id:
        group_id = input("Group ID: ").strip()

    prompt_text = f"{user_id}> "

    def log(msg: str):
        if debug:
            print(f"[debug] {msg}")

    log(f"base_url={base_url} user_id={user_id} group_id={group_id} key_file={key_file}")

    client = GroupClient(base_url, token)
    trigger = threading.Event()
    trigger.set()  # initial pull
    stop = threading.Event()

    def refresh_auth():
        nonlocal token, client
        login_data = login_flow(base_url, signing_key)
        token = login_data["auth"]["accessToken"]
        client.token = token
        log("Refreshed auth token after 401")

    def call_with_reauth(fn, *args, **kwargs):
        try:
            log(f"Calling {fn.__name__} args={args} kwargs={kwargs}")
            return fn(*args, **kwargs)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                refresh_auth()
                log(f"Retrying {fn.__name__} after 401")
                return fn(*args, **kwargs)
            raise

    def receiver_loop():
        while not stop.is_set():
            triggered = trigger.wait(timeout=poll_interval)
            trigger.clear()
            if not triggered and not poll_interval:
                continue
            cursor = None
            while not stop.is_set():
                pulled = call_with_reauth(client.group_pull, group_id, cursor, limit)
                items = pulled.get("items", [])
                log(f"pulled {len(items)} items cursor={cursor} next={pulled.get('nextCursor')}")
                ids = process_group_pull_items(items)
                if ids:
                    call_with_reauth(client.group_ack_delivered, ids)
                    call_with_reauth(client.group_ack_read, ids)
                    call_with_reauth(client.group_delete, ids)
                cursor = pulled.get("nextCursor")
                if not cursor or not items:
                    break

    receiver = threading.Thread(target=receiver_loop, daemon=True)
    receiver.start()

    try:
        while True:
            text = input(prompt_text).strip()
            if text.lower() in {"exit", "quit"}:
                break
            if text:
                payload = make_plaintext_payload(text, ttl_seconds, crypto_suite=crypto_suite)
                payload["groupId"] = group_id
                call_with_reauth(client.group_push, payload)
                log(f"pushed groupId={group_id} messageId={payload['messageId']} threadId={payload['threadId']}")
                trigger.set()  # prompt a pull after sending
    finally:
        stop.set()
        trigger.set()
        receiver.join(timeout=2)

    return 0
