"""MCP server for operating Modal apps and volumes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from modal_mcp.runner import ModalCommandRunner, guarded_response

mcp = FastMCP("modal-mcp")
runner = ModalCommandRunner()


def main() -> None:
    mcp.run()


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value.strip()


def _append_env(argv: list[str], environment: str | None) -> None:
    if environment:
        argv.extend(["--env", environment])


def _append_optional(argv: list[str], flag: str, value: str | int | None) -> None:
    if value is not None and value != "":
        argv.extend([flag, str(value)])


def _modal(*parts: str) -> list[str]:
    return ["modal", *parts]


def _run(
    argv: list[str],
    *,
    operation: str,
    environment: str | None = None,
    cwd: str | None = None,
    parse_json: bool = False,
    dry_run: bool = False,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    return runner.run(
        argv,
        operation=operation,
        cwd=cwd,
        parse_json=parse_json,
        dry_run=dry_run,
        timeout_seconds=timeout_seconds,
    )


def _modal_with_env(group: str, command: str, environment: str | None) -> list[str]:
    argv = _modal(group, command)
    _append_env(argv, environment)
    return argv


@mcp.tool()
async def deploy_modal_app(
    app_ref: str | None = None,
    absolute_path_to_app: str | None = None,
    module: bool = False,
    working_directory: str | None = None,
    use_uv: bool = False,
    name: str | None = None,
    environment: str | None = None,
    tag: str | None = None,
    stream_logs: bool = False,
    timestamps: bool = False,
    strategy: str | None = None,
    dry_run: bool = False,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    """Deploy a Modal app from a file path or Python module path."""

    ref = app_ref or absolute_path_to_app
    ref = _require_text(ref or "", "app_ref")
    cwd = working_directory
    deploy_ref = ref

    if absolute_path_to_app and not app_ref and not module:
        app_path = Path(absolute_path_to_app)
        cwd = cwd or str(app_path.parent)
        deploy_ref = app_path.name

    argv = ["uv", "run", "modal", "deploy"] if use_uv else _modal("deploy")
    _append_optional(argv, "--name", name)
    _append_env(argv, environment)
    if stream_logs:
        argv.append("--stream-logs")
    _append_optional(argv, "--tag", tag)
    if module:
        argv.append("-m")
    if timestamps:
        argv.append("--timestamps")
    _append_optional(argv, "--strategy", strategy)
    argv.append(deploy_ref)
    return _run(
        argv,
        operation="deploy_modal_app",
        cwd=cwd,
        dry_run=dry_run,
        timeout_seconds=timeout_seconds,
    )


@mcp.tool()
async def list_modal_volumes(environment: str | None = None) -> dict[str, Any]:
    """List Modal volumes."""

    return _run(
        _modal_with_env("volume", "list", environment) + ["--json"],
        operation="list_modal_volumes",
        parse_json=True,
    )


@mcp.tool()
async def list_modal_volume_contents(
    volume_name: str,
    path: str = "/",
    environment: str | None = None,
) -> dict[str, Any]:
    """List files and directories in a Modal volume."""

    volume_name = _require_text(volume_name, "volume_name")
    path = _require_text(path, "path")
    return _run(
        _modal_with_env("volume", "ls", environment) + ["--json", volume_name, path],
        operation="list_modal_volume_contents",
        parse_json=True,
    )


@mcp.tool()
async def copy_modal_volume_files(
    volume_name: str,
    paths: list[str],
    recursive: bool = False,
    environment: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Copy files inside a Modal volume."""

    volume_name = _require_text(volume_name, "volume_name")
    if len(paths) < 2 or any(not str(item).strip() for item in paths):
        return guarded_response(
            "copy_modal_volume_files",
            "At least one source path and one destination path are required",
        )
    argv = _modal_with_env("volume", "cp", environment)
    if recursive:
        argv.append("--recursive")
    argv.extend([volume_name, *paths])
    return _run(argv, operation="copy_modal_volume_files", dry_run=dry_run)


