#!/usr/bin/env python3
"""
Pytest test cases to validate the examples in the deterministic UUID documentation.

This test module validates that the deterministic UUID functionality works
as documented, without importing modules that have generation issues.

Run with: pytest tests/test_documentation_examples.py
"""

import pytest

from grid_stix.base import DeterministicUUIDGenerator, IDENTITY_PROPERTY_CONFIG


class TestDeterministicUUIDGenerator:
    """Test class for DeterministicUUIDGenerator core functionality."""

    def test_basic_uuid_generation(self):
        """Test basic UUID generation."""
        obj_type = "x-grid-generator"
        properties = {
            "name": "Main Power Plant Generator 1",
            "x_grid_component_type": ["generator"],
            "x_power_rating_mw": [500.0],
            "x_fuel_type": ["natural_gas"],
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid(obj_type, properties)

        # Should generate a valid UUID with correct prefix
        assert uuid1.startswith("x-grid-generator--")
        assert len(uuid1) == len(
            "x-grid-generator--12345678-1234-1234-1234-123456789abc"
        )

    def test_consistent_uuid_generation(self):
        """Test that same properties generate same UUID."""
        obj_type = "x-grid-generator"
        properties = {
            "name": "Main Power Plant Generator 1",
            "x_grid_component_type": ["generator"],
            "x_power_rating_mw": [500.0],
            "x_fuel_type": ["natural_gas"],
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid(obj_type, properties)
        uuid2 = DeterministicUUIDGenerator.generate_uuid(obj_type, properties)

        assert uuid1 == uuid2

    def test_different_properties_different_uuids(self):
        """Test that different properties generate different UUIDs."""
        obj_type = "x-grid-generator"

        properties1 = {
            "name": "Main Power Plant Generator 1",
            "x_grid_component_type": ["generator"],
            "x_power_rating_mw": [500.0],
            "x_fuel_type": ["natural_gas"],
        }

        properties2 = {
            "name": "Different Generator",
            "x_grid_component_type": ["generator"],
            "x_power_rating_mw": [750.0],
            "x_fuel_type": ["coal"],
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid(obj_type, properties1)
        uuid2 = DeterministicUUIDGenerator.generate_uuid(obj_type, properties2)

        assert uuid1 != uuid2

    def test_case_insensitive_normalization(self):
        """Test case insensitive normalization."""
        obj_type = "x-grid-generator"

        case_props1 = {
            "name": "Test Generator",
            "x_grid_component_type": "GENERATOR",
            "x_power_rating_mw": 100.0,
            "x_fuel_type": "NATURAL_GAS",
        }
        case_props2 = {
            "name": "test generator",
            "x_grid_component_type": "generator",
            "x_power_rating_mw": 100.0,
            "x_fuel_type": "natural_gas",
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid(obj_type, case_props1)
        uuid2 = DeterministicUUIDGenerator.generate_uuid(obj_type, case_props2)

        assert uuid1 == uuid2

    def test_list_order_normalization(self):
        """Test list order normalization."""
        obj_type = "x-grid-generator"

        list_props1 = {
            "name": "Test",
            "x_grid_component_type": "generator",
            "x_power_rating_mw": 100.0,
            "x_fuel_type": ["coal", "natural_gas"],
        }
        list_props2 = {
            "name": "Test",
            "x_grid_component_type": "generator",
            "x_power_rating_mw": 100.0,
            "x_fuel_type": ["natural_gas", "coal"],
        }

        uuid1 = DeterministicUUIDGenerator.generate_uuid(obj_type, list_props1)
        uuid2 = DeterministicUUIDGenerator.generate_uuid(obj_type, list_props2)

        assert uuid1 == uuid2

    def test_property_validation(self):
        """Test property validation detects missing properties."""
        obj_type = "x-grid-generator"
        incomplete_properties = {
            "name": "Test Generator",
            "x_grid_component_type": ["generator"],
            # Missing other required properties
        }

        missing_props = DeterministicUUIDGenerator.validate_identity_properties(
            obj_type, incomplete_properties
        )

        # Should detect missing properties
        assert missing_props is not None
        assert len(missing_props) > 0

    def test_fallback_behavior_empty_properties(self):
        """Test fallback behavior for empty properties raises ValueError."""
        obj_type = "x-grid-generator"
        empty_props = {}

        with pytest.raises(ValueError):
            DeterministicUUIDGenerator.generate_uuid(obj_type, empty_props)

    def test_multiple_object_types_different_uuids(self):
        """Test multiple object types generate different UUIDs."""
        generator_props = {
            "name": "Test Generator",
            "x_grid_component_type": ["generator"],
            "x_power_rating_mw": [500.0],
            "x_fuel_type": ["natural_gas"],
        }

        transformer_props = {
            "name": "Main Substation Transformer T1",
            "x_asset_id": ["SUB-MAIN-T1"],
            "x_voltage_primary_kv": [138.0],
            "x_voltage_secondary_kv": [13.8],
            "x_power_rating_mva": [50.0],
        }

        generator_uuid = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-generator", generator_props
        )
        transformer_uuid = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-transformer", transformer_props
        )

        assert generator_uuid != transformer_uuid
        assert generator_uuid.startswith("x-grid-generator--")
        assert transformer_uuid.startswith("x-grid-transformer--")


class TestConfigurationCoverage:
    """Test class for configuration coverage validation."""

    def test_documented_object_types_configured(self):
        """Test that documented object types are properly configured."""
        documented_types = [
            "x-grid-generator",
            "x-grid-transformer",
            "x-grid-substation",
            "x-grid-smartmeter",
            "x-grid-photovoltaic-system",
            "x-grid-cybersecurity-posture",
            "x-grid-communication-session",
            "x-grid-cyber-attack-pattern",
            "x-grid-grid-event",
            "x-grid-alarm-event",
        ]

        missing_types = []
        for obj_type in documented_types:
            if obj_type not in IDENTITY_PROPERTY_CONFIG:
                missing_types.append(obj_type)
            else:
                # Verify configuration has properties
                props = IDENTITY_PROPERTY_CONFIG[obj_type]
                assert isinstance(props, list)
                assert len(props) > 0

        assert len(missing_types) == 0, f"Missing configuration for: {missing_types}"

    def test_configuration_completeness(self):
        """Test that configuration has reasonable coverage."""
        # Should have configuration for a substantial number of object types
        total_types = len(IDENTITY_PROPERTY_CONFIG)
        assert (
            total_types >= 90
        ), f"Expected at least 90 configured types, got {total_types}"

        # Each configuration should be non-empty
        for obj_type, props in IDENTITY_PROPERTY_CONFIG.items():
            assert isinstance(
                props, list
            ), f"Properties for {obj_type} should be a list"
            assert len(props) > 0, f"Properties for {obj_type} should not be empty"


@pytest.fixture
def sample_generator_properties():
    """Fixture providing sample generator properties for testing."""
    return {
        "name": "Test Generator",
        "x_grid_component_type": ["generator"],
        "x_power_rating_mw": [100.0],
        "x_fuel_type": ["natural_gas"],
    }


@pytest.fixture
def sample_transformer_properties():
    """Fixture providing sample transformer properties for testing."""
    return {
        "name": "Test Transformer",
        "x_asset_id": ["TRANS-TEST"],
        "x_voltage_primary_kv": [138.0],
        "x_voltage_secondary_kv": [13.8],
        "x_power_rating_mva": [50.0],
    }


class TestWithFixtures:
    """Test class demonstrating pytest fixtures usage."""

    def test_generator_with_fixture(self, sample_generator_properties):
        """Test generator UUID generation using fixture."""
        uuid1 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-generator", sample_generator_properties
        )
        uuid2 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-generator", sample_generator_properties
        )

        assert uuid1 == uuid2
        assert uuid1.startswith("x-grid-generator--")

    def test_transformer_with_fixture(self, sample_transformer_properties):
        """Test transformer UUID generation using fixture."""
        uuid1 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-transformer", sample_transformer_properties
        )
        uuid2 = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-transformer", sample_transformer_properties
        )

        assert uuid1 == uuid2
        assert uuid1.startswith("x-grid-transformer--")

    def test_different_types_different_uuids(
        self, sample_generator_properties, sample_transformer_properties
    ):
        """Test that different object types produce different UUIDs using fixtures."""
        gen_uuid = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-generator", sample_generator_properties
        )
        trans_uuid = DeterministicUUIDGenerator.generate_uuid(
            "x-grid-transformer", sample_transformer_properties
        )

        assert gen_uuid != trans_uuid


if __name__ == "__main__":
    # Allow running with python directly for backwards compatibility
    pytest.main([__file__])
