# Changelog for pm

All changes to the pm project will be documented in this file.
For instructions, see the [changelog confluence page](https://epcpower.atlassian.net/l/c/zM7wz0at).

-------------------------------------------------------------------------------

## [Unreleased] - YYYY-MM-DD

### Added

- SC-795: Add units to SunSpec2/parameters for 700 series models
- SC-754: Add SunSpec 700 series models to SunSpec2
- SC-656: Add secondary SunSpec interface generation
- SC-661: Add SunSpec uint64 support
- SC-629: Added CAN parameter excel manual output.
- SC-590: Added access level column to the SunSpec and static modbus spreadsheet output.
- SC-572: Added changelog for release notes.

### Changed

- SC-869: Changed interface to support both sunspec1 and sunspec2 scaling factors
- SC-683: Changed rejected callback handling to use automatically generated interface

### Removed

- SC-623: Removed rejected callback field from c interface structures.

### Fixed

- SC-654: Fix modbus bitfield interface generation.

### CI

- SC-760: Pin poetry to 1.1.15
- SC-401: Romp Removal / Poetry Implementation
