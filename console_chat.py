from __future__ import annotations

import threading
from typing import Optional

import requests

from crypto_utils import derive_user_id, signing_key_from_b64
from flows import login_flow
from messaging import MailboxClient, make_plaintext_payload, process_pull_items
from realtime import RealtimeClient
from storage import signing_key_from_file


def _load_signing_key(signing_key_b64: Optional[str], key_file):
    if signing_key_b64:
        return signing_key_from_b64(signing_key_b64), None
    return signing_key_from_file(key_file)


def run_mailbox_console(
    base_url: str,
    key_file,
    self_user_id: Optional[str],
    to_user_id: Optional[str],
    limit: int,
    poll_interval: float,
    ttl_seconds: int,
    crypto_suite: int,
    use_socket: bool,
    signing_key_b64: Optional[str],
    debug: bool = False,
) -> int:
    signing_key, material = _load_signing_key(signing_key_b64=signing_key_b64, key_file=key_file)
    login_out = login_flow(base_url, signing_key)
    user_id = self_user_id or login_out["keys"]["userId"]
    token = login_out["auth"]["accessToken"]

    if material:
        derived = derive_user_id(signing_key.verify_key.encode())
        if derived != material.user_id:
            raise RuntimeError("Stored key mismatch after load: derived userId does not match stored userId")

    if not to_user_id:
        to_user_id = input("Recipient userId: ").strip()

    prompt_text = f"{user_id}> "

    def log(msg: str):
        if debug:
            print(f"[debug] {msg}")

    log(f"base_url={base_url} user_id={user_id} to_user_id={to_user_id} key_file={key_file}")

    mailbox = MailboxClient(base_url, token)
    trigger = threading.Event()
    trigger.set()  # initial pull to catch backlog
    stop = threading.Event()
    rt_client = None

    def on_direct(data):
        log(f"app:direct payload={data}")
        trigger.set()

    def refresh_auth():
        nonlocal token, mailbox, rt_client
        login_data = login_flow(base_url, signing_key)
        token = login_data["auth"]["accessToken"]
        mailbox.token = token
        log("Refreshed auth token after 401")
        if rt_client:
            rt_client.close()
            rt_client = RealtimeClient(base_url, user_id, token, on_direct=on_direct, on_log=log)
            rt_client.connect()

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

    if use_socket:
        rt_client = RealtimeClient(
            base_url,
            user_id,
            token,
            on_direct=on_direct,
            on_log=log,
        )
        rt_client.connect()

    def receiver_loop():
        while not stop.is_set():
            trigger.wait()  # block until notified
            trigger.clear()
            cursor = None
            while not stop.is_set():
                pulled = call_with_reauth(mailbox.pull, cursor=cursor, limit=limit)
                items = pulled.get("items", [])
                log(f"pulled {len(items)} items cursor={cursor} next={pulled.get('nextCursor')}")
                ids = process_pull_items(items)
                if ids:
                    call_with_reauth(mailbox.ack_delivered, ids)
                    call_with_reauth(mailbox.ack_read, ids)
                    call_with_reauth(mailbox.delete, ids)

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
                call_with_reauth(mailbox.push, recipient_user_id=to_user_id, payload=payload)
                log(f"pushed messageId={payload['messageId']} threadId={payload['threadId']}")
                if rt_client:
                    rt_client.notify_send(to_user_id, {"messageId": payload["messageId"], "threadId": payload["threadId"]})
    finally:
        stop.set()
        trigger.set()
        receiver.join(timeout=2)
        if rt_client:
            rt_client.close()

    return 0
