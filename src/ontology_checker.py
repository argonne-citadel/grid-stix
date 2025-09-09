from rdflib import Graph, RDF, RDFS, OWL, URIRef, BNode, Namespace
from collections import defaultdict
from networkx import DiGraph, strongly_connected_components
import logging
import re
import sys
import os
import argparse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Naming convention patterns
# URI patterns (rdf:about) - should use hyphens (kebab-case)
CLASS_URI_PATTERN = r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
PROPERTY_URI_PATTERN = r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"

# Label patterns (rdfs:label) - should use underscores (snake_case)
LABEL_PATTERN = r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"

# Legacy technical pattern for backwards compatibility
TECHNICAL_NAMING_PATTERN = r"^[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*$"


# ---- ARGUMENT PARSING ----
def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate an OWL ontology for common issues."
    )
    parser.add_argument(
        "--owl-file",
        default="root/grid-stix-2.1-root.owl",
        help="Path to the main OWL file",
    )
    parser.add_argument(
        "--base-namespace",
        default="http://www.anl.gov/sss/",
        help="Base namespace for the ontology",
    )
    parser.add_argument(
        "--catalog", default="catalog.xml", help="Path to catalog.xml for imports"
    )
    parser.add_argument(
        "--skip-checks",
        nargs="+",
        default=[],
        help='List of check types to skip (e.g., "missing_inverses unreachable uri_naming label_naming")',
    )
    return parser.parse_args()


# ---- CONFIGURATION ----
# Default values for when imported as module
OWL_FILE = "root/grid-stix-2.1-root.owl"
BASE_NAMESPACE = "http://www.anl.gov/sss/"
CATALOG_FILE = "catalog.xml"
SKIP_CHECKS = []

# Define common STIX namespaces
STIX_NAMESPACES = [
    "http://docs.oasis-open.org/ns/cti/stix",  # STIX 2.1 namespace
    "http://docs.oasis-open.org/cti/ns/stix/",  # Alternative STIX namespace
    "http://stixschema.org/v21",  # STIX 2.1 objects schema
]

# Define correct STIX class patterns
STIX_CORE_CLASSES = [
    "Infrastructure",
    "Software",
    "Location",
    "Identity",
    "Relationship",
    "DomainObject",
    "CyberObservable",
    "CourseOfAction",
    "AttackPattern",
    "Vulnerability",
    "Malware",
    "Tool",
    "Indicator",
    "Campaign",
]

# ---- LOAD CATALOG ----
import_mappings = {}
if os.path.exists(CATALOG_FILE):
    try:
        logging.info(f"Loading import mappings from catalog: {CATALOG_FILE}")
        catalog_tree = ET.parse(
            CATALOG_FILE
        )  # nosec B314 - parsing trusted local catalog.xml file
        catalog_root = catalog_tree.getroot()

        # Get the namespace for the catalog XML
        ns = {}
        if catalog_root.tag.startswith("{"):
            ns_uri = catalog_root.tag[1:].split("}", 1)[0]
            ns["cat"] = ns_uri

        # Process URI mappings from catalog
        for mapping in (
            catalog_root.findall(".//cat:uri", ns)
            if ns
            else catalog_root.findall(".//uri")
        ):
            name_attribute = mapping.get(
                "name"
            )  # This is the URI used in owl:imports statements
            uri_attribute = mapping.get(
                "uri"
            )  # This is the catalog's path to the local file

            if name_attribute and uri_attribute:
                # Start with the URI attribute from the catalog to derive the local file path
                local_file_path_str = uri_attribute

                # Remove "file:" prefix if present
                if local_file_path_str.startswith("file:"):
                    local_file_path_str = local_file_path_str[5:]

                # Remove fragment identifier to get a clean file path for file system operations.
                # The name_attribute (the key for import_mappings) retains its fragment if it has one.
                clean_file_path = local_file_path_str.split("#", 1)[0]

                import_mappings[name_attribute] = clean_file_path
                logging.debug(
                    f"Mapped import URI '{name_attribute}' → to local file path '{clean_file_path}'"
                )
    except Exception as e:
        logging.info(f"Warning: Error parsing catalog file: {e}")
else:
    logging.info(f"Catalog file not found: {CATALOG_FILE}")

# ---- LOAD ONTOLOGY ----
g = Graph()
processed_imports = set()  # Keep track of processed import URIs

# Parse main ontology file
logging.info(f"Loading main ontology: {OWL_FILE}")
try:
    g.parse(OWL_FILE, format="xml")
    # Add the main OWL file's URI to processed_imports if it's a resolvable URI
    # For now, we assume OWL_FILE is a local path and its corresponding URI might be in import_mappings
    # or it's the base URI of the ontology itself.
    # A more robust way would be to get the ontology's URI from its declaration if present.
except Exception as e:
    logging.info(f"FATAL: Error parsing main ontology file {OWL_FILE}: {e}")
    sys.exit(1)


# Use a queue to manage imports
imports_to_process = list(g.objects(None, OWL.imports))
import_count = 0

if imports_to_process:
    logging.info(
        f"Found {len(imports_to_process)} initial owl:imports statements from {OWL_FILE}"
    )

