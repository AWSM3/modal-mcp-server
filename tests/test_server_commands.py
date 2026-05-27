import asyncio
from pathlib import Path
from unittest import TestCase

from modal_mcp import server


class ServerCommandTests(TestCase):
    def test_delete_volume_requires_confirmation(self) -> None:
        result = asyncio.run(server.delete_modal_volume("models"))

        self.assertFalse(result["success"])
        self.assertIn("confirm_delete_volume", result["error"])

    def test_delete_volume_dry_run_builds_safe_command(self) -> None:
        result = asyncio.run(server.delete_modal_volume("models", dry_run=True))

        self.assertTrue(result["success"])
        self.assertEqual(
            result["command"]["argv"],
            ["modal", "volume", "delete", "--yes", "models"],
        )

    def test_deploy_absolute_path_uses_parent_cwd(self) -> None:
        app_path = Path("C:/tmp/modal_app.py")
        result = asyncio.run(
            server.deploy_modal_app(
                absolute_path_to_app=str(app_path),
                name="demo",
                environment="dev",
                dry_run=True,
            )
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["command"]["cwd"], str(app_path.parent))
        self.assertEqual(
            result["command"]["argv"],
            ["modal", "deploy", "--name", "demo", "--env", "dev", "modal_app.py"],
        )

    def test_logs_follow_requires_confirmation(self) -> None:
        result = asyncio.run(server.get_modal_app_logs("my-app", follow=True))

        self.assertFalse(result["success"])
        self.assertIn("confirm_follow", result["error"])
