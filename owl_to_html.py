import argparse
import networkx as nx
import networkx.drawing.nx_agraph as nx_agraph
import os
import plotly.graph_objects as go

from rdflib import BNode, Graph, RDF, RDFS, OWL

# Constants
STIX_BASE = "http://docs.oasis-open.org/ns/cti/stix"
CTI_BASE = "http://docs.oasis-open.org/ns/cti"
GRID_BASE = "http://www.anl.gov/sss/"

# Color scheme for node types
COLOR_SCHEME = {
    "Asset": "skyblue",
    "Component": "lightgreen",
    "Event": "salmon",
    "Context": "gold",
    "Relationship": "plum",
    "Policy": "paleturquoise",
    "Vulnerability": "orangered",
    "Attack": "firebrick",
    "Observable": "mediumpurple",
    "STIX": "darkgreen",
    "CTI": "lightgreen",
}

DEFAULT_NODE_COLOR = "black"


def get_label(uri) -> str:
    """Extract a human-readable label from a URI."""
    if isinstance(uri, BNode):
        return f"_anon_{str(uri)[:8]}"
    uri = str(uri)
    if "#" in uri:
        return uri.split("#")[-1]
    elif "/" in uri:
        return uri.rstrip("/").split("/")[-1]
    else:
        return uri[:12]


def is_stix(uri) -> bool:
    """Check if a URI is from the STIX namespace."""
    return str(uri).startswith(STIX_BASE)


def is_cti(uri) -> bool:
    """Check if a URI is from the CTI namespace."""
    return str(uri).startswith(CTI_BASE)


def is_grid(uri) -> bool:
    """Check if a URI is from the Grid-STIX namespace."""
    return str(uri).startswith(GRID_BASE)


def get_node_type(label, g, uri) -> str:
    """Determine the type of a node based on its label or properties."""
    if isinstance(uri, BNode):
        return "Anonymous"

    label = str(label).lower()

    # Check common type patterns in the label
    if "asset" in label or "device" in label:
        return "Asset"
    elif "component" in label:
        return "Component"
    elif "event" in label:
        return "Event"
    elif "context" in label:
        return "Context"
    elif "relationship" in label:
        return "Relationship"
    elif "policy" in label:
        return "Policy"
    elif "vulnerability" in label:
        return "Vulnerability"
    elif "attack" in label or "pattern" in label:
        return "Attack"
    elif "observable" in label:
        return "Observable"

    # Check if it's a STIX concept
    if is_stix(uri):
        return "STIX"
    elif is_cti(uri):
        return "CTI"

    # Check graph properties
    for _, _, o in g.triples((uri, RDFS.subClassOf, None)):
        parent_label = get_label(o).lower()
        if "asset" in parent_label:
            return "Asset"
        elif "component" in parent_label:
            return "Component"
        elif "event" in parent_label:
            return "Event"
        # Continue with other type checks...

    return "Other"


def convert_to_plotly_html(owl_path, output_path, args):
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

    # Add nodes to nxg from the comprehensive set of URIs
    for node_uri in all_node_uris:  # Iterate over the new comprehensive set
        label = get_label(node_uri)
        if args.exclude_prefix and any(
            label.startswith(prefix) for prefix in args.exclude_prefix.split(",")
        ):
            continue  # Skip adding this node if it matches an excluded prefix
        node_type = get_node_type(label, g, node_uri)
        color = COLOR_SCHEME.get(node_type, DEFAULT_NODE_COLOR)
        nxg.add_node(label, color=color, node_type=node_type) # nxg uses labels as node IDs

    # Add subclass edges
    if not args.no_inheritance:
        for s, _, o in g.triples((None, RDFS.subClassOf, None)):
            if isinstance(s, BNode) or isinstance(o, BNode):
                continue
            
            s_label = get_label(s)
            o_label = get_label(o)
            # Check if subject and object labels correspond to nodes actually added to nxg
            if s_label in nxg and o_label in nxg:
                nxg.add_edge(
                    s_label, o_label, label="subClassOf", style="dashed"
                )

    # Add object property domain → range edges
    for prop in object_properties:
        if isinstance(prop, BNode):
            continue
        prop_label = get_label(prop)
        
        # Apply --no-common-properties filter if present and active
        if hasattr(args, 'no_common_properties') and args.no_common_properties and any(
            x in prop_label.lower() for x in ["ref", "type", "status"]
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

    # Build Plotly edge and node traces

    pos = nx_agraph.graphviz_layout(
        nxg, prog="twopi", args="-Granksep=5.0 -Groot=GridEvent"
    )
    
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
            hovertexts.append(f"{node} ({node_type})")
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
            showlegend=False
        )
        edge_traces.append(solid_edge_trace)

    if dashed_edge_x:
        dashed_edge_trace = go.Scatter(
            x=dashed_edge_x,
            y=dashed_edge_y,
            line=dict(width=1, color="#888", dash="dash"),  # Apply dash style
            hoverinfo="none",
            mode="lines",
            showlegend=False, # You could set this to True and give it a name like "subClassOf"
            # name="subClassOf" 
        )
        edge_traces.append(dashed_edge_trace)


    fig = go.Figure(
        data=edge_traces + [edge_label_trace] + node_traces,
        layout=go.Layout(
            title={"text": "Grid-STIX Ontology Network", "font": {"size": 16}},
            showlegend=True,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="Ontology visualization",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.005,
                    y=-0.002,
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

    # Visualization options
    parser.add_argument(
        "--show-data-properties", action="store_true", help="Show data properties"
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"File not found: {args.input}")

    convert_to_plotly_html(args.input, args.output, args)
