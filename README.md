# Madelin Client (CLI)

Python CLI for Ed25519 authentication, direct mailbox handling, live chat, groups, and group mailboxes.

## Requirements
- Python 3.9+
- Dependencies: `pip install requests pynacl mnemonic "python-socketio[client]" base58`
- Optional environment variables: `MADELIN_BASE_URL`, `MADELIN_CONFIG_PATH`, `MADELIN_KEY_PATH` for default base URL and file locations.

## Setup
1) Save the base URL:
```bash
python main.py init --base-url https://your-api
```
2) Register keys (generates Ed25519 keys + mnemonic, stores at `~/.madelin/keys.json`):
```bash
python main.py register
```
   - Options: `--key-file <path>`, `--mnemonic <phrase>`, `--store-mnemonic`.
3) Log in (retrieves token):
```bash
python main.py login [--key-file <path>]
```

## Direct mailbox
- Interactive chat (pull + optional Socket.IO):
```bash
python main.py mailbox --key-file <keys.json> --to-user-id <destination> [--no-socket] [--debug]
```
- Incoming messages display as `sender> text` (color-coded per user).

## Groups
Subcommands under `group` (require keys/login):
- List all: `python main.py group list`
- List mine/member-of: `python main.py group list-mine`
- Group members: `python main.py group members <groupId>`
- Create: `python main.py group create [--name ...] [--member <userId> ...] [--is-open]`
- Join: `python main.py group join <groupId>`
- Accept/Reject: `python main.py group accept <groupId> <userId>` / `reject ...`
- Leave: `python main.py group leave <groupId>`
- Push to group mailbox: `python main.py group push <groupId> --text "hello" [--crypto-suite 1] [--ttl-seconds 0]`
- Manual pull: `python main.py group pull <groupId> [--cursor ...] [--limit 50]`

### Interactive group chat
```bash
python main.py groupchat --key-file <keys.json> --group-id <groupId> [--poll-interval 2] [--ttl-seconds 0] [--crypto-suite 1] [--debug]
```
Shows messages in green with per-user color. Prompt: `<userId> >`.

## Key file
- `KeyMaterial` JSON format: `signing_key_b64`, `public_key_b64`, `user_id`, optional `mnemonic`.
- Permissions 0600; defaults to `~/.madelin/keys.json`.

## Notes
- All requests use `Authorization: Bearer <token>` obtained in `login_flow`.
- Binary fields are base64-encoded; message/thread IDs and nonces are generated client-side.
- Pagination cursor is base64 `ISO_DATE|id`; send it back as-is for manual pagination.
