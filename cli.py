from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from settings import DEFAULT_CONFIG_PATH, DEFAULT_KEY_PATH


def parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Madelin auth client")

    login_parent = argparse.ArgumentParser(add_help=False)
    login_parent.add_argument(
        "--base-url",
        help="Base URL for the Madelin API. If omitted, uses config file from `init`.",
    )
    login_parent.add_argument(
        "--key-file",
        type=Path,
        default=DEFAULT_KEY_PATH,
        help=f"Path to store/load key material (default: {DEFAULT_KEY_PATH})",
    )
    login_parent.add_argument(
        "--config-file",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to store/load config (default: {DEFAULT_CONFIG_PATH})",
    )
    login_parent.add_argument("--signing-key-b64", help="Base64-encoded 32-byte Ed25519 seed")

    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Set and store the base URL securely")
    init_cmd.add_argument("--base-url", required=True, help="Base URL for the Madelin API")
    init_cmd.add_argument(
        "--config-file",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to store config (default: {DEFAULT_CONFIG_PATH})",
    )
    init_cmd.add_argument("--json", action="store_true", dest="as_json", help="Print full JSON output")

    register_cmd = sub.add_parser("register", parents=[login_parent], help="Generate mnemonic, derive keys, register, and store locally")
    mnemonic_group = register_cmd.add_mutually_exclusive_group()
    mnemonic_group.add_argument("--mnemonic", help="Existing BIP-39 mnemonic; omit to auto-generate")
    mnemonic_group.add_argument(
        "--mnemonic-words",
        nargs="+",
        dest="mnemonic_words",
        help="Existing BIP-39 mnemonic as separate words (recovery on another device)",
    )
    register_cmd.add_argument(
        "--store-mnemonic",
        action="store_true",
        help="Persist mnemonic alongside keys (default: do not store mnemonic)",
    )
    register_cmd.add_argument("--json", action="store_true", dest="as_json", help="Print full JSON output")

    login_cmd = sub.add_parser("login", parents=[login_parent], help="Login using saved or provided signing key")
    login_cmd.add_argument("--json", action="store_true", dest="as_json", help="Print full JSON output")

    mailbox_cmd = sub.add_parser("mailbox", parents=[login_parent], help="Interactive mailbox sender/receiver")
    mailbox_cmd.add_argument("--user-id", help="Override self userId (otherwise derived from key/login)")
    mailbox_cmd.add_argument("--to-user-id", help="Recipient userId to send messages to")
    mailbox_cmd.add_argument("--limit", type=int, default=50, help="Pull page size (default: 50)")
    mailbox_cmd.add_argument("--poll-interval", type=float, default=2.0, help="Seconds to wait between empty polls")
    mailbox_cmd.add_argument("--ttl-seconds", type=int, default=3600, help="TTL for pushed messages (default: 3600)")
    mailbox_cmd.add_argument("--crypto-suite", type=int, default=0, help="Crypto suite id (default: 0)")
    mailbox_cmd.add_argument("--no-socket", action="store_true", help="Disable Socket.IO realtime notifications")
    mailbox_cmd.add_argument("--debug", action="store_true", help="Log requests/responses for debugging")

    group_cmd = sub.add_parser("group", parents=[login_parent], help="Group management and group mailbox")
    group_cmd.add_argument("--json", action="store_true", dest="as_json", help="Print full JSON output")
    group_sub = group_cmd.add_subparsers(dest="group_action", required=True)

    group_list = group_sub.add_parser("list", parents=[login_parent], help="List groups")
    group_list_mine = group_sub.add_parser("list-mine", parents=[login_parent], help="List groups you own or are member of")
    group_list_members = group_sub.add_parser("members", parents=[login_parent], help="List members of a group")
    group_list_members.add_argument("group_id")

    group_create = group_sub.add_parser("create", parents=[login_parent], help="Create group")
    group_create.add_argument("--name", help="Group name")
    group_create.add_argument("--member", action="append", dest="members", help="Member userId (repeatable)")
    group_create.add_argument(
        "--is-open",
        dest="is_open",
        action="store_const",
        const=True,
        default=None,
        help="Create group as open (omit flag to leave as default/closed)",
    )

    group_delete = group_sub.add_parser("delete", parents=[login_parent], help="Delete group")
    group_delete.add_argument("group_id")

    group_join = group_sub.add_parser("join", parents=[login_parent], help="Request to join group")
    group_join.add_argument("group_id")

    group_accept = group_sub.add_parser("accept", parents=[login_parent], help="Accept pending user (admin)")
    group_accept.add_argument("group_id")
    group_accept.add_argument("user_id")

    group_reject = group_sub.add_parser("reject", parents=[login_parent], help="Reject pending user (admin)")
    group_reject.add_argument("group_id")
    group_reject.add_argument("user_id")

    group_leave = group_sub.add_parser("leave", parents=[login_parent], help="Leave group")
    group_leave.add_argument("group_id")

    group_push = group_sub.add_parser("push", parents=[login_parent], help="Send message to group mailbox")
    group_push.add_argument("group_id")
    group_push.add_argument("--text", required=True, help="Plaintext to send (demo)")
    group_push.add_argument("--crypto-suite", type=int, default=0, help="Crypto suite id")
    group_push.add_argument("--ttl-seconds", type=int, default=0, help="TTL for message (0 = no expiry)")

    group_pull = group_sub.add_parser("pull", parents=[login_parent], help="Pull messages from group mailbox")
    group_pull.add_argument("group_id")
    group_pull.add_argument("--cursor", help="Cursor for pagination")
    group_pull.add_argument("--limit", type=int, default=50, help="Page size (default: 50)")

    group_chat = sub.add_parser("groupchat", parents=[login_parent], help="Interactive group mailbox chat")
    group_chat.add_argument("--group-id", help="Group ID to chat in (prompt if omitted)")
    group_chat.add_argument("--limit", type=int, default=50, help="Pull page size (default: 50)")
    group_chat.add_argument("--poll-interval", type=float, default=2.0, help="Seconds between polls (default: 2)")
    group_chat.add_argument("--ttl-seconds", type=int, default=0, help="TTL for pushed messages (0 = no expiry)")
    group_chat.add_argument("--crypto-suite", type=int, default=1, help="Crypto suite id (default: 1)")
    group_chat.add_argument("--debug", action="store_true", help="Log requests/responses for debugging")

    return parser.parse_args(argv)