while imports_to_process:
    import_uri = imports_to_process.pop(0)  # Get the next URI to process
    uri_str = str(import_uri)

    if uri_str in processed_imports:
        logging.debug(f"Skipping already processed import: {uri_str}")
        continue

    logging.debug(f"Processing import: {uri_str}")
    processed_imports.add(uri_str)
    import_count += 1

    try:
        # uri_str is the URI from the owl:imports statement (e.g., http://stixschema.org/v21#Identity)
        # local_path_from_catalog will be the clean file system path.
        local_path_from_catalog = None
        if uri_str in import_mappings:
            local_path_from_catalog = import_mappings[uri_str]
        else:
            # Fallback: if uri_str has a fragment, try looking up its base URI.
            uri_base = uri_str.split("#", 1)[0]
            if uri_base != uri_str and uri_base in import_mappings:
                local_path_from_catalog = import_mappings[uri_base]
                logging.debug(
                    f"Used base URI '{uri_base}' from catalog for import '{uri_str}'"
                )

        if (
            local_path_from_catalog
        ):  # This path is already cleaned by catalog loading logic
            if os.path.exists(local_path_from_catalog):
                logging.info(
                    f"Loading import ({import_count}): {uri_str} → {local_path_from_catalog}"
                )
                try:
                    # Use uri_str (the original import URI) as publicID.
                    # This helps rdflib associate the loaded triples with the correct import URI context.
                    g.parse(local_path_from_catalog, publicID=uri_str, format="xml")

                    # After parsing, find new imports declared anywhere in the graph
                    all_current_imports_in_graph = list(g.objects(None, OWL.imports))

                    for new_imp_uri_node in all_current_imports_in_graph:
                        new_imp_uri_str = str(new_imp_uri_node)
                        if (
                            new_imp_uri_str not in processed_imports
                            and new_imp_uri_node not in imports_to_process
                        ):
                            imports_to_process.append(new_imp_uri_node)
                            logging.debug(
                                f"Queued new import discovered: {new_imp_uri_str}"
                            )
                except Exception as e_parse:
                    logging.info(
                        f"Warning: Error parsing imported file {local_path_from_catalog} (from {uri_str}): {e_parse}"
                    )
            else:
                logging.info(
                    f"Warning: Import file not found: {local_path_from_catalog} (mapped from {uri_str})"
                )
        else:
            # Attempt to parse directly if it's a URL and not in mappings (rdflib might handle it)
            if uri_str.startswith("http://") or uri_str.startswith("https://"):
                logging.info(f"Attempting to load unmapped URI directly: {uri_str}")
                try:
                    g.parse(uri_str, format="xml")  # Or try to infer format
                    # Check for new imports from this directly loaded URI
                    all_current_imports_in_graph = list(g.objects(None, OWL.imports))
                    for new_imp_uri in all_current_imports_in_graph:
                        if (
                            str(new_imp_uri) not in processed_imports
                            and new_imp_uri not in imports_to_process
                        ):
                            imports_to_process.append(new_imp_uri)
                            logging.debug(
                                f"Queued new import discovered from direct load: {new_imp_uri}"
                            )
                except Exception as e_direct_parse:
                    logging.info(
                        f"Warning: Could not load unmapped URI {uri_str} directly: {e_direct_parse}"
                    )
            else:
                logging.info(
                    f"Warning: No catalog mapping for {uri_str} and it's not a recognized URL."
                )
    except Exception as e:
        logging.info(f"Error processing import {uri_str}: {e}")

if import_count > 0:
    logging.info(f"Finished processing {import_count} import(s) recursively.")
else:
    logging.info("No owl:imports statements were processed.")

# Print stats about loaded ontology
logging.info(f"Loaded {len(g)} triples")
logging.info(f"Found {len(list(g.subjects(RDF.type, OWL.Class)))} classes")
logging.info(
    f"Found {len(list(g.subjects(RDF.type, OWL.ObjectProperty)))} object properties"
)

# Log import URIs to help debugging
logging.debug("Import URIs in graph:")
for s, o in g.subject_objects(OWL.imports):
    logging.debug(f"  {s} imports {o}")

logging.debug("Classes directly inheriting from owl:Thing:")
for s in g.subjects(RDFS.subClassOf, OWL.Thing):
    logging.debug(f"  {s}")

logging.debug("Namespaces in graph:")
namespaces: Set[str] = set()
for s, p, o in g:
    if isinstance(s, URIRef):
        ns_uri = (
            str(s).split("#")[0] if "#" in str(s) else str(s).rsplit("/", 1)[0] + "/"
        )
        namespaces.add(ns_uri)
for namespace in sorted(namespaces):
    logging.debug(f"  {namespace}")


# ---- FILTER FUNCTION ----
def in_namespace(uri: Union[URIRef, str], include_imports: bool = False) -> bool:
    """Check if URI is in the ontology's namespace or other included namespaces

    Args:
        uri: The URI to check
        include_imports: Whether to include imported ontologies in the check
    """
    if not isinstance(uri, URIRef):
        return False
    uri_str = str(uri)

    # Always include entities in our primary namespace
    if uri_str.startswith(BASE_NAMESPACE):
        return True

    # For imported URIs
    if include_imports:
        # Include STIX entities
        for stix_ns in STIX_NAMESPACES:
            if uri_str.startswith(stix_ns):
                return True

        # Include entities from explicitly imported ontologies
        for import_uri in import_mappings.keys():
            if uri_str.startswith(import_uri.split("#")[0]):
                return True

    return False


# ---- STIX 2.1 SPECIFIC CHECK FUNCTIONS ----


def check_stix_inheritance_compliance(graph: Graph) -> List[str]:
    """Check that all custom classes properly inherit from STIX base classes"""
    non_compliant_classes = []

    # Get all classes in our namespace
    custom_classes = set(
        s
        for s in graph.subjects(RDF.type, OWL.Class)
        if in_namespace(s)
        and not str(s).endswith("_ov")
        and "Union_" not in str(s)  # Legacy Union_ classes
        and "union-" not in str(s)  # Grid-STIX union- classes (kebab-case)
    )

    for cls in custom_classes:
        # Check if this class has proper STIX inheritance
        has_stix_ancestor = False
        visited = set()

        def check_stix_lineage(current_class: URIRef) -> bool:
            if current_class in visited:
                return False
            visited.add(current_class)

            # Check if current class is a STIX class
            cls_str = str(current_class)
            for stix_ns in STIX_NAMESPACES:
                if cls_str.startswith(stix_ns):
                    return True

            # Check if inherits from owl:Thing (acceptable for some cases)
            if current_class == OWL.Thing:
                return True

            # Traverse up the inheritance hierarchy
            for super_class in graph.objects(current_class, RDFS.subClassOf):
                if isinstance(super_class, URIRef):
                    if check_stix_lineage(super_class):
                        return True
            return False

        if not check_stix_lineage(cls):
            non_compliant_classes.append(str(cls))

    return non_compliant_classes


