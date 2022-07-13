# Changelog for pm

All changes to the pm project will be documented in this file.
For instructions, see the [changelog confluence page](https://epcpower.atlassian.net/l/c/zM7wz0at).

-------------------------------------------------------------------------------

## [Unreleased] - YYYY-MM-DD

### Added

- SC-661: Add SunSpec uint64 support
- SC-629: Added CAN parameter excel manual output.
- SC-590: Added access level column to the SunSpec and static modbus spreadsheet output.
- SC-572: Added changelog for release notes.

### Changed

- SC-683: Changed rejected callback handling to use automatically generated interface

### Removed

- SC-623: Removed rejected callback field from c interface structures.

### Fixed

- SC-654: Fix modbus bitfield interface generation.

### CI

- SC-662: Use new global token, Store credentials for private repo installs, fix submodule.
- SC-401: Romp Removal / Poetry Implementation
