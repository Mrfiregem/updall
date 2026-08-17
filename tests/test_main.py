import importlib
import logging
import subprocess
import sys
from pathlib import Path
from pprint import pprint

import pytest
import yaml
from click.testing import CliRunner

import updall
import updall.config

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


@pytest.fixture
def default_config() -> updall.config.UpdAllConfig:
    return updall.config.UpdAllConfig(entries=[])


@pytest.fixture
def fake_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    config = tmp_path / "updall"
    config.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _ = importlib.reload(updall)
    return config


def test_app_name():
    actual = updall.get_app_name()
    assert actual == "updall"


@pytest.mark.parametrize(
    "verbosity,expected",
    [(0, logging.WARNING), (1, logging.INFO), (2, logging.DEBUG)],
)
def test_log_verbosity(verbosity: int, expected: int):
    assert updall.get_log_level(verbosity) == expected


def test_run_command_success(default_config: updall.config.UpdAllConfig):
    updall.run_command(default_config.shell, "true")


def test_run_command_failure(default_config: updall.config.UpdAllConfig):
    with pytest.raises(subprocess.SubprocessError):
        updall.run_command(default_config.shell, "false")


def test_commandline_bare_config(fake_config_dir: Path):
    config = fake_config_dir / "config.yaml"
    _ = config.write_text("entries: []")
    runner = CliRunner()
    result = runner.invoke(updall.main, [])
    print(result)
    assert result.exit_code == 0


def test_cmdline_empty_config(fake_config_dir: Path):
    config = fake_config_dir / "config.yaml"
    config.touch()
    runner = CliRunner()
    result = runner.invoke(updall.main, ["--verbose"])

    assert result.exit_code == 1
    assert result.exception is not None


def test_cmdline_loop_entries(fake_config_dir: Path):
    config = fake_config_dir / "config.yaml"
    data = {
        "entries": [
            {
                "name": "always",
                "update": "printf 'Hello, %s!\\n' 'world'",
                "clean": "false",
                "when": [{"has_exe": "printf"}],
            },
        ]
    }
    with open(config, "w") as file:
        yaml.safe_dump(data, file)

    runner = CliRunner()
    result = runner.invoke(updall.main, [])
    pprint(vars(result))
    assert result.exit_code == 0
    assert "always::update" in result.stdout
    assert "always::clean" in result.stdout


def test_no_retry_failed_entry(fake_config_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    config = fake_config_dir / "config.yaml"
    data = {"entries": [{"name": "foobar", "update": "false"}]}
    with open(config, "w") as file:
        yaml.safe_dump(data, file)

    runner = CliRunner()
    result = runner.invoke(updall.main, [])
    assert result.exit_code == 0


def test_retry_failed_entry(fake_config_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]

    update_script = fake_config_dir / "fts.sh"
    check = fake_config_dir / "succeed"
    with open(update_script, "w") as file:
        _ = file.write(f"""
            #!/bin/sh
            if [ -e '{check!s}' ]; then
                true
            else
                touch '{check!s}'
                false
            fi
        """)
    update_script.chmod(0o755)

    config = fake_config_dir / "config.yaml"
    data = {"entries": [{"name": "foobar", "update": str(update_script)}]}
    with open(config, "w") as file:
        yaml.safe_dump(data, file)

    runner = CliRunner()
    result = runner.invoke(updall.main, [])
    assert result.exit_code == 0