def check_stix_namespace_consistency(graph: Graph) -> List[str]:
    """Check that STIX references use correct namespace format"""
    incorrect_references = []

    # Look for incorrect STIX namespace patterns
    # The current STIX namespace format is correct: http://docs.oasis-open.org/ns/cti/stix/infrastructure
    # We're looking for patterns that don't follow the standard STIX 2.1 format
    for s, p, o in graph:
        for obj in [s, o]:
            if isinstance(obj, URIRef):
                obj_str = str(obj)
                # Check for malformed STIX namespace patterns
                # Current format is correct, so this check should be very restrictive
                # Only flag truly malformed patterns
                if "stix" in obj_str.lower() and obj_str.startswith(
                    "http://docs.oasis-open.org/ns/cti/"
                ):
                    # Check for specific malformed patterns that would be problematic
                    if "/stix/stix/" in obj_str or obj_str.endswith("/stix/"):
                        incorrect_references.append(obj_str)

    return list(set(incorrect_references))


def check_stix_property_patterns(graph: Graph) -> List[str]:
    """Check that custom properties follow Grid-STIX naming conventions (kebab-case URIs)"""
    non_compliant_properties = []

    for prop_type in [OWL.ObjectProperty, OWL.DatatypeProperty]:
        for prop in graph.subjects(RDF.type, prop_type):
            if in_namespace(prop):
                prop_str = str(prop)
                # Extract property name from URI
                if "#" in prop_str:
                    prop_name = prop_str.split("#")[-1]
                elif "/" in prop_str:
                    prop_name = prop_str.split("/")[-1]
                else:
                    continue

                # Check naming convention (should follow kebab-case for Grid-STIX property URIs)
                if not re.match(PROPERTY_URI_PATTERN, prop_name):
                    non_compliant_properties.append(prop_str)

    return non_compliant_properties


def check_stix_relationship_compliance(graph: Graph) -> List[str]:
    """Check that custom relationships properly inherit from stix:Relationship"""
    non_compliant_relationships = []

    # Find all relationship classes in our namespace
    for cls in graph.subjects(RDF.type, OWL.Class):
        if in_namespace(cls) and "Relationship" in str(cls):
            # Check if it inherits from STIX Relationship
            has_stix_relationship_ancestor = False
            visited = set()

            def check_relationship_lineage(current_class: URIRef) -> bool:
                if current_class in visited:
                    return False
                visited.add(current_class)

                cls_str = str(current_class)
                if "stix" in cls_str.lower() and "relationship" in cls_str.lower():
                    return True

                for super_class in graph.objects(current_class, RDFS.subClassOf):
                    if isinstance(super_class, URIRef):
                        if check_relationship_lineage(super_class):
                            return True
                return False

            if not check_relationship_lineage(cls):
                non_compliant_relationships.append(str(cls))

    return non_compliant_relationships


def check_stix_vocabulary_compliance(graph: Graph) -> List[str]:
    """Check that vocabularies follow STIX patterns"""
    non_compliant_vocabularies = []

    # Check for vocabulary classes
    for cls in graph.subjects(RDF.type, OWL.Class):
        if in_namespace(cls):
            cls_str = str(cls)
            # Extract class name
            if "#" in cls_str:
                cls_name = cls_str.split("#")[-1]
            elif "/" in cls_str:
                cls_name = cls_str.split("/")[-1]
            else:
                continue

            # Check if it's a vocabulary class
            if cls_name.endswith("_ov"):
                # Check that it has proper vocabulary individuals
                has_individuals = False
                for individual in graph.subjects(RDF.type, cls):
                    if isinstance(individual, URIRef):
                        has_individuals = True
                        break

                if not has_individuals:
                    non_compliant_vocabularies.append(
                        f"{cls_str} (no individuals found)"
                    )

    return non_compliant_vocabularies


def check_stix_required_properties(graph: Graph) -> List[str]:
    """Check that STIX relationships have required source_ref and target_ref restrictions"""
    missing_restrictions = []

    # Check relationship classes for proper restrictions
    for cls in graph.subjects(RDF.type, OWL.Class):
        if in_namespace(cls) and "Relationship" in str(cls):
            cls_str = str(cls)

            # Check for source_ref and target_ref restrictions
            has_source_ref = False
            has_target_ref = False

            # Look for restriction patterns
            for restriction in graph.objects(cls, RDFS.subClassOf):
                if isinstance(restriction, BNode):
                    # Check if this is a restriction on source_ref or target_ref
                    for prop in graph.objects(restriction, OWL.onProperty):
                        prop_str = str(prop)
                        if "source_ref" in prop_str:
                            has_source_ref = True
                        elif "target_ref" in prop_str:
                            has_target_ref = True

            if not has_source_ref:
                missing_restrictions.append(
                    f"{cls_str} (missing source_ref restriction)"
                )
            if not has_target_ref:
                missing_restrictions.append(
                    f"{cls_str} (missing target_ref restriction)"
                )

    return missing_restrictions