@mcp.tool()
async def remove_modal_volume_file(
    volume_name: str,
    remote_path: str,
    recursive: bool = False,
    confirm_delete: bool = False,
    environment: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Delete a file or directory from a Modal volume."""

    volume_name = _require_text(volume_name, "volume_name")
    remote_path = _require_text(remote_path, "remote_path")
    if not confirm_delete and not dry_run:
        return guarded_response(
            "remove_modal_volume_file",
            "Set confirm_delete=true to delete a file from a Modal volume",
        )
    argv = _modal_with_env("volume", "rm", environment)
    if recursive:
        argv.append("--recursive")
    argv.extend([volume_name, remote_path])
    return _run(argv, operation="remove_modal_volume_file", dry_run=dry_run)


@mcp.tool()
async def put_modal_volume_file(
    volume_name: str,
    local_path: str,
    remote_path: str = "/",
    force: bool = False,
    environment: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Upload a local file or directory to a Modal volume."""

    volume_name = _require_text(volume_name, "volume_name")
    local_path = _require_text(local_path, "local_path")
    remote_path = _require_text(remote_path, "remote_path")
    argv = _modal_with_env("volume", "put", environment)
    if force:
        argv.append("--force")
    argv.extend([volume_name, local_path, remote_path])
    return _run(argv, operation="put_modal_volume_file", dry_run=dry_run)


@mcp.tool()
async def get_modal_volume_file(
    volume_name: str,
    remote_path: str,
    local_destination: str = ".",
    force: bool = False,
    environment: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Download a file or directory from a Modal volume."""

    volume_name = _require_text(volume_name, "volume_name")
    remote_path = _require_text(remote_path, "remote_path")
    local_destination = _require_text(local_destination, "local_destination")
    argv = _modal_with_env("volume", "get", environment)
    if force:
        argv.append("--force")
    argv.extend([volume_name, remote_path, local_destination])
    return _run(argv, operation="get_modal_volume_file", dry_run=dry_run)


@mcp.tool()
async def create_modal_volume(
    volume_name: str,
    version: int | None = None,
    environment: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create a Modal volume."""

    volume_name = _require_text(volume_name, "volume_name")
    argv = _modal_with_env("volume", "create", environment)
    _append_optional(argv, "--version", version)
    argv.append(volume_name)
    return _run(argv, operation="create_modal_volume", dry_run=dry_run)


@mcp.tool()
async def delete_modal_volume(
    volume_name: str,
    allow_missing: bool = False,
    confirm_delete_volume: bool = False,
    environment: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Delete a Modal volume and all its data."""

    volume_name = _require_text(volume_name, "volume_name")
    if not confirm_delete_volume and not dry_run:
        return guarded_response(
            "delete_modal_volume",
            "Set confirm_delete_volume=true to delete a Modal volume",
        )
    argv = _modal_with_env("volume", "delete", environment)
    if allow_missing:
        argv.append("--allow-missing")
    argv.append("--yes")
    argv.append(volume_name)
    return _run(argv, operation="delete_modal_volume", dry_run=dry_run)


@mcp.tool()
async def rename_modal_volume(
    old_name: str,
    new_name: str,
    confirm_rename: bool = False,
    environment: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Rename a Modal volume."""

    old_name = _require_text(old_name, "old_name")
    new_name = _require_text(new_name, "new_name")
    if not confirm_rename and not dry_run:
        return guarded_response(
            "rename_modal_volume",
            "Set confirm_rename=true to rename a Modal volume",
        )
    argv = _modal_with_env("volume", "rename", environment) + ["--yes", old_name, new_name]
    return _run(argv, operation="rename_modal_volume", dry_run=dry_run)


@mcp.tool()
async def list_modal_apps(environment: str | None = None) -> dict[str, Any]:
    """List Modal apps."""

    return _run(
        _modal_with_env("app", "list", environment) + ["--json"],
        operation="list_modal_apps",
        parse_json=True,
    )


@mcp.tool()
async def get_modal_app_history(
    app_identifier: str,
    environment: str | None = None,
) -> dict[str, Any]:
    """Fetch Modal app deployment history."""

    app_identifier = _require_text(app_identifier, "app_identifier")
    return _run(
        _modal_with_env("app", "history", environment) + ["--json", app_identifier],
        operation="get_modal_app_history",
        parse_json=True,
    )


@mcp.tool()
async def get_modal_app_logs(
    app_identifier: str,
    tail: int = 100,
    since: str | None = None,
    until: str | None = None,
    search: str | None = None,
    function_id: str | None = None,
    function_call_id: str | None = None,
    container_id: str | None = None,
    source: str | None = None,
    timestamps: bool = False,
    show_function_id: bool = False,
    show_function_call_id: bool = False,
    show_container_id: bool = False,
    follow: bool = False,
    confirm_follow: bool = False,
    environment: str | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Fetch recent Modal app logs. Following logs requires confirm_follow."""

    app_identifier = _require_text(app_identifier, "app_identifier")
    if follow and not confirm_follow:
        return guarded_response(
            "get_modal_app_logs",
            "Set confirm_follow=true to stream logs; bounded fetch is the default",
        )
    argv = _modal_with_env("app", "logs", environment)
    if follow:
        argv.append("--follow")
    else:
        _append_optional(argv, "--tail", tail)
    _append_optional(argv, "--since", since)
    _append_optional(argv, "--until", until)
    _append_optional(argv, "--search", search)
    _append_optional(argv, "--function", function_id)
    _append_optional(argv, "--function-call", function_call_id)
    _append_optional(argv, "--container", container_id)
    _append_optional(argv, "--source", source)
    if timestamps:
        argv.append("--timestamps")
    if show_function_id:
        argv.append("--show-function-id")
    if show_function_call_id:
        argv.append("--show-function-call-id")
    if show_container_id:
        argv.append("--show-container-id")
    argv.append(app_identifier)
    return _run(
        argv,
        operation="get_modal_app_logs",
        timeout_seconds=timeout_seconds,
    )


@mcp.tool()
async def stop_modal_app(
    app_identifier: str,
    confirm_stop: bool = False,
    environment: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Stop a Modal app and terminate its containers."""

    app_identifier = _require_text(app_identifier, "app_identifier")
    if not confirm_stop and not dry_run:
        return guarded_response("stop_modal_app", "Set confirm_stop=true to stop a Modal app")
    return _run(
        _modal_with_env("app", "stop", environment) + ["--yes", app_identifier],
        operation="stop_modal_app",
        dry_run=dry_run,
    )


@mcp.tool()
async def rollback_modal_app(
    app_identifier: str,
    version: str | None = None,
    confirm_rollback: bool = False,
    environment: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Rollback a Modal app to a previous deployment version."""

    app_identifier = _require_text(app_identifier, "app_identifier")
    if not confirm_rollback and not dry_run:
        return guarded_response(
            "rollback_modal_app",
            "Set confirm_rollback=true to rollback a Modal app",
        )
    argv = _modal_with_env("app", "rollback", environment)
    argv.append(app_identifier)
    if version:
        argv.append(version)
    return _run(argv, operation="rollback_modal_app", dry_run=dry_run)


@mcp.tool()
async def rollover_modal_app(
    app_identifier: str,
    strategy: str | None = None,
    confirm_rollover: bool = False,
    environment: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Rollover a Modal app without code changes."""

    app_identifier = _require_text(app_identifier, "app_identifier")
    if not confirm_rollover and not dry_run:
        return guarded_response(
            "rollover_modal_app",
            "Set confirm_rollover=true to rollover a Modal app",
        )
    argv = _modal_with_env("app", "rollover", environment)
    _append_optional(argv, "--strategy", strategy)
    argv.append(app_identifier)
    return _run(argv, operation="rollover_modal_app", dry_run=dry_run)


if __name__ == "__main__":
    main()
