import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.config import BridgeSettings
from src.providers import BaseTerminalProvider, BridgeProviderError, create_provider


@dataclass
class BridgeSession:
    session_id: str
    platform: str
    login: str
    server: str
    connected_at: datetime
    last_seen_at: datetime
    provider: BaseTerminalProvider

    def snapshot(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "platform": self.platform,
            "login": self.login,
            "server": self.server,
            "connected_at": self.connected_at,
            "last_seen_at": self.last_seen_at,
            "provider": self.provider.name,
        }


class SessionManager:
    def __init__(self, settings: BridgeSettings):
        self.settings = settings
        self._sessions: dict[str, BridgeSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        *,
        platform: str,
        login: str,
        password: str,
        server: str,
        terminal_path: str | None = None,
        data_path: str | None = None,
        workspace_id: str | None = None,
    ) -> BridgeSession:
        async with self._lock:
            if len(self._sessions) >= int(self.settings.MT_BRIDGE_MAX_SESSIONS):
                raise BridgeProviderError(
                    f"Max sessions reached ({self.settings.MT_BRIDGE_MAX_SESSIONS})"
                )

            provider = create_provider(platform=platform, settings=self.settings)
            safe_platform = (platform or self.settings.MT_BRIDGE_DEFAULT_PLATFORM or "mt5").strip().lower()

            # MT5 package binding is process-global; keep one active MT5 session per bridge process.
            if provider.name == "mt5":
                existing_mt5 = [s for s in self._sessions.values() if s.provider.name == "mt5"]
                if existing_mt5:
                    raise BridgeProviderError(
                        "MT5 provider mode currently supports one active session per bridge process. "
                        "Scale with multiple bridge nodes/processes."
                    )

            await provider.connect(
                login=login,
                password=password,
                server=server,
                platform=safe_platform,
                terminal_path=terminal_path,
                data_path=data_path,
                workspace_id=workspace_id,
            )
            now = datetime.now(UTC)
            session_id = f"sess_{uuid.uuid4().hex}"
            session = BridgeSession(
                session_id=session_id,
                platform=safe_platform,
                login=login,
                server=server,
                connected_at=now,
                last_seen_at=now,
                provider=provider,
            )
            self._sessions[session_id] = session
            return session

    async def disconnect_session(self, session_id: str) -> bool:
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            try:
                await session.provider.disconnect()
            finally:
                self._sessions.pop(session_id, None)
            return True

    async def shutdown_all(self) -> None:
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions = {}
        for session in sessions:
            try:
                await session.provider.disconnect()
            except Exception:
                continue

    async def list_sessions(self) -> list[dict[str, Any]]:
        return [session.snapshot() for session in self._sessions.values()]

    async def get_session(self, session_id: str) -> BridgeSession:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Unknown session_id: {session_id}")
        session.last_seen_at = datetime.now(UTC)
        return session