def check_unresolved_type_references(graph: Graph) -> List[str]:
    """Check that all domain/range references point to actual defined classes or valid types."""
    unresolved_references = []

    # Collect all defined classes in our namespace and standard XML Schema types
    defined_classes = set()
    standard_types = {
        # XML Schema data types
        "http://www.w3.org/2001/XMLSchema#string",
        "http://www.w3.org/2001/XMLSchema#int",
        "http://www.w3.org/2001/XMLSchema#integer",
        "http://www.w3.org/2001/XMLSchema#decimal",
        "http://www.w3.org/2001/XMLSchema#float",
        "http://www.w3.org/2001/XMLSchema#double",
        "http://www.w3.org/2001/XMLSchema#boolean",
        "http://www.w3.org/2001/XMLSchema#date",
        "http://www.w3.org/2001/XMLSchema#dateTime",
        "http://www.w3.org/2001/XMLSchema#time",
        "http://www.w3.org/2001/XMLSchema#duration",
        "http://www.w3.org/2001/XMLSchema#anyURI",
        "http://www.w3.org/2001/XMLSchema#base64Binary",
        "http://www.w3.org/2001/XMLSchema#hexBinary",
        # OWL and RDF types
        "http://www.w3.org/2002/07/owl#Thing",
        "http://www.w3.org/2000/01/rdf-schema#Literal",
        # STIX 2.1 standard types that are external references
        "http://docs.oasis-open.org/ns/cti/stix/vulnerability",
        "http://docs.oasis-open.org/ns/cti/stix/threat-actor",
        "http://docs.oasis-open.org/ns/cti/stix/kill-chain-phase",
        "http://docs.oasis-open.org/ns/cti/stix/indicator",
        "http://docs.oasis-open.org/ns/cti/stix/sdo",
        "http://docs.oasis-open.org/ns/cti/stix/infrastructure",
        "http://docs.oasis-open.org/ns/cti/stix/attack-pattern",
        "http://docs.oasis-open.org/ns/cti/stix/course-of-action",
        "http://docs.oasis-open.org/ns/cti/stix/identity",
        "http://docs.oasis-open.org/ns/cti/stix/location",
        "http://docs.oasis-open.org/ns/cti/stix/relationship",
        # STIX data marking
        "http://docs.oasis-open.org/ns/cti/data-marking/marking-definition",
    }

    # Collect all class definitions
    for cls in graph.subjects(RDF.type, OWL.Class):
        defined_classes.add(str(cls))

    # Also include common STIX classes that might be referenced
    stix_classes = set()
    for cls in graph.subjects(RDF.type, OWL.Class):
        cls_str = str(cls)
        if any(stix_ns in cls_str for stix_ns in STIX_NAMESPACES):
            stix_classes.add(cls_str)

    all_valid_types = defined_classes.union(standard_types).union(stix_classes)

    # Check domain references
    for prop in graph.subjects(RDF.type, OWL.ObjectProperty):
        if in_namespace(prop):
            for domain_ref in graph.objects(prop, RDFS.domain):
                domain_str = str(domain_ref)
                if domain_str not in all_valid_types:
                    unresolved_references.append(
                        f"Property {prop} has unresolved domain: {domain_str}"
                    )

    for prop in graph.subjects(RDF.type, OWL.DatatypeProperty):
        if in_namespace(prop):
            for domain_ref in graph.objects(prop, RDFS.domain):
                domain_str = str(domain_ref)
                if domain_str not in all_valid_types:
                    unresolved_references.append(
                        f"Property {prop} has unresolved domain: {domain_str}"
                    )

    # Check range references
    for prop in graph.subjects(RDF.type, OWL.ObjectProperty):
        if in_namespace(prop):
            for range_ref in graph.objects(prop, RDFS.range):
                range_str = str(range_ref)
                if range_str not in all_valid_types:
                    unresolved_references.append(
                        f"Property {prop} has unresolved range: {range_str}"
                    )

    for prop in graph.subjects(RDF.type, OWL.DatatypeProperty):
        if in_namespace(prop):
            for range_ref in graph.objects(prop, RDFS.range):
                range_str = str(range_ref)
                if range_str not in all_valid_types:
                    unresolved_references.append(
                        f"Property {prop} has unresolved range: {range_str}"
                    )

    return unresolved_references


# ---- CHECK FUNCTIONS ----
def find_properties_missing_domain_range(graph: Graph) -> Tuple[List[str], List[str]]:
    """Find properties that lack domain or range declarations"""
    missing_domain, missing_range = [], []
    for prop_type in [OWL.ObjectProperty, OWL.DatatypeProperty]:
        for prop in graph.subjects(RDF.type, prop_type):
            # Only check properties in our primary namespace
            if in_namespace(prop):
                if not list(graph.objects(prop, RDFS.domain)):
                    missing_domain.append(str(prop))
                if not list(graph.objects(prop, RDFS.range)):
                    missing_range.append(str(prop))
    return missing_domain, missing_range


def find_incomplete_unionOf_lists(graph: Graph) -> List[Tuple[str, str]]:
    """Find broken or incomplete unionOf list structures"""
    broken_unions = []
    for subj, union_node in graph.subject_objects(OWL.unionOf):
        # Only check classes in our primary namespace
        if isinstance(union_node, BNode) and in_namespace(subj):
            first = list(graph.objects(union_node, RDF.first))
            rest = list(graph.objects(union_node, RDF.rest))
            if not first or not rest:
                broken_unions.append((str(subj), str(union_node)))
    return broken_unions


def find_isolated_classes(graph: Graph) -> List[str]:
    """Find classes that aren't connected to properties or other classes"""
    # Only check classes in our primary namespace
    declared_classes = set(
        s for s in graph.subjects(RDF.type, OWL.Class) if in_namespace(s)
    )
    connected = set()
    for s, p, o in graph:
        if s in declared_classes or o in declared_classes:
            connected.add(s)
            connected.add(o)
    return sorted(str(cls) for cls in (declared_classes - connected))


