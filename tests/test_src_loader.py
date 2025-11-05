"""
Unit tests for the Grid-STIX ontology loader module in src/generator/loader.py.

This module tests ontology loading, reasoning, and error handling functionality.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from owlready2 import World

from generator.loader import (
    load_ontology,
    get_ontology_info,
    OntologyLoadError,
    ReasoningError,
    _resolve_ontology_path,
)


class TestOntologyLoader:
    """Test cases for ontology loading functionality."""

    def test_load_ontology_local_file_success(self):
        """Test successful loading of a local ontology file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = Path(temp_dir) / "test.owl"

            # Create a minimal test ontology file
            with open(ontology_path, "w") as f:
                f.write(
                    """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:owl="http://www.w3.org/2002/07/owl#"
         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
    <owl:Ontology rdf:about="http://test.example.com/ontology"/>
    <owl:Class rdf:about="http://test.example.com/TestClass"/>
</rdf:RDF>"""
                )

            with patch("generator.loader.World") as mock_world_class, patch(
                "generator.loader.get_ontology"
            ) as mock_get_ontology, patch(
                "generator.loader.owlready2.sync_reasoner"
            ) as mock_sync_reasoner:

                # Setup mocks
                mock_world = Mock(spec=World)
                mock_world.__enter__ = Mock(return_value=mock_world)
                mock_world.__exit__ = Mock(return_value=None)
                mock_world_class.return_value = mock_world

                mock_ontology = Mock()
                mock_ontology.classes.return_value = [Mock(), Mock()]  # 2 classes
                mock_ontology.object_properties.return_value = [
                    Mock()
                ]  # 1 object property
                mock_ontology.data_properties.return_value = []  # 0 data properties
                mock_get_ontology.return_value.load.return_value = mock_ontology

                # Execute
                result = load_ontology(str(ontology_path))

                # Verify
                assert result == mock_world
                mock_world_class.assert_called_once()
                mock_get_ontology.assert_called_once()
                mock_sync_reasoner.assert_called_once()

                # Verify ontology was stored in world
                assert hasattr(mock_world, "_grid_stix_primary_ontology")
                assert mock_world._grid_stix_primary_ontology == mock_ontology

    def test_load_ontology_with_sqlite_backend(self):
        """Test loading ontology with SQLite backend."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = Path(temp_dir) / "test.owl"
            sqlite_path = str(Path(temp_dir) / "test.db")

            with open(ontology_path, "w") as f:
                f.write('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')

            with patch("generator.loader.World") as mock_world_class, patch(
                "generator.loader.get_ontology"
            ) as mock_get_ontology, patch(
                "generator.loader.owlready2.sync_reasoner"
            ) as mock_sync_reasoner:

                mock_world = Mock(spec=World)
                mock_world.__enter__ = Mock(return_value=mock_world)
                mock_world.__exit__ = Mock(return_value=None)
                # Add the missing graph attribute for reasoning
                mock_graph = Mock()
                mock_graph.has_write_lock.return_value = False
                mock_world.graph = mock_graph
                mock_world_class.return_value = mock_world

                mock_ontology = Mock()
                mock_ontology.classes.return_value = [Mock(), Mock()]
                mock_ontology.object_properties.return_value = [Mock()]
                mock_ontology.data_properties.return_value = []
                mock_get_ontology.return_value.load.return_value = mock_ontology

                load_ontology(str(ontology_path), sqlite_backend=sqlite_path)

                # Verify SQLite backend was configured
                mock_world.set_backend.assert_called_once_with(filename=sqlite_path)

    def test_load_ontology_without_reasoning(self):
        """Test loading ontology with reasoning disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = Path(temp_dir) / "test.owl"

            with open(ontology_path, "w") as f:
                f.write('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')

            with patch("generator.loader.World") as mock_world_class, patch(
                "generator.loader.get_ontology"
            ) as mock_get_ontology, patch(
                "generator.loader.owlready2.sync_reasoner"
            ) as mock_sync_reasoner:

                mock_world = Mock(spec=World)
                mock_world.__enter__ = Mock(return_value=mock_world)
                mock_world.__exit__ = Mock(return_value=None)
                mock_world_class.return_value = mock_world

                mock_ontology = Mock()
                mock_ontology.classes.return_value = [Mock(), Mock()]
                mock_ontology.object_properties.return_value = [Mock()]
                mock_ontology.data_properties.return_value = []
                mock_get_ontology.return_value.load.return_value = mock_ontology

                load_ontology(str(ontology_path), reason=False)

                # Verify reasoning was not called
                mock_sync_reasoner.assert_not_called()

    def test_load_ontology_file_not_found(self):
        """Test loading non-existent ontology file."""
        non_existent_path = "/path/that/does/not/exist.owl"

        with pytest.raises(OntologyLoadError) as exc_info:
            load_ontology(non_existent_path)

        assert "Ontology file not found" in str(exc_info.value)

    def test_load_ontology_reasoning_failure(self):
        """Test handling of reasoning failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = Path(temp_dir) / "test.owl"

            with open(ontology_path, "w") as f:
                f.write('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')

            with patch("generator.loader.World") as mock_world_class, patch(
                "generator.loader.get_ontology"
            ) as mock_get_ontology, patch(
                "generator.loader.owlready2.sync_reasoner"
            ) as mock_sync_reasoner:

                mock_world = Mock(spec=World)
                mock_world.__enter__ = Mock(return_value=mock_world)
                mock_world.__exit__ = Mock(return_value=None)
                mock_world_class.return_value = mock_world

                mock_ontology = Mock()
                mock_ontology.classes.return_value = [Mock(), Mock()]
                mock_ontology.object_properties.return_value = [Mock()]
                mock_ontology.data_properties.return_value = []
                mock_get_ontology.return_value.load.return_value = mock_ontology
                mock_sync_reasoner.side_effect = Exception("Reasoning failed")

                with pytest.raises(ReasoningError) as exc_info:
                    load_ontology(str(ontology_path))

                assert "Reasoning failed" in str(exc_info.value)

    def test_load_ontology_malformed_file(self):
        """Test loading malformed ontology file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = Path(temp_dir) / "malformed.owl"

            # Create malformed XML
            with open(ontology_path, "w") as f:
                f.write("This is not valid XML or OWL")

            with patch("generator.loader.World") as mock_world_class, patch(
                "generator.loader.get_ontology"
            ) as mock_get_ontology:

                mock_world = Mock(spec=World)
                mock_world_class.return_value = mock_world
                mock_get_ontology.return_value.load.side_effect = Exception(
                    "Parse error"
                )

                with pytest.raises(OntologyLoadError) as exc_info:
                    load_ontology(str(ontology_path))

                assert "Failed to load ontology" in str(exc_info.value)


