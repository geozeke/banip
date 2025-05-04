# Changelog

<!--------------------------------------------------------------------->

## [1.3.1][1.3.1] - 2025-05-04

### Fixed

* [BUG] Host Public IP should not be in blacklist. [#40][issue40]
* Cleanup file structure. [#38][issue38]
* Cleanup Dependencies. [#39][issue39]

<!--------------------------------------------------------------------->

## [1.3.0][1.3.0] - 2025-01-13

**This is a breaking change! banip is now installed via `uv`, and your
existing data files need to move. Please see [README.md][banip] for
more.**

### Changed

**breaking**: Migrate banip to an installable package [#36][issue36].

### Fixed

* Fix italics in markdown files [#35][issue35]
* Lint code and documentation.

<!--------------------------------------------------------------------->

## [1.2.0][1.2.0] - 2025-01-11

### Changed

* Implement [tomli compatability layer][tomli].
* Optimize version numbering.

### Added

* Add statistics for a given country. [#32][issue32]
* Establish and maintain a proper changelog.

### Fixed

* Lint documentation.
* Display properly sorted options when getting help.

<!--------------------------------------------------------------------->

## [1.1.3][1.1.3] - 2024-12-19

### Added

* Add the ability to compact ipsum entries into /24 subnets.

### Fixed

* Improve input validation.
* Lint documentation.
* Refactor and optimize code.

<!--------------------------------------------------------------------->

## [1.1.2][1.1.2] - 2024-12-02

### Changed

* Tune binary search algorithm.
* Enhance `banip check` with prettier output using [rich][rich].

### Fixed

* Lint documentation.

<!--------------------------------------------------------------------->

## [1.1.1][1.1.1] - 2024-11-15

### Changed

* Get better output with the [rich][rich] library.

<!--------------------------------------------------------------------->

## [1.1.0][1.1.0] - 2024-10-23

### Changed

* Refine display of final metrics.

### Fixed

* Refactor code for better maintainability.

<!--------------------------------------------------------------------->

## [1.0.2][1.0.2] - 2024-08-09

### Changed

* Optimize binary search. [#13][issue13]
* Bumped tqdm library to v4.66.5.

### Added

* Add functionality to remove IP addresses captured in a subnets.
* Add license and acknowledgements for the tqmd library

### Fixed

* Fix calculation error in summary metrics.
* Choose Better Variable Names. [#14][issue14]
* Improve IP checking to include membership in subnets. [#15][issue15]

<!--------------------------------------------------------------------->

## [1.0.1][1.0.1] - 2024-07-30

### Added

* Add separate command line option to display version information.
* Add additional help indicators to the subcommands.

### Fixed

* Refactor code for better maintainability.

<!--------------------------------------------------------------------->

## [1.0.0][1.0.0] - 2024-03-15

### Changed

* Update documentation with page anchors.

### Added

* Introduce a plugin architecture.

### Fixed

* Fixed uncaught exception.
* Lint documentation.

<!--------------------------------------------------------------------->

## [0.1.0][0.1.0] - 2024-05-12

_Initial Release._

[0.1.0]: https://github.com/geozeke/banip/releases/tag/v0.1.0
[1.0.0]: https://github.com/geozeke/banip/releases/tag/V1.0.0
[1.0.1]: https://github.com/geozeke/banip/releases/tag/v1.0.1
[1.0.2]: https://github.com/geozeke/banip/releases/tag/v1.0.2
[1.1.0]: https://github.com/geozeke/banip/releases/tag/v1.1.0
[1.1.1]: https://github.com/geozeke/banip/releases/tag/v1.1.1
[1.1.2]: https://github.com/geozeke/banip/releases/tag/v1.1.2
[1.1.3]: https://github.com/geozeke/banip/releases/tag/v1.1.3
[1.2.0]: https://github.com/geozeke/banip/releases/tag/v1.2.0
[1.3.0]: https://github.com/geozeke/glinkfix/releases/tag/v1.3.0
[1.3.1]: https://github.com/geozeke/banip/releases/tag/v1.3.1
[banip]: https://github.com/geozeke/banip
[issue13]: https://github.com/geozeke/banip/issues/13
[issue14]: https://github.com/geozeke/banip/issues/14
[issue15]: https://github.com/geozeke/banip/issues/15
[issue32]: https://github.com/geozeke/banip/issues/32
[issue35]: https://github.com/geozeke/banip/issues/35
[issue36]: https://github.com/geozeke/banip/issues/36
[issue38]: https://github.com/geozeke/banip/issues/38
[issue39]: https://github.com/geozeke/banip/issues/39
[issue40]: https://github.com/geozeke/banip/issues/40
[rich]: https://github.com/Textualize/rich
[tomli]: https://pypi.org/project/tomli/