def find_missing_inverse_properties(graph: Graph) -> List[str]:
    """Find object properties that lack inverse property declarations"""
    # Only check properties in our primary namespace
    properties = set(
        s for s in graph.subjects(RDF.type, OWL.ObjectProperty) if in_namespace(s)
    )
    has_inverse = set(graph.subjects(OWL.inverseOf, None))
    inverse_targets = set(graph.objects(None, OWL.inverseOf))
    all_with_inverse = has_inverse.union(inverse_targets)
    return sorted(str(p) for p in (properties - all_with_inverse))


def check_unreachable_classes(graph: Graph) -> List[str]:
    """Find classes in the primary namespace that are not reachable from owl:Thing
    and do not have a STIX class as an ancestor."""

    # Classes in our primary namespace that we are evaluating
    all_classes_in_ns = set(
        s
        for s in graph.subjects(RDF.type, OWL.Class)
        if in_namespace(s)
        and not str(s).endswith("_ov")
        and "Union_" not in str(s)  # Legacy Union_ classes
        and "union-" not in str(s)  # Grid-STIX union- classes (kebab-case)
    )  # in_namespace defaults to include_imports=False

    logging.info(
        f"Checking reachability for {len(all_classes_in_ns)} classes in {BASE_NAMESPACE} (after filtering _ov/Union_)"
    )

    # 1. Find all classes that are descendants of owl:Thing
    reachable_descendants_of_owl_thing = set()
    visited_for_owl_dfs = set()

    def dfs_from_owl_thing(cls_node: URIRef) -> None:
        if cls_node in visited_for_owl_dfs:
            return
        visited_for_owl_dfs.add(cls_node)
        reachable_descendants_of_owl_thing.add(cls_node)  # Add any descendant

        for sub_class in graph.subjects(RDFS.subClassOf, cls_node):
            if isinstance(sub_class, URIRef):  # Process only URIRefs
                dfs_from_owl_thing(sub_class)

    logging.info(f"Starting DFS for descendants of owl:Thing...")
    dfs_from_owl_thing(OWL.Thing)

    # Filter to get classes in our namespace that are descendants of OWL.Thing
    reachable_in_ns_via_owl = all_classes_in_ns.intersection(
        reachable_descendants_of_owl_thing
    )

    logging.debug(
        f"Total descendants of owl:Thing found: {len(reachable_descendants_of_owl_thing)}"
    )
    logging.debug(
        f"Classes in '{BASE_NAMESPACE}' reachable from owl:Thing: {len(reachable_in_ns_via_owl)}"
    )
    sample_owl = list(reachable_in_ns_via_owl)[:5]
    if sample_owl:
        logging.debug(
            f"  Sample (from owl:Thing): {', '.join(str(c) for c in sample_owl)}"
        )

    # Candidates for being "truly unreachable" are those in our namespace NOT descending from OWL.Thing.
    # These need to be checked for STIX ancestry.
    candidates_for_stix_check = all_classes_in_ns - reachable_in_ns_via_owl

    truly_unreachable_classes = set()

    # Helper function to check for STIX ancestors (traverses upwards via rdfs:subClassOf)
    def has_stix_ancestor(
        cls_uri: Union[URIRef, BNode],
        current_graph: Graph,
        visited_ancestor_nodes: Set[Union[URIRef, BNode]],
    ) -> bool:
        if cls_uri in visited_ancestor_nodes:
            return False  # Cycle detected or path already checked
        visited_ancestor_nodes.add(cls_uri)

        if not isinstance(cls_uri, URIRef):  # Blank nodes cannot be STIX classes by URI
            return False

        # Check if the current class URI itself starts with any of the STIX namespaces
        for stix_ns in STIX_NAMESPACES:
            if str(cls_uri).startswith(stix_ns):
                return True

        # Traverse upwards to superclasses
        for super_class_node in current_graph.objects(cls_uri, RDFS.subClassOf):
            if has_stix_ancestor(
                super_class_node, current_graph, visited_ancestor_nodes
            ):
                return True
        return False

    if candidates_for_stix_check:
        logging.debug(
            f"Found {len(candidates_for_stix_check)} classes in '{BASE_NAMESPACE}' not descending from owl:Thing. "
            f"Now checking them for STIX ancestry..."
        )

    for cls_candidate in candidates_for_stix_check:
        visited_for_this_stix_check: Set[Union[URIRef, BNode]] = (
            set()
        )  # Fresh set for each candidate's upward search
        if not has_stix_ancestor(cls_candidate, graph, visited_for_this_stix_check):
            truly_unreachable_classes.add(cls_candidate)
            logging.debug(
                f"  Class {cls_candidate} is TRULY UNREACHABLE (no STIX ancestor)."
            )
        else:
            logging.debug(
                f"  Class {cls_candidate} has a STIX ancestor, considered reachable."
            )

    effectively_reachable_in_ns = all_classes_in_ns - truly_unreachable_classes
    logging.debug(
        f"Total effectively reachable classes in '{BASE_NAMESPACE}': {len(effectively_reachable_in_ns)}"
    )
    sample_effective = list(effectively_reachable_in_ns)[:5]
    if sample_effective:
        logging.debug(
            f"  Sample (effectively reachable): {', '.join(str(c) for c in sample_effective)}"
        )

    return sorted(str(c) for c in truly_unreachable_classes)


