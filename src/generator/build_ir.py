"""
Grid-STIX Intermediate Representation Builder

This module extracts ontology information and builds an intermediate representation (IR)
suitable for code generation. It serves as Stage 2 of the Grid-STIX code generation pipeline.

Features:
- Class Extraction:
  • Extract OWL classes with inheritance hierarchies
  • Handle multiple inheritance and mixin patterns
  • Support for abstract and concrete class distinctions
  • Namespace-based module mapping
- Property Analysis:
  • Object and data property extraction
  • Cardinality constraint detection (exactly, some, min/max)
  • Range and domain analysis
  • Functional and inverse property identification
- Constraint Processing:
  • OWL restriction processing (someValuesFrom, allValuesFrom, hasValue)
  • Union and intersection class handling
  • Enumeration and datatype restrictions
- Module Organization:
  • Namespace to Python package mapping
  • Configurable consolidation rules
  • Forward reference detection preparation

Use Cases:
- Convert OWL ontologies to structured Python class definitions
- Preserve semantic relationships in generated code
- Support complex inheritance patterns from ontologies
- Generate type-safe property definitions with constraints
- Enable modular code organization based on ontology structure
"""

import logging
import re

from dataclasses import dataclass, field
from typing import Any, Optional

import owlready2
import yaml
from owlready2 import World


logger = logging.getLogger(__name__)


@dataclass
class AttrDef:
    """Definition of a class attribute/property."""

    name: str
    range: str
    mult: str  # "1" | "+" | "*" | "?"
    forward_ref: bool = False
    description: Optional[str] = None
    functional: bool = False
    inverse_of: Optional[str] = None


@dataclass
class ClassDef:
    """Definition of a generated Python class."""

    name: str
    bases: list[str]
    module: str
    attrs: list[AttrDef]
    annotations: dict[str, Any] = field(default_factory=dict)
    is_abstract: bool = False
    description: Optional[str] = None
    namespace_iri: Optional[str] = None
    owl_fragment: Optional[str] = (
        None  # Original OWL fragment name (e.g., "photovoltaic-system")
    )


@dataclass
class IntermediateRepresentation:
    """Complete intermediate representation of the ontology."""

    classes: dict[str, ClassDef]
    namespaces: dict[str, str]  # IRI -> module mapping
    imports: dict[str, set[str]]  # module -> set of imported types
    special_handlers: dict[str, str]  # pattern -> handler function


class IRBuilderError(Exception):
    """Raised when IR building fails."""

    pass


