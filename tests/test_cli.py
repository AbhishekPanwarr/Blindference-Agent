"""Tests for blindference_agent.cli."""

import os
from click.testing import CliRunner

from blindference_agent.cli import main


class TestCliInit:
    def test_init_creates_files(self, tmp_path):
        runner = CliRunner()
        target = str(tmp_path / "my-agent")
        result = runner.invoke(main, ["init", "--dir", target])

        assert result.exit_code == 0
        assert os.path.exists(os.path.join(target, ".env"))
        assert os.path.exists(os.path.join(target, "agent.py"))
        assert os.path.exists(os.path.join(target, "requirements.txt"))

    def test_env_template_contains_required_vars(self, tmp_path):
        runner = CliRunner()
        target = str(tmp_path / "my-agent")
        runner.invoke(main, ["init", "--dir", target])

        with open(os.path.join(target, ".env")) as f:
            content = f.read()
        assert "BLF_ICL_URL" in content
        assert "BLF_COFHE_RPC" in content
        assert "BLF_PRIVATE_KEY" in content

    def test_agent_template_uses_model_id(self, tmp_path):
        runner = CliRunner()
        target = str(tmp_path / "my-agent")
        runner.invoke(main, ["init", "--dir", target])

        with open(os.path.join(target, "agent.py")) as f:
            content = f.read()
        assert "model_id=" in content
        assert "model=" not in content  # old broken template

    def test_init_idempotent(self, tmp_path):
        runner = CliRunner()
        target = str(tmp_path / "my-agent")
        result1 = runner.invoke(main, ["init", "--dir", target])
        result2 = runner.invoke(main, ["init", "--dir", target])

        assert result1.exit_code == 0
        assert result2.exit_code == 0
        assert "already exists" in result2.output.lower() or "created" in result2.output.lower()


class TestCliHelp:
    def test_main_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.output
        assert "test" in result.output
        assert "run" in result.output

    def test_init_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--help"])
        assert result.exit_code == 0
        assert "--dir" in result.output
