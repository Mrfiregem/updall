import logging
import shlex
import subprocess

from updall.config import PackagerEntry, resolve_when_conditions

logger = logging.getLogger(__name__)


def run_command(shell: list[str], command: str) -> None:
    with subprocess.Popen(shell + [command]) as process:
        logger.info(f"Running command: {process.args}")

        returncode = process.wait()
        if returncode != 0:
            logger.warning("%s returned non-zero exit code.", shell + [command])
            raise subprocess.CalledProcessError(returncode, cmd=process.args)


# `clean` implies `dry_run` but not the other way around.
def run_updaters(
    shell: list[str],
    *entries: PackagerEntry,
    disabled: list[str],
    dry_run: bool,
    clean: bool,
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
            if not clean:
                print(f"\n :: [ {entry.name + '::update':^20} ] ::")
            if entry.clean is not None:
                clean_cmds += [(entry.name, entry.clean)]
            while True:
                try:
                    if dry_run and not clean:
                        print(f"Would run: << {shlex.join(shell + [entry.update])} >>")
                    elif not dry_run:
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
