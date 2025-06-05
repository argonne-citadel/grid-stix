# Grid-STIX 2.1 Electrical Grid Cybersecurity Ontology

Grid-STIX is a comprehensive extension of the STIX (Structured Threat Information Expression) 2.1 ontology specifically designed for electrical distribution grid cybersecurity applications. This ontology provides a standardized, machine-readable framework for modeling grid assets, operational technology devices, threats, vulnerabilities, supply chain risks, and security relationships in electrical power systems.

## 🌟 Key Features

- **Comprehensive Grid Coverage**: Physical assets, OT devices, grid components, sensors, and energy storage systems
- **Advanced Security Modeling**: Attack patterns, vulnerabilities, mitigations, and supply chain risks
- **Critical Grid Relationships**: Power flow, protection, control, and synchronization relationships
- **Supply Chain Security**: Supplier modeling, country of origin tracking, and risk assessment
- **Protocol Support**: DNP3, Modbus, IEC 61850, IEC 60870-5-104, OPC-UA, and IEEE standards
- **Interactive Visualization**: Enhanced HTML network graphs with grid-specific categorization
- **STIX 2.1 Compliance**: Full compatibility with STIX threat intelligence ecosystem

## 📂 Repository Structure

```
grid-stix/
├── catalog.xml                               # XML catalog for import resolution
├── contexts/                                 # Context-specific ontologies
│   ├── grid-stix-2.1-cyber-contexts.owl      # Cybersecurity posture and contexts
│   ├── grid-stix-2.1-environmental-contexts.owl # Weather, natural disasters
│   ├── grid-stix-2.1-operational-contexts.owl   # Grid operating conditions
│   └── grid-stix-2.1-physical-contexts.owl      # Physical security contexts
├── core/                                     # Core ontology components
│   ├── grid-stix-2.1-assets.owl              # Assets, suppliers, supply chain
│   ├── grid-stix-2.1-components.owl          # Grid components, OT devices, sensors
│   └── grid-stix-2.1-relationships.owl       # Power flow, protection, control
├── environment.yml                           # Conda/Mamba environment specification
├── Makefile                                  # Build automation and workflows
├── observables/                              # Observable events and monitoring
│   └── grid-stix-2.1-events-observables.owl  # Grid events, alarms, anomalies
├── ontology_checker.py                       # Comprehensive validation script
├── owl_to_html.py                            # Enhanced visualization generator
├── policy/                                   # Security policies and procedures
│   └── grid-stix-2.1-policies.owl            # Grid security policies
├── root/                                     # Root ontology integration
│   └── grid-stix-2.1-root.owl                # Master ontology file
├── tac-ontology/                             # STIX 2.1 base ontologies
├── threat/                                   # Threat and attack modeling
│   └── grid-stix-2.1-attack-patterns.owl     # Grid-specific attack patterns
└── vocabularies/                             # Controlled vocabularies
    └── grid-stix-2.1-vocab.owl               # Open vocabularies and protocols
```

## 🚀 Quick Start

### Prerequisites

- **Micromamba** for environment management
- **Robot Framework** (OWL toolkit) for ontology operations
- **xmllint** for XML validation and formatting

### Environment Setup

Create and activate the development environment:

```bash
make init
```

This creates a `grid-stix` conda environment with all required dependencies including:
- Python 3.12
- RDFLib for ontology processing
- NetworkX & Plotly for visualization
- PyGraphviz for advanced layouts
- Black for code formatting
- Security tools (Bandit)

## 🔧 Development Workflow

### Code Quality & Formatting

Format all Python and OWL files:
```bash
make format
```

Run quality checks without modifications:
```bash
make lint
```

Run comprehensive security analysis:
```bash
make security
```

### Ontology Operations

**Merge all component ontologies:**
```bash
make merge
```
Creates `grid-stix-2.1-full.owl` with all modules integrated.

**Validate ontology consistency:**
```bash
make check
```
Runs comprehensive validation including:
- Class hierarchy connectivity
- Missing domain/range declarations
- Label format consistency (snake_case)
- Property declaration validation
- STIX compliance verification
- Supply chain relationship validation

**Generate interactive visualization:**
```bash
make html
```
Creates `grid-stix.html` with enhanced electrical grid visualization.

## 🎨 Advanced Visualization

The enhanced `owl_to_html.py` tool provides Grid-STIX specific visualization capabilities:

### Basic Usage
```bash
python owl_to_html.py grid-stix-2.1-full.owl output.html
```

### Grid-STIX Specific Options

**Focus on grid infrastructure:**
```bash
python owl_to_html.py --focus-infrastructure grid-stix-2.1-full.owl grid-infrastructure.html
```

**Focus on security concepts:**
```bash
python owl_to_html.py --focus-security grid-stix-2.1-full.owl grid-security.html
```

**Focus on supply chain security:**
```bash
python owl_to_html.py --focus-supply-chain grid-stix-2.1-full.owl supply-chain.html
```

**Show only Grid-STIX classes (exclude base STIX):**
```bash
python owl_to_html.py --grid-only grid-stix-2.1-full.owl grid-only.html
```

