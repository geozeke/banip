# Optimization Opportunities

This document scopes higher-impact optimization work for future
`banip` releases. The current Python floor should remain `>=3.12` unless
a future change depends on a Python 3.14-only feature for a measured,
user-visible benefit.

## Baseline First

Start by profiling the expensive commands against realistic local data.
Use the same GeoLite2, ipsum, whitelist, blacklist, and target files that
represent normal use. Capture separate timings for `build`, `check`, and
`stats`, because they exercise different paths.

Useful baseline questions:

- How much wall time is spent parsing files versus searching networks?
- How many times is `ip_in_network()` called during a normal build?
- How much time is spent converting `ipaddress` objects to integers?
- How large are the IPv4 and IPv6 network lists after GeoLite loading?
- Does startup/import time matter compared with processing time?

Keep optimization work tied to before/after measurements. Small code
cleanups are useful, but the goal of this plan is runtime improvement.

## Network Lookup Path

The most likely high-impact target is repeated network membership
testing in `src/banip/utilities.py`.

Current behavior:

- `ip_in_network()` uses recursive binary search over sorted
  `ipaddress` network objects.
- Each recursive step recomputes `int(ip)`.
- Each step also converts the candidate network's `network_address` and
  `broadcast_address` to integers.
- `build` calls this routine many times while pruning custom entries,
  filtering ipsum entries, applying whitelists, and removing redundant
  entries.

Planned optimizations:

- Replace recursive binary search with an iterative loop.
- Compute `ip_int = int(ip)` once per lookup.
- Precompute network bounds once per sorted network list:
  `(first_int, last_int, network)`.
- Search precomputed bounds instead of converting network endpoints on
  every lookup.
- Keep IPv4 and IPv6 bounds in separate lists if profiling shows mixed
  address-family comparisons are adding overhead or complexity.

Expected impact:

- Iteration alone removes function-call and stack-frame overhead but
  keeps the same `O(log n)` algorithm.
- Precomputed bounds should produce the larger gain because repeated
  integer conversion is avoided across many lookups.
- Separating IPv4 and IPv6 may reduce search work and make comparison
  assumptions clearer.

Risks and constraints:

- Preserve the current return value: the containing network object, or
  `None`.
- Preserve behavior for both IPv4 and IPv6 addresses.
- Avoid changing parser or command behavior while replacing the lookup
  implementation.
- Update tests to cover boundary addresses, misses before/after a
  network, IPv4, IPv6, and mixed lists.

## Build Pipeline Data Flow

The `build` command repeatedly converts between sets, lists, sorted
lists, dictionaries, and `ipaddress` objects. Some of this is necessary,
but several passes can likely be tightened after profiling.

Planned optimizations:

- Keep membership-only collections as sets when order is not required.
- Avoid converting a set to a list only to split and sort it when a
  downstream function can accept an iterable.
- Avoid repeated `len(networks) - 1` calculations at call sites by
  moving range handling into the lookup function.
- Build reusable lookup structures for `target_geolite`, `custom_nets`,
  `white_nets`, `ipsum_nets`, and rendered blacklist networks.
- Consider passing a small lookup object through the build pipeline
  instead of passing raw network lists plus index bounds.

Expected impact:

- Fewer temporary objects during large ipsum and GeoLite processing.
- Less repeated setup for hot membership checks.
- Cleaner call sites with lower risk of off-by-one range arguments.

Risks and constraints:

- Do not change output ordering unless tests and documentation establish
  a new stable order.
- Keep code understandable; avoid a complex custom index unless profiling
  proves it is needed.
- Maintain compatibility with existing pickled data unless a migration
  is explicitly planned.

## Serialized Build Products

`tag_networks()` writes both a text file and a pickle containing a
dictionary of `ipaddress` network objects mapped to country codes.
`check` and `stats` load the pickle and rebuild sorted lookup lists as
needed.

Planned optimizations:

- Measure load time and memory use for the existing pickle.
- Evaluate whether storing precomputed network bounds in the build
  product materially improves `check` startup and repeated lookup time.
- If changing the pickle format, include a format/version marker so old
  cache files can be detected and regenerated safely.
- Keep the HAProxy-friendly text output unchanged.

Expected impact:

- Faster `check` startup if lookup-ready data is serialized.
- Less repeated sorting and conversion when the same GeoLite cache is
  reused.

Risks and constraints:

- Pickle format changes can break existing local `~/.banip` state.
- Any cache migration should fail clearly and recommend rerunning
  `banip build` if automatic migration is not worth the complexity.
- Do not optimize the cache format until profiling shows it matters.

## File I/O and Rendering

File I/O is probably secondary to network lookup work, but the command
modules write several output files line by line.

Planned optimizations:

- Prefer `Path.open()` for consistency with the existing `Path`
  constants.
- Use context managers for stub file creation instead of manual
  `open()`/`close()` pairs.
- Consider batching writes with `"\n".join(...)` for large rendered
  output sections.
- Keep streaming reads for large input files unless profiling shows a
  full read is faster and memory use remains acceptable.

Expected impact:

- Small runtime improvement for large output files.
- Clearer file handling with fewer open-file edge cases.

Risks and constraints:

- Preserve trailing newline behavior in generated files.
- Avoid reading very large files fully into memory without measurement.
- Do not change file locations or generated file names.

## Python 3.14 Evaluation

Python 3.14 may provide modest automatic wins through interpreter and
standard-library improvements, but it should not be the primary
optimization strategy.

Planned evaluation:

- Add Python 3.14 to the test matrix when dependencies and tooling are
  ready.
- Benchmark the same workloads on Python 3.12, 3.13, and 3.14.
- Treat Python 3.14-only features, such as subinterpreters through
  `InterpreterPoolExecutor`, as optional experiments rather than
  prerequisites.

Expected impact:

- Possible small improvements in startup, imports, file reads, and
  pickle behavior.
- Larger gains still likely require code-level lookup and data-flow
  changes.

Risks and constraints:

- Raising the package floor to Python 3.14 would reduce compatibility.
- Free-threaded or subinterpreter-based designs add complexity and must
  beat simpler single-process optimizations in benchmarks.

## Verification

For each implemented optimization:

- Run `just lint` after Python code changes.
- Run `just typecheck` when behavior or types change.
- Run `just test` for lookup, build, check, stats, and cache-format
  changes.
- Compare benchmark results before and after the change.
- Verify generated blacklist, whitelist, country whitelist, and GeoLite
  output files remain behaviorally equivalent unless the change
  intentionally updates their format.
