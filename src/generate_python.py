import sys
import os

from pathlib import Path
from rdflib import Graph, RDF, RDFS, OWL
from jinja2 import Template
from collections import defaultdict
from typing import Dict, List, Any
from rdflib.term import URIRef
import importlib
import pkgutil
import inspect

try:
    import stix2
    STIX2_AVAILABLE = True
except ImportError:
    STIX2_AVAILABLE = False
    print("Warning: stix2 library not available. Some features may be limited.")


def discover_stix_modules(base_module):
    discovered = {}
    if not base_module:
        return discovered
        
    visited = set()
    modules = [base_module.__name__]

    try:
        for finder, name, ispkg in pkgutil.walk_packages(
            base_module.__path__, base_module.__name__ + "."
        ):
            modules.append(name)
    except Exception:
        return discovered

    for modname in modules:
        if modname in visited:
            continue
        visited.add(modname)
        try:
            mod = importlib.import_module(modname)
            for name, obj in inspect.getmembers(mod):
                if inspect.isclass(obj) and not obj.__module__.startswith("stix2.v20"):
                    discovered[name] = obj.__module__
        except Exception:
            continue

    return discovered


def ensure_directory(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def create_init_files():
    output_dir = Path("python/grid_stix")
    # Create main __init__.py file
    main_init = output_dir / "__init__.py"
    main_init_content = [
        "# Grid-STIX 2.1 Python Classes",
        "",
        "from . import assets",
        "from . import attack_patterns",
        "from . import components",
        "from . import cyber_contexts",
        "from . import environmental_contexts",
        "from . import events_observables",
        "from . import nuclear_safeguards",
        "from . import operational_contexts",
        "from . import physical_contexts",
        "from . import policies",
        "from . import relationships",
        "from . import vocab",
        "",
        "__version__ = '0.1.0'  # Update this as needed"
    ]
    main_init.write_text("\n".join(main_init_content))

    # Create __init__.py files for submodules
    submodules = [
        "assets", "attack_patterns", "components", "cyber_contexts",
        "environmental_contexts", "events_observables", "nuclear_safeguards",
        "operational_contexts", "physical_contexts", "policies",
        "relationships", "vocab"
    ]
    for submodule in submodules:
        submodule_init = output_dir / submodule / "__init__.py"
        ensure_directory(submodule_init.parent)
        submodule_init.touch()

def get_vocab_consolidation_rules():
    """Define consolidation rules based on patterns and keywords"""
    return {
        "authentication": ["authentication", "auth"],
        "grid": ["grid", "ot_device", "sensor", "voltage", "operational"],
        "security": ["security", "defensive", "detection", "trust", "alert"],
        "maintenance": ["maintenance", "response", "emergency", "incident", "communications", "transportation"],
        "nuclear": ["nuclear", "radiation", "safeguard", "monitoring", "inspection", "enrichment"],
        "environmental": ["weather", "storm", "disaster", "environmental"],
        "energy": ["fuel", "renewable", "generation", "outage", "impact"],
        "compliance": ["regulatory", "compliance", "supply_chain"]
    }

def main() -> None:
    print("Starting generate_python.py...")
    if len(sys.argv) != 2:
        print("Usage: python generate_python.py <ontology_file>")
        sys.exit(1)

    if not Path(sys.argv[1]).exists():
        print(f"Error: The file {sys.argv[1]} does not exist.")
        sys.exit(1)

    print(f"Parsing ontology file: {sys.argv[1]}")
    g = Graph()
    g.parse(str(sys.argv[1]), format="xml")
    print(f"Parsed graph with {len(g)} triples")

    # Create __init__.py files
    create_init_files()

def categorize_vocab_class(class_name):
    """Categorize a vocabulary class based on keywords in its name"""
    if not class_name.endswith("_Ov"):
        return None  # Not a vocabulary class
        
    name_lower = class_name.lower()
    rules = get_vocab_consolidation_rules()
    
    # Check each category for keyword matches
    for category, keywords in rules.items():
        for keyword in keywords:
            if keyword in name_lower:
                return f"{category}_vocab.py"
    
    # Default category for unmatched vocab classes
    return "misc_vocab.py"
    
    def get_relationship_consolidation_rules():
        """Define consolidation rules for relationship classes"""
        return {
            "connection": ["connects", "feeds", "depends", "contains", "supplies", "aggregates", "located"],
            "operational": ["controls", "monitors", "affects", "triggers", "produces"],
            "security": ["protects", "authenticates", "vulnerability", "within_security"],
            "power": ["power", "generates", "converts"],
            "union": ["union"]  # All Union types
        }
    
    def get_component_consolidation_rules():
        """Define consolidation rules for component classes"""
        return {
            "generation": ["generator", "plant", "facility", "nuclear", "fossil", "renewable", "solar", "wind", "fuel"],
            "distribution": ["transformer", "breaker", "regulator", "capacitor", "recloser", "sectionalizer"],
            "control": ["plc", "rtu", "hmi", "ied", "smart"],
            "protection": ["relay", "protective"],
            "measurement": ["sensor", "meter"],
            "storage": ["storage", "battery"]
        }
    
    def get_event_consolidation_rules():
        """Define consolidation rules for event/observable classes"""
        return {
            "security": ["authentication", "physical", "access"],
            "operational": ["control", "maintenance", "configuration", "state"],
            "grid": ["grid", "alarm", "anomaly"],
            "protocol": ["protocol", "telemetry", "firmware", "traffic"]
        }
    
    def categorize_relationship_class(class_name):
        """Categorize a relationship class based on keywords in its name"""
        if not (class_name.endswith("Relationship") or class_name.startswith("Union")):
            return None  # Not a relationship class
            
        name_lower = class_name.lower()
        rules = get_relationship_consolidation_rules()
        
        # Check each category for keyword matches
        for category, keywords in rules.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return f"{category}_relationships.py"
        
        # Default category for unmatched relationship classes  
        return "misc_relationships.py"
    
    def categorize_component_class(class_name):
        """Categorize a component class based on keywords in its name"""
        # Component classes are typically in the components module or inherit from certain base classes
        # We'll check for common component patterns and base classes
        name_lower = class_name.lower()
        rules = get_component_consolidation_rules()
        
        # Check each category for keyword matches
        for category, keywords in rules.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return f"{category}_components.py"
        
        # Default category for unmatched component classes
        return "misc_components.py"
    
    def categorize_event_class(class_name):
        """Categorize an event/observable class based on keywords in its name"""
        # Event classes typically end with "Event" or contain "Telemetry", "Traffic", etc.
        name_lower = class_name.lower()
        rules = get_event_consolidation_rules()
        
        # Check each category for keyword matches
        for category, keywords in rules.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return f"{category}_events.py"
        
        # Default category for unmatched event classes
        return "misc_events.py"
    
    classes = {
        c
        for c in g.subjects(RDF.type, OWL.Class)
        if isinstance(c, URIRef)
    }
    object_properties = set(g.subjects(RDF.type, OWL.ObjectProperty))

    # Helper functions
    def qname(uri: URIRef) -> str:
        return uri.split("#")[-1] if "#" in uri else uri.split("/")[-1]

    def to_class_name(uri: URIRef) -> str:
        name = qname(uri).replace("-", " ").title().replace(" ", "")
        # Handle common abbreviations to maintain proper casing
        name = name.replace("Ot", "OT")
        name = name.replace("It", "IT") 
        name = name.replace("Ai", "AI")
        name = name.replace("Ml", "ML")
        name = name.replace("Hmi", "HMI")
        name = name.replace("Plc", "PLC")
        name = name.replace("Rtu", "RTU")
        name = name.replace("Ied", "IED")
        return name

    def to_attr_name(uri: URIRef) -> str:
        return qname(uri).replace("-", "_").lower()

    def sanitize_path_part(part: str) -> str:
        part = part.replace("-", "_").replace(".", "_").replace(" ", "_")
        part = part.replace("grid_stix_2_1_", "")  # Remove specific prefix
        if part.endswith("_owl"):
            part = part[:-4]  # Remove trailing '_owl' if from .owl
        return part

    # Gather subclass relationships
    subclass_map: Dict[str, List[str]] = {to_class_name(c): [] for c in classes}
    for c in classes:
        for superclass in g.objects(c, RDFS.subClassOf):
            if (superclass, RDF.type, OWL.Class) in g and isinstance(superclass, URIRef):
                subclass_map[to_class_name(c)].append(to_class_name(superclass))

    # Helper function to resolve property types
    def resolve_property_type(ranges):
        if not ranges:
            return "Any"
        
        range_node = ranges[0]
        
        # Handle standard Thing types
        range_class_name = to_class_name(range_node)
        if range_class_name in {"Thing", "owl_Thing"}:
            return "Any"
        
        # Check if it's a known class
        if range_node in classes:
            return range_class_name
        
        # Handle anonymous union classes
        union_members = list(g.objects(range_node, OWL.unionOf))
        if union_members:
            # Extract classes from the union
            union_classes = []
            for union_list in union_members:
                # Parse RDF collection
                members = []
                current = union_list
                while current and current != RDF.nil:
                    first = list(g.objects(current, RDF.first))
                    if first and first[0] in classes:
                        # Ensure we have a URIRef before calling to_class_name
                        if isinstance(first[0], URIRef):
                            members.append(to_class_name(first[0]))
                    rest = list(g.objects(current, RDF.rest))
                    current = rest[0] if rest else None
                union_classes.extend(members)
            
            if union_classes:
                # For now, use the first class as fallback instead of Union type
                # This prevents hash-based names while keeping functionality
                return union_classes[0]
        
        # If we can't resolve it, use Any instead of hash-based names
        if range_class_name.startswith('N') and len(range_class_name) > 10:
            return "Any"
        
        return range_class_name

    # Gather properties
    class_props: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for prop in object_properties:
        domains = list(g.objects(prop, RDFS.domain))
        ranges = list(g.objects(prop, RDFS.range))

        for d in domains:
            if d in classes and isinstance(d, URIRef):
                class_props[to_class_name(d)].append(
                    {
                        "name": to_attr_name(prop) if isinstance(prop, URIRef) else str(prop),
                        "type": resolve_property_type(ranges),
                    }
                )

    output_dir = Path("python/grid_stix")
    output_dir.mkdir(parents=True, exist_ok=True)

    class_name_to_uri: Dict[str, URIRef] = {}
    class_to_module_path: Dict[str, str] = {}

    # First pass: collect all STIX classes and prioritize hyphenated format
    stix_classes = {}
    for c in classes:
        class_name = to_class_name(c)
        if "docs.oasis-open.org" in str(c):
            uri_str = str(c)
            # Prioritize hyphenated format over fragment format
            if class_name not in stix_classes:
                stix_classes[class_name] = c
            elif "/stix/" in uri_str and "#" not in uri_str.split("/stix/")[-1]:
                # Prefer URLs like /stix/identity over /stix#Identity
                stix_classes[class_name] = c
            elif "/stix/" in uri_str and "data-marking" not in uri_str:
                # Prefer /stix/ URLs over /ns/cti# URLs
                stix_classes[class_name] = c
    
    
    # Add prioritized STIX classes to the URI mapping
    for class_name, uri in stix_classes.items():
        class_name_to_uri[class_name] = uri
    
    # Second pass: handle Grid-STIX classes 
    for c in classes:
        class_name = to_class_name(c)
        
        # Skip STIX classes - already handled above
        if "docs.oasis-open.org" in str(c):
            continue
        
        # Prioritize assets.owl over components.owl for duplicate class names  
        if class_name in class_name_to_uri:
            existing_uri = class_name_to_uri[class_name]
            # Prefer assets.owl over components.owl for GridComponent and other core classes
            if "assets.owl" in str(c) and "components.owl" in str(existing_uri):
                class_name_to_uri[class_name] = c
        else:
            class_name_to_uri[class_name] = c
    
    # Third pass: build module paths from final prioritized URIs
    for class_name, c in class_name_to_uri.items():
        # Skip STIX classes
        if "docs.oasis-open.org" in str(c):
            continue
            
        ns_uri = str(c).rsplit("#", 1)[0]
        ns_parts = [
            sanitize_path_part(p)
            for p in ns_uri.split("/")
            if p and p not in {"http:", "https:", "www.anl.gov", "sss"}
        ]
        # Remove leading grid parts and just use the meaningful namespace parts
        if len(ns_parts) >= 2:
            module_path = ".".join(ns_parts[-2:])
        else:
            module_path = ".".join(ns_parts)
        class_to_module_path[class_name] = module_path

    used_types = {
        prop["type"]
        for props_list in class_props.values()
        for prop in props_list
        if prop["type"] != "Any"
    }

    for typename in used_types:
        if typename not in class_to_module_path:
            matching_uri = class_name_to_uri.get(typename)
            if matching_uri:
                ns_uri = str(matching_uri).rsplit("#", 1)[0]
                ns_parts = [
                    sanitize_path_part(p)
                    for p in ns_uri.split("/")
                    if p and p not in {"http:", "https:", "www.anl.gov", "sss"}
                ]
                # Remove leading grid parts and just use the meaningful namespace parts
                if len(ns_parts) >= 2:
                    module_path = ".".join(ns_parts[-2:])
                else:
                    module_path = ".".join(ns_parts)
                class_to_module_path[typename] = module_path
            else:
                print(f"Warning: Used type '{typename}' not found in RDF class set.")

    # Combine all known class sources
    stix_class_to_path = {}
    if STIX2_AVAILABLE:
        try:
            import stix2
            stix_class_to_path = discover_stix_modules(stix2)
        except (ImportError, NameError):
            print("Warning: stix2 module not found or cannot be imported. STIX classes will not be available.")
    gridstix_class_to_path = class_to_module_path.copy()

    # Identify classes that need forward references
    forward_ref_classes = set()
    for cls, parents in subclass_map.items():
        for parent in parents:
            if parent in gridstix_class_to_path:
                parent_module = gridstix_class_to_path[parent]
                cls_module = gridstix_class_to_path.get(cls, "")
                if parent_module == cls_module:
                    forward_ref_classes.add(parent)
    
    # Remove STIX classes from gridstix_class_to_path to prevent conflicts
    for class_name in stix_classes.keys():
        if class_name in gridstix_class_to_path:
            del gridstix_class_to_path[class_name]
    
    # Create dynamic consolidation file mapping using the categorization functions
    consolidation_class_to_file = {}
    
    # Process vocabulary classes
    for class_name in gridstix_class_to_path.keys():
        vocab_file = categorize_vocab_class(class_name)
        if vocab_file:
            consolidation_class_to_file[class_name] = vocab_file
    
    # Process relationship classes
    for class_name in gridstix_class_to_path.keys():
        relationship_file = categorize_relationship_class(class_name)
        if relationship_file:
            consolidation_class_to_file[class_name] = relationship_file
    
    # Process component classes
    for class_name in gridstix_class_to_path.keys():
        component_file = categorize_component_class(class_name)
        # Only consolidate if it's actually in the components module/namespace
        if component_file and class_name in gridstix_class_to_path:
            module_path = gridstix_class_to_path[class_name]
            if "components" in module_path:
                consolidation_class_to_file[class_name] = component_file
    
    # Process event/observable classes
    for class_name in gridstix_class_to_path.keys():
        event_file = categorize_event_class(class_name)
        # Only consolidate if it's actually in the events_observables module/namespace
        if event_file and class_name in gridstix_class_to_path:
            module_path = gridstix_class_to_path[class_name]
            if "events_observables" in module_path:
                consolidation_class_to_file[class_name] = event_file
    
    # Update gridstix_class_to_path for consolidated files
    for class_name, consolidated_file in consolidation_class_to_file.items():
        if class_name in gridstix_class_to_path:
            # Change the path to point to the consolidated file (remove .py extension)
            module_path = gridstix_class_to_path[class_name]
            # Get the base namespace path (e.g., "grid.vocab" from "grid.vocab.SomeClass")
            base_path = module_path.rsplit('.', 1)[0] if '.' in module_path else module_path
            # Set to consolidated file path without .py extension
            consolidated_module = consolidated_file.rsplit('.', 1)[0]
            gridstix_class_to_path[class_name] = f"{base_path}.{consolidated_module}"
    
    # Enhanced circular import detection
    forward_ref_classes = set()  # Define forward_ref_classes

    def normalize_name(name: str) -> str:
        return name.lower()

    # Storage for consolidated file classes (vocabulary + relationships)
    consolidated_file_classes = {}

    subclass_map = {to_class_name(c): [] for c in classes}
    for c in classes:
        for superclass in g.objects(c, RDFS.subClassOf):
            if (superclass, RDF.type, OWL.Class) in g and isinstance(superclass, URIRef):
                subclass_map[to_class_name(c)].append(to_class_name(superclass))

    for cls, parents in subclass_map.items():
        # Skip generating files for STIX classes - they come from the stix2 library
        class_uri = class_name_to_uri.get(cls)
        if not class_uri or "docs.oasis-open.org" in str(class_uri):
            continue
            
        # Determine module path from prefix
        ns_uri = str(class_uri).rsplit("#", 1)[0]
        ns_tail = [
            part
            for part in ns_uri.split("/")
            if part not in {"http:", "https:", "www.anl.gov", "sss"}
        ][-2:]
        ns_parts = [sanitize_path_part(p) for p in ns_tail if p]
        class_path = output_dir.joinpath(*ns_parts)
        ensure_directory(class_path)

        # Insert __init__.py files in all parent directories up to output_dir
        current_path = class_path
        while True:
            init_file = current_path / "__init__.py"
            if not init_file.exists():
                init_file.touch()
            if current_path == output_dir:
                break
            current_path = current_path.parent

        props = class_props.get(cls, [])
        
        # Detect circular imports by checking if any property type references back to current class
        current_module_path = gridstix_class_to_path.get(cls, "")
        circular_refs = set()
        
        # Build imports: referenced class names in type hints, plus all superclasses except self and BaseModel
        all_refs = {
            prop["type"]
            for prop in props
            if prop["type"] != "Any" and prop["type"] != cls
        }.union({p for p in parents if p != "BaseModel" and p != cls})
        
        for ref in all_refs:
            # Self-references always need quotes
            if ref == cls:
                circular_refs.add(ref)
                continue
            
            # Use forward references for classes in the forward_ref_classes set
            if ref in forward_ref_classes:
                circular_refs.add(ref)
                continue
            
            # Use forward references for same-module dependencies
            if ref in gridstix_class_to_path and cls in gridstix_class_to_path:
                ref_module = gridstix_class_to_path[ref]
                cls_module = gridstix_class_to_path[cls]
                if ref_module == cls_module:
                    circular_refs.add(ref)
        
        # Split into direct imports and forward references
        imports = sorted(all_refs - circular_refs)
        forward_refs = sorted(circular_refs)

        resolved_imports = []
        import_paths = {}
        for i in imports:
            if i in gridstix_class_to_path:
                # For Grid-STIX classes, use the module path + class name for import
                module_path = gridstix_class_to_path[i]
                import_paths[i] = f"{module_path}.{i}"
                resolved_imports.append(i)
            else:
                # Try exact match first
                if i in stix_class_to_path:
                    # STIX classes should be imported directly from stix2, not grid_stix
                    import_paths[i] = stix_class_to_path[i].replace("grid_stix.", "")
                    resolved_imports.append(i)
                else:
                    # Try case-insensitive lookup
                    lookup = normalize_name(i)
                    stix_normalized = {normalize_name(k): k for k in stix_class_to_path}
                    if lookup in stix_normalized:
                        true_key = stix_normalized[lookup]
                        # STIX classes should be imported directly from stix2, not grid_stix
                        import_paths[i] = stix_class_to_path[true_key].replace("grid_stix.", "")
                        resolved_imports.append(i)
                    else:
                        print(f"Warning: Unresolved type hint '{i}'")
        imports = resolved_imports

        # Use the resolved import name for parent class if it exists
        resolved_parent = "BaseModel"
        if parents:
            parent_name = parents[0]
            if parent_name in imports:
                resolved_parent = parent_name
            elif parent_name in forward_refs:
                # Parent is a forward reference - we MUST import it for inheritance
                # Remove from forward_refs and add to imports
                forward_refs = [f for f in forward_refs if f != parent_name]
                imports.append(parent_name)
                if parent_name in gridstix_class_to_path:
                    import_paths[parent_name] = gridstix_class_to_path[parent_name]
                elif parent_name in stix_class_to_path:
                    import_paths[parent_name] = stix_class_to_path[parent_name].replace("grid_stix.", "")
                resolved_parent = parent_name
            else:
                resolved_parent = parent_name
        
        class_def = Template(
            """
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from grid_stix.assets.GridComponent import GridComponent
    from grid_stix.assets.PhysicalAsset import PhysicalAsset
    from grid_stix.events_observables.grid_events import GridEvent
    from grid_stix.relationships.misc_relationships import GridRelationship
    from grid_stix.relationships.union_relationships import UnionAllAssets
    from grid_stix.operational_contexts.OperationalContext import OperationalContext

{% for import in imports %}
{% if import_paths[import].startswith('stix2') %}
from {{ import_paths[import] }} import {{ import }}
{% else %}
from grid_stix.{{ import_paths[import] }} import {{ import }}
{% endif %}
{% endfor %}

class {{ cls }}({{ parent }}):
    {% if not props %}
    pass
    {% else %}
    {% for prop in props %}
    {% if prop.type == "Any" %}
    {{ prop.name }}: Optional[Any] = None
    {% elif prop.type == cls %}
    {{ prop.name }}: Optional["{{ prop.type }}"] = None
    {% elif prop.type in forward_refs or prop.type in central_classes %}
    {{ prop.name }}: Optional["{{ prop.type }}"] = None
    {% else %}
    {{ prop.name }}: Optional[{{ prop.type }}] = None
    {% endif %}
    {% endfor %}
    {% endif %}
"""
        ).render(
            cls=cls,
            parent=resolved_parent,
            props=props,
            imports=imports,
            import_paths=import_paths,
            forward_refs=forward_refs,
            central_classes={"GridComponent", "PhysicalAsset", "GridEvent", "GridRelationship", "UnionAllAssets", "OperationalContext"}
        )
        
        # For individual files, extract additional imports from rendered template and regenerate
        if not cls in consolidation_class_to_file:  # Only for individual files
            import re
            # Extract all quoted types from the rendered template
            quoted_types = re.findall(r'Optional\["([^"]+)"\]', class_def)
            additional_imports = set()
            additional_import_paths = {}
            
            
            for quoted_type in quoted_types:
                if quoted_type != cls and quoted_type in gridstix_class_to_path:
                    # Check if this would create a circular import
                    # For consolidated classes, be more permissive since they're in separate files
                    should_import = False
                    if quoted_type not in forward_ref_classes:
                        should_import = True
                    elif quoted_type in consolidation_class_to_file:
                        # Consolidated classes can usually be imported safely
                        current_module = gridstix_class_to_path.get(cls, "")
                        target_module = gridstix_class_to_path.get(quoted_type, "")
                        # Only avoid import if same module
                        if current_module != target_module:
                            should_import = True
                    
                    if should_import:
                        additional_imports.add(quoted_type)
                        # Use the updated path (which may point to consolidated file) + class name
                        module_path = gridstix_class_to_path[quoted_type]
                        additional_import_paths[quoted_type] = f"{module_path}.{quoted_type}"
            
            # If we found additional imports, regenerate the template with them
            if additional_imports:
                all_imports = sorted(set(imports) | additional_imports)
                all_import_paths = {**import_paths, **additional_import_paths}
                
                # Regenerate template with additional imports
                class_def = Template(
                    """
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..assets.GridComponent import GridComponent
    from ..assets.PhysicalAsset import PhysicalAsset
    from ..events_observables.grid_events import GridEvent
    from ..relationships.misc_relationships import GridRelationship
    from ..relationships.union_relationships import UnionAllAssets
    from ..operational_contexts.OperationalContext import OperationalContext

{% for import in imports %}
{% if import_paths[import].startswith('stix2') %}
from {{ import_paths[import] }} import {{ import }}
{% else %}
from ..{{ import_paths[import] }} import {{ import }}
{% endif %}
{% endfor %}

class {{ cls }}({{ parent }}):
    {% if not props %}
    pass
    {% else %}
    {% for prop in props %}
    {% if prop.type == "Any" %}
    {{ prop.name }}: Optional[Any] = None
    {% elif prop.type == cls or prop.type in forward_refs %}
    {{ prop.name }}: Optional["{{ prop.type }}"] = None
    {% else %}
    {{ prop.name }}: Optional[{{ prop.type }}] = None
    {% endif %}
    {% endfor %}
    {% endif %}
"""
                ).render(
                    cls=cls,
                    parent=resolved_parent,
                    props=props,
                    imports=all_imports,
                    import_paths=all_import_paths,
                    forward_refs=forward_ref_classes,
                )
            
            # Unquote imported types and self-references
            for imported_class in set(imports) | additional_imports:
                if imported_class != cls:
                    class_def = class_def.replace(f'"{imported_class}"', imported_class)
            # Always unquote self-references
            class_def = class_def.replace(f'"{cls}"', cls)

        # Check if this class should be consolidated (vocabulary or relationship)
        if cls in consolidation_class_to_file:
            # This class should be consolidated - add to consolidated file (don't write individual file)
            consolidated_file = consolidation_class_to_file[cls]
            
            # Collect all classes for this consolidated file
            if consolidated_file not in consolidated_file_classes:
                consolidated_file_classes[consolidated_file] = []
            
            consolidated_file_classes[consolidated_file].append({
                'class_name': cls,
                'class_def': class_def,
                'path': class_path
            })
            # Skip writing individual file for consolidated classes
        else:
            # Regular class - write individual file
            file_name = f"{cls}.py"
            file_path = class_path / file_name
            ensure_directory(file_path.parent)
            with open(file_path, "w") as f:
                f.write(class_def)

    # Write consolidated files (vocabulary and relationships)
    if consolidated_file_classes:
        for consolidated_file, class_list in consolidated_file_classes.items():
            if class_list:
                # Use the path from the first class (they should all be in same namespace folder)
                file_path = class_list[0]['path'] / consolidated_file
                ensure_directory(file_path.parent)
                
                # Collect all imports needed across all classes
                all_imports = set()
                all_import_paths = {}
                stix_imports = set()
                classes_in_this_file = {class_info['class_name'] for class_info in class_list}
                
                for class_info in class_list:
                    class_def = class_info['class_def']
                    lines = class_def.split('\n')
                    
                    # Extract imports from each class
                    for line in lines:
                        line = line.strip()
                        if line.startswith('from ') and ' import ' in line:
                            # Parse import line: "from grid_stix.module.Class import Class"
                            if 'grid_stix.' in line:
                                parts = line.split(' import ')
                                if len(parts) == 2:
                                    module_part = parts[0].replace('from ', '')
                                    class_name = parts[1]
                                    
                                    # Skip imports for classes that are defined in this consolidated file
                                    if class_name not in classes_in_this_file:
                                        # Extract the correct module path (remove the redundant class name)
                                        module_parts = module_part.replace('grid_stix.', '').split('.')
                                        if len(module_parts) >= 2:
                                            # Take the first two parts: namespace.module
                                            clean_module_path = '.'.join(module_parts[:2])
                                            all_imports.add(class_name)
                                            all_import_paths[class_name] = clean_module_path
                            elif line.startswith('from stix2.'):
                                # Keep STIX imports as-is
                                stix_imports.add(line)
                        
                        # Also extract quoted type hints that need imports
                        elif ':' in line and 'Optional[' in line:
                            # Look for quoted type hints like: Optional["SomeClass"] = None
                            import re
                            quoted_types = re.findall(r'Optional\["([^"]+)"\]', line)
                            for quoted_type in quoted_types:
                                if quoted_type not in classes_in_this_file:
                                    # Check if this is a known class that needs importing
                                    if quoted_type in gridstix_class_to_path:
                                        module_path = gridstix_class_to_path[quoted_type]
                                        all_imports.add(quoted_type)
                                        all_import_paths[quoted_type] = module_path
                
                # Combine all class definitions with proper imports
                combined_content = []
                combined_content.append("from __future__ import annotations")
                combined_content.append("from pydantic import BaseModel")
                combined_content.append("from typing import Optional, Any, TYPE_CHECKING")
                combined_content.append("")
                combined_content.append("if TYPE_CHECKING:")
                combined_content.append("    from grid_stix.assets.GridComponent import GridComponent")
                combined_content.append("    from grid_stix.assets.PhysicalAsset import PhysicalAsset")
                combined_content.append("    from grid_stix.events_observables.grid_events import GridEvent")
                combined_content.append("    from grid_stix.relationships.misc_relationships import GridRelationship")
                combined_content.append("    from grid_stix.relationships.union_relationships import UnionAllAssets")
                combined_content.append("    from grid_stix.operational_contexts.OperationalContext import OperationalContext")
                combined_content.append("")
                
                # Add STIX imports
                for stix_import in sorted(stix_imports):
                    combined_content.append(stix_import)
                
                # Add Grid-STIX imports (avoid self-imports)
                for class_name in sorted(all_imports):
                    if class_name in all_import_paths and class_name not in {"GridComponent", "PhysicalAsset", "GridEvent", "GridRelationship", "UnionAllAssets", "OperationalContext"}:
                        # Use relative imports for classes in the same package
                        if all_import_paths[class_name].startswith(consolidated_file.split('_')[0]):
                            combined_content.append(f"from .{all_import_paths[class_name]} import {class_name}")
                        else:
                            combined_content.append(f"from ..{all_import_paths[class_name]} import {class_name}")
                
                if all_imports or stix_imports:
                    combined_content.append("")
                
                # Add all class definitions (clean up whitespace and unquote imported types)
                for class_info in class_list:
                    class_def = class_info['class_def']
                    lines = class_def.split('\n')
                    
                    # Find where the class definition starts
                    class_start = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith('class '):
                            class_start = i
                            break
                    
                    # Add the class definition with cleaned whitespace and unquoted types
                    class_lines = lines[class_start:]
                    cleaned_lines = []
                    for line in class_lines:
                        if line.strip() or (cleaned_lines and cleaned_lines[-1].strip()):
                            # Unquote type hints for classes we're importing OR classes defined in this file
                            processed_line = line
                            for class_to_unquote in set(all_imports) | classes_in_this_file:
                                if f'"{class_to_unquote}"' in processed_line:
                                    # Keep quotes for forward references (classes in the same file)
                                    if class_to_unquote in classes_in_this_file and 'class ' + class_to_unquote not in '\n'.join(cleaned_lines):
                                        continue
                                    processed_line = processed_line.replace(f'"{class_to_unquote}"', class_to_unquote)
                            cleaned_lines.append(processed_line)
                    
                    combined_content.extend(cleaned_lines)
                    combined_content.append("")  # Single blank line between classes
                
                # Write consolidated file
                with open(file_path, "w") as f:
                    f.write('\n'.join(combined_content))
                
                file_type = "vocabulary" if "vocab" in consolidated_file else "relationship"
                print(f"Created consolidated {file_type} file: {consolidated_file} with {len(class_list)} classes")

    # Process classes
    classes = {
        c
        for c in g.subjects(RDF.type, OWL.Class)
        if isinstance(c, URIRef)
    }
    object_properties = set(g.subjects(RDF.type, OWL.ObjectProperty))

    # ... (rest of the main function content)

if __name__ == "__main__":
    main()
