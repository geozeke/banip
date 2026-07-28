# Plugins

banip plugins add commands that can use generated build products. Each
plugin has two required Python files:

1. An argument-parser module in `~/.banip/plugins/parsers`.
2. A command implementation module in `~/.banip/plugins/code`.

Copy and adapt the included samples:

```text
samples/plugins/foo.py
samples/plugins/foo_args.py
```

Keep the required `task_runner(args)` and `load_command_args(sp)` entry
points unchanged. The sample comments describe the expected filenames,
command naming, and parser wiring.
