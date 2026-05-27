# Modal MCP Server

MCP server for operating Modal apps and volumes through the Modal CLI.

This fork is hardened for local agent usage:

- read-only inspection for Modal apps and volumes;
- deploy support for file refs and module refs;
- volume upload, download, copy, create, rename, and delete;
- bounded app log fetching by default;
- confirmation flags for destructive operations;
- `.env` support for local credentials without echoing secrets.

## Requirements

- Python 3.11+
- `uv`
- Modal CLI credentials

Modal officially reads credentials from `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`.

Supported local `.env` keys:

```env
MODAL_TOKEN_ID=ak-...
MODAL_TOKEN_SECRET=as-...
```

Proxy Auth Tokens are different. They are used as HTTP headers for protected Web
Functions, not for Modal CLI authentication. Store them separately if your app
needs to call proxy-protected endpoints:

```env
MODAL_PROXY_AUTH_KEY=wk-...
MODAL_PROXY_AUTH_SECRET=ws-...
```

The server searches for `.env` from the current working directory up through
parent directories. You can override this with `MODAL_MCP_ENV_FILE`.

## Install

```bash
uv sync
```

## Run

```bash
uv run modal-mcp-server
```

## MCP Client Configuration

Example:

```json
{
  "mcpServers": {
    "modal-mcp": {
      "command": "uv",
      "args": [
        "--project",
        "G:/RunComfy/vendor/modal-mcp",
        "run",
        "modal-mcp-server"
      ]
    }
  }
}
```

If the MCP client starts the server from another directory, set an explicit env
file path:

```json
{
  "mcpServers": {
    "modal-mcp": {
      "command": "uv",
      "args": [
        "--project",
        "G:/RunComfy/vendor/modal-mcp",
        "run",
        "modal-mcp-server"
      ],
      "env": {
        "MODAL_MCP_ENV_FILE": "G:/RunComfy/.env"
      }
    }
  }
}
```

## Tools

### Deploy

- `deploy_modal_app`

Supports:

- `app_ref`
- `absolute_path_to_app`
- `module`
- `working_directory`
- `use_uv`
- `name`
- `environment`
- `tag`
- `stream_logs`
- `timestamps`
- `strategy`
- `dry_run`

### Volumes

- `list_modal_volumes`
- `list_modal_volume_contents`
- `copy_modal_volume_files`
- `remove_modal_volume_file`
- `put_modal_volume_file`
- `get_modal_volume_file`
- `create_modal_volume`
- `delete_modal_volume`
- `rename_modal_volume`

Destructive tools require confirmation flags unless `dry_run=true`:

- `remove_modal_volume_file`: `confirm_delete=true`
- `delete_modal_volume`: `confirm_delete_volume=true`
- `rename_modal_volume`: `confirm_rename=true`

### Apps

- `list_modal_apps`
- `get_modal_app_history`
- `get_modal_app_logs`
- `stop_modal_app`
- `rollback_modal_app`
- `rollover_modal_app`

Destructive or state-changing app tools require confirmation flags unless
`dry_run=true`:

- `stop_modal_app`: `confirm_stop=true`
- `rollback_modal_app`: `confirm_rollback=true`
- `rollover_modal_app`: `confirm_rollover=true`

`get_modal_app_logs` defaults to bounded fetch. Streaming logs with `follow=true`
requires `confirm_follow=true`.

## Response Shape

All tools return:

```json
{
  "success": true,
  "operation": "list_modal_volumes",
  "command": {
    "argv": ["modal", "volume", "list", "--json"],
    "display": "modal volume list --json",
    "cwd": null,
    "dry_run": false
  },
  "returncode": 0,
  "data": [],
  "stdout": "",
  "stderr": "",
  "error": null
}
```

## Test

```bash
uv run python -m unittest discover -s tests
```

On locked-down Windows environments, use a workspace-local uv cache:

```powershell
$env:UV_CACHE_DIR='G:\RunComfy\vendor\modal-mcp\.uv-cache'
uv run python -m unittest discover -s tests
```
