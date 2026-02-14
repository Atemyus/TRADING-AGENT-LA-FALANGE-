import asyncio
import shlex
from dataclasses import dataclass
from datetime import UTC, datetime

from src.config import BridgeSettings
from src.providers.base import BridgeProviderError


@dataclass
class ManagedTerminal:
    process: asyncio.subprocess.Process
    path: str
    args: list[str]
    started_at: datetime

    @property
    def pid(self) -> int | None:
        return self.process.pid


class TerminalManager:
    """
    Optional process orchestrator for MT terminal executables.

    Used when MT_BRIDGE_TERMINAL_AUTO_LAUNCH=true and terminal_path is provided.
    """

    def __init__(self, settings: BridgeSettings):
        self._settings = settings

    def _build_args(
        self,
        terminal_path: str,
        *,
        platform: str,
        login: str,
        server: str,
        data_path: str | None,
        workspace_id: str | None,
    ) -> list[str]:
        args: list[str] = []
        raw_default_args = (self._settings.MT_BRIDGE_TERMINAL_DEFAULT_ARGUMENTS or "").strip()
        if raw_default_args:
            try:
                args.extend(shlex.split(raw_default_args, posix=False))
            except Exception:
                args.extend(raw_default_args.split())

        # Best-effort startup hints used by MT terminals.
        profile_value = (workspace_id or login).strip()
        if profile_value:
            args.extend(["/profile", profile_value])
        if data_path:
            args.extend(["/portable"])

        _ = terminal_path, platform, server
        return args

    async def launch_terminal(
        self,
        *,
        terminal_path: str,
        platform: str,
        login: str,
        server: str,
        data_path: str | None = None,
        workspace_id: str | None = None,
    ) -> ManagedTerminal:
        path = (terminal_path or "").strip()
        if not path:
            raise BridgeProviderError("terminal_path is required to auto-launch terminal")

        args = self._build_args(
            path,
            platform=platform,
            login=login,
            server=server,
            data_path=data_path,
            workspace_id=workspace_id,
        )

        try:
            process = await asyncio.create_subprocess_exec(
                path,
                *args,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise BridgeProviderError(f"Terminal executable not found: {path}") from exc
        except Exception as exc:
            raise BridgeProviderError(f"Failed to start terminal '{path}': {exc}") from exc

        timeout = max(float(self._settings.MT_BRIDGE_TERMINAL_LAUNCH_TIMEOUT_SECONDS), 1.0)
        await asyncio.sleep(min(1.0, timeout))
        if process.returncode is not None:
            raise BridgeProviderError(
                f"Terminal process exited early with code {process.returncode}. "
                f"path={path}"
            )

        return ManagedTerminal(
            process=process,
            path=path,
            args=args,
            started_at=datetime.now(UTC),
        )

    async def stop_terminal(
        self,
        managed: ManagedTerminal,
        *,
        graceful_timeout_seconds: float = 5.0,
    ) -> None:
        process = managed.process
        if process.returncode is not None:
            return

        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=max(graceful_timeout_seconds, 0.5))
            return
        except Exception:
            pass

        process.kill()
        try:
            await asyncio.wait_for(process.wait(), timeout=3.0)
        except Exception:
            return
