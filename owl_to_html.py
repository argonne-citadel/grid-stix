import argparse
import networkx as nx
import networkx.drawing.nx_agraph as nx_agraph
import os
import plotly.graph_objects as go
from typing import Any, Union

from rdflib import BNode, Graph, RDF, RDFS, OWL

# Constants
STIX_BASE = "http://docs.oasis-open.org/ns/cti/stix"
CTI_BASE = "http://docs.oasis-open.org/ns/cti"
GRID_BASE = "http://www.anl.gov/sss/"

# Enhanced color scheme for electrical grid cybersecurity ontology
COLOR_SCHEME = {
    # Core Grid Infrastructure
    "Asset": "#4A90E2",  # Blue - physical infrastructure
    "Component": "#7ED321",  # Green - grid components
    "OTDevice": "#F5A623",  # Orange - operational technology
    "GridComponent": "#50E3C2",  # Teal - electrical components
    # Security & Operations
    "Event": "#D0021B",  # Red - security events
    "Context": "#F8E71C",  # Yellow - operational contexts
    "Relationship": "#9013FE",  # Purple - relationships
    "Policy": "#00BCD4",  # Cyan - policies & procedures
    "Attack": "#B71C1C",  # Dark red - attack patterns
    "Mitigation": "#4CAF50",  # Green - mitigations
    "Vulnerability": "#FF5722",  # Orange-red - vulnerabilities
    # Supply Chain & Protocols
    "Supplier": "#795548",  # Brown - supply chain entities
    "Protocol": "#607D8B",  # Blue-grey - communication protocols
    "SupplyChainRisk": "#E91E63",  # Pink - supply chain risks
    # Observables & Monitoring
    "Observable": "#673AB7",  # Deep purple - cyber observables
    "Sensor": "#009688",  # Teal - sensor devices
    "Telemetry": "#3F51B5",  # Indigo - telemetry data
    # STIX Framework
    "STIX": "#2E7D32",  # Dark green - STIX core
    "CTI": "#66BB6A",  # Light green - CTI framework
    # Power System Specific
    "PowerFlow": "#FF6F00",  # Amber - power flow relationships
    "Protection": "#1976D2",  # Blue - protective devices
    "Control": "#8BC34A",  # Light green - control systems
    # Default
    "Other": "#424242",  # Grey - uncategorized
}

DEFAULT_NODE_COLOR = "black"


def get_label(uri: Union[str, BNode, Any]) -> str:
    """Extract a human-readable label from a URI."""
    if isinstance(uri, BNode):
        return f"_anon_{str(uri)[:8]}"
    uri = str(uri)
    if "#" in uri:
        return str(uri.split("#")[-1])
    elif "/" in uri:
        return str(uri.rstrip("/").split("/")[-1])
    else:
        return str(uri[:12])


def is_stix(uri: Union[str, BNode, Any]) -> bool:
    """Check if a URI is from the STIX namespace."""
    return str(uri).startswith(STIX_BASE)


def is_cti(uri: Union[str, BNode, Any]) -> bool:
    """Check if a URI is from the CTI namespace."""
    return str(uri).startswith(CTI_BASE)


def is_grid(uri: Union[str, BNode, Any]) -> bool:
    """Check if a URI is from the Grid-STIX namespace."""
    return str(uri).startswith(GRID_BASE)


