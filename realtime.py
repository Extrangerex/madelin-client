from __future__ import annotations

from typing import Callable, Optional


def get_socketio_client():
    try:
        import socketio  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency notice
        raise RuntimeError("Dependency missing: install 'python-socketio[client]'") from exc
    return socketio


class RealtimeClient:
    def __init__(self, base_url: str, user_id: str, token: str, on_direct: Callable[[object], None], on_log: Optional[Callable[[str], None]] = None) -> None:
        socketio = get_socketio_client()
        self._sio = socketio.Client(reconnection=True)
        self._base_url = base_url
        self._user_id = user_id
        self._token = token
        self._on_direct = on_direct
        self._log = on_log or (lambda _: None)

        @self._sio.event
        def connect():  # type: ignore
            self._log("socket connected, registering user")
            self._sio.emit("app:user:register", {"userId": self._user_id})

        @self._sio.event
        def disconnect():  # type: ignore
            self._log("socket disconnected")

        @self._sio.event
        def connect_error(data):  # type: ignore
            self._log(f"socket connect_error: {data}")

        @self._sio.on("app:direct")
        def _on_direct(data):  # type: ignore
            self._log(f"socket app:direct received: {data}")
            self._on_direct(data)

    def connect(self) -> None:
        self._log(f"socket connecting to {self._base_url}")
        self._sio.connect(
            self._base_url,
            auth={"token": self._token},
            headers={"Authorization": f"Bearer {self._token}"},
        )

    def notify_send(self, to_user_id: str, payload: object) -> None:
        self._log(f"socket notify_send to={to_user_id} payload={payload}")
        self._sio.emit("app:user:send", {"toUserId": to_user_id, "event": "app:direct", "data": payload})

    def close(self) -> None:
        try:
            self._sio.disconnect()
        except Exception:
            pass
