# Plugins

> **Deprecated:** Plugins remain supported throughout banip 2.x but
> will be removed in banip 3.0. New integrations should be implemented
> outside banip while their requirements are evaluated for possible
> first-class commands.

See [Deprecations](deprecations.md#plug-in-architecture) for the public
status and version 3 removal checklist.

Legacy banip plugins add commands that can use generated build products.
Each plugin has two required Python files:

1. An argument-parser module in `~/.banip/plugins/parsers`.
2. A command implementation module in `~/.banip/plugins/code`.

Copy and adapt the included samples:

```text
samples/plugins/foo.py
samples/plugins/foo_args.py
```

Existing plugins should keep the required `task_runner(args)` and
`load_command_args(sp)` entry points unchanged. banip prints a
deprecation warning when it discovers plugin code but continues loading
valid plugins during the 2.x release line.

The `patch` command may already cover simple log-derived address lists:
it accepts whitespace-delimited input and lets the user select the IP
address field with `--index`. A future log-ingestion feature will be
designed only after representative formats and extraction requirements
are available.
