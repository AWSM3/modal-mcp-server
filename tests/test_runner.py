from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from modal_mcp.runner import CommandResult, ModalCommandRunner, envelope, modal_environment


class RunnerTests(TestCase):
    def test_dry_run_returns_success_without_executing(self) -> None:
        runner = ModalCommandRunner()
        with patch("subprocess.run") as run:
            result = runner.run(["modal", "volume", "list"], operation="list", dry_run=True)

        run.assert_not_called()
        self.assertTrue(result["success"])
        self.assertTrue(result["command"]["dry_run"])
        self.assertEqual(result["command"]["argv"], ["modal", "volume", "list"])

    def test_json_parse_failure_is_reported(self) -> None:
        result = envelope(
            CommandResult("list", ["modal"], None, 0, "not-json", ""),
            error="Failed to parse JSON output",
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Failed to parse JSON output")

    def test_dotenv_modal_token_credentials_are_loaded(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            env_file = Path("test.env").resolve()
            try:
                env_file.write_text(
                    "MODAL_TOKEN_ID=ak-test\nMODAL_TOKEN_SECRET=as-test\n",
                    encoding="utf-8",
                )
                with patch.dict(
                    "os.environ",
                    {"MODAL_MCP_ENV_FILE": str(env_file)},
                    clear=True,
                ), patch("modal_mcp.runner._candidate_dotenv_paths", return_value=[env_file]):
                    env = modal_environment(Path.cwd())
            finally:
                if env_file.exists():
                    env_file.unlink()

        self.assertEqual(env["MODAL_TOKEN_ID"], "ak-test")
        self.assertEqual(env["MODAL_TOKEN_SECRET"], "as-test")

    def test_modal_token_can_act_as_id_when_secret_is_present(self) -> None:
        with patch.dict(
            "os.environ",
            {"MODAL_TOKEN": "ak-test", "MODAL_TOKEN_SECRET": "as-test"},
            clear=True,
        ), patch("modal_mcp.runner._candidate_dotenv_paths", return_value=[]):
            env = modal_environment(Path.cwd())

        self.assertEqual(env["MODAL_TOKEN_ID"], "ak-test")
        self.assertEqual(env["MODAL_TOKEN_SECRET"], "as-test")