class TestPathResolution:
    """Test cases for ontology path resolution."""

    def test_resolve_local_file_path(self):
        """Test resolving local file path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.owl"
            test_file.touch()

            result = _resolve_ontology_path(str(test_file))
            assert result == str(test_file.absolute())

    def test_resolve_http_url(self):
        """Test resolving HTTP URL."""
        test_url = "http://example.com/ontology.owl"

        with patch("generator.loader.urlretrieve") as mock_urlretrieve, patch(
            "generator.loader.tempfile.NamedTemporaryFile"
        ) as mock_tempfile:

            mock_temp = Mock()
            mock_temp.name = "/tmp/downloaded.owl"  # nosec B101 - test code
            mock_tempfile.return_value = mock_temp

            result = _resolve_ontology_path(test_url)

            assert result == "/tmp/downloaded.owl"  # nosec B101 - test code
            mock_urlretrieve.assert_called_once_with(
                test_url, "/tmp/downloaded.owl"
            )  # nosec B101 - test code

    def test_resolve_https_url(self):
        """Test resolving HTTPS URL."""
        test_url = "https://example.com/ontology.owl"

        with patch("generator.loader.urlretrieve") as mock_urlretrieve, patch(
            "generator.loader.tempfile.NamedTemporaryFile"
        ) as mock_tempfile:

            mock_temp = Mock()
            mock_temp.name = "/tmp/downloaded.owl"  # nosec B101 - test code
            mock_tempfile.return_value = mock_temp

            result = _resolve_ontology_path(test_url)

            assert result == "/tmp/downloaded.owl"  # nosec B101 - test code
            mock_urlretrieve.assert_called_once_with(
                test_url, "/tmp/downloaded.owl"
            )  # nosec B101 - test code

    def test_resolve_url_download_failure(self):
        """Test handling URL download failure."""
        test_url = "http://example.com/nonexistent.owl"

        with patch("generator.loader.urlretrieve") as mock_urlretrieve:
            mock_urlretrieve.side_effect = Exception("Download failed")

            with pytest.raises(OntologyLoadError) as exc_info:
                _resolve_ontology_path(test_url)

            assert "Failed to download ontology" in str(exc_info.value)

    def test_resolve_nonexistent_local_file(self):
        """Test resolving non-existent local file."""
        nonexistent_path = "/path/that/does/not/exist.owl"

        with pytest.raises(OntologyLoadError) as exc_info:
            _resolve_ontology_path(nonexistent_path)

        assert "Ontology file not found" in str(exc_info.value)

    def test_resolve_directory_instead_of_file(self):
        """Test resolving directory path instead of file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(OntologyLoadError) as exc_info:
                _resolve_ontology_path(temp_dir)

            assert "Path is not a file" in str(exc_info.value)


