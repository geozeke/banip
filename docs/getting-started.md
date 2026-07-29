# Getting started

## Requirements

banip runs on macOS, Linux, and Windows Subsystem for Linux and requires
Python 3.12 or newer. The recommended installer,
[uv](https://docs.astral.sh/uv/), can download and manage a compatible
Python version automatically. The pipx and pip installation methods
require a compatible Python installation.

Installing and running banip does not require uv. It is required only
for banip development.

After installation, downloading GeoLite2 Country CSV data requires a
free or paid MaxMind account. The ipsum feed does not require MaxMind
credentials.

## Install banip

Install banip as an isolated command-line application. This avoids
dependency conflicts with other Python applications and protects
operating-system-managed Python environments. Do not install banip
globally into the system Python environment.

### uv (recommended)

uv installs banip in an isolated environment and supplies a managed
Python version:

```console
uv tool install --managed-python banip
```

Upgrade an existing installation with:

```console
uv tool upgrade banip
```

If uv reports that its executable directory is not on `PATH`, run
`uv tool update-shell` and open a new terminal.

See the
[uv tool documentation](https://docs.astral.sh/uv/concepts/tools/) for
installation and environment-management details.

### pipx

[pipx](https://pipx.pypa.io/stable/) also installs command-line
applications into isolated environments. Install pipx, make its
application directory available on `PATH`, and install banip using
Python 3.12 or newer:

```console
pipx ensurepath
pipx install --python 3.12 banip
```

Open a new terminal after `pipx ensurepath` if it changed your shell
configuration. If pipx cannot locate Python 3.12, pass the full path to
a compatible Python executable with `--python`.

Upgrade an existing installation with:

```console
pipx upgrade banip
```

See the
[pipx installation guide](https://pipx.pypa.io/stable/how-to/install-pipx.html)
for platform-specific setup.

### pip in a virtual environment

For manual environment management, create a dedicated virtual
environment with Python 3.12 or newer, activate it, and install banip:

```console
python3.12 -m venv ~/.local/share/banip-venv
source ~/.local/share/banip-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install banip
```

Activate this environment before running or upgrading banip in a new
terminal. Upgrade banip with:

```console
source ~/.local/share/banip-venv/bin/activate
python -m pip install --upgrade banip
```

See the
[Python Packaging User Guide](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/)
for more information about pip and virtual environments.

### Verify the installation

For any installation method, confirm that the command is available:

```console
banip --version
```

## Initialize local data

Create the local directory structure and starter configuration:

```console
banip database init
```

This writes `~/.banip/banip.yaml` and creates the local data
directories. During the banip 2.x compatibility period it also creates
the deprecated plugin directories. If the prior flat configuration
files exist, initialization imports their non-comment entries into the
new YAML configuration without deleting the source files.

## Download source data

Download the ipsum feed:

```console
banip database update ipsum
```

Set MaxMind credentials in the environment or in the dotenv-style file
named by `database.secrets_file` in `banip.yaml`:

```text
MAXMIND_ACCOUNT_ID=123456
MAXMIND_LICENSE_KEY=example
```

Then download the GeoLite2 Country CSV files:

```console
banip database update geolite
```

Run `banip database update` to refresh both sources.

## Build your first blocklist

Review the example restricted and public country policies in
`banip.yaml`, adjust their country codes, then run:

```console
banip build
```

The build writes:

```text
~/.banip/ip_blocklist.txt
~/.banip/ip_allowlist.txt
~/.banip/country_allowlist.txt
~/.banip/country_allowlist_restricted.txt
~/.banip/country_allowlist_public.txt
~/.banip/haproxy_geo_ip.txt
```

Additional named country policies produce corresponding
`country_allowlist_<policy>.txt` files. Use these named products for new
integrations. The unqualified `country_allowlist.txt` product is
deprecated and will be removed in banip 3.0.

See [Configuration](configuration.md) for the available settings and
[Commands](commands.md) for build options. Review
[Deprecations](deprecations.md) before planning a major-version
upgrade.
