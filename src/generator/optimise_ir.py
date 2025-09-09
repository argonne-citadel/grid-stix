"""
Grid-STIX Intermediate Representation Optimizer

This module optimizes the intermediate representation by analyzing dependency graphs
and resolving circular imports using forward references. It serves as Stage 3 of
the Grid-STIX code generation pipeline.

Features:
- Dependency Analysis:
  • Build directed graphs of class dependencies
  • Identify inheritance and type annotation dependencies
  • Track cross-module and intra-module references
  • Support for complex dependency patterns
- Circular Import Resolution:
  • Tarjan's algorithm for strongly connected component detection
  • Automatic forward reference insertion for circular dependencies
  • Optimal topological ordering of modules and classes
  • Minimal forward reference usage to maintain readability
- Import Optimization:
  • Consolidate and minimize import statements
  • Group imports by module and type
  • Generate relative vs absolute import strategies
  • Remove unused imports and detect missing dependencies
- Code Organization:
  • Topological module ordering for clean builds
  • Class consolidation for related entities
  • Template parameter optimization
  • Memory-efficient dependency tracking

Use Cases:
- Resolve circular imports between generated Python classes
- Optimize import statements for faster loading and reduced complexity
- Ensure deterministic code generation order
- Support complex inheritance hierarchies from ontologies
- Enable incremental code regeneration with dependency tracking
"""

import logging

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Optional

from .build_ir import AttrDef, ClassDef, IntermediateRepresentation


logger = logging.getLogger(__name__)


@dataclass
class DependencyNode:
    """Node in the dependency graph."""

    name: str
    module: str
    dependencies: set[str]
    dependents: set[str]
    in_cycle: bool = False


@dataclass
class OptimizedIR:
    """Optimized intermediate representation with resolved dependencies."""

    classes: dict[str, ClassDef]
    dependency_graph: dict[str, DependencyNode]
    module_order: list[str]
    forward_refs: dict[str, set[str]]  # class -> set of forward referenced types
    consolidated_modules: dict[str, set[str]]  # module -> consolidated class names


class IROptimizerError(Exception):
    """Raised when IR optimization fails."""

    pass