def get_node_type(label: str, g: Graph, uri: Union[str, BNode, Any]) -> str:
    """Determine the type of a node based on its label or properties with Grid-STIX specific categorization."""
    if isinstance(uri, BNode):
        return "Anonymous"

    label = str(label).lower()
    uri_str = str(uri).lower()

    # Grid-STIX specific type detection

    # Supply Chain Security
    if "supplier" in label or "supply_chain" in label:
        return "Supplier" if "risk" not in label else "SupplyChainRisk"

    # Grid Infrastructure - More specific categorization
    if (
        "ot_device" in label
        or "otdevice" in label
        or any(x in label for x in ["rtu", "plc", "ied", "hmi", "smart_meter"])
    ):
        return "OTDevice"
    elif (
        "grid_component" in label
        or "gridcomponent" in label
        or any(
            x in label
            for x in [
                "transformer",
                "capacitor",
                "voltage_regulator",
                "circuit_breaker",
                "recloser",
                "sectionalizer",
            ]
        )
    ):
        return "GridComponent"
    elif "sensor" in label:
        return "Sensor"
    elif "asset" in label or "device" in label:
        return "Asset"
    elif "component" in label:
        return "Component"

    # Security & Threats
    elif "attack" in label or "pattern" in label or "mitigation" in label:
        return "Mitigation" if "mitigation" in label else "Attack"
    elif "vulnerability" in label:
        return "Vulnerability"

    # Operations & Monitoring
    elif "event" in label:
        return "Event"
    elif "context" in label:
        return "Context"
    elif "observable" in label:
        return "Observable"
    elif "telemetry" in label or "monitoring" in label:
        return "Telemetry"

    # Relationships & Policies
    elif "relationship" in label:
        return "Relationship"
    elif "policy" in label:
        return "Policy"

    # Protocols
    elif "protocol" in label or any(
        x in label for x in ["dnp3", "modbus", "iec", "opc", "ieee"]
    ):
        return "Protocol"

    # Power System Specific
    elif any(x in label for x in ["feeds_power", "power_flow", "electrical"]):
        return "PowerFlow"
    elif any(x in label for x in ["protects", "protection", "protective"]):
        return "Protection"
    elif any(x in label for x in ["controls", "control", "regulates", "regulation"]):
        return "Control"

    # Check if it's a STIX concept
    if is_stix(uri):
        return "STIX"
    elif is_cti(uri):
        return "CTI"

    # Check parent classes for inheritance-based typing
    for _, _, o in g.triples((uri, RDFS.subClassOf, None)):
        parent_label = get_label(o).lower()
        if "otdevice" in parent_label:
            return "OTDevice"
        elif "gridcomponent" in parent_label:
            return "GridComponent"
        elif "asset" in parent_label:
            return "Asset"
        elif "component" in parent_label:
            return "Component"
        elif "event" in parent_label:
            return "Event"
        elif "context" in parent_label:
            return "Context"
        elif "relationship" in parent_label:
            return "Relationship"
        elif "observable" in parent_label:
            return "Observable"
        elif "supplier" in parent_label:
            return "Supplier"

    return "Other"


