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

- SC-922: Fix SIL array table element setter for groups
- SC-654: Fix modbus bitfield interface generation.

### CI

- BA-510: Update poetry to 1.5.1 version
- SC-1157: Pin versions of all python packages for installing poetry
- SC-1112: Remove codecov python dependency
- SC-995: Update actions versions to alleviate CI build warnings
- SC-760: Pin poetry to 1.1.15
- SC-401: Romp Removal / Poetry Implementation
