from rdflib import Graph, RDF, RDFS, OWL, URIRef, BNode, Namespace
from collections import defaultdict
from networkx import DiGraph, strongly_connected_components
import logging
import re
import sys
import os
import argparse
import xml.etree.ElementTree as ET

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ---- ARGUMENT PARSING ----
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
    help='List of check types to skip (e.g., "missing_inverses unreachable")',
)
args = parser.parse_args()

# ---- CONFIGURATION ----
OWL_FILE = args.owl_file
BASE_NAMESPACE = args.base_namespace
CATALOG_FILE = args.catalog
SKIP_CHECKS = args.skip_checks

# Define common STIX namespaces
STIX_NAMESPACES = [
    "http://docs.oasis-open.org/cti/ns/stix/",  # Covers STIX general namespace
    "http://stixschema.org/v21"  # Covers STIX 2.1 objects often imported with this base
]

# ---- LOAD CATALOG ----
import_mappings = {}
if os.path.exists(CATALOG_FILE):
    try:
        logging.info(f"Loading import mappings from catalog: {CATALOG_FILE}")
        catalog_tree = ET.parse(CATALOG_FILE)
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
namespaces = set()
for s, p, o in g:
    if isinstance(s, URIRef):
        ns_uri = (
            str(s).split("#")[0]
            if "#" in str(s)
            else str(s).rsplit("/", 1)[0] + "/"
        )
        namespaces.add(ns_uri)
for ns in sorted(namespaces):
    logging.debug(f"  {ns}")


# ---- FILTER FUNCTION ----
def in_namespace(uri, include_imports=False):
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


# ---- CHECK FUNCTIONS ----
def find_properties_missing_domain_range(graph):
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


def find_incomplete_unionOf_lists(graph):
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


def find_isolated_classes(graph):
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


def find_missing_inverse_properties(graph):
    """Find object properties that lack inverse property declarations"""
    # Only check properties in our primary namespace
    properties = set(
        s for s in graph.subjects(RDF.type, OWL.ObjectProperty) if in_namespace(s)
    )
    has_inverse = set(graph.subjects(OWL.inverseOf, None))
    inverse_targets = set(graph.objects(None, OWL.inverseOf))
    all_with_inverse = has_inverse.union(inverse_targets)
    return sorted(str(p) for p in (properties - all_with_inverse))


def check_unreachable_classes(graph):
    """Find classes in the primary namespace that are not reachable from owl:Thing
    and do not have a STIX class as an ancestor."""

    # Classes in our primary namespace that we are evaluating
    all_classes_in_ns = set(
        s
        for s in graph.subjects(RDF.type, OWL.Class)
        if in_namespace(s)
        and not str(s).endswith("_ov")
        and "Union_" not in str(s) # Corrected line: was `and not str(s).startswith("Union_")`
    )  # in_namespace defaults to include_imports=False

    logging.info(
        f"Checking reachability for {len(all_classes_in_ns)} classes in {BASE_NAMESPACE} (after filtering _ov/Union_)"
    )

    # 1. Find all classes that are descendants of owl:Thing
    reachable_descendants_of_owl_thing = set()
    visited_for_owl_dfs = set()

    def dfs_from_owl_thing(cls_node):
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
    def has_stix_ancestor(cls_uri, current_graph, visited_ancestor_nodes):
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
        visited_for_this_stix_check = (
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


def check_subclass_cycles(graph):
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


def check_undeclared_properties(graph):
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


def check_disjoint_violations(graph):
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


def check_missing_labels(graph):
    """Find entities that lack rdfs:label annotations"""
    # Only check for missing labels in our primary namespace
    return sorted(
        str(s)
        for s in graph.subjects(RDF.type, None)
        if in_namespace(s) and not list(graph.objects(s, RDFS.label))
    )


def is_snake_case(label):
    """Check if a label follows snake_case convention"""
    return bool(re.fullmatch(r"[a-z0-9_]+", label))


def check_non_snake_case_labels(graph):
    """Find entities with labels that aren't in snake_case format"""
    non_snake = []
    # Only check for non-snake_case labels in our primary namespace
    for s, label in graph.subject_objects(RDFS.label):
        if in_namespace(s):
            if isinstance(label, str):
                label_str = label
            else:
                label_str = str(label)
            if not is_snake_case(label_str):
                non_snake.append(f"{s} -> '{label_str}'")
    return non_snake


# ---- RUN CHECKS ----
check_results = {}

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
    check_results["non_snake_labels"] = check_non_snake_case_labels(g)
else:
    check_results["non_snake_labels"] = []

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
    logging.warning("=== NON-SNAKE_CASE LABELS ===")
    logging.warning(
        "These ontology entities have rdfs:label values that are not snake_case. Update them for consistency."
    )
    logging.warning("\n".join(check_results["non_snake_labels"]))

if not issues_found:
    logging.info("No issues found in the ontology.")
else:
    logging.error("Issues were found in the ontology. Please review and fix them.")

# Set exit code based on whether issues were found
sys.exit(1 if issues_found else 0)
