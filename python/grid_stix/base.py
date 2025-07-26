"""
Grid-STIX Base Classes

This module provides base classes for all Grid-STIX objects that properly extend
the official STIX 2.1 library classes for grid-specific cybersecurity use cases.
"""

from __future__ import annotations

from typing import Optional, Any, Dict, List
from uuid import uuid4

from collections import OrderedDict

from stix2.v21 import _DomainObject, _RelationshipObject, _Observable  # type: ignore[import-untyped]
from stix2.properties import (  # type: ignore[import-untyped]
    StringProperty,
    IntegerProperty,
    BooleanProperty,
    FloatProperty,
    ListProperty,
    DictionaryProperty,
    TimestampProperty,
    IDProperty,
    TypeProperty,
)
from stix2.utils import NOW  # type: ignore[import-untyped]


class GridSTIXDomainObject(_DomainObject):  # type: ignore[misc]
    """
    Base class for Grid-STIX Domain Objects extending STIX 2.1 SDOs.

    This is an abstract base class. Concrete Grid-STIX classes should define
    their own _type and extend _properties appropriately.
    """

    # Base properties that all Grid-STIX domain objects should have
    # Concrete classes will extend this with their own _type and specific properties
    _base_properties = OrderedDict(
        [
            ("x_grid_context", DictionaryProperty()),
            ("x_operational_status", StringProperty()),
            ("x_compliance_framework", ListProperty(StringProperty)),
            ("x_grid_component_type", StringProperty()),
            ("x_criticality_level", IntegerProperty()),
        ]
    )


class GridSTIXRelationshipObject(_RelationshipObject):  # type: ignore[misc]
    """
    Base class for Grid-STIX Relationship Objects extending STIX 2.1 SROs.

    This is an abstract base class. Concrete Grid-STIX relationship classes
    should define their own _type and extend _properties appropriately.
    """

    # Base properties that all Grid-STIX relationship objects should have
    _base_properties = OrderedDict(
        [
            ("x_grid_relationship_context", DictionaryProperty()),
            ("x_physical_connection", BooleanProperty()),
            ("x_logical_connection", BooleanProperty()),
            ("x_power_flow_direction", StringProperty()),
        ]
    )


class GridSTIXObservableObject(_Observable):  # type: ignore[misc]
    """
    Base class for Grid-STIX Cyber Observable Objects extending STIX 2.1 SCOs.

    This is an abstract base class. Concrete Grid-STIX observable classes
    should define their own _type and extend _properties appropriately.
    """

    # Base properties that all Grid-STIX observable objects should have
    _base_properties = OrderedDict(
        [
            ("x_grid_measurement_type", StringProperty()),
            ("x_sensor_location", StringProperty()),
            ("x_measurement_unit", StringProperty()),
            ("x_sampling_rate", FloatProperty()),
        ]
    )
