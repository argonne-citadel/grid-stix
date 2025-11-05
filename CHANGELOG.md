# Changelog

All notable changes to the Grid-STIX project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2024-11-05

### Added
- Asset type taxonomy for ATT&CK integration with comprehensive classification system
- New `grid-stix-2.1-asset-types.owl` ontology file with 243 lines of asset type definitions
- Enhanced asset modeling in `grid-stix-2.1-assets.owl` with 17 new lines
- Catalog.xml entries for new asset type ontology
- Improved DER (Distributed Energy Resource) modeling capabilities
- Python code generation from OWL ontologies using OwlReady2
- pyproject.toml for modern Python packaging
- Updated .gitignore for better Python project hygiene

### Changed
- Updated environment.yml dependencies for improved compatibility
- Enhanced Makefile with additional build targets

### Fixed
- Test failures - achieved 100% test pass rate
- Build_module call for union types in Python code generation
- Ontology checker issues in asset type taxonomy

### Documentation
- Simplified README to focus on make targets for better usability

## [2.0.0] - 2024-09-08

Initial GitHub release with comprehensive Grid-STIX 2.1 ontology framework.

### Added
- Core Grid-STIX 2.1 ontology files
- STIX 2.1 extensions for grid infrastructure
- Comprehensive grid component modeling
