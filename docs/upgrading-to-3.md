# Upgrading to 3.0

banip 3.0 removes the plug-in architecture and the unqualified country
allowlist that were deprecated in the 2.x release line. Review the
following changes before upgrading an existing installation.

## Plug-ins

Commands stored under `~/.banip/plugins` are no longer discovered or
loaded. Move integrations into separately managed commands or services
before upgrading. banip does not delete existing plug-in files or
directories, so they may be archived or removed manually after their
replacements are in place.

## Country policy outputs

Builds now write only explicitly named policy products:

```text
~/.banip/country_allowlist_<policy>.txt
```

Update every consumer of `~/.banip/country_allowlist.txt` to use the
corresponding named policy file before upgrading. A 3.0 build neither
updates nor deletes an existing unqualified file. Remove that stale file
manually after all consumers have migrated.

## Configuration schema

The current configuration schema is version 4. banip automatically
upgrades version-1, version-2, and version-3 files when it loads them.
The version-3 `countries.default_policy` setting is removed while every
entry under `countries.policies` is preserved.

For example, this version-3 section:

```yaml
version: 3
countries:
  default_policy: restricted
  policies:
    restricted:
      mode: allowlist
      codes:
        - CA
        - US
```

becomes:

```yaml
version: 4
countries:
  policies:
    restricted:
      mode: allowlist
      codes:
        - CA
        - US
```

The converted configuration is validated before it atomically replaces
the prior file. A failed conversion leaves the original unchanged.