def check_subclass_cycles(graph: Graph) -> List[List[str]]:
    """Find cycles in the subClassOf hierarchy"""
    g_sub = DiGraph()
    for s, o in graph.subject_objects(RDFS.subClassOf):
        # Only check for cycles in our primary namespace
        if in_namespace(s) and in_namespace(o):
            g_sub.add_edge(s, o)
    cycles = [
        sorted(str(n) for n in scc)
        for scc in strongly_connected_components(g_sub)
        if len(scc) > 1
    ]
    return cycles


def check_undeclared_properties(graph: Graph) -> List[str]:
    """Find properties used but not declared with a specific property type"""
    # Only check properties in our primary namespace
    used_props = set(p for s, p, o in graph if in_namespace(p))
    declared_props = set(graph.subjects(RDF.type, RDF.Property)).union(
        graph.subjects(RDF.type, OWL.ObjectProperty),
        graph.subjects(RDF.type, OWL.DatatypeProperty),
        graph.subjects(RDF.type, OWL.AnnotationProperty),
    )
    undeclared = used_props - declared_props
    return sorted(str(p) for p in undeclared)


def check_disjoint_violations(graph: Graph) -> List[Tuple[str, str, str]]:
    """Find instances that belong to disjoint classes"""
    # Only check for disjoint violations in our primary namespace
    disjoints = [
        (a, b)
        for a, b in graph.subject_objects(OWL.disjointWith)
        if in_namespace(a) and in_namespace(b)
    ]
    instance_types = defaultdict(set)
    for inst, cls in graph.subject_objects(RDF.type):
        if in_namespace(inst):
            instance_types[inst].add(cls)
    violations = []
    for inst, types in instance_types.items():
        for a, b in disjoints:
            if a in types and b in types:
                violations.append((str(inst), str(a), str(b)))
    return violations


def check_missing_labels(graph: Graph) -> List[str]:
    """Find entities that lack rdfs:label annotations"""
    # Only check for missing labels in our primary namespace
    return sorted(
        str(s)
        for s in graph.subjects(RDF.type, None)
        if in_namespace(s) and not list(graph.objects(s, RDFS.label))
    )


def is_valid_technical_name(label: str) -> bool:
    """Check if a label follows acceptable technical naming conventions"""
    return bool(re.fullmatch(TECHNICAL_NAMING_PATTERN, label))


def check_invalid_technical_names(graph: Graph) -> List[str]:
    """Find entities with labels that don't follow technical naming conventions"""
    invalid_names = []
    # Only check labels in our primary namespace
    for s, label in graph.subject_objects(RDFS.label):
        if in_namespace(s):
            if isinstance(label, str):
                label_str = label
            else:
                label_str = str(label)
            if not is_valid_technical_name(label_str):
                invalid_names.append(f"{s} -> '{label_str}'")
    return invalid_names


def check_uri_naming_conventions(graph: Graph) -> Dict[str, List[str]]:
    """Check that URI names follow strict naming conventions

    Returns:
        Dict with 'class_uri_violations' and 'property_uri_violations' keys
    """
    violations = {"class_uri_violations": [], "property_uri_violations": []}

    # Check class URI naming (should use hyphens)
    for cls in graph.subjects(RDF.type, OWL.Class):
        if in_namespace(cls):
            cls_str = str(cls)
            # Extract the local name from URI
            if "#" in cls_str:
                local_name = cls_str.split("#")[-1]
            elif "/" in cls_str:
                local_name = cls_str.split("/")[-1]
            else:
                continue

            # Skip special cases like vocabulary classes and union classes
            if (
                local_name.endswith("_ov")
                or local_name.startswith("union-")
                or local_name.startswith("Union_")
            ):
                continue

            if not re.fullmatch(CLASS_URI_PATTERN, local_name):
                violations["class_uri_violations"].append(
                    f"{cls_str} -> '{local_name}' (should use hyphens: {to_kebab_case(local_name)})"
                )

    # Check property URI naming (should use hyphens)
    for prop_type in [OWL.ObjectProperty, OWL.DatatypeProperty]:
        for prop in graph.subjects(RDF.type, prop_type):
            if in_namespace(prop):
                prop_str = str(prop)
                # Extract the local name from URI
                if "#" in prop_str:
                    local_name = prop_str.split("#")[-1]
                elif "/" in prop_str:
                    local_name = prop_str.split("/")[-1]
                else:
                    continue

                if not re.fullmatch(PROPERTY_URI_PATTERN, local_name):
                    violations["property_uri_violations"].append(
                        f"{prop_str} -> '{local_name}' (should use hyphens: {to_kebab_case(local_name)})"
                    )

    return violations


def check_label_naming_conventions(graph: Graph) -> List[str]:
    """Check that labels follow strict snake_case conventions"""
    violations = []

    for s, label in graph.subject_objects(RDFS.label):
        if in_namespace(s):
            if isinstance(label, str):
                label_str = label
            else:
                label_str = str(label)

            # Skip special cases
            if label_str.endswith("_ov"):
                continue

            if not re.fullmatch(LABEL_PATTERN, label_str):
                violations.append(
                    f"{s} -> '{label_str}' (should use snake_case: {to_snake_case(label_str)})"
                )

    return violations


def to_kebab_case(text: str) -> str:
    """Convert text to kebab-case (hyphens)"""
    # Handle various patterns
    # PascalCase -> kebab-case
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", text)
    # snake_case -> kebab-case
    text = text.replace("_", "-")
    # Multiple hyphens -> single hyphen
    text = re.sub(r"-+", "-", text)
    # Remove leading/trailing hyphens
    text = text.strip("-")
    return text.lower()


def to_snake_case(text: str) -> str:
    """Convert text to snake_case (underscores)"""
    # Handle various patterns
    # PascalCase -> snake_case
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    # kebab-case -> snake_case
    text = text.replace("-", "_")
    # Multiple underscores -> single underscore
    text = re.sub(r"_+", "_", text)
    # Remove leading/trailing underscores
    text = text.strip("_")
    return text.lower()


