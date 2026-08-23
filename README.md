# updall

Simple command runner designed to run package managers if they exist on the system.

```shellsession
$ updall --help
Usage: updall [OPTIONS]

  A simple package manager update runner.

Options:
  -h, --help              Show this message and exit.
  -V, --version           Show the version and exit.
  -v, --verbose           Output debug info to stderr. Pass multiple times to
                          show more logging.
  -c, --config-file FILE  Alternate location of the config file.
  -d, --disable ENTRY     Disable an entry (repeatable).
  -n, --dry-run           Only print what updaters would run.
  -C, --clean             Don't update. Only run cleaners.
```

## Installing

You can install `updall` directly from [PyPI](https://pypi.org/project/updall/). It's recommended to install Python scripts using a tool like [`pipx`](https://pipx.pypa.io/stable/) or [`uv`](https://github.com/astral-sh/uv). If either of those commands are installed, simply run this command to add `updall` to your PATH.

```nushell
uv tool install updall  # If you're using `uv`
pipx install updall     # If you're using `pipx`
```

If you'd rather build from source, that's easy too.

```nushell
git clone https://github.com/Mrfiregem/updall.git
cd updall
uv build
```

## Getting started

To start using `updall`, you must first create a config file. You can find the path `updall` expects its config file to be at on your system in the table below, or you can specify your own location by passing the `-c / --config-file` flag when running the command.

| System  | Path to Configuration                              |
| :------ | :------------------------------------------------- |
| Linux   | `~/.config/updall/config.yaml`                     |
| Windows | `C:\Users\<User>\AppData\Local\updall\config.yaml` |
| MacOS   | `~/Library/Application Support/updall/config.yaml` |

You can see the entire config structure and its default values [below](#config-reference), but the only key required to use `updall` is **`entries`**.

This should be a list of `PackagerEntries`, which are objects containing at least `name` and `update` fields. `name` should be a unique string identifier representing the packager the entry works with, and `update` is a command string that'll be called to update packages.

Once you've populated the config file with entries, all you need to do next is run `updall` with no arguments:

```shellsession
$ updall
Running Updaters ...

 :: [   flatpak::update    ] ::
Looking for updates…

Nothing to update.

 :: [   uv-tools::update   ] ::
Nothing to upgrade

 :: [     paru::update     ] ::
[sudo] password for user:
no new news
:: Looking for PKGBUILD upgrades...
:: Looking for AUR upgrades...
:: Looking for devel upgrades...
:: Resolving dependencies...
:: Calculating conflicts...
:: Calculating inner conflicts...
:: packages not in the AUR: worm_hole
:: orphans: pest-language-server
 there is nothing to do
:: Synchronizing package databases...
 cachyos-v3 is up to date
 cachyos-extra-v3 is up to date
 cachyos-core-v3 is up to date
 cachyos is up to date
 core is up to date
 extra is up to date
 multilib is up to date
:: Starting full system upgrade...
 there is nothing to do

 :: [    flatpak::clean    ] ::
Nothing unused to uninstall

 :: [     paru::clean      ] ::
 there is nothing to do
==> no candidate packages found for pruning
```

## Config Reference

```yaml
# The shell used to run each entry's `update` and `clean` scripts.
shell:
  - /bin/sh
  - -c
# The program's default log level, from 0 to 2.
# Same as if passing `--verbose` that many times.
log_level: 0
# A list of PackagerEntries.
entries: []
```

### PackagerEntry

```yaml
# The entry's identifier used for headers.
name: "<unique string>"
# The command run by the shell to update packages.
update: "<some shell command>"
# An optional separate command to run after all `update` scripts.
clean: null
# A list of WhenConditions that determine if the entry's commands are run.
# The entry is run when *ANY* condition is true, and a single entry is
# true when *ALL* of its keys are true.
when: []
```

### WhenCondition

A when condition is an object that can define various kinds of checks to determine if the entry it's tied to can be run.
When all fields of a when condition are true, the entire when condition object resolves to true. If a field fails, the entire when condition also fails.

If an entry defines multiple when condition objects, that entry gets run when any condition object resolves to true, even if others fail.

```yaml
# Check if the user has a specific command on the PATH.
# A `str` matching some executable name or full path.
has_exe: null # e.g. "flatpak"

# Check if the user is running on a certain operating system.
# A `str` matching the value of `sys.platform` or `platform.system()` output
is_os: null # e.g. "windows", "darwin", "win32", "linux"

# Checks if all key variables exist and that their values match those defined.
# A `dict` of keys representing environment variable names, and values.
env_equals: null # e.g. {"FOO": "bar"} is true if `$FOO` is exported with value "bar"

# Checks if a when condition is *not* true
is_not: null # e.g. {"has_exe": "/some/fake/command"}
```

## Example Config

This is the config used to run the command from the first code block.

```yaml
entries:
  - name: flatpak
    update: flatpak update
    clean: flatpak uninstall --delete-data --unused
    when:
      - has_exe: flatpak
        is_os: Linux

  - name: uv-tools
    update: uv tool upgrade --all
    when:
      - has_exe: uv

  - name: scoop
    update: scoop update --all
    when:
      - has_exe: scoop
        is_os: Windows

  - name: paru
    update: paru
    clean: |-
      paru -c
      command -v paccache >/dev/null && paccache -r
    when:
      - has_exe: paru
        is_os: Linux

  - name: pacman
    update: sudo pacman -Syu
    when:
      - is_os: Linux
        is_not:
          has_exe: paru
```
