# Grid-STIX Deterministic UUID Generation Guide

## Overview

Grid-STIX implements deterministic UUID generation to ensure that the same logical object always generates the same UUID across different systems and time periods. This enables reliable deduplication, consistent object identification, and improved data integrity in Grid-STIX deployments.

## How It Works

### UUID Generation Method

Grid-STIX uses **UUID5 (namespace-based SHA-1)** with a Grid-STIX specific namespace UUID (`6ba7b810-9dad-11d1-80b4-00c04fd430c8`). This approach provides:

- **Deterministic generation** based on key object properties
- **Cryptographically secure** and collision-resistant UUIDs
- **Standard UUID format** compliance
- **Reproducible results** across different systems

### Identity Properties

Each Grid-STIX object type has a defined set of "identity properties" that uniquely identify that object. These properties are used to generate the deterministic UUID. For example:

- **Generators**: `name`, `asset_id`, `power_rating_mw`, `fuel_type`, `owner_organization`
- **Smart Meters**: `name`, `asset_id`, `ip_address`, `mac_address`
- **Cyber Attack Patterns**: `name`, `capec_id`, `attack_id`

## Basic Usage

### Automatic UUID Generation

When creating Grid-STIX objects, deterministic UUIDs are generated automatically if no explicit ID is provided:

```python
from grid_stix.assets.Generator import Generator

# Create a generator - UUID will be generated automatically
generator = Generator(
    name="Main Power Plant Generator 1",
    x_asset_id=["GEN-001"],
    x_power_rating_mw=[500.0],
    x_fuel_type=["natural_gas"],
    x_owner_organization=["City Electric Utility"]
)

print(f"Generated UUID: {generator.id}")
# Output: x-grid-generator--4d29ed73-d166-51df-88ba-f53d97b54f48
```

### Consistent UUID Generation

Creating the same object multiple times will always generate the same UUID:

```python
# First instance
gen1 = Generator(
    name="Main Power Plant Generator 1",
    x_asset_id=["GEN-001"],
    x_power_rating_mw=[500.0],
    x_fuel_type=["natural_gas"],
    x_owner_organization=["City Electric Utility"]
)

# Second instance with identical properties
gen2 = Generator(
    name="Main Power Plant Generator 1",
    x_asset_id=["GEN-001"],
    x_power_rating_mw=[500.0],
    x_fuel_type=["natural_gas"],
    x_owner_organization=["City Electric Utility"]
)

assert gen1.id == gen2.id  # This will always be True
```

### Explicit ID Override

You can still provide explicit IDs when needed:

```python
generator = Generator(
    id="x-grid-generator--12345678-1234-1234-1234-123456789abc",
    name="Custom Generator",
    x_asset_id=["GEN-002"]
)
# The explicit ID will be used instead of generating a deterministic one
```

## Property Normalization

To ensure consistent UUID generation, property values are normalized:

### Case Insensitivity

String values are normalized to lowercase:

```python
# These will generate the same UUID
gen1 = Generator(name="Test Generator", x_fuel_type=["NATURAL_GAS"])
gen2 = Generator(name="test generator", x_fuel_type=["natural_gas"])
assert gen1.id == gen2.id
```

### List Ordering

Lists are sorted to ensure consistent ordering:

```python
# These will generate the same UUID
gen1 = Generator(name="Test", x_fuel_type=["coal", "natural_gas"])
gen2 = Generator(name="Test", x_fuel_type=["natural_gas", "coal"])
assert gen1.id == gen2.id
```

## Examples by Object Type

### Physical Assets

#### Generator
```python
from grid_stix.assets.Generator import Generator

generator = Generator(
    name="Riverside Power Plant Unit 1",
    x_asset_id=["RPP-U1"],
    x_power_rating_mw=[750.0],
    x_fuel_type=["natural_gas"],
    x_owner_organization=["Regional Power Authority"]
)
```

