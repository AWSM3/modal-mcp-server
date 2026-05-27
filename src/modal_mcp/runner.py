"""Command runner helpers for Modal CLI backed MCP tools."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def _read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return values

    for line in lines:
        item = _parse_dotenv_line(line)
        if item is None:
            continue
        key, value = item
        values[key] = value
    return values


def _candidate_dotenv_paths(start: Path) -> list[Path]:
    candidates: list[Path] = []
    env_file = os.environ.get("MODAL_MCP_ENV_FILE")
    if env_file:
        candidates.append(Path(env_file).expanduser())

    resolved = start.resolve()
    search_root = resolved if resolved.is_dir() else resolved.parent
    parents = [search_root, *search_root.parents]
    for directory in reversed(parents):
        candidates.append(directory / ".env")

    seen: set[Path] = set()
    unique: list[Path] = []
    for path in candidates:
        normalized = path.resolve() if path.exists() else path
        if normalized not in seen:
            seen.add(normalized)
            unique.append(path)
    return unique


def modal_environment(start: Path | None = None) -> dict[str, str]:
    """Build a subprocess environment with Modal token aliases normalized."""

    env = dict(os.environ)
    base = start or Path.cwd()
    for dotenv_path in _candidate_dotenv_paths(base):
        env.update(_read_dotenv(dotenv_path))

    token = env.get("MODAL_TOKEN", "")
    if token and not env.get("MODAL_TOKEN_ID") and env.get("MODAL_TOKEN_SECRET"):
        env["MODAL_TOKEN_ID"] = token
    if token and (not env.get("MODAL_TOKEN_ID") or not env.get("MODAL_TOKEN_SECRET")):
        for separator in (":", ";", ","):
            if separator in token:
                token_id, token_secret = token.split(separator, 1)
                env.setdefault("MODAL_TOKEN_ID", token_id.strip())
                env.setdefault("MODAL_TOKEN_SECRET", token_secret.strip())
                break

    return env


@dataclass(frozen=True)
class CommandResult:
    operation: str
    argv: list[str]
    cwd: str | None
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out


class ModalCommandRunner:
    def __init__(self, timeout_seconds: int = 120) -> None:
        self.timeout_seconds = timeout_seconds

    def run(
        self,
        argv: list[str],
        *,
        operation: str,
        cwd: str | None = None,
        timeout_seconds: int | None = None,
        parse_json: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if dry_run:
            return envelope(
                CommandResult(operation, argv, cwd, None, "", ""),
                data=None,
                dry_run=True,
            )

        timeout = timeout_seconds or self.timeout_seconds
        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                env=modal_environment(Path(cwd) if cwd else Path.cwd()),
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
                timeout=timeout,
                check=False,
            )
            result = CommandResult(
                operation=operation,
                argv=argv,
                cwd=cwd,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except FileNotFoundError as exc:
            result = CommandResult(operation, argv, cwd, 127, "", str(exc))
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode(errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            result = CommandResult(
                operation=operation,
                argv=argv,
                cwd=cwd,
                returncode=None,
                stdout=stdout,
                stderr=stderr,
                timed_out=True,
            )

        data: Any = None
        error: str | None = None
        if result.success and parse_json:
            try:
                data = json.loads(result.stdout or "null")
            except json.JSONDecodeError as exc:
                error = f"Failed to parse JSON output: {exc}"
        return envelope(result, data=data, error=error)


def envelope(
    result: CommandResult,
    *,
    data: Any = None,
    error: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    success = (dry_run or result.success) and error is None
    if dry_run:
        error = None
    elif result.timed_out:
        error = "Command timed out"
    elif not result.success and error is None:
        error = result.stderr.strip() or result.stdout.strip() or "Command failed"

    return {
        "success": success,
        "operation": result.operation,
        "command": {
            "argv": result.argv,
            "display": " ".join(result.argv),
            "cwd": result.cwd,
            "dry_run": dry_run,
        },
        "returncode": result.returncode,
        "data": data,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "error": error,
    }


def guarded_response(operation: str, message: str, argv: list[str] | None = None) -> dict[str, Any]:
    result = CommandResult(operation, argv or [], None, None, "", "")
    response = envelope(result, error=message)
    response["success"] = False
    return response
