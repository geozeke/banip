# Deprecations

This page tracks features that remain available for compatibility but
are scheduled for removal. New integrations should not depend on them.

| Feature | Deprecated | Supported through | Removal |
| --- | --- | --- | --- |
| Plug-in architecture | 2.1 | 2.x | 3.0 |
| Legacy country allowlist output | 2.1 | 2.x | 3.0 |

## Plug-in architecture

The dynamic plug-in architecture loads custom argument parsers and
command implementations from `~/.banip/plugins`. Existing plug-ins
continue to work throughout banip 2.x, and banip warns when it discovers
plug-in code.

Do not create new plug-ins. Implement new integrations outside banip
while their requirements are evaluated for possible first-class
features. See [Plugins](plugins.md) for the remaining compatibility
interface.

### Version 3 removal checklist

- Remove dynamic parser and command loading.
- Remove plug-in detection and its runtime warning.
- Stop creating plug-in directories during database initialization.
- Remove the plug-in path constants.
- Remove the sample plug-ins and compatibility documentation.
- Remove plug-in loading, dispatch, and initialization tests.

## Legacy country allowlist output

`country_allowlist.txt` is a compatibility copy of one named country
policy output. The `countries.default_policy` configuration key selects
the policy copied to that file. The key and file are deprecated
together because `default_policy` has no other purpose.

Migrate consumers to an explicit
`country_allowlist_<policy>.txt` product before upgrading to banip 3.0.
For example, a consumer using the `restricted` policy should read
`country_allowlist_restricted.txt`.

### Version 3 prerequisite

- Update HAProxy and every other consumer to use a named policy output.

### Version 3 removal checklist

- Stop generating `country_allowlist.txt`.
- Remove its path constant and compatibility-file tests.
- Remove `default_policy` from the configuration model and validation.
- Remove `default_policy` from the starter template and build summary.
- Introduce the next configuration schema.
- Migrate schema version 3 configurations by dropping
  `default_policy`.
- Update configuration, migration, command, and output documentation
  and tests.

