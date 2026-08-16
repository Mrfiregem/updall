import logging
import subprocess
import sys
from pathlib import Path

import click
from platformdirs import user_config_path

from updall.config import UpdAllConfig, read_config, resolve_when_conditions


def get_app_name() -> str:
    """Get the name of the program (usually "updall")."""
    return __package__ or "<unknown>" if __name__ == "__main__" else __name__


# Create a new logger instance
logger = logging.getLogger(__name__)


def get_default_config_file() -> Path:
    """Return the path to the config file `updall` checks if the user doesn't provide their own."""
    name = get_app_name()
    return user_config_path(name) / "config.yaml"


def get_log_level(verbosity: int) -> int:
    """Set log level based on the count of verbosity flags provided by click."""
    match verbosity:
        case 0:
            return logging.WARNING
        case 1:
            return logging.INFO
        case _:
            return logging.DEBUG


def run_command(config: UpdAllConfig, command: str):
    with subprocess.Popen(config.shell + [command]) as process:
        logger.info(f"Running command: {process.args}")

        returncode = process.wait()
        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, cmd=process.args)


@click.command()
@click.help_option("-h", "--help")
@click.version_option(None, "-V", "--version")
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Output debug info to stderr. Pass multiple times to show more logging.",
)
@click.option(
    "-c",
    "--config-file",
    show_default=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Alternate location of the config file.",
)
def main(config_file: Path, verbose: int) -> None:
    """A simple package manager update runner."""
    # Setup logging using verbosity flag
    logging.basicConfig(
        level=get_log_level(verbose), format="%(levelname)s: %(message)s"
    )

    # Set config file to user's file if click verifies it exists as a readable file
    user_config_path = config_file or get_default_config_file()
    logger.info(f"Using config file: {user_config_path!s}")

    # Read user config to value
    try:
        user_config = read_config(user_config_path)
    except Exception as e:  # noqa: BLE001
        logger.error(e)
        sys.exit(1)
    logger.debug(f"{user_config = }")

    # Main functionality
    # 1. Loop over all entries
    # 2. Determine if they should run by checking all WhenConditions and store in `should_run`
    # 3. Store entry.clean in list for later if it needs run
    # 4. If should_run is true, run each entry.update command
    clean_cmds: list[tuple[str, str]] = []

    print("Running Updaters ...")

    for entry in user_config.entries:
        should_run = resolve_when_conditions(*entry.when)
        if should_run:
            if entry.clean is not None:
                clean_cmds += [(entry.name, entry.clean)]
            print(f"\n :: [ {entry.name + '::update':^20} ] ::")
            run_command(user_config, entry.update)

    for entry_name, cmd in clean_cmds:
        print(f"\n :: [ {entry_name + '::clean':^20} ] ::")
        try:
            run_command(user_config, cmd)
        except subprocess.CalledProcessError:
            logger.warning(f"The `clean` script for {entry_name} failed. Continuing...")
            continue
