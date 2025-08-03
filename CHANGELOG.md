# Changelog

All notable changes to this project will be documented in this file.

## [0.3.1]

### Fix
- pagination for Omni

## [0.3.0]

### Added
- Catalogs caching with configurable limits

### Changed
- Cache refactor with stable, config-independent keys
- Mask sensitive config values in logs
- Load config with new URL handling
- Update preview and index templates for cached catalogs
- Dependency updates and fixes

### Fixed
- Test stability and minor issues

## [0.2.3]

### Changed
- Show response time in preview
- Minor refactoring

## [0.2.2]

### Added
- Background image and footer in UI

### Changed
- GitHub Actions workflow updates
- Default LLM model set to horizon-beta
- Improved manifest splitting handling and config extraction
- Better error handling on decryption failures

## [0.2.1]
- Github Action push…

## [0.2.0]

### Added
- Split manifest support for separate movie and series addons
  - Query parameter support: `?type=movie` or `?type=series`
  - Dedicated endpoints: `/manifest/movie.json` and `/manifest/series.json`
  - Web UI dropdown to select addon type (Combined, Movies Only, Series Only)
  - New `SPLIT_MANIFESTS` environment variable for future configuration
- Comprehensive test coverage for all manifest URL variations
- Backward compatibility maintained for existing manifest URLs

### Changed
- Enhanced preview page with manifest type selection dropdown
- Improved manifest builder with configurable content types
- Updated API routes to support multiple manifest formats

## [0.1.1]

### Added
- Catalog View
  - Show 50 Recommendations from LLM
  - New env MAX_CATALOG_RESULTS

### Fixed
- Install to app

## [0.1.0]

### Added
- TV show support with comprehensive integration
- Worker configuration system with documentation
- Request scheme handling from headers
- New test files for scheme handling
- TMDb service for TV show data retrieval
- Utility functions for data conversion

### Changed
- Updated Docker configuration for better worker support
- Improved Stremio API implementation
- Enhanced preview template with TV show display
- Updated README with latest information
- Fixed Docker Compose configuration

### Removed
- Debug endpoint from web API

## [0.0.4] - 2025-08-01

### Changed
- Use .env file for configuration (marked as minor change)

## [0.0.3]

### Changed
- Updated README (marked as patch)

## [0.0.2]

### Added
- First public version

## [0.0.1]

### Added
- Initial project setup
