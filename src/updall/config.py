import logging
import os
import platform
import shutil
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class WhenCondition(BaseModel):
    """Used in a `PackagerEntry` to determine if it should run by default."""

    has_exe: str | None = None
    """Used to check if the caller has `exe` on their PATH."""
    is_os: str | None = None
    """Used to check if the caller is on Windows, Linux, or MacOS."""
    env_equals: dict[str, str] | None = None
    """Used to check if all environment variable dict keys exist with values equaling dict values."""
    is_not: WhenCondition | None = None


class PackagerEntry(BaseModel):
    """The main point of `updall`. Each entry specifies an `update` script and an optional `clean` script to run at the end."""

    name: str
    """The name of the entry."""
    update: str
    """The command to run to update packages."""
    clean: str | None = None
    """An additional script run after all updates intended to run an additional cleanup command."""
    when: list[WhenCondition] = Field(default_factory=list)


class UpdAllConfig(BaseModel):
    """Validator class for `updall`'s config file."""

    shell: list[str] = ["/bin/sh", "-c"]
    """The shell command used to run each PackagerEntry's `update` and `clean` fields."""
    log_level: int = Field(default=0, ge=0, lt=3)
    """The log level to use, as if you passed `--verbose` that many times [0-2]."""
    entries: list[PackagerEntry]

    @field_validator("shell")
    @classmethod
    def validate_executable(cls, cmd: list[str]) -> list[str]:
        if len(cmd) < 1:
            raise ValueError("`shell` cannot be empty.")
        elif not shutil.which(cmd[0]):
            raise ValueError(
                f"Command '{cmd[0]}' is not a valid or accessible executable."
            )
        return cmd


def read_config(config_file: Path) -> UpdAllConfig:
    if not config_file.exists():
        logger.error(f"Config file does not exist or is inaccessible: {config_file!s}")
        raise OSError("File not found")

    try:
        with open(config_file, "r") as file:
            raw_yaml_data = yaml.safe_load(file)  # pyright: ignore[reportAny]

        if raw_yaml_data is None:
            raise ValueError("Config file was empty.")
        logger.debug(f"{raw_yaml_data = }")
        return UpdAllConfig(**raw_yaml_data)  # pyright: ignore[reportAny]
    except yaml.YAMLError, TypeError:
        logger.error("Failed to parse config file.")
        raise
    except ValueError:
        logger.error("Failed to validate config file.")
        raise
    except OSError:
        logger.error(f"Failed to read config file: {config_file!s}")
        raise


def resolve_when_conditions(*when_conditions: WhenCondition) -> bool:
    if when_conditions:
        return any(resolve_when_condition(cond) for cond in when_conditions)
    else:
        return True


def resolve_when_condition(cond: WhenCondition) -> bool:
    valid_os_strings = [s.casefold() for s in (platform.system(), sys.platform)]

    if cond.is_not is not None and resolve_when_condition(cond.is_not):
        logger.debug("`is_not` inner condition resolved True")
        return False
    if cond.has_exe is not None and not shutil.which(cond.has_exe):
        logger.debug("`has_exe` condition resolved False")
        return False
    if cond.is_os is not None and cond.is_os.casefold() not in valid_os_strings:
        logger.debug("`is_os` condition resolved False")
        return False
    if cond.env_equals is not None and not all(
        os.environ.get(key) == value for key, value in cond.env_equals.items()
    ):
        logger.debug("`env_equals` condition resolved False")
        return False

    return True
