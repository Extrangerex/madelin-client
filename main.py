from __future__ import annotations

import json
from typing import Optional, Sequence

from cli import parse_args
from config import resolve_base_url
from crypto_utils import derive_user_id, signing_key_from_b64
from flows import login_flow, register_flow
from storage import save_config, signing_key_from_file
from console_chat import run_mailbox_console
from group_client import GroupClient
from group_chat import run_group_chat_console
from messaging import make_plaintext_payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    if args.command == "init":
        save_config(args.config_file, args.base_url)
        result = {"base_url": args.base_url, "storedAt": str(args.config_file)}
    elif args.command == "register":
        result = register_flow(
            base_url=resolve_base_url(args.base_url, args.config_file),
            key_path=args.key_file,
            mnemonic=args.mnemonic,
            store_mnemonic=args.store_mnemonic,
        )
    elif args.command == "mailbox":
        return run_mailbox_console(
            base_url=resolve_base_url(args.base_url, args.config_file),
            key_file=args.key_file,
            self_user_id=args.user_id,
            to_user_id=args.to_user_id,
            limit=args.limit,
            poll_interval=args.poll_interval,
            ttl_seconds=args.ttl_seconds,
            crypto_suite=args.crypto_suite,
            use_socket=not args.no_socket,
            signing_key_b64=getattr(args, "signing_key_b64", None),
            debug=getattr(args, "debug", False),
        )
    elif args.command == "group":
        signing_key = signing_key_from_b64(args.signing_key_b64) if getattr(args, "signing_key_b64", None) else None
        if signing_key is None:
            signing_key, _ = signing_key_from_file(args.key_file)
        base_url = resolve_base_url(args.base_url, args.config_file)
        login_data = login_flow(base_url, signing_key)
        token = login_data["auth"]["accessToken"]
        user_id = login_data["keys"]["userId"]
        gc = GroupClient(base_url, token)

        action = args.group_action
        if action == "list":
            result = gc.list_groups()
        elif action == "list-mine":
            result = gc.list_mine()
        elif action == "members":
            result = gc.list_members(args.group_id)
        elif action == "create":
            result = gc.create_group(args.name, args.members, args.is_open if hasattr(args, "is_open") else None)
        elif action == "delete":
            gc.delete_group(args.group_id)
            result = {"deleted": args.group_id}
        elif action == "join":
            result = gc.join_group(args.group_id)
        elif action == "accept":
            result = gc.accept_request(args.group_id, args.user_id)
        elif action == "reject":
            result = gc.reject_request(args.group_id, args.user_id)
        elif action == "leave":
            result = gc.leave_group(args.group_id)
        elif action == "push":
            payload = make_plaintext_payload(args.text, args.ttl_seconds, crypto_suite=args.crypto_suite)
            payload["groupId"] = args.group_id
            result = gc.group_push(payload)
        else:  # pull
            pulled = gc.group_pull(args.group_id, args.cursor, args.limit)
            # auto-ack/del/read/delete to mirror direct mailbox behaviour
            items = pulled.get("items", [])
            ids = [item.get("id") for item in items if item.get("id")]
            if ids:
                gc.group_ack_delivered(ids)
                gc.group_ack_read(ids)
                gc.group_delete(ids)
            result = pulled
        result = {"userId": user_id, "result": result}
    elif args.command == "groupchat":
        return run_group_chat_console(
            base_url=resolve_base_url(args.base_url, args.config_file),
            key_file=args.key_file,
            group_id=args.group_id,
            limit=args.limit,
            poll_interval=args.poll_interval,
            ttl_seconds=args.ttl_seconds,
            crypto_suite=args.crypto_suite,
            signing_key_b64=getattr(args, "signing_key_b64", None),
            debug=getattr(args, "debug", False),
        )
    else:
        signing_key = signing_key_from_b64(args.signing_key_b64) if args.signing_key_b64 else None
        material = None
        if signing_key is None:
            signing_key, material = signing_key_from_file(args.key_file)

        base_url = resolve_base_url(args.base_url, args.config_file)
        result = login_flow(base_url, signing_key)
        if material:
            derived = derive_user_id(signing_key.verify_key.encode())
            if derived != material.user_id:
                raise RuntimeError("Stored key mismatch after load: derived userId does not match stored userId")

    if getattr(args, "as_json", False):
        print(json.dumps(result, indent=2))
    else:
        if args.command == "init":
            print("baseUrl stored at:", result["storedAt"])
            print("baseUrl:", result["base_url"])
        elif args.command == "register":
            print("mnemonic:", result["mnemonic"])
            print("publicKey:", result["keys"]["public_key_b64"])
            print("privateKey:", result.get("privateKeyB64") or result["keys"]["signing_key_b64"])
            print("userId:", result["keys"]["user_id"])
            print("storedAt:", result["storedAt"])
        elif args.command == "group":
            res = result.get("result", result)
            if args.group_action in {"list", "list-mine"}:
                if isinstance(res, list):
                    for g in res:
                        gid = g.get("groupId") or g.get("group_id") or g.get("id")
                        if gid:
                            print(gid)
                elif isinstance(res, dict):
                    owned = res.get("owned") or []
                    member_of = res.get("memberOf") or []
                    for g in owned:
                        gid = g.get("groupId") or g.get("group_id") or g.get("id")
                        if gid:
                            print(f"\033[32m{gid}\033[0m")  # owner in green
                    for g in member_of:
                        gid = g.get("groupId") or g.get("group_id") or g.get("id")
                        if gid:
                            print(f"\033[36m{gid}\033[0m")  # member in cyan
            else:
                print("userId:", result.get("userId"))
                print("result:", res)
        else:
            print("userId:", result["keys"]["userId"])
            print("token:", result["auth"]["accessToken"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