**Choose layout algorithm:**
```bash
python owl_to_html.py --layout twopi grid-stix-2.1-full.owl radial-layout.html
# Available layouts: dot, twopi, neato, circo, spring
```

**Advanced filtering:**
```bash
python owl_to_html.py --exclude-prefix "Union_,stix" --no-inheritance grid-stix-2.1-full.owl clean-view.html
```

### Visualization Features

- **Color-coded categories**: Infrastructure (blue), Security (red), Supply chain (brown)
- **Interactive hover**: Detailed information about each concept
- **Hierarchical layout**: Clear visualization of STIX inheritance
- **Relationship types**: Solid lines for relationships, dashed for inheritance
- **Professional presentation**: Publication-ready titles and legends

## 🏗️ Ontology Architecture

### Core Components

1. **Assets & Infrastructure** (`core/grid-stix-2.1-assets.owl`)
   - Physical assets (substations, transmission lines)
   - Security zones and perimeters
   - Supply chain entities and risk modeling

2. **Grid Components** (`core/grid-stix-2.1-components.owl`)
   - Electrical equipment (transformers, capacitors, voltage regulators)
   - OT devices (RTUs, PLCs, IEDs, HMIs, smart meters)
   - Protective devices (circuit breakers, reclosers, sectionalizers)
   - Energy storage systems

3. **Relationships** (`core/grid-stix-2.1-relationships.owl`)
   - Power flow relationships (`feedsPowerTo`)
   - Protection relationships (`protectsAsset`)
   - Control and regulation (`synchronizesWith`, `regulatesVoltage`)
   - Monitoring and dependency relationships

4. **Protocols & Communications** (`vocabularies/grid-stix-2.1-vocab.owl`)
   - DNP3, Modbus, IEC 61850, IEC 60870-5-104
   - OPC-UA, IEEE C37.118, IEC 62351
   - Communication security protocols

5. **Supply Chain Security** (integrated across multiple files)
   - Supplier risk assessment
   - Country of origin tracking
   - Security clearance requirements
   - Supply chain verification processes

### Security Modeling

- **Attack Patterns**: Grid-specific threats (DNP3 spoofing, firmware modification)
- **Vulnerabilities**: Asset and protocol-specific weaknesses
- **Mitigations**: Grid security countermeasures and best practices
- **Events & Observables**: Security monitoring and incident detection

## 🎓 Extension Points

The ontology includes structured TODO comments for additional work:

### 1. Distributed Energy Resources (DER) & Microgrids
- `DistributedEnergyResource` class with renewable energy modeling
- `Microgrid` islanding and autonomy capabilities
- `Inverter` grid integration technology
- Power generation and aggregation relationships

### 2. Smart Grid Demand Response
- `DemandResponseProgram` policy modeling
- `SmartAppliance` controllable load devices
- Load curtailment and shifting relationships
- Time-based pricing and incentive structures

### 3. Advanced Distribution Management Systems (ADMS)
- `ADMS` optimization and analytics platforms
- `DistributionAutomationDevice` intelligent switching
- Grid optimization functions and coordination

## 🔍 Validation & Quality Assurance

The `ontology_checker.py` script provides comprehensive validation:

```bash
# Basic validation
python ontology_checker.py

# Advanced options
python ontology_checker.py --owl-file custom.owl --skip-checks "labels,domains"
```

**Validation Categories:**
- **Structural**: Class hierarchy integrity, relationship consistency
- **Semantic**: Domain/range validation, property inheritance
- **Syntactic**: Naming conventions, label formatting
- **Grid-specific**: Power system relationship validation
- **STIX compliance**: Proper inheritance from STIX base classes

## 🤝 Contributing

When contributing to Grid-STIX:

1. **Development Cycle:**
   ```bash
   # Make your changes to appropriate files
   make lint          # Format and validate syntax
   make check         # Comprehensive ontology validation
   make html          # Generate updated visualization
   ```

2. **Best Practices:**
   - Follow snake_case naming for all labels
   - Maintain proper STIX inheritance patterns
   - Add comprehensive comments for new concepts
   - Test with both `--grid-only` and full visualizations

3. **File Organization:**
   - Assets & infrastructure → `core/grid-stix-2.1-assets.owl`
   - Grid equipment → `core/grid-stix-2.1-components.owl`
   - Relationships → `core/grid-stix-2.1-relationships.owl`
   - Vocabularies → `vocabularies/grid-stix-2.1-vocab.owl`

## 📊 Current Ontology Status

- **Classes**: 50+ grid-specific classes with proper STIX inheritance
- **Relationships**: 25+ critical grid relationships including power flow and protection
- **Protocols**: Complete coverage of major ICS/SCADA protocols
- **Supply Chain**: Comprehensive supplier risk and verification modeling
- **Extensibility**: Clear extension points for additional features

## 📚 Documentation & Resources

- **Interactive Visualization**: Run `make html` to explore the complete ontology
- **Validation Reports**: Run `make check` for detailed consistency analysis
- **Grid-STIX Specification**: See inline comments and class definitions
- **STIX 2.1 Reference**: [OASIS STIX 2.1 Specification](https://docs.oasis-open.org/cti/stix/v2.1/)


---

*Grid-STIX 2.1 - Advancing electrical grid cybersecurity through standardized threat intelligence modeling*