class TestOntologyInfo:
    """Test cases for ontology information extraction."""

    def test_get_ontology_info_success(self):
        """Test successful extraction of ontology information."""
        mock_world = Mock(spec=World)
        mock_world.__enter__ = Mock(return_value=mock_world)
        mock_world.__exit__ = Mock(return_value=None)
        mock_ontology = Mock()

        # Setup mock classes, properties, individuals
        mock_classes = [Mock(), Mock(), Mock()]  # 3 classes
        mock_object_props = [Mock(), Mock()]  # 2 object properties
        mock_data_props = [Mock()]  # 1 data property
        mock_individuals = []  # 0 individuals

        mock_ontology.classes.return_value = mock_classes
        mock_ontology.object_properties.return_value = mock_object_props
        mock_ontology.data_properties.return_value = mock_data_props
        mock_ontology.individuals.return_value = mock_individuals
        mock_ontology.base_iri = "http://test.example.com/ontology"

        # Setup namespace information
        for i, cls in enumerate(mock_classes):
            mock_namespace = Mock()
            mock_namespace.base_iri = f"http://test.example.com/ns{i}"
            cls.namespace = mock_namespace

        for i, prop in enumerate(mock_object_props + mock_data_props):
            mock_namespace = Mock()
            mock_namespace.base_iri = f"http://test.example.com/ns{i}"
            prop.namespace = mock_namespace

        # Mock the ontologies attribute properly
        mock_ontologies = Mock()
        mock_ontologies.values.return_value = [mock_ontology]
        mock_world.ontologies = mock_ontologies

        result = get_ontology_info(mock_world)

        assert result["ontology_iri"] == "http://test.example.com/ontology"
        assert result["total_classes"] == 3
        assert result["total_object_properties"] == 2
        assert result["total_data_properties"] == 1
        assert result["total_individuals"] == 0
        assert "namespaces" in result

    def test_get_ontology_info_no_ontologies(self):
        """Test handling case with no ontologies in world."""
        mock_world = Mock(spec=World)
        mock_world.__enter__ = Mock(return_value=mock_world)
        mock_world.__exit__ = Mock(return_value=None)
        mock_ontologies = Mock()
        mock_ontologies.values.return_value = []
        mock_world.ontologies = mock_ontologies

        result = get_ontology_info(mock_world)

        assert "error" in result
        assert "No ontologies found" in result["error"]

    def test_get_ontology_info_namespace_counting(self):
        """Test correct counting of entities by namespace."""
        mock_world = Mock(spec=World)
        mock_world.__enter__ = Mock(return_value=mock_world)
        mock_world.__exit__ = Mock(return_value=None)
        mock_ontology = Mock()

        # Create mock entities with specific namespaces
        mock_class1 = Mock()
        mock_class1.namespace.base_iri = "http://ns1.example.com/"
        mock_class2 = Mock()
        mock_class2.namespace.base_iri = "http://ns1.example.com/"
        mock_class3 = Mock()
        mock_class3.namespace.base_iri = "http://ns2.example.com/"

        mock_prop1 = Mock()
        mock_prop1.namespace.base_iri = "http://ns1.example.com/"
        mock_prop2 = Mock()
        mock_prop2.namespace.base_iri = "http://ns2.example.com/"

        mock_ontology.classes.return_value = [mock_class1, mock_class2, mock_class3]
        mock_ontology.object_properties.return_value = [mock_prop1]
        mock_ontology.data_properties.return_value = [mock_prop2]
        mock_ontology.individuals.return_value = []
        mock_ontology.base_iri = "http://test.example.com/ontology"

        # Mock the ontologies attribute properly
        mock_ontologies = Mock()
        mock_ontologies.values.return_value = [mock_ontology]
        mock_world.ontologies = mock_ontologies

        result = get_ontology_info(mock_world)

        namespaces = result["namespaces"]
        assert "http://ns1.example.com/" in namespaces
        assert "http://ns2.example.com/" in namespaces
        assert namespaces["http://ns1.example.com/"]["classes"] == 2
        assert namespaces["http://ns1.example.com/"]["properties"] == 1
        assert namespaces["http://ns2.example.com/"]["classes"] == 1
        assert namespaces["http://ns2.example.com/"]["properties"] == 1