class IROptimizer:
    """Optimizes intermediate representation for code generation."""

    def __init__(self):
        """Initialize IR optimizer."""
        self.visited = set()
        self.stack = []
        self.index_counter = 0
        self.strongly_connected_components = []

    def optimize_ir(self, ir: IntermediateRepresentation) -> OptimizedIR:
        """
        Optimize intermediate representation.

        Args:
            ir: Input intermediate representation

        Returns:
            OptimizedIR: Optimized IR with resolved dependencies

        Raises:
            IROptimizerError: If optimization fails
        """
        logger.info("Optimizing intermediate representation...")

        try:
            # Build dependency graph
            dependency_graph = self._build_dependency_graph(ir)

            # Find strongly connected components (cycles)
            self._find_strongly_connected_components(dependency_graph)

            # Mark classes in cycles for forward references
            forward_refs = self._identify_forward_references(ir, dependency_graph)

            # Update class definitions with forward reference flags
            optimized_classes = self._update_class_definitions(ir.classes, forward_refs)

            # Determine optimal module ordering
            module_order = self._determine_module_order(dependency_graph)

            # Apply consolidation rules
            consolidated_modules = self._apply_consolidation_rules(ir)

            optimized_ir = OptimizedIR(
                classes=optimized_classes,
                dependency_graph=dependency_graph,
                module_order=module_order,
                forward_refs=forward_refs,
                consolidated_modules=consolidated_modules,
            )

            logger.info(
                f"Optimization complete. Forward refs needed for {len(forward_refs)} classes"
            )
            return optimized_ir

        except Exception as e:
            raise IROptimizerError(f"Failed to optimize IR: {e}") from e

    def _build_dependency_graph(
        self, ir: IntermediateRepresentation
    ) -> dict[str, DependencyNode]:
        """Build directed dependency graph from class definitions."""
        logger.info("Building dependency graph...")

        graph = {}

        # Initialize nodes
        for class_name, class_def in ir.classes.items():
            graph[class_name] = DependencyNode(
                name=class_name,
                module=class_def.module,
                dependencies=set(),
                dependents=set(),
            )

        # Add dependency edges
        for class_name, class_def in ir.classes.items():
            node = graph[class_name]

            # Dependencies from base classes
            for base in class_def.bases:
                if base in graph and base != class_name:
                    node.dependencies.add(base)
                    graph[base].dependents.add(class_name)

            # Dependencies from attribute types
            for attr in class_def.attrs:
                if attr.range in graph and attr.range != class_name:
                    node.dependencies.add(attr.range)
                    graph[attr.range].dependents.add(class_name)

        logger.info(f"Built dependency graph with {len(graph)} nodes")
        return graph

    def _find_strongly_connected_components(
        self, graph: dict[str, DependencyNode]
    ) -> None:
        """Find strongly connected components using Tarjan's algorithm."""
        logger.info("Finding strongly connected components...")

        # Reset algorithm state
        self.visited = set()
        self.stack = []
        self.index_counter = 0
        self.strongly_connected_components = []

        # Node data for Tarjan's algorithm
        indices = {}
        lowlinks = {}
        on_stack = set()

        def tarjan_visit(node_name: str) -> None:
            """Visit node in Tarjan's algorithm."""
            # Set the depth index for this node
            indices[node_name] = self.index_counter
            lowlinks[node_name] = self.index_counter
            self.index_counter += 1
            self.stack.append(node_name)
            on_stack.add(node_name)

            # Consider successors (dependencies)
            node = graph[node_name]
            for dep_name in node.dependencies:
                if dep_name not in graph:
                    continue  # Skip external dependencies

                if dep_name not in indices:
                    # Successor has not yet been visited; recurse
                    tarjan_visit(dep_name)
                    lowlinks[node_name] = min(lowlinks[node_name], lowlinks[dep_name])
                elif dep_name in on_stack:
                    # Successor is in stack and hence in the current SCC
                    lowlinks[node_name] = min(lowlinks[node_name], indices[dep_name])

            # If node is a root node, pop the stack and generate an SCC
            if lowlinks[node_name] == indices[node_name]:
                component = []
                while True:
                    w = self.stack.pop()
                    on_stack.remove(w)
                    component.append(w)
                    if w == node_name:
                        break
                self.strongly_connected_components.append(component)

        # Run Tarjan's algorithm on all unvisited nodes
        for node_name in graph:
            if node_name not in indices:
                tarjan_visit(node_name)

        # Mark nodes that are in cycles
        for component in self.strongly_connected_components:
            if len(component) > 1:  # Cycle detected
                logger.info(f"Found cycle with {len(component)} classes: {component}")
                for node_name in component:
                    if node_name in graph:
                        graph[node_name].in_cycle = True

        logger.info(
            f"Found {len(self.strongly_connected_components)} strongly connected components"
        )

    def _identify_forward_references(
        self, ir: IntermediateRepresentation, graph: dict[str, DependencyNode]
    ) -> dict[str, set[str]]:
        """Identify which type references need to be forward references."""
        logger.info("Identifying forward references...")

        forward_refs = defaultdict(set)

        for class_name, class_def in ir.classes.items():
            node = graph.get(class_name)
            if not node:
                continue

            # If class is in a cycle, some references may need to be forward refs
            if node.in_cycle:
                # Check each dependency
                for dep_name in node.dependencies:
                    dep_node = graph.get(dep_name)
                    if dep_node and dep_node.in_cycle:
                        # Both classes are in cycles - check if same module
                        if class_def.module == dep_node.module:
                            # Same module + cycle = forward reference needed
                            forward_refs[class_name].add(dep_name)
                        # Different modules can usually import directly

            # Also check for self-references
            for attr in class_def.attrs:
                if attr.range == class_name:
                    forward_refs[class_name].add(class_name)

        # Additional heuristics for forward references
        for class_name, class_def in ir.classes.items():
            current_module = class_def.module

            # Check attribute types for same-module references
            for attr in class_def.attrs:
                if attr.range in ir.classes:
                    attr_class = ir.classes[attr.range]
                    if attr_class.module == current_module and attr.range != class_name:
                        # Check if this creates an import ordering issue
                        if self._would_create_import_cycle(class_name, attr.range, ir):
                            forward_refs[class_name].add(attr.range)

        total_forward_refs = sum(len(refs) for refs in forward_refs.values())
        logger.info(
            f"Identified {total_forward_refs} forward references across {len(forward_refs)} classes"
        )

        return dict(forward_refs)

    def _would_create_import_cycle(
        self, class_a: str, class_b: str, ir: IntermediateRepresentation
    ) -> bool:
        """Check if importing class_b in class_a would create a cycle."""
        # Simple heuristic: if class_b also references class_a, it's likely a cycle
        class_b_def = ir.classes.get(class_b)
        if not class_b_def:
            return False

        # Check if class_b has class_a as base or attribute type
        if class_a in class_b_def.bases:
            return True

        for attr in class_b_def.attrs:
            if attr.range == class_a:
                return True

        return False

    def _update_class_definitions(
        self, classes: dict[str, ClassDef], forward_refs: dict[str, set[str]]
    ) -> dict[str, ClassDef]:
        """Update class definitions with forward reference information."""
        logger.info("Updating class definitions with forward reference flags...")

        updated_classes = {}

        for class_name, class_def in classes.items():
            # Create copy of class definition
            updated_attrs = []

            for attr in class_def.attrs:
                # Check if this attribute type should be a forward reference
                should_be_forward_ref = (
                    class_name in forward_refs
                    and attr.range in forward_refs[class_name]
                )

                updated_attr = AttrDef(
                    name=attr.name,
                    range=attr.range,
                    mult=attr.mult,
                    forward_ref=should_be_forward_ref,
                    description=attr.description,
                    functional=attr.functional,
                    inverse_of=attr.inverse_of,
                )
                updated_attrs.append(updated_attr)

            updated_class = ClassDef(
                name=class_def.name,
                bases=class_def.bases,
                module=class_def.module,
                attrs=updated_attrs,
                annotations=class_def.annotations,
                is_abstract=class_def.is_abstract,
                description=class_def.description,
                namespace_iri=class_def.namespace_iri,
            )

            updated_classes[class_name] = updated_class

        return updated_classes

    def _determine_module_order(self, graph: dict[str, DependencyNode]) -> list[str]:
        """Determine optimal module ordering for code generation."""
        logger.info("Determining module ordering...")

        # Group nodes by module
        modules = defaultdict(set)
        for node in graph.values():
            modules[node.module].add(node.name)

        # Build module dependency graph
        module_deps = defaultdict(set)
        for node in graph.values():
            for dep_name in node.dependencies:
                dep_node = graph.get(dep_name)
                if dep_node and dep_node.module != node.module:
                    module_deps[node.module].add(dep_node.module)

        # Topological sort of modules
        module_order = self._topological_sort_modules(module_deps)

        logger.info(f"Module order: {module_order}")
        return module_order

    def _topological_sort_modules(self, module_deps: dict[str, set[str]]) -> list[str]:
        """Topologically sort modules by dependencies."""
        # Kahn's algorithm for topological sorting
        # We want dependencies to come before dependents
        in_degree = defaultdict(int)
        all_modules = set(module_deps.keys())

        # Add modules that are dependencies but not in keys
        for deps in module_deps.values():
            all_modules.update(deps)

        # Calculate in-degrees - how many modules this module depends on
        for module in all_modules:
            in_degree[module] = 0

        # Count incoming edges (dependencies)
        for module, deps in module_deps.items():
            in_degree[module] = len(deps)

        # Queue of modules with no dependencies (in-degree 0)
        queue = deque([module for module in all_modules if in_degree[module] == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(current)

            # For each module that depends on current, reduce its in-degree
            for module, deps in module_deps.items():
                if current in deps:
                    in_degree[module] -= 1
                    if in_degree[module] == 0:
                        queue.append(module)

        # Check for cycles in module dependencies
        if len(result) != len(all_modules):
            logger.warning("Cycle detected in module dependencies, using partial order")
            # Add remaining modules
            for module in all_modules:
                if module not in result:
                    result.append(module)

        return result

    def _apply_consolidation_rules(
        self, ir: IntermediateRepresentation
    ) -> dict[str, set[str]]:
        """Apply class consolidation rules from configuration."""
        logger.info("Applying consolidation rules...")

        consolidated = defaultdict(set)

        # Group classes by module for potential consolidation
        for class_name, class_def in ir.classes.items():
            base_module = class_def.module

            # Check for vocabulary classes (ending in _Ov)
            if class_name.endswith("_Ov"):
                consolidated_module = f"{base_module}.vocab"
                consolidated[consolidated_module].add(class_name)

            # Check for relationship classes
            elif "Relationship" in class_name or class_name.startswith("Union"):
                consolidated_module = f"{base_module}.relationships"
                consolidated[consolidated_module].add(class_name)

            # Regular classes stay in their own modules
            else:
                consolidated[base_module].add(class_name)

        logger.info(f"Consolidated into {len(consolidated)} modules")
        return dict(consolidated)
