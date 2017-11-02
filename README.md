# Parameter Manager [![Build status](https://ci.appveyor.com/api/projects/status/jgv6i25s9b4g94ga?svg=true)](https://ci.appveyor.com/project/KyleAltendorf/pm)

![Parameter Manager screenshot](/screenshot.png?raw=true)

## Running From Binary

### Windows

- Download artifact from the [build history on AppVeyor](https://ci.appveyor.com/project/KyleAltendorf/pm/history)
- Extract contents of the `.zip` file
- Run `epcpm.exe`

A sample project is available in `epcpm/tests/`

## Running From Source

Instructions are for Python 3.6 but they should work with slight tweaks with 3.5.

### Windows

- Install [Python 3.6](https://www.python.org/downloads/)
- Install [Git](https://git-scm.com/download)
- `git clone https://github.com/altendky/pm`
- `cd pm`
- `copy .gitmodules.github .gitmodules`
- `git submodule update --init`
- `py -3.6 venv.py`
- wait
- wait some more...
- ...
- Ignore the links provided.  They leaked over from another application.
- Run `venv\Scripts\epcpm`.

A sample project is available in `src/epcpm/test/`

### Linux

This procedure will install `virtualenv` and `tox` using `pip --user`.
Expecting the user to handle properly installing these would be better but is not how it works presently.

- Install Python 3.6
  - The [deadsnakes PPA](https://launchpad.net/~fkrull/+archive/ubuntu/deadsnakes/+index?batch=75&memo=75&start=75) has it for Ubuntu Xenial and Trusty
  - Also consider [pyenv](https://github.com/pyenv/pyenv)
- Install git
- `git clone https://github.com/altendky/pm`
- `cd pm`
- `cp .gitmodules.github .gitmodules`
- `git submodule update --init`
- `python3.6 venv.py`
- wait
- a bit more, but not nearly as much as Windows
- Run `venv/bin/epcpm`

A sample project is available in `src/epcpm/tests/`
