# Changelog for pm

All changes to the pm project will be documented in this file.
For instructions, see the [changelog confluence page](https://epcpower.atlassian.net/l/c/zM7wz0at).

-------------------------------------------------------------------------------

## [Unreleased] - YYYY-MM-DD

### Added

- SC-1163: Add parameter min, max and read-only to SIL parameter generation
- SC-1110: Added scale factor column and enumerations worksheet to static modbus spreadsheet output
- MDL-378: Add parameter name, group and getter function to SIL parameter generation
- SC-835: SunSpec2 table support
- SC-795: Add units to SunSpec2/parameters for 700 series models
- SC-754: Add SunSpec 700 series models to SunSpec2
- SC-656: Add secondary SunSpec interface generation
- SC-661: Add SunSpec uint64 support
- SC-629: Added CAN parameter excel manual output.
- SC-590: Added access level column to the SunSpec and static modbus spreadsheet output.
- SC-572: Added changelog for release notes.

### Changed

- SC-935: SunSpec2 start address 40k for spreadsheet output
- SC-805: No longer output dummy SunSpec1 models in user spreadsheet
- SC-869: Changed interface to support both sunspec1 and sunspec2 scaling factors
- SC-683: Changed rejected callback handling to use automatically generated interface

### Removed

- SC-623: Removed rejected callback field from c interface structures.

### Fixed

- SC-1195: Fix SunSpec2 bitfield interface generation
- SC-910: Fix SunSpec2 table parameter interface generation.
- SC-922: Fix SIL array table element setter for groups
- SC-654: Fix modbus bitfield interface generation.

### CI

- SC-1157: Pin versions of all python packages for installing poetry
- SC-1112: Remove codecov python dependency
- SC-995: Update actions versions to alleviate CI build warnings
- SC-760: Pin poetry to 1.1.15
- SC-401: Romp Removal / Poetry Implementation
