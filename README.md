# banip

<img
src="https://drive.google.com/uc?export=view&id=1H04KVAA3ohH_dLXIrC0bXuJXDn3VutKc"
alt = "Dinobox logo" width="120"/>

This tool will create a customized list of IP addresses that are
cross-referenced between two sources:

1. A global (worldwide) list of identified blacklisted IPs.
2. A list of the IP subnets associated with each country.

The result is a customized blacklist of IP addresses based on
countries that you select.

## Why not just use the source list of all blacklisted IPs?

You could, but where's the fun in that?

You may want to create a list of bad actors for specific countries. The
global list contains several hundred thousand entries, and you may need
more targeted list for testing or deployment in production.

For example, I've configured my HAProxy server to drop IP connections
from all countries except those that I've whitelisted. I also want the
ability to create a customized IP list to block any bad actors from
those whitelisted countries. This tool accomplishes that.

## Requirements

### Operating System

banip runs in Unit-like OSes (including macOS). Either a Linux PC, Linux
Virtual Machine, or [Windows Subsystem for Linux (WSL)][def7] is
required.

### Maxmind Database

You'll need a copy of the [Maxmind](https://www.maxmind.com/en/home)
GeoLite2 database for country-level geotagging of IP addresses. If you
have a premium or corporate Maxmind account, you're all set. If not, the
free GeoLite2 account ([signup
here](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data))
will work just fine. The file you want to download is the
`GeoLite2-Country-CSV_YYYYMMDD.zip` file.

### poetry

banip requires [poetry][def2] for dependency management. Poetry is well
behaved and if you're a Python developer you should check it out. It
installs itself in a virtual environment, uninstalls cleanly and easily,
and doesn't require `sudo` for installation. Visit the [poetry
site][def2] and install it using your preferred method, with the
instructions for your operating system.

### gitignore (optional)

If you want to fork and develop this repo, I've included a file called
`global-gitignore.txt` which is a copy of the `.gitignore` I placed in
my home directory and configured globally for all my development
projects. The `global-gitignore.txt` file reflects my development setup
(for example using tools like vscode), but yours may be different. Just
cherrypick any necessary elements from `global-gitignore.txt` for your
own use.

*Details on gitignore files are available on [GitHub][def3].*

### List of blacklisted IPs

Download the list as follows:

```shell
curl -sL https://raw.githubusercontent.com/stamparm/ipsum/master/ipsum.txt > ipsum.txt
```

### make

You'll need the [make][def6] utility installed (*it probably
already is*).

## Setup

### Unpack GeoLite2 data

Unpack the `GeoLite2-Country-CSV_YYYYMMDD.zip` file and save the files
to a location you can easily get to.

### Clone the repository

Clone this repository. We'll assume you clone it your home directory
(`~`):

```shell
git clone https://github.com/geozeke/banip.git
```

Change to `~/banip` and run this command:

```shell
make setup
```

### Copy files

#### GeoLite2 Files

```shell
cp <wherever you put them>/* ./data/geolite/
```

#### Blacklisted IPs

```shell
cp <wherever you put it>/ipsum.txt ./data/ipsum.txt
```

#### Target countries

```shell
cp sample-targets.txt ./data/targets.txt
```

Modify `./data/targets.txt` to select your desired target countries. The
comments in the file will guide you.

#### Custom bans

```shell
cp sample-custom_bans.txt ./data/custom_bans.txt
```

These will be specific IP address or subnets (one per line, in
[CIDR][def] format) that you want to block. Some of your custom IPs may
be found when you run the tool, so this file (`custom_bans.txt`) will be
overwritten to remove the duplicates. The contents of the de-duplicated
file will be appended to the list generated when you run the program.

*Note: If you're concerned about keeping your original list of custom
bans, save a copy of it somewhere outside the repository.*

When you're done, the `~/banip/data` directory should look like this:

```text
├── data
│   ├── custom_bans.txt
│   ├── geolite
│   │   ├── COPYRIGHT.txt
│   │   ├── GeoLite2-Country-Blocks-IPv4.csv
│   │   ├── GeoLite2-Country-Blocks-IPv6.csv
│   │   ├── GeoLite2-Country-Locations-de.csv
│   │   ├── GeoLite2-Country-Locations-en.csv
│   │   ├── GeoLite2-Country-Locations-es.csv
│   │   ├── GeoLite2-Country-Locations-fr.csv
│   │   ├── GeoLite2-Country-Locations-ja.csv
│   │   ├── GeoLite2-Country-Locations-pt-BR.csv
│   │   ├── GeoLite2-Country-Locations-ru.csv
│   │   ├── GeoLite2-Country-Locations-zh-CN.csv
│   │   └── LICENSE.txt
│   ├── ipsum.txt
│   └── targets.txt
```

## Running

After copying/tweaking all the required files, start with this command
to learn how to build your custom blacklist:

```shell
poetry run banip -h
```

When you're ready, run banip again using poetry:

```shell
poetry run banip <output_file> [OPTIONS]
```

## Updating

The Maxmind database is updated on Tuesdays and Fridays, and the list of
blacklisted IPs is updated daily. Pull updated copies of both and put
them in `banip/data/geolite` (for the GeoLite2 data) and `banip/data`
(for the `ipsum.txt` file). Run `banip` again to generate an updated
blacklist.

[def]: https://aws.amazon.com/what-is/cidr/#:~:text=CIDR%20notation%20represents%20an%20IP,as%20192.168.1.0%2F22.
[def2]: https://python-poetry.org/
[def3]: https://docs.github.com/en/get-started/getting-started-with-git/ignoring-files
[def6]: https://man7.org/linux/man-pages/man1/make.1p.html
[def7]: https://docs.microsoft.com/en-us/windows/wsl/install
