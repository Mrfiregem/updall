import logging
import sys
from pathlib import Path
from typing import Literal

import click
from platformdirs import user_config_path
from rich.console import Console
from rich.logging import RichHandler

from updall.config import read_config
from updall.run import run_cleaners, run_updaters

# Create a new logger instance
logger = logging.getLogger(__name__)


def get_default_config_file() -> Path:
    """Return the path to the config file `updall` checks if the user doesn't provide their own."""
    return user_config_path("updall", False) / "config.yaml"


def get_log_level(verbosity: int) -> int:
    """Set log level based on the count of verbosity flags provided by click."""
    match verbosity:
        case 0:
            return logging.WARNING
        case 1:
            return logging.INFO
        case _:
            return logging.DEBUG


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
@click.option(
    "-d",
    "--disable",
    multiple=True,
    metavar="ENTRY",
    help="Disable an entry (repeatable).",
)
@click.option(
    "-n", "--dry-run", is_flag=True, help="Only print what updaters would run."
)
@click.option("-C", "--clean", is_flag=True, help="Don't update. Only run cleaners.")
@click.option(
    "--color",
    metavar="WHEN",
    type=click.Choice(["always", "auto", "never"]),
    default="auto",
    help="When to show colored output. Does not apply to updaters or cleaners.",
)
def main(
    config_file: Path,
    verbose: int,
    disable: list[str],
    dry_run: bool,
    clean: bool,
    color: Literal["always", "auto", "never"],
) -> None:
    """A simple package manager update runner."""
    # Setup colored terminal output
    console = Console(no_color=None if color == "auto" else color == "never")

    # Setup logging using verbosity flag
    logging.basicConfig(
        level=get_log_level(verbose),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
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

    # Loop over updaters
    if not clean:
        print("Running Updaters ...")
    clean_cmds = run_updaters(
        user_config.shell,
        *user_config.entries,
        disabled=disable,
        dry_run=dry_run or clean,
        clean=clean,
        console=console,
    )

    # Loop over cleaners
    run_cleaners(user_config.shell, *clean_cmds, dry_run=dry_run, console=console)