#### Transformer
```python
from grid_stix.assets.Transformer import Transformer

transformer = Transformer(
    name="Main Substation Transformer T1",
    x_asset_id=["SUB-MAIN-T1"],
    x_voltage_primary_kv=[138.0],
    x_voltage_secondary_kv=[13.8],
    x_power_rating_mva=[50.0]
)
```

#### Substation
```python
from grid_stix.assets.Substation import Substation

substation = Substation(
    name="Downtown Distribution Substation",
    x_asset_id=["SUB-DOWNTOWN"],
    x_high_voltage_level_kv=[69.0],
    x_substation_type=["distribution"],
    x_gps_coordinates=["40.7128,-74.0060"]
)
```

### Components

#### Smart Meter
```python
from grid_stix.components.SmartMeter import SmartMeter

smart_meter = SmartMeter(
    name="Residential Smart Meter 12345",
    x_asset_id=["SM-12345"],
    x_ip_address=["192.168.1.100"],
    x_mac_address=["00:1B:44:11:3A:B7"]
)
```

#### Photovoltaic System
```python
from grid_stix.components.PhotovoltaicSystem import PhotovoltaicSystem

pv_system = PhotovoltaicSystem(
    name="Rooftop Solar Array Building A",
    x_system_id=["PV-BLDG-A"],
    x_capacity_kw=[100.0],
    x_panel_type=["monocrystalline"]
)
```

### Cyber Contexts

#### Cybersecurity Posture
```python
from grid_stix.cyber_contexts.CybersecurityPosture import CybersecurityPosture

posture = CybersecurityPosture(
    x_trust_level=["high"],
    x_alert_level=["green"],
    x_defensive_posture=["normal"],
    x_authorized_by=["security_operations_center"]
)
```

#### Communication Session
```python
from grid_stix.cyber_contexts.CommunicationSession import CommunicationSession

session = CommunicationSession(
    x_session_id=["sess_20250108_001"],
    x_protocol_type=["dnp3"],
    x_session_start_time=["2025-01-08T10:00:00Z"]
)
```

### Attack Patterns

#### Cyber Attack Pattern
```python
from grid_stix.attack_patterns.CyberAttackPattern import CyberAttackPattern

attack_pattern = CyberAttackPattern(
    name="DNP3 Function Code Manipulation",
    x_capec_id=["CAPEC-123"],
    x_attack_id=["T1565.001"]
)
```

### Relationships

#### Grid Relationship
```python
from grid_stix.relationships.GridRelationship import GridRelationship

relationship = GridRelationship(
    x_source_ref=["x-grid-generator--4d29ed73-d166-51df-88ba-f53d97b54f48"],
    x_target_ref=["x-grid-transformer--9ed616b6-0138-5117-8bb6-fbbc31074828"],
    relationship_type="feeds-power-to"
)
```

### Events/Observables

#### Grid Event
```python
from grid_stix.events_observables.GridEvent import GridEvent

event = GridEvent(
    x_event_type=["voltage_anomaly"],
    x_timestamp=["2025-01-08T14:30:00Z"],
    x_source_component=["x-grid-transformer--9ed616b6-0138-5117-8bb6-fbbc31074828"]
)
```

#### Alarm Event
```python
from grid_stix.events_observables.AlarmEvent import AlarmEvent

alarm = AlarmEvent(
    x_alarm_type=["overcurrent"],
    x_timestamp=["2025-01-08T14:35:00Z"],
    x_source_component=["x-grid-generator--4d29ed73-d166-51df-88ba-f53d97b54f48"],
    x_severity=["high"]
)
```

## Fallback Behavior

If required identity properties are missing, the system will:

1. **Log a warning** indicating which properties are missing
2. **Generate a random UUID** as fallback
3. **Continue normal operation** without errors

```python
# This will generate a random UUID and log a warning
generator = Generator(
    description="Generator without required identity properties"
)
# Warning: Could not generate deterministic UUID for x-grid-generator: No identity properties found
```

## Best Practices

### 1. Provide Complete Identity Properties