# ---- RUN CHECKS ----
check_results: Dict[str, Any] = {}

# Only run checks that aren't skipped
if "missing_domain_range" not in SKIP_CHECKS:
    check_results["missing_domain"], check_results["missing_range"] = (
        find_properties_missing_domain_range(g)
    )
else:
    check_results["missing_domain"], check_results["missing_range"] = [], []

if "unionof_issues" not in SKIP_CHECKS:
    check_results["unionof_issues"] = find_incomplete_unionOf_lists(g)
else:
    check_results["unionof_issues"] = []

if "isolated_classes" not in SKIP_CHECKS:
    check_results["isolated_classes"] = find_isolated_classes(g)
else:
    check_results["isolated_classes"] = []

if "missing_inverses" not in SKIP_CHECKS:
    check_results["missing_inverses"] = find_missing_inverse_properties(g)
else:
    check_results["missing_inverses"] = []

if "unreachable" not in SKIP_CHECKS:
    check_results["unreachable"] = check_unreachable_classes(g)
else:
    check_results["unreachable"] = []

if "subclass_cycles" not in SKIP_CHECKS:
    check_results["subclass_cycles"] = check_subclass_cycles(g)
else:
    check_results["subclass_cycles"] = []

if "undeclared_props" not in SKIP_CHECKS:
    check_results["undeclared_props"] = check_undeclared_properties(g)
else:
    check_results["undeclared_props"] = []

if "disjoint_violations" not in SKIP_CHECKS:
    check_results["disjoint_violations"] = check_disjoint_violations(g)
else:
    check_results["disjoint_violations"] = []

if "missing_labels" not in SKIP_CHECKS:
    check_results["missing_labels"] = check_missing_labels(g)
else:
    check_results["missing_labels"] = []

if "non_snake_labels" not in SKIP_CHECKS:
    check_results["non_snake_labels"] = check_invalid_technical_names(g)
else:
    check_results["non_snake_labels"] = []

# New strict naming convention checks
if "uri_naming" not in SKIP_CHECKS:
    uri_violations = check_uri_naming_conventions(g)
    check_results["class_uri_violations"] = uri_violations["class_uri_violations"]
    check_results["property_uri_violations"] = uri_violations["property_uri_violations"]
else:
    check_results["class_uri_violations"] = []
    check_results["property_uri_violations"] = []

if "label_naming" not in SKIP_CHECKS:
    check_results["label_violations"] = check_label_naming_conventions(g)
else:
    check_results["label_violations"] = []

# STIX 2.1 compliance checks
if "stix_inheritance" not in SKIP_CHECKS:
    check_results["stix_inheritance"] = check_stix_inheritance_compliance(g)
else:
    check_results["stix_inheritance"] = []

if "stix_namespace" not in SKIP_CHECKS:
    check_results["stix_namespace"] = check_stix_namespace_consistency(g)
else:
    check_results["stix_namespace"] = []

if "stix_properties" not in SKIP_CHECKS:
    check_results["stix_properties"] = check_stix_property_patterns(g)
else:
    check_results["stix_properties"] = []

if "stix_relationships" not in SKIP_CHECKS:
    check_results["stix_relationships"] = check_stix_relationship_compliance(g)
else:
    check_results["stix_relationships"] = []

if "stix_vocabularies" not in SKIP_CHECKS:
    check_results["stix_vocabularies"] = check_stix_vocabulary_compliance(g)
else:
    check_results["stix_vocabularies"] = []

if "stix_required_properties" not in SKIP_CHECKS:
    check_results["stix_required_properties"] = check_stix_required_properties(g)
else:
    check_results["stix_required_properties"] = []

if "unresolved_types" not in SKIP_CHECKS:
    check_results["unresolved_types"] = check_unresolved_type_references(g)
else:
    check_results["unresolved_types"] = []

# ---- PRINT ONLY ISSUES THAT EXIST ----
issues_found = False

if check_results["missing_domain"]:
    issues_found = True
    logging.warning("=== MISSING DOMAIN ===")
    logging.warning(
        "Properties in your namespace lack an rdfs:domain. Add domain declarations to clarify which classes use them."
    )
    logging.warning("\n".join(check_results["missing_domain"]))

if check_results["missing_range"]:
    issues_found = True
    logging.warning("=== MISSING RANGE ===")
    logging.warning(
        "Properties in your namespace lack an rdfs:range. Add range declarations to constrain expected value types."
    )
    logging.warning("\n".join(check_results["missing_range"]))

if check_results["unionof_issues"]:
    issues_found = True
    logging.warning("=== MALFORMED UNIONOF ===")
    logging.warning(
        "Some owl:unionOf expressions in your ontology are incomplete RDF lists. Ensure they include rdf:first/rest/nil."
    )
    for s, u in check_results["unionof_issues"]:
        logging.warning(f"{s} -> {u}")

if check_results["isolated_classes"]:
    issues_found = True
    logging.warning("=== ISOLATED CLASSES ===")
    logging.warning(
        "These classes are not connected to any properties or subclass relations. Review if they should be linked or removed."
    )
    logging.warning("\n".join(check_results["isolated_classes"]))

# if check_results["missing_inverses"]:
#     issues_found = True
#     logging.warning("=== MISSING INVERSEOF ===")
#     logging.warning(
#         "These object properties lack owl:inverseOf definitions. Adding inverses improves querying and reasoning consistency."
#     )
#     logging.warning("\n".join(check_results["missing_inverses"]))

if check_results["unreachable"]:
    issues_found = True
    logging.warning("=== UNREACHABLE CLASSES ===")
    logging.warning(
        "These classes are not reachable via rdfs:subClassOf chains from owl:Thing or a STIX class. Consider linking or reclassifying them."
    )
    logging.warning("\n".join(check_results["unreachable"]))

