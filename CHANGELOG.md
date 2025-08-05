# Changelog

All notable changes to this project will be documented in this file.

## [0.8.2]

### Fix
- hasScheduledVideos is bool

## [0.8.1]

### Added
- Logos

### Fix
- imdbRating as str

## [0.8.0]

### Added
- Poster URLs are done on a per config base (TMDB or PosterDB)

### Fix
- Use IMDB_ID where possible to better work with default stremio clients

## [0.7.5]

### Added
- slugify for search cache key

## [0.7.5]

### Added
- Configuration validation on save: tests LLM, TMDB, and RPDB connections
- Meaningful error messages for configuration validation failures

### Fixed
- Configuration save now validates all services before creating manifest URLs

## [0.7.4]

### Fixed
- removed behavior which led to an infinite loop

## [0.7.3]

### Added
- validation for TMDB key

### Fixed
- fix empty cache served for searches

## [0.7.2]

### Fixed
- fix CACHE catalog:critics_picks

## [0.7.1]

### Fixed
- get correct CATALOG_PROMPTS

## [0.7.0]

### Changed
- Cache searches for 2h

## [0.6.0]

### Changed
- CI/CD complete refactor
- Better Prompting

## [0.5.3]

### Changed
- CI/CD complete refactor
- Better Prompting

## [0.5.3]

### Changed
- Configure: Auto-fetch models on first focus with spinner and keep placeholder selected until user chooses

## [0.5.2]

### Changed
- Configure: Provider first, dynamic API key label per provider, custom uses "LLM API Key" and no help text
- Configure: Remove default model unless provided by existing configuration

## [0.5.0]

### Added
- Cache for static content
- simplify pagination for catalogs

## [0.5.0]

Easier initial setup with builtin support for Openrouter, Gemini, OpenAI and Anthropic models

### Added
- Gzip compression for responses
- Browser caching for static content (30-day cache with immutable flag)

### Changed
- Refactor Configure page for easier support of multiple model providers
- Refactor Prompt handling (inspired by stremio-ai-search)
- Nicer error message on wrong API key
- General refactoring and duplicate removal

## [0.3.6]

### Changed
- Minor patches and maintenance.

## [0.3.5]

### Changed
- Reduce log verbosity: demote noisy INFO logs to DEBUG in API and services; keep critical warnings/errors. Improves ops signal-to-noise.

## [0.3.4]

### Fixed
- Routes for splitted manifest

## [0.3.3]

### Changed
- Configure page: support adult flag via URL and redirect endpoint

## [0.3.2]

### Added

- Dynamic caching

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
