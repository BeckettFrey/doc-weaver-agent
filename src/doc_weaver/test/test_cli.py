import json
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from click.testing import CliRunner
from doc_weaver.cli import cli, validate_template


VALID_TEMPLATE = """\
# John Doe - Software Engineer
> <2, 30, 80>
## Experience
### Work
- <1, 20, 100>
- Led a team of 5 engineers.
## Skills
### Technical
- <1, 10, 50>
"""

VALID_SINGLE = """\
# Title
> <1, 10, 50>
## Section
### Sub
- Content item
"""

class TestConfigSet:

    def test_set_creates_env_file(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".doc_weaver"
        env_file = config_dir / ".env"
        monkeypatch.setattr("doc_weaver.cli.CONFIG_DIR", config_dir)
        monkeypatch.setattr("doc_weaver.cli.ENV_FILE", env_file)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "OPENAI_API_KEY", "sk-test123"])
        assert result.exit_code == 0
        assert "Saved" in result.output
        assert env_file.exists()
        assert "OPENAI_API_KEY=sk-test123" in env_file.read_text()

    def test_set_updates_existing_key(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".doc_weaver"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("KEY=old\n")
        monkeypatch.setattr("doc_weaver.cli.CONFIG_DIR", config_dir)
        monkeypatch.setattr("doc_weaver.cli.ENV_FILE", env_file)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "KEY", "new"])
        assert result.exit_code == 0
        assert "KEY=new" in env_file.read_text()

    def test_set_preserves_other_keys(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".doc_weaver"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("A=1\nB=2\n")
        monkeypatch.setattr("doc_weaver.cli.CONFIG_DIR", config_dir)
        monkeypatch.setattr("doc_weaver.cli.ENV_FILE", env_file)

        runner = CliRunner()
        runner.invoke(cli, ["config", "set", "C", "3"])
        content = env_file.read_text()
        assert "A=1" in content
        assert "B=2" in content
        assert "C=3" in content


class TestConfigShow:

    def test_show_no_config(self, tmp_path, monkeypatch):
        env_file = tmp_path / "nonexistent" / ".env"
        monkeypatch.setattr("doc_weaver.cli.ENV_FILE", env_file)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        assert "No config" in result.output

    def test_show_masks_values(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".doc_weaver"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("API_KEY=sk-very-secret-key\n")
        monkeypatch.setattr("doc_weaver.cli.ENV_FILE", env_file)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        assert "API_KEY" in result.output
        assert "sk-very-secret-key" not in result.output
        assert "sk-v****" in result.output

    def test_show_short_value(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".doc_weaver"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("X=ab\n")
        monkeypatch.setattr("doc_weaver.cli.ENV_FILE", env_file)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        assert "****" in result.output

    def test_show_skips_comments_and_blanks(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".doc_weaver"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("# comment\n\nKEY=value123\n")
        monkeypatch.setattr("doc_weaver.cli.ENV_FILE", env_file)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        assert "KEY" in result.output


class TestTemplateList:

    def test_list_empty(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        runner = CliRunner()
        result = runner.invoke(cli, ["template", "list"])
        assert result.exit_code == 0
        assert "No templates" in result.output

    def test_list_shows_templates(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "resume.md").write_text("# Test\n")
        (templates_dir / "letter.md").write_text("# Test\n")
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        runner = CliRunner()
        result = runner.invoke(cli, ["template", "list"])
        assert result.exit_code == 0
        assert "letter" in result.output
        assert "resume" in result.output


class TestTemplateAdd:

    def test_add_valid_template(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        src = tmp_path / "input.md"
        src.write_text(VALID_TEMPLATE)

        runner = CliRunner()
        result = runner.invoke(cli, ["template", "add", "mytemplate", str(src)])
        assert result.exit_code == 0
        assert "added" in result.output
        assert (templates_dir / "mytemplate.md").exists()

    def test_add_invalid_template(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        src = tmp_path / "bad.md"
        src.write_text("no structure at all")

        runner = CliRunner()
        result = runner.invoke(cli, ["template", "add", "bad", str(src)])
        assert result.exit_code == 1

    def test_add_overwrites_existing(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "t.md").write_text("old")
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        src = tmp_path / "input.md"
        src.write_text(VALID_TEMPLATE)

        runner = CliRunner()
        result = runner.invoke(cli, ["template", "add", "t", str(src)])
        assert result.exit_code == 0
        assert "Overwriting" in result.output


class TestTemplateShow:

    def test_show_existing(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "demo.md").write_text("# Demo Content")
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        runner = CliRunner()
        result = runner.invoke(cli, ["template", "show", "demo"])
        assert result.exit_code == 0
        assert "Demo Content" in result.output

    def test_show_nonexistent(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        runner = CliRunner()
        result = runner.invoke(cli, ["template", "show", "nope"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestTemplateRemove:
    def test_remove_existing(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "old.md").write_text("# Old")
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        runner = CliRunner()
        result = runner.invoke(cli, ["template", "remove", "old"])
        assert result.exit_code == 0
        assert "removed" in result.output
        assert not (templates_dir / "old.md").exists()

    def test_remove_nonexistent(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        runner = CliRunner()
        result = runner.invoke(cli, ["template", "remove", "nope"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestGenerate:

    def test_generate_success(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "resume.md").write_text(VALID_TEMPLATE)
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        output_dir = tmp_path / "output"

        metadata = {
            "tasks": [{"task_number": 0}],
            "total_elapsed_ms": 123.45,
            "model": "gpt-4o",
        }

        async def mock_hydrate(md, context="", model="gpt-4o", timeout=30):
            return "# Hydrated doc\n", metadata

        with patch("doc_weaver.cli.hydrate", side_effect=mock_hydrate):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "generate", "resume",
                "--output-dir", str(output_dir),
                "--prompt", "Write for senior role",
            ])

        assert result.exit_code == 0
        assert (output_dir / "output.md").exists()
        assert (output_dir / "metadata.json").exists()

    def test_generate_with_prompt_file(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "t.md").write_text(VALID_TEMPLATE)
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Context from file")
        output_dir = tmp_path / "out"

        metadata = {"tasks": [], "total_elapsed_ms": 10.0, "model": "gpt-4o"}

        async def mock_hydrate(md, context="", model="gpt-4o", timeout=30):
            return "# Result\n", metadata

        with patch("doc_weaver.cli.hydrate", side_effect=mock_hydrate):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "generate", "t",
                "--output-dir", str(output_dir),
                "--prompt-file", str(prompt_file),
            ])

        assert result.exit_code == 0

    def test_generate_both_prompt_and_file_errors(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "t.md").write_text(VALID_TEMPLATE)
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("text")

        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate", "t",
            "--output-dir", str(tmp_path / "out"),
            "--prompt", "inline",
            "--prompt-file", str(prompt_file),
        ])
        assert result.exit_code != 0
        assert "not both" in result.output

    def test_generate_template_not_found(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate", "nonexistent",
            "--output-dir", str(tmp_path / "out"),
        ])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_generate_no_prompt(self, tmp_path, monkeypatch):
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "t.md").write_text(VALID_TEMPLATE)
        monkeypatch.setattr("doc_weaver.cli.TEMPLATES_DIR", templates_dir)

        output_dir = tmp_path / "out"
        metadata = {"tasks": [], "total_elapsed_ms": 5.0, "model": "gpt-4o"}

        async def mock_hydrate(md, context="", model="gpt-4o", timeout=30):
            assert context == ""
            return "# Output\n", metadata

        with patch("doc_weaver.cli.hydrate", side_effect=mock_hydrate):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "generate", "t",
                "--output-dir", str(output_dir),
            ])

        assert result.exit_code == 0


class TestValidateTemplateEdgeCases:

    def test_placeholder_not_alone_on_line(self):
        md = """\
# Title
> Tagline
## Section
### Sub
- some text <1, 10, 50> more text
"""
        errors = validate_template(md)
        assert any("only content on its line" in e for e in errors)

    def test_batch_zero(self):
        md = """\
# Title
> <0, 10, 50>
## Section
### Sub
- Content
"""
        errors = validate_template(md)
        assert any("batch number must be >= 1" in e for e in errors)

    def test_negative_min_chars(self):
        md = """\
# Title
> <1, -5, 50>
## Section
### Sub
- Content
"""
        errors = validate_template(md)
        # Negative numbers won't match the regex \d+ so no placeholder found
        assert any("No placeholders" in e for e in errors)

    def test_max_chars_zero(self):
        md = """\
# Title
> <1, 0, 0>
## Section
### Sub
- Content
"""
        errors = validate_template(md)
        assert any("max_chars must be >= 1" in e for e in errors)



class TestValidateTemplate:

    def test_valid_template(self):
        errors = validate_template(VALID_TEMPLATE)
        assert errors == []

    def test_valid_single_placeholder(self):
        errors = validate_template(VALID_SINGLE)
        assert errors == []

    def test_no_placeholders(self):
        md = """\
# Title
> Tagline
## Section
### Sub
- Content
"""
        errors = validate_template(md)
        assert any("No placeholders" in e for e in errors)

    def test_min_gte_max(self):
        md = """\
# Title
> <1, 100, 50>
## Section
### Sub
- Content
"""
        errors = validate_template(md)
        assert any("min_chars" in e and "less than" in e for e in errors)

    def test_equal_min_max(self):
        md = """\
# Title
> <1, 50, 50>
## Section
### Sub
- Content
"""
        errors = validate_template(md)
        assert any("min_chars" in e and "less than" in e for e in errors)

    def test_missing_title(self):
        md = """\
> <1, 10, 50>
## Section
### Sub
- Content
"""
        errors = validate_template(md)
        assert any("Structure error" in e for e in errors)

    def test_missing_tagline(self):
        md = """\
# Title
## Section
### Sub
- <1, 10, 50>
"""
        errors = validate_template(md)
        assert any("Structure error" in e for e in errors)

    def test_content_before_subsection(self):
        md = """\
# Title
> Tagline
## Section
- <1, 10, 50>
### Sub
"""
        errors = validate_template(md)
        assert any("Structure error" in e for e in errors)

    def test_multiple_errors(self):
        md = """\
> <1, 100, 50>
## Section
### Sub
- Content
"""
        errors = validate_template(md)
        assert len(errors) >= 2  # min >= max AND structure error


class TestValidateCLI:

    def test_valid_file(self, tmp_path):
        f = tmp_path / "template.md"
        f.write_text(VALID_TEMPLATE)
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", str(f)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()
        assert "Placeholders: 3" in result.output
        assert "Batches: 1, 2" in result.output

    def test_invalid_file(self, tmp_path):
        md = """\
# Title
> Tagline
## Section
### Sub
- No placeholders here
"""
        f = tmp_path / "bad.md"
        f.write_text(md)
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", str(f)])
        assert result.exit_code == 1
        assert "error" in result.output.lower()

    def test_nonexistent_file(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "/nonexistent/file.md"])
        assert result.exit_code != 0