if check_results["subclass_cycles"]:
    issues_found = True
    logging.warning("=== SUBCLASS CYCLES ===")
    logging.warning(
        "Cycles in rdfs:subClassOf hierarchy were found. These may confuse OWL reasoners. Break the cycle if unintentional."
    )
    for cycle in check_results["subclass_cycles"]:
        logging.warning(" -> ".join(cycle))

if check_results["undeclared_props"]:
    issues_found = True
    logging.warning("=== UNDECLARED PROPERTIES ===")
    logging.warning(
        "These properties are used in your namespace but never declared. Declare them as rdf/OWL properties."
    )
    logging.warning("\n".join(check_results["undeclared_props"]))

if check_results["disjoint_violations"]:
    issues_found = True
    logging.warning("=== DISJOINT VIOLATIONS ===")
    logging.warning(
        "Instances were found that belong to disjoint classes. This violates OWL DL semantics and should be corrected."
    )
    for inst, a, b in check_results["disjoint_violations"]:
        logging.warning(f"{inst} has both {a} and {b}")

if check_results["missing_labels"]:
    issues_found = True
    logging.warning("=== MISSING LABELS ===")
    logging.warning(
        "These ontology entities are missing rdfs:label annotations. Add labels to improve readability and tooling support."
    )
    logging.warning("\n".join(check_results["missing_labels"]))

if check_results["non_snake_labels"]:
    issues_found = True
    logging.warning("=== INVALID TECHNICAL NAMES ===")
    logging.warning(
        "These ontology entities have rdfs:label values that don't follow technical naming conventions (allow letters, numbers, underscores)."
    )
    logging.warning("\n".join(check_results["non_snake_labels"]))

# New strict naming convention reporting
if check_results["class_uri_violations"]:
    issues_found = True
    logging.warning("=== CLASS URI NAMING VIOLATIONS ===")
    logging.warning(
        "These class URIs don't follow kebab-case convention. Class rdf:about URIs should use hyphens (e.g., 'generation-asset')."
    )
    logging.warning("\n".join(check_results["class_uri_violations"]))

if check_results["property_uri_violations"]:
    issues_found = True
    logging.warning("=== PROPERTY URI NAMING VIOLATIONS ===")
    logging.warning(
        "These property URIs don't follow kebab-case convention. Property rdf:about URIs should use hyphens (e.g., 'has-component')."
    )
    logging.warning("\n".join(check_results["property_uri_violations"]))

if check_results["label_violations"]:
    issues_found = True
    logging.warning("=== LABEL NAMING VIOLATIONS ===")
    logging.warning(
        "These rdfs:label values don't follow snake_case convention. Labels should use underscores (e.g., 'generation_asset')."
    )
    logging.warning("\n".join(check_results["label_violations"]))

# STIX 2.1 compliance issue reporting
if check_results["stix_inheritance"]:
    issues_found = True
    logging.warning("=== STIX INHERITANCE NON-COMPLIANCE ===")
    logging.warning(
        "These classes do not properly inherit from STIX base classes. Ensure all Grid-STIX classes inherit from appropriate STIX classes."
    )
    logging.warning("\n".join(check_results["stix_inheritance"]))

if check_results["stix_namespace"]:
    issues_found = True
    logging.warning("=== STIX NAMESPACE INCONSISTENCY ===")
    logging.warning(
        "These references use incorrect STIX namespace formats. Update to use proper STIX 2.1 namespace patterns."
    )
    logging.warning("\n".join(check_results["stix_namespace"]))

if check_results["stix_properties"]:
    issues_found = True
    logging.warning("=== GRID-STIX PROPERTY NAMING NON-COMPLIANCE ===")
    logging.warning(
        "These properties do not follow Grid-STIX naming conventions. Property URIs should use kebab-case (hyphens)."
    )
    logging.warning("\n".join(check_results["stix_properties"]))

if check_results["stix_relationships"]:
    issues_found = True
    logging.warning("=== STIX RELATIONSHIP NON-COMPLIANCE ===")
    logging.warning(
        "These relationship classes do not properly inherit from STIX Relationship base class."
    )
    logging.warning("\n".join(check_results["stix_relationships"]))

if check_results["stix_vocabularies"]:
    issues_found = True
    logging.warning("=== STIX VOCABULARY NON-COMPLIANCE ===")
    logging.warning(
        "These vocabulary classes have issues with their STIX vocabulary patterns."
    )
    logging.warning("\n".join(check_results["stix_vocabularies"]))

if check_results["stix_required_properties"]:
    issues_found = True
    logging.warning("=== STIX REQUIRED PROPERTIES MISSING ===")
    logging.warning(
        "These relationship classes are missing required source_ref or target_ref restrictions."
    )
    logging.warning("\n".join(check_results["stix_required_properties"]))

if check_results["unresolved_types"]:
    issues_found = True
    logging.warning("=== UNRESOLVED TYPE REFERENCES ===")
    logging.warning(
        "These properties have domain/range references that don't resolve to defined classes or valid types."
    )
    logging.warning("\n".join(check_results["unresolved_types"]))

if not issues_found:
    logging.info("No issues found in the ontology.")
else:
    logging.error("Issues were found in the ontology. Please review and fix them.")

if __name__ == "__main__":
    # Parse command line arguments when run as script
    args = parse_arguments()

    # Update configuration with parsed arguments
    OWL_FILE = args.owl_file
    BASE_NAMESPACE = args.base_namespace
    CATALOG_FILE = args.catalog
    SKIP_CHECKS = args.skip_checks

    # Set exit code based on whether issues were found
    sys.exit(1 if issues_found else 0)
