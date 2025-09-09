"""
Unit tests for the Grid-STIX IR (Intermediate Representation) modules.

This module tests IR building, optimization, and code generation functionality.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
from owlready2 import World

from generator.build_ir import (
    IRBuilder,
    IRBuilderError,
    ClassDef,
    AttrDef,
    IntermediateRepresentation,
)
from generator.optimise_ir import (
    IROptimizer,
    IROptimizerError,
    OptimizedIR,
    DependencyNode,
)


class TestIRBuilder:
    """Test cases for intermediate representation building."""

    def test_ir_builder_initialization(self):
        """Test IRBuilder initialization with config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"

            # Create test config
            config_data = {
                "namespaces": {
                    "http://test.example.com/": "test_module",
                    "http://stix.example.com/": "stix2",
                },
                "special_classes": {"TestPattern": "special_handler"},
                "reserved_suffix": "_cls",
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            builder = IRBuilder(str(config_path))

            assert builder.namespaces == config_data["namespaces"]
            assert builder.special_classes == config_data["special_classes"]
            assert builder.reserved_suffix == "_cls"

    def test_ir_builder_config_load_failure(self):
        """Test IRBuilder handling of config load failure."""
        non_existent_config = "/path/that/does/not/exist.yml"

        with pytest.raises(IRBuilderError) as exc_info:
            IRBuilder(non_existent_config)

        assert "Failed to load config" in str(exc_info.value)

    def test_sanitize_class_name(self):
        """Test class name sanitization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"

            with open(config_path, "w") as f:
                yaml.dump({"namespaces": {}}, f)

            builder = IRBuilder(str(config_path))

            # Test various name patterns
            assert builder._sanitize_class_name("test-class") == "TestClass"
            assert builder._sanitize_class_name("test_class") == "TestClass"
            assert builder._sanitize_class_name("TestClass") == "TestClass"
            assert (
                builder._sanitize_class_name("renewablegenerationfacility")
                == "RenewableGenerationFacility"
            )
            assert builder._sanitize_class_name("electricvehicle") == "ElectricVehicle"

            # Test reserved words
            assert builder._sanitize_class_name("class") == "Class_cls"
            assert builder._sanitize_class_name("def") == "Def_cls"

            # Test empty names
            assert builder._sanitize_class_name("") == ""
            assert builder._sanitize_class_name("   ") == ""

    def test_sanitize_attr_name(self):
        """Test attribute name sanitization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"

            with open(config_path, "w") as f:
                yaml.dump({"namespaces": {}}, f)

            builder = IRBuilder(str(config_path))

            # Test various attribute patterns
            assert builder._sanitize_attr_name("hasComponent") == "hascomponent"
            assert builder._sanitize_attr_name("has-component") == "has_component"
            assert builder._sanitize_attr_name("has component") == "has_component"

            # Test reserved words
            assert builder._sanitize_attr_name("class") == "class_attr"
            assert builder._sanitize_attr_name("type") == "type_attr"

    def test_determine_appropriate_base_class(self):
        """Test base class determination logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"

            with open(config_path, "w") as f:
                yaml.dump({"namespaces": {}}, f)

            builder = IRBuilder(str(config_path))

            # Mock OWL class objects
            relationship_class = Mock()
            relationship_class.name = "TestRelationship"

            event_class = Mock()
            event_class.name = "TestEvent"

            domain_class = Mock()
            domain_class.name = "TestDomain"

            # Test base class determination
            assert (
                builder._determine_appropriate_base_class(relationship_class)
                == "GridSTIXRelationshipObject"
            )
            assert (
                builder._determine_appropriate_base_class(event_class)
                == "GridSTIXObservableObject"
            )
            assert (
                builder._determine_appropriate_base_class(domain_class)
                == "GridSTIXDomainObject"
            )

    def test_get_class_name_from_entity(self):
        """Test entity name extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"

            with open(config_path, "w") as f:
                yaml.dump({"namespaces": {}}, f)

            builder = IRBuilder(str(config_path))

            # Test with mock entity
            entity = Mock()
            entity.name = "TestEntity"

            result = builder._get_class_name_from_entity(entity)
            assert result == "TestEntity"

            # Test with basic types
            string_entity = Mock()
            string_entity.name = "string"
            assert builder._get_class_name_from_entity(string_entity) == "str"

            integer_entity = Mock()
            integer_entity.name = "integer"
            assert builder._get_class_name_from_entity(integer_entity) == "int"

            boolean_entity = Mock()
            boolean_entity.name = "boolean"
            assert builder._get_class_name_from_entity(boolean_entity) == "bool"

            # Test with unknown entity (no name attribute)
            unknown_entity = Mock(spec=[])  # Mock with no attributes
            result = builder._get_class_name_from_entity(unknown_entity)
            assert result == "Any"

    def test_build_ir_empty_world(self):
        """Test IR building with empty world."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"

            config_data = {"namespaces": {"http://test.example.com/": "test_module"}}

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            builder = IRBuilder(str(config_path))

            # Mock empty world with context manager support
            mock_world = Mock(spec=World)
            mock_world.__enter__ = Mock(return_value=mock_world)
            mock_world.__exit__ = Mock(return_value=None)
            mock_world._grid_stix_primary_ontology = Mock()
            mock_world._grid_stix_primary_ontology.classes.return_value = []
            mock_world._grid_stix_primary_ontology.object_properties.return_value = []
            mock_world._grid_stix_primary_ontology.data_properties.return_value = []

            result = builder.build_ir(mock_world)

            assert isinstance(result, IntermediateRepresentation)
            assert len(result.classes) == 0
            assert result.namespaces == config_data["namespaces"]

    def test_build_ir_with_classes(self):
        """Test IR building with mock classes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"

            config_data = {"namespaces": {"http://test.example.com/": "test_module"}}

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            builder = IRBuilder(str(config_path))

            # Mock world with classes and context manager support
            mock_world = Mock(spec=World)
            mock_world.__enter__ = Mock(return_value=mock_world)
            mock_world.__exit__ = Mock(return_value=None)
            mock_ontology = Mock()

            # Create mock class
            mock_class = Mock()
            mock_class.name = "TestClass"
            mock_class.iri = "http://test.example.com/TestClass"
            mock_class.namespace.base_iri = "http://test.example.com/"
            mock_class.is_a = []
            mock_class.instances.return_value = []
            mock_class.subclasses.return_value = []

            mock_ontology.classes.return_value = [mock_class]
            mock_ontology.object_properties.return_value = []
            mock_ontology.data_properties.return_value = []

            mock_world._grid_stix_primary_ontology = mock_ontology

            result = builder.build_ir(mock_world)

            assert isinstance(result, IntermediateRepresentation)
            assert len(result.classes) == 1
            assert "TestClass" in result.classes

            class_def = result.classes["TestClass"]
            assert isinstance(class_def, ClassDef)
            assert class_def.name == "TestClass"
            assert class_def.module == "test_module"

    def test_build_ir_failure(self):
        """Test IR building failure handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"

            with open(config_path, "w") as f:
                yaml.dump({"namespaces": {}}, f)

            builder = IRBuilder(str(config_path))

            # Mock world that raises exception
            mock_world = Mock(spec=World)
            mock_world.__enter__ = Mock(side_effect=Exception("World access failed"))

            with pytest.raises(IRBuilderError) as exc_info:
                builder.build_ir(mock_world)

            assert "Failed to build IR" in str(exc_info.value)


class TestIROptimizer:
    """Test cases for IR optimization."""

    def test_ir_optimizer_initialization(self):
        """Test IROptimizer initialization."""
        optimizer = IROptimizer()

        assert optimizer.visited == set()
        assert optimizer.stack == []
        assert optimizer.index_counter == 0
        assert optimizer.strongly_connected_components == []

    def test_build_dependency_graph_simple(self):
        """Test dependency graph building with simple classes."""
        optimizer = IROptimizer()

        # Create simple IR with two classes
        class_a = ClassDef(
            name="ClassA",
            bases=["ClassB"],
            module="test_module",
            attrs=[],
        )

        class_b = ClassDef(
            name="ClassB",
            bases=[],
            module="test_module",
            attrs=[],
        )

        ir = IntermediateRepresentation(
            classes={"ClassA": class_a, "ClassB": class_b},
            namespaces={},
            imports={},
            special_handlers={},
        )

        graph = optimizer._build_dependency_graph(ir)

        assert len(graph) == 2
        assert "ClassA" in graph
        assert "ClassB" in graph

        # ClassA should depend on ClassB
        assert "ClassB" in graph["ClassA"].dependencies
        assert "ClassA" in graph["ClassB"].dependents

    def test_build_dependency_graph_with_attributes(self):
        """Test dependency graph building with attribute dependencies."""
        optimizer = IROptimizer()

        # Create IR with attribute dependencies
        attr = AttrDef(name="ref", range="ClassB", mult="1")

        class_a = ClassDef(
            name="ClassA",
            bases=[],
            module="test_module",
            attrs=[attr],
        )

        class_b = ClassDef(
            name="ClassB",
            bases=[],
            module="test_module",
            attrs=[],
        )

        ir = IntermediateRepresentation(
            classes={"ClassA": class_a, "ClassB": class_b},
            namespaces={},
            imports={},
            special_handlers={},
        )

        graph = optimizer._build_dependency_graph(ir)

        # ClassA should depend on ClassB through attribute
        assert "ClassB" in graph["ClassA"].dependencies
        assert "ClassA" in graph["ClassB"].dependents

    def test_find_strongly_connected_components_no_cycles(self):
        """Test SCC detection with no cycles."""
        optimizer = IROptimizer()

        # Create graph with no cycles
        graph = {
            "A": DependencyNode("A", "module", {"B"}, set()),
            "B": DependencyNode("B", "module", {"C"}, {"A"}),
            "C": DependencyNode("C", "module", set(), {"B"}),
        }

        optimizer._find_strongly_connected_components(graph)

        # Should find 3 SCCs (one for each node)
        assert len(optimizer.strongly_connected_components) == 3

        # No nodes should be marked as in cycle
        for node in graph.values():
            assert not node.in_cycle

    def test_find_strongly_connected_components_with_cycle(self):
        """Test SCC detection with cycles."""
        optimizer = IROptimizer()

        # Create graph with cycle: A -> B -> A
        graph = {
            "A": DependencyNode("A", "module", {"B"}, {"B"}),
            "B": DependencyNode("B", "module", {"A"}, {"A"}),
        }

        optimizer._find_strongly_connected_components(graph)

        # Should find 1 SCC with both nodes
        assert len(optimizer.strongly_connected_components) == 1
        assert len(optimizer.strongly_connected_components[0]) == 2

        # Both nodes should be marked as in cycle
        assert graph["A"].in_cycle
        assert graph["B"].in_cycle

    def test_identify_forward_references(self):
        """Test forward reference identification."""
        optimizer = IROptimizer()

        # Create IR with potential forward references
        attr = AttrDef(name="self_ref", range="ClassA", mult="1")

        class_a = ClassDef(
            name="ClassA",
            bases=[],
            module="test_module",
            attrs=[attr],  # Self-reference
        )

        ir = IntermediateRepresentation(
            classes={"ClassA": class_a},
            namespaces={},
            imports={},
            special_handlers={},
        )

        # Create graph with self-cycle
        graph = {
            "ClassA": DependencyNode("ClassA", "test_module", {"ClassA"}, {"ClassA"})
        }
        graph["ClassA"].in_cycle = True

        forward_refs = optimizer._identify_forward_references(ir, graph)

        # Should identify self-reference as forward reference
        assert "ClassA" in forward_refs
        assert "ClassA" in forward_refs["ClassA"]

    def test_would_create_import_cycle(self):
        """Test import cycle detection."""
        optimizer = IROptimizer()

        # Create IR with mutual references
        attr_a = AttrDef(name="ref_b", range="ClassB", mult="1")
        attr_b = AttrDef(name="ref_a", range="ClassA", mult="1")

        class_a = ClassDef(
            name="ClassA",
            bases=[],
            module="test_module",
            attrs=[attr_a],
        )

        class_b = ClassDef(
            name="ClassB",
            bases=[],
            module="test_module",
            attrs=[attr_b],
        )

        ir = IntermediateRepresentation(
            classes={"ClassA": class_a, "ClassB": class_b},
            namespaces={},
            imports={},
            special_handlers={},
        )

        # Test cycle detection
        would_cycle = optimizer._would_create_import_cycle("ClassA", "ClassB", ir)
        assert would_cycle is True

        # Test non-cycle case
        class_c = ClassDef(
            name="ClassC",
            bases=[],
            module="test_module",
            attrs=[],
        )
        ir.classes["ClassC"] = class_c

        would_cycle = optimizer._would_create_import_cycle("ClassA", "ClassC", ir)
        assert would_cycle is False

    def test_topological_sort_modules(self):
        """Test topological sorting of modules."""
        optimizer = IROptimizer()

        # Create module dependencies: A depends on B, B depends on C
        # This means C should be processed first, then B, then A
        module_deps = {
            "module_a": {"module_b"},
            "module_b": {"module_c"},
            "module_c": set(),
        }

        result = optimizer._topological_sort_modules(module_deps)

        # In topological order, dependencies should come before dependents
        # module_c has no dependencies, so it should come first
        # module_b depends on module_c, so it should come after module_c
        # module_a depends on module_b, so it should come after module_b
        assert result.index("module_c") < result.index("module_b")
        assert result.index("module_b") < result.index("module_a")

    def test_topological_sort_modules_with_cycle(self):
        """Test topological sorting with circular dependencies."""
        optimizer = IROptimizer()

        # Create circular dependencies: A -> B -> A
        module_deps = {
            "module_a": {"module_b"},
            "module_b": {"module_a"},
        }

        result = optimizer._topological_sort_modules(module_deps)

        # Should still return all modules despite cycle
        assert len(result) == 2
        assert "module_a" in result
        assert "module_b" in result

    def test_apply_consolidation_rules(self):
        """Test class consolidation rules."""
        optimizer = IROptimizer()

        # Create IR with different class types
        vocab_class = ClassDef(
            name="TestVocab_Ov",
            bases=[],
            module="test_module",
            attrs=[],
        )

        relationship_class = ClassDef(
            name="TestRelationship",
            bases=[],
            module="test_module",
            attrs=[],
        )

        regular_class = ClassDef(
            name="RegularClass",
            bases=[],
            module="test_module",
            attrs=[],
        )

        ir = IntermediateRepresentation(
            classes={
                "TestVocab_Ov": vocab_class,
                "TestRelationship": relationship_class,
                "RegularClass": regular_class,
            },
            namespaces={},
            imports={},
            special_handlers={},
        )

        result = optimizer._apply_consolidation_rules(ir)

        # Check consolidation results
        assert "test_module.vocab" in result
        assert "test_module.relationships" in result
        assert "test_module" in result

        assert "TestVocab_Ov" in result["test_module.vocab"]
        assert "TestRelationship" in result["test_module.relationships"]
        assert "RegularClass" in result["test_module"]

    def test_optimize_ir_complete_workflow(self):
        """Test complete IR optimization workflow."""
        optimizer = IROptimizer()

        # Create simple IR
        class_a = ClassDef(
            name="ClassA",
            bases=["ClassB"],
            module="test_module",
            attrs=[],
        )

        class_b = ClassDef(
            name="ClassB",
            bases=[],
            module="test_module",
            attrs=[],
        )

        ir = IntermediateRepresentation(
            classes={"ClassA": class_a, "ClassB": class_b},
            namespaces={},
            imports={},
            special_handlers={},
        )

        result = optimizer.optimize_ir(ir)

        assert isinstance(result, OptimizedIR)
        assert len(result.classes) == 2
        assert len(result.dependency_graph) == 2
        assert isinstance(result.module_order, list)
        assert isinstance(result.forward_refs, dict)
        assert isinstance(result.consolidated_modules, dict)

    def test_optimize_ir_failure(self):
        """Test IR optimization failure handling."""
        optimizer = IROptimizer()

        # Create IR that will cause failure
        with patch.object(
            optimizer,
            "_build_dependency_graph",
            side_effect=Exception("Graph building failed"),
        ):
            ir = IntermediateRepresentation(
                classes={},
                namespaces={},
                imports={},
                special_handlers={},
            )

            with pytest.raises(IROptimizerError) as exc_info:
                optimizer.optimize_ir(ir)

            assert "Failed to optimize IR" in str(exc_info.value)


class TestIRIntegration:
    """Integration tests for IR building and optimization."""

    def test_ir_builder_to_optimizer_workflow(self):
        """Test complete workflow from IR building to optimization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"

            config_data = {"namespaces": {"http://test.example.com/": "test_module"}}

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Build IR
            builder = IRBuilder(str(config_path))

            mock_world = Mock(spec=World)
            mock_world.__enter__ = Mock(return_value=mock_world)
            mock_world.__exit__ = Mock(return_value=None)
            mock_ontology = Mock()
            mock_ontology.classes.return_value = []
            mock_ontology.object_properties.return_value = []
            mock_ontology.data_properties.return_value = []
            mock_world._grid_stix_primary_ontology = mock_ontology

            ir = builder.build_ir(mock_world)

            # Optimize IR
            optimizer = IROptimizer()
            optimized_ir = optimizer.optimize_ir(ir)

            # Verify workflow completion
            assert isinstance(ir, IntermediateRepresentation)
            assert isinstance(optimized_ir, OptimizedIR)
            assert optimized_ir.classes == ir.classes

    def test_ir_data_structures_consistency(self):
        """Test consistency of IR data structures."""
        # Test ClassDef creation
        attr = AttrDef(
            name="test_attr",
            range="str",
            mult="1",
            forward_ref=False,
            description="Test attribute",
            functional=True,
            inverse_of=None,
        )

        class_def = ClassDef(
            name="TestClass",
            bases=["BaseClass"],
            module="test_module",
            attrs=[attr],
            annotations={"test": "value"},
            is_abstract=False,
            description="Test class",
            namespace_iri="http://test.example.com/",
        )

        # Verify all fields are accessible
        assert class_def.name == "TestClass"
        assert class_def.bases == ["BaseClass"]
        assert class_def.module == "test_module"
        assert len(class_def.attrs) == 1
        assert class_def.attrs[0].name == "test_attr"
        assert class_def.annotations["test"] == "value"
        assert class_def.is_abstract is False
        assert class_def.description == "Test class"
        assert class_def.namespace_iri == "http://test.example.com/"

    def test_dependency_node_creation(self):
        """Test DependencyNode creation and manipulation."""
        node = DependencyNode(
            name="TestNode",
            module="test_module",
            dependencies={"NodeB", "NodeC"},
            dependents={"NodeA"},
            in_cycle=False,
        )

        assert node.name == "TestNode"
        assert node.module == "test_module"
        assert "NodeB" in node.dependencies
        assert "NodeC" in node.dependencies
        assert "NodeA" in node.dependents
        assert node.in_cycle is False

        # Test cycle marking
        node.in_cycle = True
        assert node.in_cycle is True

    def test_optimized_ir_structure(self):
        """Test OptimizedIR structure and content."""
        class_def = ClassDef(
            name="TestClass",
            bases=[],
            module="test_module",
            attrs=[],
        )

        dependency_node = DependencyNode(
            name="TestClass",
            module="test_module",
            dependencies=set(),
            dependents=set(),
        )

        optimized_ir = OptimizedIR(
            classes={"TestClass": class_def},
            dependency_graph={"TestClass": dependency_node},
            module_order=["test_module"],
            forward_refs={"TestClass": {"SelfRef"}},
            consolidated_modules={"test_module": {"TestClass"}},
        )

        assert len(optimized_ir.classes) == 1
        assert "TestClass" in optimized_ir.classes
        assert len(optimized_ir.dependency_graph) == 1
        assert "TestClass" in optimized_ir.dependency_graph
        assert optimized_ir.module_order == ["test_module"]
        assert "TestClass" in optimized_ir.forward_refs
        assert "SelfRef" in optimized_ir.forward_refs["TestClass"]
        assert "test_module" in optimized_ir.consolidated_modules
        assert "TestClass" in optimized_ir.consolidated_modules["test_module"]
