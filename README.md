# <a id="top"></a> banip

<img
src="https://lh3.googleusercontent.com/d/1H04KVAA3ohH_dLXIrC0bXuJXDn3VutKc"
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

## Contents

* [Requirements](#requirements)
* [Setup](#setup)
* [Running](#running)
* [Updating](#updating)
* [Plugins](#plugins)
* [Uninstalling](#uninstall)

## <a id="requirements"></a> Requirements

### Operating System

banip runs in Unix-like OSes. Either macOS, a Linux PC, Linux Virtual
Machine, or [Windows Subsystem for Linux (WSL)][def7] is required.

### MaxMind Database

You'll need a copy of the [MaxMind][def8] GeoLite2 database for
country-level geotagging of IP addresses. If you have a premium or
corporate MaxMind account, you're all set. If not, the free GeoLite2
account will work just fine ([sign up here][def5]). Once you login,
using the menu on the top right select:

```text
My Account > My Account
```

From there, click on `Download Files` on the bottom left. The file you
want to download is:

```text
GeoLite2 Country: CSV format
```

### uv

banip requires [uv][def2] for dependency management. uv is well behaved
and extremely fast. If you're a Python developer you should check it
out. Visit the [uv site][def2] and install it using your preferred
method, with the instructions for your operating system.

### gitignore (optional)

If you want to fork and develop this repo, I've included a file called
`global-gitignore.txt` which is a copy of the `.gitignore` I placed in
my home directory and configured globally for all my development
projects. The `global-gitignore.txt` file reflects my development setup
(for example using tools like vscode), but yours may be different. Just
cherrypick any necessary elements from `global-gitignore.txt` for your
own use.

*Details on gitignore files are available on [GitHub][def3].*

### Global List of Blacklisted IPs

banip uses the [ipsum][def9] threat intelligence blacklist. You can
direct download it using:

```shell
curl -sL https://raw.githubusercontent.com/stamparm/ipsum/master/ipsum.txt > ipsum.txt
```

### make

You'll need the [make][def6] utility installed (*it probably
already is*).

[top](#top)

## <a id="setup"></a> Setup

### Unpack GeoLite2 data

Unpack the GeoLite2-Country zip archive and save the files to a location
you can easily get to.

*Note: if you're looking for a quick way to download the MaxMind data
using `curl` and a direct download permalink, [SEE HERE][def4].*

### Clone the Repository

Clone this repository. We'll assume you clone it to your home directory
(`~`):

```shell
git clone https://github.com/geozeke/banip.git
```

Change to `~/banip` and run this command:

```shell
make setup
```

### Copy Files

#### GeoLite2 Files

```shell
cp <wherever you put them>/* ./data/geolite/
```

#### Blacklisted IPs

```shell
cp <wherever you put it>/ipsum.txt ./data/ipsum.txt
```

#### Target Countries

```shell
cp ./samples/targets.txt ./data/targets.txt
```

Modify `./data/targets.txt` to select your desired target countries. The
comments in the file will guide you.

#### Custom Whitelist (Optional)

```shell
cp ./samples/custom_whitelist.txt ./data/custom_whitelist.txt
```

There may be IP addresses that banip will flag as malicious, but you
still want to whitelist them (for example to use for testing). This file
will contain specific IP addresses, one per line, that you want to
allow.

This file is optional. If you choose not to use it, banip will create a
blank one when you run it.

#### Custom Blacklist (Optional)

```shell
cp ./samples/custom_blacklist.txt ./data/custom_blacklist.txt
```

The source database of banned IPs isn't perfect. You may determine that
there's an IP address you want to ban this is not found in `ipsum.txt`.
Also, the `ipsum.txt` file only contains IP addresses, and you may want
to ban an entire subnet. The custom blacklist allows you to capture
specific IP addresses or subnets (in [CIDR][def] format), one per line,
that you want to block. Some of your custom blacklist IPs may be found
when you run the banip, so this file (`custom_blacklist.txt`) will be
overwritten to remove the duplicates. The contents of the de-duplicated
file will then be appended to the list generated when you run the
program.

This file is optional. If you choose not to use it, banip will create a
blank one when you run it.

*Note: If you're concerned about keeping your original list of custom
blacklisted IPs, save a copy of it somewhere outside the repository.*

When you're done, the `~/banip/data` directory should look like this:

```text
data
├── custom_blacklist.txt (optional)
├── custom_whitelist.txt (optional)
├── geolite (required)
│   ├── COPYRIGHT.txt
│   ├── GeoLite2-Country-Blocks-IPv4.csv
│   ├── GeoLite2-Country-Blocks-IPv6.csv
│   ├── GeoLite2-Country-Locations-de.csv
│   ├── GeoLite2-Country-Locations-en.csv
│   ├── GeoLite2-Country-Locations-es.csv
│   ├── GeoLite2-Country-Locations-fr.csv
│   ├── GeoLite2-Country-Locations-ja.csv
│   ├── GeoLite2-Country-Locations-pt-BR.csv
│   ├── GeoLite2-Country-Locations-ru.csv
│   ├── GeoLite2-Country-Locations-zh-CN.csv
│   └── LICENSE.txt
├── ipsum.txt (required)
└── targets.txt (required)
```

[top](#top)

## <a id="running"></a> Running

After copying/tweaking all the required files, start by activating the
python virtual environment:

```shell
source .venv/bin/activate
```

Now run this command to learn how to build your custom blacklist:

```shell
banip -h
```

[top](#top)

## <a id="updating"></a> Updating

MaxMind updates the GeoLite2 Country database on Tuesdays and Fridays,
and the list of blacklisted IPs (`ipsum.txt`) is updated daily. Pull
updated copies of both and put them in `banip/data/geolite` (for the
GeoLite2 data) and `banip/data` (for the `ipsum.txt` file). Run `banip`
again to generate an updated blacklist.

[top](#top)

## <a id="plugins"></a> Plugins

banip generates some data that you may want to use for other purposes.
For example, everytime you build a new blacklist banip also creates and
saves a textfile of all worldwide subnets, each tagged with a two-letter
country code. The file is saved in:

```'text
./banip/data/haproxy_geo_ip.txt
```

Next time you run banip, open that file and take a look at it. Since you
may have a very specific usecase for that data, you can write a plugin
for banip which will make use of the build products for your purposes.

A banip plugin consists of two required files:

1. Code that generates an argument parser for your new command.
2. Code that implements the functionality of your new command.

All your plugins go into the `./src/plugins` directory in the
appropriate subdirectory (either `parsers` or `code`). Your
plugins are not under version control, so they will only reside on your
machine.

Look at the comments in these two files for instructions on how to
create your own plugins:

```text
./samples/plugins/foo.py
./samples/plugins/foo_args.py
```

[top](#top)

## <a id="uninstall"></a> Uninstalling banip

If you want out, just do this:

```shell
rm -rf ~/.banip
```

[top](#top)

[def]: https://aws.amazon.com/what-is/cidr/#:~:text=CIDR%20notation%20represents%20an%20IP,as%20192.168.1.0%2F22.
[def2]: https://docs.astral.sh/uv/
[def3]: https://docs.github.com/en/get-started/getting-started-with-git/ignoring-files
[def4]: https://dev.maxmind.com/geoip/updating-databases#directly-downloading-databases
[def5]: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
[def6]: https://man7.org/linux/man-pages/man1/make.1p.html
[def7]: https://docs.microsoft.com/en-us/windows/wsl/install
[def8]: https://www.maxmind.com/en/home
[def9]: https://github.com/stamparm/ipsum
