# Runtime Type Groups

This TODO scopes a small typing and clarity cleanup for IP address and
network handling. The goal is to distinguish static type aliases from
runtime class groups used by `isinstance()`.

## Summary

Keep the existing singular names in `src/banip/constants.py` for type
annotations, and add plural names for runtime checks.

Intended constants:

- `AddressType: TypeAlias = IPv4Address | IPv6Address`
- `NetworkType: TypeAlias = IPv4Network | IPv6Network`
- `AddressTypes = (IPv4Address, IPv6Address)`
- `NetworkTypes = (IPv4Network, IPv6Network)`

The singular aliases describe values for static typing. The plural
tuples group concrete classes for runtime predicates.

## Implementation Notes

- Add `AddressTypes` and `NetworkTypes` in `src/banip/constants.py` near
  the existing `AddressType` and `NetworkType` aliases.
- Update `split_hybrid()` in `src/banip/utilities.py` to use
  `isinstance(value, AddressTypes)` and
  `isinstance(value, NetworkTypes)`.
- Import the plural names only where runtime checks need them.
- Preserve command behavior, generated files, return types, and CLI
  output.
- Search for any additional `isinstance()` checks before implementing,
  but keep the first pass scoped to existing IP address/network checks.

## Verification

- Run `just lint` after the Python code change.
- Run `just typecheck` to verify the alias and runtime tuple distinction.
- Run `just test`, with attention to
  `test_split_hybrid_sorts_addresses_and_networks`.

## Assumptions

- This is a clarity and typing cleanup, not a runtime optimization.
- The requested names `AddressTypes` and `NetworkTypes` are acceptable
  even though they are constants, because they intentionally pair with
  `AddressType` and `NetworkType`.
- Python compatibility remains `>=3.12`.