def convert_to_plotly_html(
    owl_path: str, output_path: str, args: argparse.Namespace
) -> None:
    """Convert an OWL ontology to a Plotly HTML network visualization."""
    g = Graph()
    g.parse(owl_path)
    nxg = nx.DiGraph()

    # Extract explicit classes and object properties
    explicit_classes = {
        cls for cls in g.subjects(RDF.type, OWL.Class) if not isinstance(cls, BNode)
    }
    object_properties = {
        prop
        for prop in g.subjects(RDF.type, OWL.ObjectProperty)
        if not isinstance(prop, BNode)
    }

    # Gather all URIs that should be treated as nodes:
    # explicit classes + non-BNode domains/ranges of object properties.
    all_node_uris = set(explicit_classes)
    for prop in object_properties:
        domain_uri_for_prop = next(g.objects(prop, RDFS.domain), None)
        range_uri_for_prop = next(g.objects(prop, RDFS.range), None)
        if domain_uri_for_prop and not isinstance(domain_uri_for_prop, BNode):
            all_node_uris.add(domain_uri_for_prop)
        if range_uri_for_prop and not isinstance(range_uri_for_prop, BNode):
            all_node_uris.add(range_uri_for_prop)

    # Add nodes to nxg from the comprehensive set of URIs with Grid-STIX filtering
    for node_uri in all_node_uris:  # Iterate over the new comprehensive set
        label = get_label(node_uri)

        # Apply prefix exclusion filter
        if args.exclude_prefix and any(
            label.startswith(prefix) for prefix in args.exclude_prefix.split(",")
        ):
            continue

        # Apply Grid-STIX specific filters
        if (
            args.grid_only
            and (is_stix(node_uri) or is_cti(node_uri))
            and not is_grid(node_uri)
        ):
            continue  # Skip base STIX/CTI classes when showing grid-only

        node_type = get_node_type(label, g, node_uri)

        # Apply focus filters
        if args.focus_infrastructure and node_type not in [
            "Asset",
            "Component",
            "OTDevice",
            "GridComponent",
            "Sensor",
        ]:
            continue
        elif args.focus_security and node_type not in [
            "Attack",
            "Vulnerability",
            "Mitigation",
            "Event",
            "Policy",
        ]:
            continue
        elif args.focus_supply_chain and node_type not in [
            "Supplier",
            "SupplyChainRisk",
        ]:
            continue

        color = COLOR_SCHEME.get(node_type, DEFAULT_NODE_COLOR)
        nxg.add_node(
            label, color=color, node_type=node_type
        )  # nxg uses labels as node IDs

    # Add subclass edges
    if not args.no_inheritance:
        for s, _, o in g.triples((None, RDFS.subClassOf, None)):
            if isinstance(s, BNode) or isinstance(o, BNode):
                continue

            s_label = get_label(s)
            o_label = get_label(o)
            # Check if subject and object labels correspond to nodes actually added to nxg
            if s_label in nxg and o_label in nxg:
                nxg.add_edge(s_label, o_label, label="subClassOf", style="dashed")

    # Add object property domain → range edges
    for prop in object_properties:
        if isinstance(prop, BNode):
            continue
        prop_label = get_label(prop)

        # Apply --no-common-properties filter if present and active
        if (
            hasattr(args, "no_common_properties")
            and args.no_common_properties
            and any(x in prop_label.lower() for x in ["ref", "type", "status"])
        ):
            continue

        # Get all domains and ranges for this property
        domain_uris = list(g.objects(prop, RDFS.domain))
        range_uris = list(g.objects(prop, RDFS.range))

        # If no explicit domains/ranges, don't create an edge
        if not domain_uris or not range_uris:
            continue

        # Create edges for all domain/range combinations
        for domain_uri in domain_uris:
            if isinstance(domain_uri, BNode):
                continue

            for range_uri in range_uris:
                if isinstance(range_uri, BNode):
                    continue

                domain_label = get_label(domain_uri)
                range_label = get_label(range_uri)

                # Check if domain and range labels correspond to nodes actually added to nxg
                if domain_label in nxg and range_label in nxg:
                    nxg.add_edge(domain_label, range_label, label=prop_label)

    # Remove nodes with degree 0
    zero_degree_nodes = [n for n, d in nxg.degree() if d == 0]
    nxg.remove_nodes_from(zero_degree_nodes)

    # Build Plotly edge and node traces with improved layout for electrical grid visualization

    # Try to find a good root node for the layout - prefer grid infrastructure
    root_candidates = [
        "PhysicalAsset",
        "GridComponent",
        "OTDevice",
        "GridEvent",
        "grid_stix_2_1",
    ]
    root_node = None
    for candidate in root_candidates:
        if candidate in nxg:
            root_node = candidate
            break

    # Use user-specified layout for electrical grid visualization
    try:
        if args.layout == "spring":
            pos = nx.spring_layout(nxg, k=3, iterations=50)
        else:
            layout_args = "-Granksep=3.0 -Gnodesep=2.0"
            if root_node and args.layout in ["dot", "twopi"]:
                layout_args += f" -Groot={root_node}"
            pos = nx_agraph.graphviz_layout(nxg, prog=args.layout, args=layout_args)
    except:
        # Fallback to spring layout if graphviz fails
        print(f"Warning: {args.layout} layout failed, falling back to spring layout")
        pos = nx.spring_layout(nxg, k=3, iterations=50)

    solid_edge_x, solid_edge_y = [], []
    dashed_edge_x, dashed_edge_y = [], []

    for u, v, d in nxg.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        if d.get("style") == "dashed":
            dashed_edge_x.extend([x0, x1, None])
            dashed_edge_y.extend([y0, y1, None])
        else:
            solid_edge_x.extend([x0, x1, None])
            solid_edge_y.extend([y0, y1, None])

    # Add invisible edge label markers for better hover
    edge_label_x = []
    edge_label_y = []
    edge_label_text = []
    for u, v, d in nxg.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_label_x.append((x0 + x1) / 2)
        edge_label_y.append((y0 + y1) / 2)
        edge_label_text.append(d.get("label", ""))

    edge_label_trace = go.Scatter(
        x=edge_label_x,
        y=edge_label_y,
        mode="markers",
        marker=dict(size=2, color="#888"),
        hoverinfo="text",
        hovertext=edge_label_text,
        showlegend=False,
    )

    degrees = dict(nxg.degree())
    min_label_degree = 1

    # Group nodes by type
    from collections import defaultdict

    node_groups = defaultdict(list)
    for node, data in nxg.nodes(data=True):
        node_groups[data.get("node_type", "Other")].append(node)

    node_traces = []
    for node_type, nodes in node_groups.items():
        xs, ys, texts, hovertexts, colors, sizes, fonts = [], [], [], [], [], [], []
        for node in nodes:
            x, y = pos[node]
            deg = degrees[node]
            xs.append(x)
            ys.append(y)
            if deg >= min_label_degree:
                texts.append(f"{node}")
                fonts.append(min(24, max(8, 8 + deg * 2)))
            else:
                texts.append("")
                fonts.append(10)
            # Enhanced hover text with Grid-STIX context
            hover_info = f"<b>{node}</b><br>"
            hover_info += f"Type: {node_type}<br>"
            hover_info += f"Connections: {deg}<br>"

            # Add Grid-STIX specific context
            if node_type == "OTDevice":
                hover_info += "Category: Operational Technology<br>"
            elif node_type == "GridComponent":
                hover_info += "Category: Electrical Grid Equipment<br>"
            elif node_type == "Supplier":
                hover_info += "Category: Supply Chain Entity<br>"
            elif node_type == "Attack":
                hover_info += "Category: Threat Pattern<br>"
            elif node_type == "Protection":
                hover_info += "Category: Protective System<br>"
            elif node_type == "PowerFlow":
                hover_info += "Category: Electrical Flow<br>"
            elif node_type == "Protocol":
                hover_info += "Category: Communication Protocol<br>"

            hovertexts.append(hover_info)
            colors.append(COLOR_SCHEME.get(node_type, DEFAULT_NODE_COLOR))
            sizes.append(10 + deg)
        node_traces.append(
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers+text",
                text=texts,
                hovertext=hovertexts,
                hoverinfo="text",
                textposition="top center",
                marker=dict(showscale=False, size=sizes, color=colors, line_width=1),
                textfont=dict(size=fonts),
                name=node_type,
                legendgroup=node_type,
                showlegend=True,
            )
        )

    edge_traces = []
    if solid_edge_x:
        solid_edge_trace = go.Scatter(
            x=solid_edge_x,
            y=solid_edge_y,
            line=dict(width=1, color="#888"),
            hoverinfo="none",
            mode="lines",
            showlegend=False,
        )
        edge_traces.append(solid_edge_trace)

    if dashed_edge_x:
        dashed_edge_trace = go.Scatter(
            x=dashed_edge_x,
            y=dashed_edge_y,
            line=dict(width=1, color="#888", dash="dash"),  # Apply dash style
            hoverinfo="none",
            mode="lines",
            showlegend=False,  # You could set this to True and give it a name like "subClassOf"
            # name="subClassOf"
        )
        edge_traces.append(dashed_edge_trace)

    # Create comprehensive title and annotations for Grid-STIX
    title_text = "Grid-STIX 2.1 Electrical Grid Cybersecurity Ontology"
    subtitle = "Interactive visualization of grid assets, threats, and relationships"

    fig = go.Figure(
        data=edge_traces + [edge_label_trace] + node_traces,
        layout=go.Layout(
            title={
                "text": f"<b>{title_text}</b><br><sub>{subtitle}</sub>",
                "font": {"size": 20},
                "x": 0.5,
                "xanchor": "center",
            },
            showlegend=True,
            hovermode="closest",
            margin=dict(b=60, l=5, r=5, t=80),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="rgba(0,0,0,0.2)",
                borderwidth=1,
            ),
            annotations=[
                dict(
                    text="<b>Legend:</b> Solid lines = relationships | Dashed lines = inheritance (subClassOf)<br>"
                    + "<b>Node size</b> indicates connectivity | <b>Colors</b> represent functional categories",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=-0.08,
                    xanchor="center",
                    font=dict(size=12),
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="rgba(0,0,0,0.2)",
                    borderwidth=1,
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )

    fig.write_html(output_path)
    print(f"Plotly HTML graph written to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert OWL file to interactive Plotly HTML network visualization."
    )
    parser.add_argument("input", help="Input OWL file")
    parser.add_argument(
        "output",
        help="Output file (should end with .html for Plotly HTML)",
    )

    # Filtering options
    parser.add_argument(
        "--filter-type",
        help="Filter nodes by type (comma-separated, e.g. 'Asset,Event')",
    )
    parser.add_argument(
        "--filter-namespace", help="Filter nodes by namespace (comma-separated)"
    )
    parser.add_argument(
        "--exclude-prefix",
        help="Exclude classes with specific prefixes (comma-separated)",
    )
    parser.add_argument(
        "--no-unions", action="store_true", help="Exclude Union_ classes"
    )
    parser.add_argument(
        "--no-inheritance", action="store_true", help="Hide subClassOf relationships"
    )

    # Grid-STIX specific filtering options
    parser.add_argument(
        "--grid-only",
        action="store_true",
        help="Show only Grid-STIX specific classes (exclude base STIX/CTI)",
    )
    parser.add_argument(
        "--focus-infrastructure",
        action="store_true",
        help="Focus on grid infrastructure (assets, components, devices)",
    )
    parser.add_argument(
        "--focus-security",
        action="store_true",
        help="Focus on security concepts (attacks, vulnerabilities, mitigations)",
    )
    parser.add_argument(
        "--focus-supply-chain",
        action="store_true",
        help="Focus on supply chain security concepts",
    )

    # Visualization options
    parser.add_argument(
        "--show-data-properties", action="store_true", help="Show data properties"
    )
    parser.add_argument(
        "--layout",
        choices=["dot", "twopi", "neato", "circo", "spring"],
        default="dot",
        help="Graph layout algorithm (default: dot)",
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"File not found: {args.input}")

    convert_to_plotly_html(args.input, args.output, args)
