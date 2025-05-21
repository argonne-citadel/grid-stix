# Grid-STIX Ontology

Grid-STIX is an extension of the STIX (Structured Threat Information Expression) ontology specifically designed for electric grid cybersecurity applications. This ontology provides a standardized way to model grid assets, components, relationships, events, threats, and policies in a machine-readable format.

## Repository Structure

```
.
├── catalog.xml                               # XML catalog for import resolution
├── contexts/                                 # Context-specific ontologies
│   ├── grid-stix-2.1-cyber-contexts.owl      # Cyber context definitions
│   ├── grid-stix-2.1-environmental-contexts.owl # Environmental context definitions
│   ├── grid-stix-2.1-operational-contexts.owl # Operational context definitions
│   └── grid-stix-2.1-physical-contexts.owl   # Physical context definitions
├── core/                                     # Core ontology components
│   ├── grid-stix-2.1-assets.owl              # Asset definitions
│   ├── grid-stix-2.1-components.owl          # Component definitions
│   └── grid-stix-2.1-relationships.owl       # Relationship definitions
├── environment.yml                           # Conda/Mamba environment specification
├── Makefile                                  # Build automation
├── observables/                              # Observable events
│   └── grid-stix-2.1-events-observables.owl  # Event and observable definitions
├── ontology_checker.py                       # Validation script
├── owl_to_html.py                            # Visualization generator
├── policy/                                   # Policy definitions
│   └── grid-stix-2.1-policies.owl            # Security policy definitions
├── root/                                     # Root ontology files
│   └── grid-stix-2.1-root.owl                # Root ontology definition
├── threat/                                   # Threat definitions
│   └── grid-stix-2.1-attack-patterns.owl     # Attack pattern definitions
└── vocabularies/                             # Controlled vocabularies
    └── grid-stix-2.1-vocab.owl               # Vocabulary definitions
```

## Prerequisites

- Micromamba or Conda for environment management
- Robot (OWL toolkit) for ontology manipulation
- xmllint for XML formatting

## Setup

To set up the development environment:

```bash
make init
```

This will create a conda/micromamba environment with all required dependencies.

## Usage

### Linting and Formatting

To format code and OWL files:

```bash
make lint
```

This runs Black on Python files and xmllint on OWL files.

### Merging Ontologies

To merge all component ontologies into a single file:

```bash
make merge
```

This creates `grid-stix-2.1-full.owl` with all ontologies merged.

### Validation

To check the ontology for consistency and common issues:

```bash
make check
```

The `ontology_checker.py` script performs various validations:
- Checks for missing domain/range declarations
- Validates class hierarchy connectivity
- Detects cycles in subclass relationships
- Ensures proper label formatting (snake_case)
- Verifies property declarations
- And many other quality checks

### Visualization

To generate an HTML visualization of the ontology:

```bash
make html
```

This creates `grid-stix.html`, an interactive network visualization of the ontology.

## Key Tools

### ontology_checker.py

The ontology validator performs comprehensive checks on the merged ontology to ensure it follows best practices. It:

- Recursively loads ontologies using catalog.xml for import resolution
- Validates namespace consistency
- Checks for structural issues
- Verifies naming conventions
- Reports issues with exit code 1 if problems are found

Usage:
```bash
python ontology_checker.py [--owl-file FILE] [--base-namespace NS] [--catalog FILE] [--skip-checks LIST]
```

### owl_to_html.py

Generates an interactive HTML visualization of the ontology using Plotly:

- Creates a network graph of classes and properties
- Color-codes entities by type (Asset, Component, Event, etc.)
- Shows class hierarchies with dashed lines
- Displays property relationships between classes

Usage:
```bash
python owl_to_html.py INPUT_OWL OUTPUT_HTML
```

## Contributing

When contributing to the Grid-STIX ontology:

1. Make changes to the appropriate component file
2. Run `make lint` to format files
3. Run `make check` to validate your changes
4. Generate an updated visualization with `make html`
5. Commit all updated files

## License

[Insert your license information here]