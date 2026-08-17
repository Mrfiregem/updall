import logging
import shlex
import subprocess
import sys
from pathlib import Path

import click
from platformdirs import user_config_path

from updall.config import (
    PackagerEntry,
    read_config,
    resolve_when_conditions,
)


def get_app_name() -> str:
    """Get the name of the program (usually "updall")."""
    return __package__ or "<unknown>" if __name__ == "__main__" else __name__


# Create a new logger instance
logger = logging.getLogger(__name__)


def get_default_config_file() -> Path:
    """Return the path to the config file `updall` checks if the user doesn't provide their own."""
    name = get_app_name()
    return user_config_path(name, False) / "config.yaml"


def get_log_level(verbosity: int) -> int:
    """Set log level based on the count of verbosity flags provided by click."""
    match verbosity:
        case 0:
            return logging.WARNING
        case 1:
            return logging.INFO
        case _:
            return logging.DEBUG


def run_command(shell: list[str], command: str) -> None:
    with subprocess.Popen(shell + [command]) as process:
        logger.info(f"Running command: {process.args}")

        returncode = process.wait()
        if returncode != 0:
            logger.warning("%s returned non-zero exit code.", shell + [command])
            raise subprocess.CalledProcessError(returncode, cmd=process.args)


def run_updaters(
    shell: list[str],
    *entries: PackagerEntry,
    disabled: list[str],
    dry_run: bool = False,
) -> list[tuple[str, str]]:
    """Loop over entries, run their updaters, and return a list of tuples of their names and cleaner scripts.

    1. Loop over all entries
    2. Determine if updater should run by checking all WhenConditions
    3. Store (entry.name, entry.clean) in result for later if it should run
    4. If it should, run the entry.update script"""
    clean_cmds: list[tuple[str, str]] = []
    logger.debug("Starting updater loop...")

    for entry in entries:
        logger.debug("Checking entry: %s", entry.name)
        should_run = entry.name not in disabled and resolve_when_conditions(*entry.when)
        logger.debug(f"{should_run = }")
        if should_run:
            print(f"\n :: [ {entry.name + '::update':^20} ] ::")
            if entry.clean is not None:
                clean_cmds += [(entry.name, entry.clean)]
            while True:
                try:
                    if dry_run:
                        print(f"Would run: << {shlex.join(shell + [entry.update])} >>")
                    else:
                        run_command(shell, entry.update)
                except subprocess.CalledProcessError:
                    # If command exited with non-zero exit code, or failed,
                    # ask user if they want to skip to the next updater or try again.
                    answer = input(
                        f"Running update script for {entry.name} failed. Try again? [y/N]: "
                    )
                    if answer.casefold().startswith("y"):
                        continue
                    else:
                        break
                else:
                    break
    return clean_cmds


def run_cleaners(
    shell: list[str], *cleaner_entries: tuple[str, str], dry_run: bool = False
) -> None:
    """Loop over tuples of entry names and cleaner scripts, and run them.

    Their when conditions should already be checked by `run_updaters`, so no need to recheck.
    Cleaner script errors don't illicit a repeat prompt, so they're just logged and skipped over."""
    for entry_name, cmd in cleaner_entries:
        print(f"\n :: [ {entry_name + '::clean':^20} ] ::")
        try:
            if dry_run:
                print(f"Would run: << {shlex.join(shell + [cmd])} >>")
            else:
                run_command(shell, cmd)
        except subprocess.CalledProcessError:
            # For cleaners, we don't prompt to retry, we just go to the next one.
            logger.warning(f"The `clean` script for {entry_name} failed. Continuing...")
            continue


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
def main(config_file: Path, verbose: int, disable: list[str], dry_run: bool) -> None:
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

    # Loop over updaters
    print("Running Updaters ...")
    clean_cmds = run_updaters(
        user_config.shell, *user_config.entries, disabled=disable, dry_run=dry_run
    )

    # Loop over cleaners
    run_cleaners(user_config.shell, *clean_cmds, dry_run=dry_run)