Always include the identity properties for your object type to ensure deterministic UUID generation:

```python
# Good - includes all identity properties
generator = Generator(
    name="Power Plant Unit 1",
    x_asset_id=["PP-U1"],
    x_power_rating_mw=[500.0],
    x_fuel_type=["natural_gas"],
    x_owner_organization=["Utility Company"]
)

# Avoid - missing identity properties will result in random UUID
generator = Generator(
    description="Some generator"
)
```

### 2. Use Consistent Naming Conventions

Maintain consistent naming and formatting for better UUID consistency:

```python
# Good - consistent naming
gen1 = Generator(name="Main Plant Generator 1", x_asset_id=["MP-GEN-001"])
gen2 = Generator(name="Main Plant Generator 2", x_asset_id=["MP-GEN-002"])

# Avoid - inconsistent naming
gen1 = Generator(name="main plant generator 1", x_asset_id=["mp_gen_001"])
gen2 = Generator(name="Main Plant Gen #2", x_asset_id=["MP-GEN-002"])
```

### 3. Validate Properties Before Object Creation

Check that you have the required properties before creating objects:

```python
from grid_stix.base import DeterministicUUIDGenerator

# Validate identity properties
obj_type = "x-grid-generator"
properties = {
    "name": "Test Generator",
    "x_asset_id": ["GEN-001"]
    # Missing other required properties
}

missing_props = DeterministicUUIDGenerator.validate_identity_properties(obj_type, properties)
if missing_props:
    print(f"Missing required properties: {missing_props}")
    # Add missing properties before creating object
```

### 4. Handle Property Updates Carefully

Remember that changing identity properties will result in a different UUID:

```python
# Original object
gen1 = Generator(name="Generator 1", x_asset_id=["GEN-001"])
original_id = gen1.id

# If you change identity properties, you get a different UUID
gen2 = Generator(name="Generator 1 Updated", x_asset_id=["GEN-001"])
new_id = gen2.id

assert original_id != new_id  # Different UUIDs due to name change
```

## Integration with Existing Systems

### Database Storage

When storing Grid-STIX objects in databases, the deterministic UUIDs enable:

- **Deduplication**: Automatically detect and merge duplicate objects
- **Consistency**: Maintain consistent references across different data sources
- **Synchronization**: Reliably sync objects between systems

### Data Exchange

When exchanging Grid-STIX data between systems:

- **Same objects** will have the same UUIDs across systems
- **Relationships** remain consistent using deterministic UUIDs
- **Data integrity** is maintained during import/export operations

### Monitoring and Analytics

Deterministic UUIDs enable:

- **Tracking objects** across time and systems
- **Correlating events** with specific assets or components
- **Building consistent** dashboards and reports

## Performance Considerations

- **UUID generation** is fast (microseconds per object)
- **Memory usage** is minimal (no caching required)
- **Scalability** is excellent (O(1) generation time)
- **Network efficiency** improved through deduplication

## Migration from Random UUIDs

If you have existing systems using random UUIDs:

1. **Dual support**: The system supports both deterministic and explicit UUIDs
2. **Gradual migration**: New objects can use deterministic UUIDs immediately
3. **Mapping tables**: Create mappings between old and new UUIDs if needed
4. **Validation tools**: Use provided tools to verify UUID consistency

## Next Steps

- Review the [Identity Properties Reference](IDENTITY_PROPERTIES_REFERENCE.md) for complete property listings
- Check the [Troubleshooting Guide](TROUBLESHOOTING_UUID.md) for common issues
- See [Advanced Usage Examples](ADVANCED_UUID_EXAMPLES.md) for complex scenarios
- Explore the [API Reference](API_REFERENCE.md) for programmatic access

## Support

For questions or issues related to deterministic UUID generation:

1. Check the troubleshooting guide
2. Review the test cases in `tests/test_phase3_core_validation.py`
3. Examine the implementation in `python/grid_stix/base.py`
4. Consult the identity properties configuration