class IRBuilder:
    """Builds intermediate representation from loaded ontology."""

    def __init__(self, config_path: str):
        """
        Initialize IR builder with configuration.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config = self._load_config(config_path)
        self.namespaces = self.config.get("namespaces", {})
        self.special_classes = self.config.get("special_classes", {})
        self.reserved_suffix = self.config.get("reserved_suffix", "_cls")

    def build_ir(self, world: World) -> IntermediateRepresentation:
        """
        Build intermediate representation from ontology world.

        Args:
            world: Owlready2 World containing loaded ontology

        Returns:
            IntermediateRepresentation: Complete IR for code generation

        Raises:
            IRBuilderError: If IR building fails
        """
        logger.info("Building intermediate representation...")

        try:
            with world:
                # Extract all relevant entities
                classes = self._extract_classes(world)

                # Build class definitions
                class_defs = {}
                for cls in classes:
                    logger.debug(f"Building class definition for: {cls.name}")
                    class_def = self._build_class_def(cls, world)
                    if class_def:
                        class_defs[class_def.name] = class_def
                        logger.debug(
                            f"Successfully built class definition for: {class_def.name}"
                        )
                    else:
                        logger.warning(
                            f"Failed to build class definition for: {cls.name}"
                        )

                # Analyze imports and dependencies
                imports = self._analyze_imports(class_defs)

                ir = IntermediateRepresentation(
                    classes=class_defs,
                    namespaces=self.namespaces,
                    imports=imports,
                    special_handlers=self.special_classes,
                )

                logger.info(f"Built IR with {len(class_defs)} class definitions")
                return ir

        except Exception as e:
            raise IRBuilderError(f"Failed to build IR: {e}") from e

    def _load_config(self, config_path: str) -> dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise IRBuilderError(
                f"Failed to load config from {config_path}: {e}"
            ) from e

    def _extract_classes(self, world: World) -> list[owlready2.ThingClass]:
        """Extract relevant OWL classes for code generation."""
        all_classes = []

        # Debug: log all found namespaces
        found_namespaces = set()
        class_iris = set()

        # Get classes from the primary ontology stored by the loader
        with world:
            all_world_classes = []

            # Try to use the primary ontology stored by the loader
            if hasattr(world, "_grid_stix_primary_ontology"):
                primary_ontology = world._grid_stix_primary_ontology
                all_world_classes = list(primary_ontology.classes())
                logger.debug(
                    f"Using primary ontology {primary_ontology.base_iri} with {len(all_world_classes)} classes"
                )
            else:
                # Fallback: get classes from ALL ontologies in the world
                logger.debug("No primary ontology found, searching all ontologies")
                for ontology in world.ontologies.values():
                    classes_in_ont = list(ontology.classes())
                    logger.debug(
                        f"Ontology {ontology.base_iri} has {len(classes_in_ont)} classes"
                    )
                    all_world_classes.extend(classes_in_ont)

                logger.debug(
                    f"Found {len(all_world_classes)} total classes across all ontologies"
                )

            for cls in all_world_classes:
                # Use the class IRI to determine namespace, not the ontology
                class_iri = str(cls.iri)
                class_iris.add(class_iri)
                logger.debug(f"Processing class: {cls.name} with IRI: {class_iri}")

                # Extract namespace from class IRI
                namespace_iri = None
                for configured_namespace in self.namespaces.keys():
                    if class_iri.startswith(configured_namespace):
                        namespace_iri = configured_namespace
                        break

                if namespace_iri:
                    found_namespaces.add(namespace_iri)
                    target_module = self.namespaces[namespace_iri]
                    if target_module != "stix2":  # Don't generate STIX classes
                        all_classes.append(cls)
                        logger.debug(
                            f"Adding class {cls.name} from IRI {class_iri} -> namespace {namespace_iri}"
                        )
                else:
                    # Check the actual namespace as fallback
                    fallback_namespace = cls.namespace.base_iri
                    found_namespaces.add(fallback_namespace)
                    logger.debug(
                        f"Class {cls.name} has fallback namespace: {fallback_namespace}"
                    )
                    if fallback_namespace in self.namespaces:
                        target_module = self.namespaces[fallback_namespace]
                        if target_module != "stix2":
                            all_classes.append(cls)
                            logger.debug(
                                f"Adding class {cls.name} from fallback namespace {fallback_namespace}"
                            )

        logger.info(f"Found namespaces in ontology: {sorted(found_namespaces)}")
        logger.info(f"Sample class IRIs: {sorted(list(class_iris))[:10]}")
        logger.info(f"Configured namespaces: {list(self.namespaces.keys())}")
        logger.info(f"Found {len(all_classes)} classes to generate")
        return all_classes

    def _build_class_def(
        self, cls: owlready2.ThingClass, world: World
    ) -> Optional[ClassDef]:
        """Build ClassDef from OWL class."""
        try:
            # Get class name and handle reserved words
            class_name = self._sanitize_class_name(cls.name)

            # Validate class name is not empty
            if not class_name or not class_name.strip():
                logger.warning(f"Skipping class with empty name: {cls}")
                return None

            # Determine module from namespace using same logic as extraction
            class_iri = str(cls.iri)
            namespace_iri = None

            # First try to match against configured namespaces by IRI prefix
            for configured_namespace in self.namespaces.keys():
                if class_iri.startswith(configured_namespace):
                    namespace_iri = configured_namespace
                    break

            # Fallback to using the class namespace
            if not namespace_iri:
                namespace_iri = cls.namespace.base_iri

            logger.debug(
                f"Class {class_name} with IRI {class_iri} has namespace IRI: {namespace_iri}"
            )
            module = self._get_module_for_namespace(namespace_iri)
            logger.debug(f"Module mapping for {namespace_iri}: {module}")
            if not module:
                logger.warning(f"No module mapping for namespace: {namespace_iri}")
                return None

            # Extract base classes
            bases = self._extract_base_classes(cls)

            # Extract properties/attributes
            attrs = self._extract_attributes(cls, world)

            # Extract description/annotation
            description = self._extract_description(cls)

            # Check if abstract (has no direct instances)
            is_abstract = (
                len(list(cls.instances())) == 0 and len(list(cls.subclasses())) > 0
            )

            # Extract OWL fragment name from IRI (part after #)
            owl_fragment = None
            logger.debug(f"Attempting to extract OWL fragment from IRI: {class_iri}")
            if "#" in class_iri:
                owl_fragment = class_iri.split("#")[-1]
                logger.info(
                    f"Extracted OWL fragment '{owl_fragment}' for class {class_name} from IRI {class_iri}"
                )
            else:
                logger.warning(
                    f"No '#' found in IRI for class {class_name}: {class_iri}"
                )

            return ClassDef(
                name=class_name,
                bases=bases,
                module=module,
                attrs=attrs,
                is_abstract=is_abstract,
                description=description,
                namespace_iri=namespace_iri,
                owl_fragment=owl_fragment,
            )

        except Exception as e:
            logger.error(f"Failed to build class definition for {cls}: {e}")
            return None

    def _sanitize_class_name(self, name: str) -> str:
        """Sanitize class name for Python."""
        # Handle empty or whitespace-only names
        if not name or not name.strip():
            return ""

        name = name.strip()

        # Handle specific known compound words first
        compound_words = {
            "renewablegenerationfacility": "RenewableGenerationFacility",
            "electricvehicle": "ElectricVehicle",
            "gridcomponent": "GridComponent",
            "controlcenter": "ControlCenter",
            "dercommunicationinterface": "DerCommunicationInterface",
            "distributionline": "DistributionLine",
            "electronicsecurityperimeter": "ElectronicSecurityPerimeter",
            "operationalgridentity": "OperationalGridEntity",
            "physicalasset": "PhysicalAsset",
            "physicalgridasset": "PhysicalGridAsset",
            "physicalsecurityperimeter": "PhysicalSecurityPerimeter",
            "securityzone": "SecurityZone",
            "supplychainrisk": "SupplyChainRisk",
            "transmissionline": "TransmissionLine",
        }

        # Check for exact match (case insensitive)
        name_lower = name.lower()
        if name_lower in compound_words:
            return compound_words[name_lower]

        # Convert to PascalCase properly
        # Split on hyphens, underscores, and spaces, then capitalize each part
        parts = re.split(r"[-_\s]+", name)

        # If no delimiters found, try to split camelCase
        if len(parts) == 1 and len(name) > 1:
            # Split on capital letters (but keep them)
            parts = re.findall(r"[A-Z]?[a-z]*|[A-Z]+(?=[A-Z][a-z]|\b)", name)
            if not parts:  # If regex didn't match, use the original name
                parts = [name]

        clean_name = "".join(part.capitalize() for part in parts if part)

        # Handle common abbreviations (whole word replacements)
        replacements = {
            "Ot": "OT",
            "It": "IT",
            "Ai": "AI",
            "Ml": "ML",
            "Hmi": "HMI",
            "Plc": "PLC",
            "Rtu": "RTU",
            "Ied": "IED",
            "Otdevice": "OTDevice",
            "Itdevice": "ITDevice",
        }
        for old, new in replacements.items():
            clean_name = clean_name.replace(old, new)

        # Handle Python reserved words
        if clean_name.lower() in {
            "class",
            "def",
            "if",
            "else",
            "for",
            "while",
            "import",
            "from",
        }:
            clean_name += self.reserved_suffix

        return clean_name

    def _get_module_for_namespace(self, namespace_iri: str) -> Optional[str]:
        """Get Python module path for namespace IRI."""
        return self.namespaces.get(namespace_iri)

    def _extract_base_classes(self, cls: owlready2.ThingClass) -> list[str]:
        """Extract base class names."""
        bases = []

        for parent in cls.is_a:
            if isinstance(parent, owlready2.ThingClass):
                # Check if parent should be generated or imported
                parent_namespace = parent.namespace.base_iri
                if parent_namespace in self.namespaces:
                    parent_name = self._sanitize_class_name(parent.name)
                    # Filter out empty parent names
                    if parent_name and parent_name.strip():
                        bases.append(parent_name)
                    else:
                        logger.debug(f"Skipping empty parent name for class {cls.name}")

        # Default to appropriate Grid-STIX base class if no bases found
        if not bases:
            base_class = self._determine_appropriate_base_class(cls)
            bases = [base_class]

        return bases

    def _determine_appropriate_base_class(self, cls: owlready2.ThingClass) -> str:
        """Determine the most appropriate base class based on ontology class characteristics."""
        class_name = cls.name.lower()

        # Relationship objects
        if "relationship" in class_name:
            return "GridSTIXRelationshipObject"

        # Observable objects (events, telemetry, etc.)
        if any(
            term in class_name
            for term in ["event", "telemetry", "traffic", "observable"]
        ):
            return "GridSTIXObservableObject"

        # Domain objects (most classes fall here)
        return "GridSTIXDomainObject"

    def _extract_attributes(
        self, cls: owlready2.ThingClass, world: World
    ) -> list[AttrDef]:
        """Extract property attributes for class."""
        attrs = []

        # Get properties from the primary ontology, not the world
        if hasattr(world, "_grid_stix_primary_ontology"):
            ontology = world._grid_stix_primary_ontology

            # Get all properties that have this class in their domain
            for prop in ontology.object_properties():
                if cls in prop.domain:
                    attr_def = self._build_attr_def(prop, world)
                    if attr_def:
                        attrs.append(attr_def)
                        logger.debug(
                            f"Added object property {prop.name} to class {cls.name}"
                        )

            for prop in ontology.data_properties():
                if cls in prop.domain:
                    attr_def = self._build_attr_def(prop, world)
                    if attr_def:
                        attrs.append(attr_def)
                        logger.debug(
                            f"Added data property {prop.name} to class {cls.name}"
                        )
        else:
            # Fallback to world properties
            for prop in world.object_properties():
                if cls in prop.domain:
                    attr_def = self._build_attr_def(prop, world)
                    if attr_def:
                        attrs.append(attr_def)

            for prop in world.data_properties():
                if cls in prop.domain:
                    attr_def = self._build_attr_def(prop, world)
                    if attr_def:
                        attrs.append(attr_def)

        # Also check for restrictions in is_a
        for restriction in cls.is_a:
            if isinstance(restriction, owlready2.Restriction):
                attr_def = self._build_attr_from_restriction(restriction)
                if attr_def:
                    attrs.append(attr_def)
                    logger.debug(
                        f"Added restriction-based property to class {cls.name}"
                    )

        logger.debug(f"Extracted {len(attrs)} attributes for class {cls.name}")
        return attrs

    def _build_attr_def(
        self, prop: owlready2.Property, world: World
    ) -> Optional[AttrDef]:
        """Build AttrDef from OWL property."""
        try:
            # Get property name
            attr_name = self._sanitize_attr_name(prop.name)

            # Determine range/type
            range_type = self._determine_range_type(prop)

            # Determine multiplicity
            mult = self._determine_multiplicity(prop)

            # Check if functional
            functional = isinstance(prop, owlready2.FunctionalProperty)

            # Get inverse
            inverse_of = None
            if hasattr(prop, "inverse_property") and prop.inverse_property:
                inverse_of = self._sanitize_attr_name(prop.inverse_property.name)

            # Get description
            description = self._extract_description(prop)

            return AttrDef(
                name=attr_name,
                range=range_type,
                mult=mult,
                functional=functional,
                inverse_of=inverse_of,
                description=description,
            )

        except Exception as e:
            logger.error(f"Failed to build attribute definition for {prop}: {e}")
            return None

    def _build_attr_from_restriction(
        self, restriction: owlready2.Restriction
    ) -> Optional[AttrDef]:
        """Build AttrDef from OWL restriction."""
        try:
            prop = restriction.property
            attr_name = self._sanitize_attr_name(prop.name)

            # Handle different restriction types
            if hasattr(restriction, "value"):
                # hasValue restriction
                range_type = "Any"  # Specific value
                mult = "1"
            elif hasattr(restriction, "some"):
                # someValuesFrom restriction
                range_type = self._get_class_name_from_entity(restriction.some)
                mult = "+"
            elif hasattr(restriction, "all"):
                # allValuesFrom restriction
                range_type = self._get_class_name_from_entity(restriction.all)
                mult = "*"
            elif hasattr(restriction, "exactly"):
                # exact cardinality
                range_type = self._determine_range_type(prop)
                mult = "1" if restriction.exactly == 1 else "+"
            elif hasattr(restriction, "min"):
                # min cardinality
                range_type = self._determine_range_type(prop)
                mult = "+" if restriction.min > 0 else "*"
            elif hasattr(restriction, "max"):
                # max cardinality
                range_type = self._determine_range_type(prop)
                mult = "?" if restriction.max == 1 else "*"
            else:
                # Generic restriction
                range_type = self._determine_range_type(prop)
                mult = "*"

            return AttrDef(name=attr_name, range=range_type, mult=mult)

        except Exception as e:
            logger.error(
                f"Failed to build attribute from restriction {restriction}: {e}"
            )
            return None

    def _sanitize_attr_name(self, name: str) -> str:
        """Sanitize attribute name for Python."""
        # Convert to snake_case
        clean_name = re.sub(r"[- ]+", "_", name).lower()

        # Handle Python reserved words
        if clean_name in {
            "class",
            "def",
            "if",
            "else",
            "for",
            "while",
            "import",
            "from",
            "type",
        }:
            clean_name += "_attr"

        return clean_name

    def _determine_range_type(self, prop: owlready2.Property) -> str:
        """Determine Python type for property range."""
        # Check explicit range
        if prop.range:
            if len(prop.range) == 1:
                range_entity = prop.range[0]
                return self._get_class_name_from_entity(range_entity)
            elif len(prop.range) > 1:
                # Union type - for now just use the first one
                return self._get_class_name_from_entity(prop.range[0])

        # Default based on property type
        if isinstance(prop, owlready2.ObjectProperty):
            return "Any"
        elif isinstance(prop, owlready2.DataProperty):
            return "str"  # Default to string for data properties

        return "Any"

    def _get_class_name_from_entity(self, entity) -> str:
        """Get Python class name from OWL entity."""
        name = None

        # Try to get name from entity
        if hasattr(entity, "name") and entity.name is not None:
            name = str(entity.name)
        elif hasattr(entity, "__name__") and entity.__name__ is not None:
            name = str(entity.__name__)
        else:
            return "Any"

        # Handle basic Python data types - don't capitalize these
        basic_types = {
            "str",
            "int",
            "float",
            "bool",
            "bytes",
            "list",
            "dict",
            "set",
            "tuple",
            "string",
            "integer",
            "float",
            "double",
            "boolean",
        }

        # Check if this is a basic data type (case insensitive)
        name_lower = name.lower()
        for basic_type in basic_types:
            if name_lower == basic_type:
                # Map some OWL types to Python types
                type_mapping = {
                    "string": "str",
                    "integer": "int",
                    "double": "float",
                    "boolean": "bool",
                }
                return type_mapping.get(name_lower, name_lower)

        # For other entities, sanitize as class names
        return self._sanitize_class_name(name)

    def _determine_multiplicity(self, prop: owlready2.Property) -> str:
        """Determine multiplicity constraint for property."""
        # Check if functional (at most one value)
        if isinstance(prop, owlready2.FunctionalProperty):
            return "?"  # Optional single value

        # Default to many values allowed
        return "*"

    def _extract_description(self, entity) -> Optional[str]:
        """Extract description/comment from OWL entity."""
        # Check for rdfs:comment
        if hasattr(entity, "comment") and entity.comment:
            if isinstance(entity.comment, list) and entity.comment:
                return str(entity.comment[0])
            else:
                return str(entity.comment)

        # Check for rdfs:label as fallback
        if hasattr(entity, "label") and entity.label:
            if isinstance(entity.label, list) and entity.label:
                return str(entity.label[0])
            else:
                return str(entity.label)

        return None

    def _analyze_imports(self, class_defs: dict[str, ClassDef]) -> dict[str, set[str]]:
        """Analyze import dependencies between modules."""
        imports = {}

        for class_def in class_defs.values():
            module = class_def.module
            if module not in imports:
                imports[module] = set()

            # Add imports for base classes
            for base in class_def.bases:
                if base != "BaseModel":  # Skip Pydantic base
                    # Find which module this base class is in
                    for other_class in class_defs.values():
                        if other_class.name == base and other_class.module != module:
                            imports[module].add(base)
                            break

            # Add imports for attribute types
            for attr in class_def.attrs:
                if attr.range != "Any" and attr.range in class_defs:
                    target_class = class_defs[attr.range]
                    if target_class.module != module:
                        imports[module].add(attr.range)

        return imports
