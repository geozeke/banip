# banip

<img
src="https://drive.google.com/uc?export=view&id=1H04KVAA3ohH_dLXIrC0bXuJXDn3VutKc"
alt = "Dinobox logo" width="120"/>

This tool will create a customized list of IP addresses that are
cross-referenced between two sources:

1. A global (worldwide) list of identified blacklisted IPs.
2. A list of the IP subnets associated with each country.

The result is a customized list of IP blacklisted addresses based on
countries that you select.

## Why not just use the source list of all blacklisted IPs?

You could, but where's the fun in that?

You may want to create a list of bad actors for specific countries. The
global list contains several hundred thousand entries, and you may need
more targeted list for testing or deployment in production.

For example, using the IP subnets list (#2 above) I've configured my
HAProxy server to drop IP connections from all countries except a few
that I've whitelisted. I also wanted the ability to create a customized
IP list to block any bad actors from those whitelisted countries. This
tool accomplishes that.

## Requirements

### Operating System

banip runs in Linuxes (including macOS). Either a Linux PC, Linux
Virtual Machine, or [Windows Subsystem for Linux (WSL)][def7] is
required.

### poetry

banip requires [poetry][def2] for dependency management. Poetry is well
behaved and if you're a Python developer you should check it out. It
installs itself in a virtual environment, uninstalls cleanly and easily,
and doesn't require `sudo` for installation. Visit the [poetry
site][def2] and install it using your preferred methods, with the
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

### List of subnets for all countries

Download the list from [this site][def4].

### List of blacklisted IPs

Clone the [ipsum repository][def5] to a location of your choosing (let's
say your home directory `~`). You'll need to copy a file from it later.

### make

You'll need the linux [make][def6] utility installed (*it probably
already is*).

## Setup

Clone this repository. Let's assume you clone it your home directory
(`~`)

Change to `~/banip` and run this command:

```shell
make setup
```

Copy the following files as indicated below.

### Country subnets

```shell
cp <wherever you put it>/haproxy_geo_ip.txt ./data/haproxy_geo_ip.txt
```

### Blacklisted IPs

```shell
cp ~/ipsum/ipsum.txt ./data/ipsum.txt
```

### Target countries

```shell
cp sample-targets.txt ./data/targets.txt
```

Modify `./data/targets.txt` to select your desired target countries. The
comments in the file will guide you.

### Custom bans

```shell
cp sample-custom_bans.txt ./data/custom_bans.txt
```

These will be specific IP address or subnets (one per line, in
[CIDR][def] format) that you want to block. Some of your IPs may be
found when you run the tool, so this file (`custom_bans.txt`) will be
overwritten to remove the duplicates. The contents of the de-duplicated
file will be appended to the list generated when you run the program.

*Note: If you're concerned about keeping your original list of custom
bans, save a copy of it somewhere outside the repository.*

## Running

After copying/tweaking all the required files, start with this command
to learn how to build your custom blacklist:

```shell
poetry run banip -h
```

## Updating

The source lists of blacklisted IPs and country subnets are updated by
their authors daily (sometimes twice daily). When you're ready to create
a new blacklist, start with this:

```shell
cp ~/ipsum
git pull --rebase
```

Next, download a new copy of `haproxy_geo_ip.txt` as discussed above.
Put new copies of `ipsum.txt` and `haproxy_geo_ip.txt` in `./data`.
Tweak `./data/targets.txt` and `./data/custom_bans.txt` to your liking, and
run `banip` again.

[def]: https://aws.amazon.com/what-is/cidr/#:~:text=CIDR%20notation%20represents%20an%20IP,as%20192.168.1.0%2F22.
[def2]: https://python-poetry.org/
[def3]: https://docs.github.com/en/get-started/getting-started-with-git/ignoring-files
[def4]: https://wetmore.ca/ip/
[def5]: https://github.com/stamparm/ipsum
[def6]: https://man7.org/linux/man-pages/man1/make.1p.html
[def7]: https://docs.microsoft.com/en-us/windows/wsl/install
