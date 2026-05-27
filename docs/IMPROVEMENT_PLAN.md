# Modal MCP Improvement Plan

## Baseline

Repository forked from `https://github.com/smehmood/modal-mcp-server.git`.

Current upstream snapshot:

- Commit: `576468e22a07669b1bd922c3b269383762652d00`
- Commit date: `2025-03-25 18:53:41 -0400`
- Main implementation: `src/modal_mcp/server.py`
- Current tools: deploy app, list volumes, list volume contents, copy volume files, remove volume files, upload files, download files.

The current implementation is useful but thin: it shells out to `modal`, has no package entry point, has no tests, has limited input validation, and does not expose app/deployment operations beyond deploy.

## Product Goal

Make this MCP server safe and practical for day-to-day Modal operations from Codex/Cursor/Claude:

- deploy and inspect Modal apps;
- manage Modal volumes used for models, generated assets, logs, and workflow state;
- expose errors in a structured way;
- avoid accidental destructive actions;
- be easy to install as a local MCP server on Windows and Unix-like systems.

## External API Reference Points

The plan follows the current Modal CLI surface:

- `modal deploy [OPTIONS] APP_REF` supports `--name`, `--env`, `--stream-logs`, `--tag`, `-m`, `--timestamps`, and deployment strategy.
- `modal volume` supports `list`, `ls`, `put`, `get`, `cp`, `rm`, `create`, `delete`, `rename`, and `dashboard`.
- `modal app` supports `list`, `history`, `logs`, `stop`, `rollback`, `rollover`, and `dashboard`.

## Stage 1 - Packaging And Runtime Hygiene

Scope:

- Add a proper Python package entry point, for example `modal-mcp-server = "modal_mcp.server:main"`.
- Replace direct `if __name__ == "__main__": mcp.run()` with a reusable `main()` function.
- Remove unused imports from `server.py`.
- Add a typed command runner module instead of keeping subprocess logic inside every tool.
- Add timeout support and predictable command metadata to every response.
- Stop requiring `uv` for every deploy path; support plain `modal deploy`, `uv run`, and explicit working directory.

Acceptance criteria:

- `uv run modal-mcp-server` starts the MCP server.
- Existing README configuration uses the entry point instead of a raw `server.py` path.
- Command failures preserve `returncode`, `stdout`, `stderr`, and argv.

## Stage 2 - Strong Schemas And Safer Inputs

Scope:

- Introduce Pydantic models or explicit validation helpers for tool inputs.
- Normalize local paths and reject ambiguous empty paths.
- Add `environment` parameter to Modal operations that support `-e/--env`.
- Add `dry_run` to all write/destructive operations.
- Add explicit confirmation parameters for destructive operations:
  - `confirm_delete=true` for volume file delete;
  - `confirm_delete_volume=true` for volume delete;
  - `confirm_stop=true` for app stop.
- Make recursive operations explicit and visible in the returned command metadata.

Acceptance criteria:

- Destructive tools fail closed unless the confirmation flag is set.
- Every tool returns a consistent envelope: `success`, `operation`, `command`, `data`, `error`, `stdout`, `stderr`.
- Sensitive environment values are never echoed.

## Stage 3 - Complete Modal Volume Coverage

Scope:

- Keep and harden existing tools:
  - `list_modal_volumes`
  - `list_modal_volume_contents`
  - `put_modal_volume_file`
  - `get_modal_volume_file`
  - `copy_modal_volume_files`
  - `remove_modal_volume_file`
- Add missing volume tools:
  - `create_modal_volume`
  - `delete_modal_volume`
  - `rename_modal_volume`
  - `get_modal_volume_dashboard_url` or `open_modal_volume_dashboard` depending on client expectations.
- Add optional recursive copy support for `modal volume cp -r`.
- Add output parsing for JSON-capable commands and plain-text fallback for commands without JSON.

Acceptance criteria:

- All documented `modal volume` commands except browser-opening dashboard are represented or intentionally omitted with rationale.
- JSON commands are parsed into `data`; plain output commands are returned as text with command metadata.

## Stage 4 - App And Deployment Operations

Scope:

- Expand deploy:
  - support file path and module path (`-m`);
  - support deployment name;
  - support environment;
  - support tag;
  - support stream logs;
  - support timestamps;
  - support deployment strategy.
- Add app tools:
  - `list_modal_apps`
  - `get_modal_app_history`
  - `get_modal_app_logs`
  - `stop_modal_app`
  - `rollback_modal_app`
  - `rollover_modal_app`
- Keep long-running log streaming out of the default path; first implement bounded log fetch via `--tail`, `--since`, `--until`, `--search`, `--source`, and ID filters.

Acceptance criteria:

- A user can deploy, list apps, fetch recent logs, inspect history, and stop/rollback/rollover an app through MCP.
- Log tools default to bounded output to avoid hanging MCP clients.

## Stage 5 - Tests And Local Verification

Scope:

- Add unit tests for command building and response normalization.
- Add tests for destructive-operation guards.
- Add tests for JSON parsing and plain-text fallback.
- Add a fake command runner so tests do not require Modal credentials.
- Add optional integration smoke tests that run only when Modal credentials are present.

Acceptance criteria:

- `uv run pytest` passes without Modal credentials.
- Integration tests are opt-in via an environment variable, for example `MODAL_MCP_RUN_INTEGRATION=1`.
- CI or local check command is documented.

## Stage 6 - Documentation And MCP Client Setup

Scope:

- Rewrite README around real usage:
  - install;
  - configure with Codex/Cursor/Claude;
  - authenticate Modal CLI;
  - run MCP Inspector;
  - example tool calls;
  - safety model for destructive operations.
- Add a Windows-specific configuration example.
- Add a troubleshooting section for:
  - missing `modal`;
  - missing Modal credentials;
  - `uv` path issues;
  - invalid working directory;
  - JSON parse failures.

Acceptance criteria:

- A fresh user can clone, run `uv sync`, start the MCP server, and validate it with MCP Inspector.
- README does not require reading source code to understand the tool surface.

## Stage 7 - RunComfy-Oriented Extensions

Scope:

- Add documented examples for model/artifact volume workflows:
  - upload model files;
  - list generated output folders;
  - download selected outputs;
  - fetch recent app logs after a failed generation.
- Consider thin convenience tools only after generic tools are stable:
  - `sync_modal_volume_directory`
  - `download_modal_outputs`
  - `tail_modal_generation_logs`

Acceptance criteria:

- RunComfy workflows can be done with generic Modal tools first.
- Convenience tools are additive and do not hide the underlying Modal command behavior.

## First Implementation Batch

Recommended first batch:

1. Stage 1 packaging/runtime hygiene.
2. Stage 2 response envelope and destructive guards.
3. Stage 5 unit-test scaffold for the new command runner.

This gives a stable foundation before expanding the tool surface.

## Open Decisions

1. Should this remain a nested Git repository under `vendor/modal-mcp`, or should it be vendored as normal source inside the RunComfy repository?
2. Should `origin` continue pointing at upstream, or should it be changed to a personal GitHub fork before local commits?
3. Should destructive Modal operations be enabled by default with confirmation flags, or disabled by config unless explicitly allowed?
4. Should deploy default to the system Modal CLI, or should `uv run` remain the default for reproducibility?
