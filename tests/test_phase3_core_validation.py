#!/usr/bin/env python3
"""
Pytest test cases for Phase 3 Core Validation of Grid-STIX Deterministic UUID Generation

This test suite validates the core deterministic UUID generation functionality
without relying on the full Grid-STIX object imports, which have dependency issues.
It focuses on testing the DeterministicUUIDGenerator class directly.

Run with: pytest tests/test_phase3_core_validation.py
"""

import pytest
import logging

# Import only the core functionality
from grid_stix.base import DeterministicUUIDGenerator, IDENTITY_PROPERTY_CONFIG

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


class TestGeneratorUUIDConsistency:
    """Test deterministic UUID generation for Generator objects."""

    def test_generator_uuid_consistency(self):
        """Test same properties generate same UUID for generators."""
        props1 = {
            "name": "Main Power Plant Generator",
            "x_asset_id": "GEN-001",
            "x_power_rating_mw": 500.0,
            "x_fuel_type": "natural_gas",
            "x_owner_organization": "Test Utility Corp",
        }

        props2 = {
            "name": "Main Power Plant Generator",
            "x_asset_id": "GEN-001",
            "x_power_rating_mw": 500.0,
            "x_fuel_type": "natural_gas",
            "x_owner_organization": "Test Utility Corp",
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid("x-grid-generator", props1)
        uuid2 = DeterministicUUIDGenerator.generate_uuid("x-grid-generator", props2)

        assert uuid1 == uuid2
        assert uuid1.startswith("x-grid-generator--")

    def test_different_generators_different_uuids(self):
        """Test different properties generate different UUIDs for generators."""
        props1 = {
            "name": "Main Power Plant Generator",
            "x_asset_id": "GEN-001",
            "x_power_rating_mw": 500.0,
            "x_fuel_type": "natural_gas",
            "x_owner_organization": "Test Utility Corp",
        }

        props2 = {
            "name": "Different Generator",
            "x_asset_id": "GEN-002",
            "x_power_rating_mw": 300.0,
            "x_fuel_type": "coal",
            "x_owner_organization": "Different Utility",
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid("x-grid-generator", props1)
        uuid2 = DeterministicUUIDGenerator.generate_uuid("x-grid-generator", props2)

        assert uuid1 != uuid2


class TestTransformerUUIDConsistency:
    """Test deterministic UUID generation for Transformer objects."""

    def test_transformer_uuid_consistency(self):
        """Test same properties generate same UUID for transformers."""
        props1 = {
            "name": "Main Substation Transformer",
            "x_asset_id": "TRANS-001",
            "x_voltage_primary_kv": 138.0,
            "x_voltage_secondary_kv": 13.8,
            "x_power_rating_mva": 100.0,
        }

        props2 = {
            "name": "Main Substation Transformer",
            "x_asset_id": "TRANS-001",
            "x_voltage_primary_kv": 138.0,
            "x_voltage_secondary_kv": 13.8,
            "x_power_rating_mva": 100.0,
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid("x-grid-transformer", props1)
        uuid2 = DeterministicUUIDGenerator.generate_uuid("x-grid-transformer", props2)

        assert uuid1 == uuid2
        assert uuid1.startswith("x-grid-transformer--")


class TestSmartMeterUUIDConsistency:
    """Test deterministic UUID generation for SmartMeter objects."""

    def test_smart_meter_uuid_consistency(self):
        """Test same properties generate same UUID for smart meters."""
        props1 = {
            "name": "Residential Smart Meter",
            "x_asset_id": "METER-001",
            "x_ip_address": "192.168.1.100",
            "x_mac_address": "00:11:22:33:44:55",
        }

        props2 = {
            "name": "Residential Smart Meter",
            "x_asset_id": "METER-001",
            "x_ip_address": "192.168.1.100",
            "x_mac_address": "00:11:22:33:44:55",
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid("x-grid-smartmeter", props1)
        uuid2 = DeterministicUUIDGenerator.generate_uuid("x-grid-smartmeter", props2)

        assert uuid1 == uuid2
        assert uuid1.startswith("x-grid-smartmeter--")


class TestCybersecurityPostureUUIDConsistency:
    """Test deterministic UUID generation for CybersecurityPosture objects."""

    def test_cybersecurity_posture_uuid_consistency(self):
        """Test same properties generate same UUID for cybersecurity posture."""
        props1 = {
            "x_trust_level": "high",
            "x_alert_level": "green",
            "x_defensive_posture": "normal",
            "x_authorized_by": "security_team",
        }

        props2 = {
            "x_trust_level": "high",
            "x_alert_level": "green",
            "x_defensive_posture": "normal",
            "x_authorized_by": "security_team",
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-cybersecurity-posture", props1
        )
        uuid2 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-cybersecurity-posture", props2
        )

        assert uuid1 == uuid2
        assert uuid1.startswith("x-grid-cybersecurity-posture--")


class TestAttackPatternUUIDConsistency:
    """Test deterministic UUID generation for AttackPattern objects."""

    def test_attack_pattern_uuid_consistency(self):
        """Test same properties generate same UUID for attack patterns."""
        props1 = {
            "name": "SCADA System Intrusion",
            "x_capec_id": "CAPEC-94",
            "x_attack_id": "T1190",
        }

        props2 = {
            "name": "SCADA System Intrusion",
            "x_capec_id": "CAPEC-94",
            "x_attack_id": "T1190",
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-cyber-attack-pattern", props1
        )
        uuid2 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-cyber-attack-pattern", props2
        )

        assert uuid1 == uuid2
        assert uuid1.startswith("x-grid-cyber-attack-pattern--")


class TestGridEventUUIDConsistency:
    """Test deterministic UUID generation for GridEvent objects."""

    def test_grid_event_uuid_consistency(self):
        """Test same properties generate same UUID for grid events."""
        props1 = {
            "x_event_type": "voltage_anomaly",
            "x_timestamp": "2025-01-08T14:30:00Z",
            "x_source_component": "TRANS-001",
        }

        props2 = {
            "x_event_type": "voltage_anomaly",
            "x_timestamp": "2025-01-08T14:30:00Z",
            "x_source_component": "TRANS-001",
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid("x-grid-grid-event", props1)
        uuid2 = DeterministicUUIDGenerator.generate_uuid("x-grid-grid-event", props2)

        assert uuid1 == uuid2
        assert uuid1.startswith("x-grid-grid-event--")


class TestPropertyNormalization:
    """Test property normalization across different scenarios."""

    def test_case_insensitive_normalization(self):
        """Test case-insensitive normalization."""
        props1 = {
            "name": "Test Generator",
            "x_asset_id": "GEN-001",
            "x_fuel_type": "NATURAL_GAS",
            "x_power_rating_mw": 100.0,
            "x_owner_organization": "Test Utility",
        }

        props2 = {
            "name": "test generator",
            "x_asset_id": "gen-001",
            "x_fuel_type": "natural_gas",
            "x_power_rating_mw": 100.0,
            "x_owner_organization": "test utility",
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid("x-grid-generator", props1)
        uuid2 = DeterministicUUIDGenerator.generate_uuid("x-grid-generator", props2)

        assert uuid1 == uuid2

    def test_list_normalization(self):
        """Test list order normalization."""
        props1 = {
            "name": "Test Meter",
            "x_asset_id": "METER-001",
            "x_ip_address": ["192.168.1.100", "10.0.0.1"],
            "x_mac_address": "00:11:22:33:44:55",
        }

        props2 = {
            "name": "Test Meter",
            "x_asset_id": "METER-001",
            "x_ip_address": ["10.0.0.1", "192.168.1.100"],  # Different order
            "x_mac_address": "00:11:22:33:44:55",
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid("x-grid-smartmeter", props1)
        uuid2 = DeterministicUUIDGenerator.generate_uuid("x-grid-smartmeter", props2)

        assert uuid1 == uuid2


class TestMissingPropertiesFallback:
    """Test fallback behavior when identity properties are missing."""

    def test_missing_properties_raise_value_error(self):
        """Test that missing required properties raise ValueError."""
        props_minimal = {"name": "Minimal Generator"}

        with pytest.raises(ValueError):
            DeterministicUUIDGenerator.generate_uuid("x-grid-generator", props_minimal)

    def test_validate_identity_properties(self):
        """Test validation of identity properties."""
        props_minimal = {"name": "Minimal Generator"}

        missing_props = DeterministicUUIDGenerator.validate_identity_properties(
            "x-grid-generator", props_minimal
        )

        assert missing_props is not None
        assert len(missing_props) > 0


class TestConfigurationCoverage:
    """Test that the configuration covers all major Grid-STIX object types."""

    def test_major_types_coverage(self):
        """Test that we have configurations for major object types."""
        required_types = [
            "x-grid-generator",
            "x-grid-transformer",
            "x-grid-substation",
            "x-grid-smartmeter",
            "x-grid-cybersecurity-posture",
            "x-grid-cyber-attack-pattern",
            "x-grid-grid-event",
            "x-grid-nuclear-facility",
            "x-grid-grid-relationship",
        ]

        missing_types = []
        for obj_type in required_types:
            if obj_type not in IDENTITY_PROPERTY_CONFIG:
                missing_types.append(obj_type)

        assert len(missing_types) == 0, f"Missing types: {missing_types}"

    def test_sufficient_coverage(self):
        """Test that we have sufficient configuration coverage."""
        total_types = len(IDENTITY_PROPERTY_CONFIG)
        expected_minimum = 90  # Should have at least 90 object types configured

        assert (
            total_types >= expected_minimum
        ), f"Expected at least {expected_minimum} types, got {total_types}"

    def test_configuration_validity(self):
        """Test that all configurations are valid."""
        for obj_type, props in IDENTITY_PROPERTY_CONFIG.items():
            assert isinstance(
                props, list
            ), f"Properties for {obj_type} should be a list"
            assert len(props) > 0, f"Properties for {obj_type} should not be empty"

            # Each property should be a string
            for prop in props:
                assert isinstance(
                    prop, str
                ), f"Property {prop} for {obj_type} should be a string"


# Fixtures for common test data
@pytest.fixture
def generator_properties():
    """Fixture providing generator properties."""
    return {
        "name": "Test Generator",
        "x_asset_id": "GEN-TEST",
        "x_power_rating_mw": 100.0,
        "x_fuel_type": "natural_gas",
        "x_owner_organization": "Test Utility",
    }


@pytest.fixture
def transformer_properties():
    """Fixture providing transformer properties."""
    return {
        "name": "Test Transformer",
        "x_asset_id": "TRANS-TEST",
        "x_voltage_primary_kv": 138.0,
        "x_voltage_secondary_kv": 13.8,
        "x_power_rating_mva": 50.0,
    }


@pytest.fixture
def smart_meter_properties():
    """Fixture providing smart meter properties."""
    return {
        "name": "Test Smart Meter",
        "x_asset_id": "METER-TEST",
        "x_ip_address": "192.168.1.100",
        "x_mac_address": "00:11:22:33:44:55",
    }


class TestWithFixtures:
    """Test class using pytest fixtures."""

    def test_generator_consistency_with_fixture(self, generator_properties):
        """Test generator UUID consistency using fixture."""
        uuid1 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-generator", generator_properties
        )
        uuid2 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-generator", generator_properties
        )

        assert uuid1 == uuid2
        assert uuid1.startswith("x-grid-generator--")

    def test_transformer_consistency_with_fixture(self, transformer_properties):
        """Test transformer UUID consistency using fixture."""
        uuid1 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-transformer", transformer_properties
        )
        uuid2 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-transformer", transformer_properties
        )

        assert uuid1 == uuid2
        assert uuid1.startswith("x-grid-transformer--")

    def test_smart_meter_consistency_with_fixture(self, smart_meter_properties):
        """Test smart meter UUID consistency using fixture."""
        uuid1 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-smartmeter", smart_meter_properties
        )
        uuid2 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-smartmeter", smart_meter_properties
        )

        assert uuid1 == uuid2
        assert uuid1.startswith("x-grid-smartmeter--")

    def test_different_object_types_different_uuids(
        self, generator_properties, transformer_properties, smart_meter_properties
    ):
        """Test that different object types produce different UUIDs."""
        gen_uuid = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-generator", generator_properties
        )
        trans_uuid = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-transformer", transformer_properties
        )
        meter_uuid = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-smartmeter", smart_meter_properties
        )

        # All UUIDs should be different
        assert gen_uuid != trans_uuid
        assert gen_uuid != meter_uuid
        assert trans_uuid != meter_uuid

        # Each should have correct prefix
        assert gen_uuid.startswith("x-grid-generator--")
        assert trans_uuid.startswith("x-grid-transformer--")
        assert meter_uuid.startswith("x-grid-smartmeter--")


if __name__ == "__main__":
    # Allow running with python directly for backwards compatibility
    pytest.main([__file__])
