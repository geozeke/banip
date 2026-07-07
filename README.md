# <a id="top"></a> banip

<img
src="https://raw.githubusercontent.com/geozeke/banip/main/assets/banip-logo.png"
alt = "Dinobox logo" width="120"/>

_banip_ creates a customized list of IP addresses by cross-referencing
two data sources:

1. [ipsum][ipsum] threat-intelligence data for globally identified
   blacklisted IP addresses.
2. Country-specific IP subnet data from MaxMind GeoLite2.

The result is a targeted IP blacklist for the countries you select.

## Why not just use the source list of all blacklisted IPs?

You could, but where's the fun in that?

The global list contains several hundred thousand entries. For testing
or production use, a smaller country-specific list may be easier to
review, deploy, and maintain.

For example, you may configure HAProxy to drop connections from all
countries except those you explicitly allow, while still blocking known
malicious IP addresses from the allowed countries. _banip_ supports that
workflow by building a focused blacklist from the source data.

## Contents

* [Requirements](#requirements)
* [Setup](#setup)
* [Running](#running)
* [Updating](#updating)
* [Plugins](#plugins)
* [Development](#development)
* [Upgrading](#upgrade)
* [Uninstalling](#uninstall)

## <a id="requirements"></a> Requirements

### Operating System

_banip_ runs on Unix-like operating systems. macOS, Linux, a Linux
virtual machine, or [Windows Subsystem for Linux (WSL)][wsl] is
required.

### MaxMind Database

You need a copy of the [MaxMind][mmh] GeoLite2 database for
country-level IP geolocation. A premium or corporate MaxMind account
works, and the free GeoLite2 account is also sufficient ([sign up
here][mmgeo]).

After logging in, use the menu in the upper right and select:

```text
My Account > My Account
```

Then click `Download Files` in the lower left. Download this file:

```text
GeoLite2 Country: CSV format
```

### uv

_banip_ uses [uv][astral] for installation and dependency management.
Install `uv` from the [uv documentation][astral] for your operating
system.

### gitignore (optional)

If you want to fork and develop this repository,
`global-gitignore.txt` contains a copy of the `.gitignore` file used in
the author's global Git configuration. It reflects one development
environment, including tools such as VS Code, but yours may be
different.

Use any relevant entries from `global-gitignore.txt` in your own global
Git ignore configuration. Do not modify the repository's `.gitignore`
for personal editor or operating-system files.

_Details about gitignore files are available on [GitHub][git-ignore]._

### Global List of Blacklisted IPs

_banip_ uses the [ipsum][ipsum] threat-intelligence blacklist. Download
it directly with:

```text
curl -sL https://raw.githubusercontent.com/stamparm/ipsum/master/ipsum.txt > ipsum.txt
```

[top](#top)

## <a id="setup"></a> Setup

### Unpack GeoLite2 data

Unpack the GeoLite2-Country zip archive and save the files somewhere
easy to access.

_Note: For a quick way to download MaxMind data with `curl` and a direct
download permalink, [see the MaxMind documentation][mmd]._

### Install banip

```shell
uv tool install --from git+https://github.com/geozeke/banip.git@latest banip
```

### Create Required Directories

Create the required local directories:

```text
mkdir -p ~/.banip/geolite ~/.banip/plugins/code ~/.banip/plugins/parsers
```

### Copy Files

#### GeoLite2 Files

```text
cp <wherever you put them>/* ~/.banip/geolite/
```

#### ipsum Data

```text
cp <wherever you put it>/ipsum.txt ~/.banip/ipsum.txt
```

#### Targets

The global blacklist is large. When _banip_ builds a custom blacklist,
it limits the output to the countries listed in your targets file.

```text
cp ./samples/targets.txt ~/.banip/targets.txt
```

See the header in `~/.banip/targets.txt` for instructions on selecting
target countries.

#### Custom Whitelist (Optional)

```text
cp ./samples/custom_whitelist.txt ~/.banip/custom_whitelist.txt
```

Some IP addresses may be flagged as malicious even though you still want
to allow them, such as addresses used for testing. Add those addresses
to this file, one per line. If the file does not exist, _banip_ creates
a blank one when it runs.

#### Custom Blacklist (Optional)

```text
cp ./samples/custom_blacklist.txt ~/.banip/custom_blacklist.txt
```

The ipsum database may not include every address you want to block. It
also contains only IP addresses, while you may want to block an entire
subnet.

The custom blacklist accepts IP addresses or subnets in [CIDR][cidr]
format, one per line. Some custom blacklist entries may already appear
in the generated output. When that happens, _banip_ overwrites
`custom_blacklist.txt` to remove duplicates, then appends the remaining
custom entries to the generated blacklist. Like the whitelist, this file
is optional. If it does not exist, _banip_ creates a blank one when it
runs.

_Note: If you want to preserve the original custom blacklist exactly as
written, save a copy outside `~/.banip`._

When setup is complete, the `~/.banip` directory should look like this:

```text
.banip
├── custom_blacklist.txt (optional)
├── custom_whitelist.txt (optional)
├── geolite (required)
│   ├── COPYRIGHT.txt
│   ├── GeoLite2-Country-Blocks-IPv4.csv (required)
│   ├── GeoLite2-Country-Blocks-IPv6.csv (required)
│   ├── GeoLite2-Country-Locations-de.csv (required)
│   ├── GeoLite2-Country-Locations-en.csv (required)
│   ├── GeoLite2-Country-Locations-es.csv (required)
│   ├── GeoLite2-Country-Locations-fr.csv (required)
│   ├── GeoLite2-Country-Locations-ja.csv (required)
│   ├── GeoLite2-Country-Locations-pt-BR.csv (required)
│   ├── GeoLite2-Country-Locations-ru.csv (required)
│   ├── GeoLite2-Country-Locations-zh-CN.csv (required)
│   └── LICENSE.txt (required)
├── ipsum.txt (required)
├── plugins (required)
│   ├── code (required)
│   └── parsers (required)
└── targets.txt (required)
```

[top](#top)

## <a id="running"></a> Running

After copying and configuring the required files, run this command to
see how to build a custom blacklist:

```text
banip -h
```

[top](#top)

## <a id="updating"></a> Updating

MaxMind updates the GeoLite2 Country database on Tuesdays and Fridays,
and `ipsum.txt` is updated daily. Download updated copies of both files
and place them in `~/.banip/geolite` for GeoLite2 data and
`~/.banip/ipsum.txt` for the ipsum data. Run _banip_ again to generate
an updated blacklist.

Automating this process with cron or systemd helps keep your lists
current.

[top](#top)

## <a id="plugins"></a> Plugins

_banip_ generates build products that may be useful for other workflows.
For example, each time it builds a blacklist, _banip_ also creates a
text file of worldwide subnets tagged with two-letter country codes.
The file is saved here:

```text
~/.banip/haproxy_geo_ip.txt
```

After running _banip_, open that file to review the generated data. If
you have a specific use case for that data, you can write a plugin that
uses _banip_ build products.

A _banip_ plugin consists of two required files:

1. Code that creates an argument parser for the new command.
2. Code that implements the new command's functionality.

Place plugins in the appropriate subdirectory under
`~/.banip/plugins`: either `parsers` or `code`. See the comments in
these sample files for plugin implementation details:

```text
./samples/plugins/foo.py
./samples/plugins/foo_args.py
```

[top](#top)

## <a id="development"></a> Development

Use `just` for common maintainer tasks:

```text
just setup
just lint
just typecheck
just test
```

Release preparation uses `just bump <version>` to update project
metadata and the changelog. After committing the release changes, use
`just tag-release` to push the `vX.Y.Z` tag, or
`just tag-release-latest` to also update the mutable `latest` tag.

[top](#top)

## <a id="upgrade"></a> Upgrading banip

To upgrade _banip_, run:

```text
uv tool upgrade banip
```

[top](#top)

## <a id="uninstall"></a> Uninstalling banip

To uninstall _banip_ and remove its local data directory, run:

```text
uv tool uninstall banip
rm -rf ~/.banip
```

[top](#top)

<!--------------------------------------------------------------------->

[astral]: https://docs.astral.sh/uv/
[cidr]: https://aws.amazon.com/what-is/cidr/#:~:text=CIDR%20notation%20represents%20an%20IP,as%20192.168.1.0%2F22.
[git-ignore]: https://docs.github.com/en/get-started/getting-started-with-git/ignoring-files
[ipsum]: https://github.com/stamparm/ipsum
[mmd]: https://dev.maxmind.com/geoip/updating-databases#directly-downloading-databases
[mmgeo]: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
[mmh]: https://www.maxmind.com/en/home
[wsl]: https://docs.microsoft.com/en-us/windows/wsl/install