class TestLoaderIntegration:
    """Integration tests for loader functionality."""

    def test_load_ontology_with_reasoning_timeout(self):
        """Test loading ontology with custom reasoning timeout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = Path(temp_dir) / "test.owl"

            with open(ontology_path, "w") as f:
                f.write('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')

            with patch("generator.loader.World") as mock_world_class, patch(
                "generator.loader.get_ontology"
            ) as mock_get_ontology, patch(
                "generator.loader.owlready2.sync_reasoner"
            ) as mock_sync_reasoner:

                mock_world = Mock(spec=World)
                mock_world.__enter__ = Mock(return_value=mock_world)
                mock_world.__exit__ = Mock(return_value=None)
                # Add the missing graph attribute for reasoning
                mock_graph = Mock()
                mock_graph.has_write_lock.return_value = False
                mock_world.graph = mock_graph
                mock_world_class.return_value = mock_world

                mock_ontology = Mock()
                mock_ontology.classes.return_value = [Mock(), Mock()]
                mock_ontology.object_properties.return_value = [Mock()]
                mock_ontology.data_properties.return_value = []
                mock_get_ontology.return_value.load.return_value = mock_ontology

                # Test with custom timeout (parameter is accepted but not directly testable)
                result = load_ontology(str(ontology_path), reasoning_timeout=600)

                assert result == mock_world

    def test_load_ontology_logging_messages(self):
        """Test that loader produces expected logging messages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = Path(temp_dir) / "test.owl"

            with open(ontology_path, "w") as f:
                f.write('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')

            with patch("generator.loader.World") as mock_world_class, patch(
                "generator.loader.get_ontology"
            ) as mock_get_ontology, patch("generator.loader.logger") as mock_logger:

                mock_world = Mock(spec=World)
                mock_world.__enter__ = Mock(return_value=mock_world)
                mock_world.__exit__ = Mock(return_value=None)
                mock_world_class.return_value = mock_world

                mock_ontology = Mock()
                mock_ontology.classes.return_value = [Mock(), Mock()]
                mock_ontology.object_properties.return_value = [Mock()]
                mock_ontology.data_properties.return_value = []
                mock_get_ontology.return_value.load.return_value = mock_ontology

                load_ontology(str(ontology_path), reason=False)

                # Verify expected log messages
                mock_logger.info.assert_any_call(
                    f"Loading ontology from: {ontology_path}"
                )
                mock_logger.info.assert_any_call("Loaded ontology with 2 classes")
                mock_logger.info.assert_any_call("Found 1 object properties")
                mock_logger.info.assert_any_call("Found 0 data properties")
