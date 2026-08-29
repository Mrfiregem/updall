from pathlib import Path

import pytest
import yaml

import updall.config as uc


def test_config_shell_empty_list():
    with pytest.raises(ValueError):
        _ = uc.UpdAllConfig(entries=[], shell=[])


def test_config_shell_non_executable():
    with pytest.raises(ValueError):
        _ = uc.UpdAllConfig(entries=[], shell=["not-a-file"])


def test_config_shell():
    _ = uc.UpdAllConfig(entries=[], shell=["true"])


def test_read_nonexisitent_file():
    with pytest.raises(OSError):
        _ = uc.read_config(Path("/not/a/file"))


def test_read_empty_config(tmp_path: Path):
    config = tmp_path / "empty.yaml"
    config.touch()
    with pytest.raises(ValueError):
        _ = uc.read_config(config)


def test_read_bare_config(tmp_path: Path):
    config = tmp_path / "bare.yaml"
    _ = config.write_text("entries: []")
    actual = uc.read_config(config)
    assert actual == uc.UpdAllConfig(entries=[])


def test_read_invalid_yaml_config(tmp_path: Path):
    config = tmp_path / "invalid.yaml"
    _ = config.write_text("/ not! valid...")
    with pytest.raises((yaml.YAMLError, TypeError)):
        _ = uc.read_config(config)


def test_read_unreadable_config(tmp_path: Path):
    config = tmp_path / "secret.yaml"
    _ = config.write_text("entries: []")
    config.chmod(0o000)
    try:
        with pytest.raises(OSError):
            _ = uc.read_config(config)
    finally:
        # Let pytest cleanup file
        config.chmod(0o644)


def test_resolve_when_conditions(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("UPDALL_TEST", "12")
    assert uc.resolve_when_conditions(
        uc.WhenCondition(env_equals={"UPDALL_TEST": "12"}, has_exe="true")
    )


@pytest.mark.parametrize(
    "cond",
    [
        uc.WhenCondition(has_exe="not-a-real-cmd"),
        uc.WhenCondition(is_os="NotWindows"),
        uc.WhenCondition(env_equals={"FOO": "bar"}),
        uc.WhenCondition(is_not=uc.WhenCondition(env_equals={"FOO": "baz"})),
        uc.WhenCondition(
            all=[
                uc.WhenCondition(env_equals={"FOO": "baz"}),
                uc.WhenCondition(has_exe="another-fake-command"),
            ]
        ),
    ],
)
def test_resolve_failed_when_condition(
    cond: uc.WhenCondition, monkeypatch: pytest.MonkeyPatch
):
    """Check that each when condition fails"""
    monkeypatch.setenv("FOO", "baz")
    assert not uc.resolve_when_condition(cond)
