"""
grid_stix.relationships - Generated Grid-STIX module

This module was automatically generated from the Grid-STIX ontology.
It contains Python classes corresponding to OWL classes in the ontology.
"""

# Import all classes from this module


from .AffectsOperationOfRelationship import AffectsOperationOfRelationship


from .AggregatesRelationship import AggregatesRelationship


from .AuthenticatesToRelationship import AuthenticatesToRelationship


from .ConnectsToRelationship import ConnectsToRelationship


from .ContainedInFacilityRelationship import ContainedInFacilityRelationship


from .ContainsRelationship import ContainsRelationship


from .ControlsRelationship import ControlsRelationship


from .ConvertsForRelationship import ConvertsForRelationship


from .DependsOnRelationship import DependsOnRelationship


from .FeedsPowerToRelationship import FeedsPowerToRelationship


from .FeedsRelationship import FeedsRelationship


from .GeneratesPowerForRelationship import GeneratesPowerForRelationship


from .GridRelationship import GridRelationship


from .HasVulnerabilityRelationship import HasVulnerabilityRelationship


from .IslandsFromRelationship import IslandsFromRelationship


from .LocatedAtRelationship import LocatedAtRelationship


from .MonitoredByEnvironmentalSensorRelationship import (
    MonitoredByEnvironmentalSensorRelationship,
)


from .MonitorsRelationship import MonitorsRelationship


from .ProducesWasteRelationship import ProducesWasteRelationship


from .ProtectsAssetRelationship import ProtectsAssetRelationship


from .ProtectsRelationship import ProtectsRelationship


from .SuppliedByRelationship import SuppliedByRelationship


from .TriggersRelationship import TriggersRelationship


from .UnionAllAssets import UnionAllAssets


from .UnionOTDeviceGridComponent import UnionOTDeviceGridComponent


from .UnionOTDeviceIdentity import UnionOTDeviceIdentity


from .UnionPhysicalAssetGridComponent import UnionPhysicalAssetGridComponent


from .UnionPhysicalAssetOTDevice import UnionPhysicalAssetOTDevice


from .UnionSecurityZoneLocation import UnionSecurityZoneLocation


from .UnionSecurityZoneOTDeviceCourseOfAction import (
    UnionSecurityZoneOTDeviceCourseOfAction,
)


from .WithinSecurityZoneRelationship import WithinSecurityZoneRelationship


# Resolve forward references


UnionAllAssets.model_rebuild()


UnionPhysicalAssetGridComponent.model_rebuild()


# Public API
__all__ = [
    "AffectsOperationOfRelationship",
    "AggregatesRelationship",
    "AuthenticatesToRelationship",
    "ConnectsToRelationship",
    "ContainedInFacilityRelationship",
    "ContainsRelationship",
    "ControlsRelationship",
    "ConvertsForRelationship",
    "DependsOnRelationship",
    "FeedsPowerToRelationship",
    "FeedsRelationship",
    "GeneratesPowerForRelationship",
    "GridRelationship",
    "HasVulnerabilityRelationship",
    "IslandsFromRelationship",
    "LocatedAtRelationship",
    "MonitoredByEnvironmentalSensorRelationship",
    "MonitorsRelationship",
    "ProducesWasteRelationship",
    "ProtectsAssetRelationship",
    "ProtectsRelationship",
    "SuppliedByRelationship",
    "TriggersRelationship",
    "UnionAllAssets",
    "UnionOTDeviceGridComponent",
    "UnionOTDeviceIdentity",
    "UnionPhysicalAssetGridComponent",
    "UnionPhysicalAssetOTDevice",
    "UnionSecurityZoneLocation",
    "UnionSecurityZoneOTDeviceCourseOfAction",
    "WithinSecurityZoneRelationship",
]
