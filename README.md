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
  -c, --config-file FILE  Alternate location of the config file.  [default:
                          /home/user/.config/updall/config.yaml]
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

Create a config file. You can find the path `updall` expects to find this file by calling `updall --help`, or you can specify your own location by passing the `-c / --config-file` flag when running the command.

You can see the entire config structure and its default values below, but the only key you need to use `updall` is `entries`. This should be a list of `PackagerEntries`, which are objects containing at least `name` and `update` fields. `name` should be a unique string identifier representing the packager the entry works with, and `update` is a command string that'll be called to update packages.

Once you've populated the config file with entries, all you need to do next is run `updall` with no arguments:

```shellsession
$ updall
Running Updaters ...

 :: [   flatpak::update    ] ::
Looking for updates…


        ID                                                Branch                 Op            Remote             Download
 1. [✓] org.freedesktop.Platform.GL.default               25.08                  u             flathub             69.7 MB / 146.0 MB
 2. [✓] org.freedesktop.Platform.GL.default               25.08-extra            u             flathub              3.6 MB / 146.1 MB
 3. [✓] org.freedesktop.Platform.Locale                   25.08                  u             flathub             18.5 kB / 379.4 MB
 4. [✓] org.freedesktop.Platform.codecs-extra             25.08-extra            u             flathub            698.8 kB / 14.6 MB
 5. [✓] org.freedesktop.Sdk.Locale                        25.08                  u             flathub             18.5 kB / 395.2 MB
 6. [✓] org.freedesktop.Sdk                               25.08                  u             flathub             29.3 MB / 606.7 MB
 7. [✓] org.freedesktop.Platform                          25.08                  u             flathub              3.4 MB / 257.1 MB

Updates complete.

 :: [    pacman::update    ] ::
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

 :: [    pacman::clean     ] ::
 there is nothing to do
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

```yaml
# Check if the user has a specific command on the PATH.
has_exe: "<some command on PATH>"
# Check if the user is running on a certain operating system.
is_os: Windows # or 'Darwin' or 'Linux'
# A dict of keys representing environment variable names, and values.
# Checks if all key variables exist and that their values match those defined.
env_equals: {}
```

## Example Config

```yaml
entries:
  - name: flatpak
    update: flatpak update
    clean: flatpak uninstall --delete-data --unused
    when:
      - has_exe: flatpak
        is_os: Linux
  - name: scoop
    update: scoop update --all
    when:
      - has_exe: scoop
        is_os: Windows
  - name: pacman
    update: paru
    clean: paru -c
    when:
      - has_exe: paru
        is_os: Linux
```
