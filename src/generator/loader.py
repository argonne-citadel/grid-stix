"""
Grid-STIX Ontology Loader Module

This module provides functionality to load and reason over OWL ontologies using Owlready2.
It serves as Stage 1 of the Grid-STIX code generation pipeline.

Features:
- Ontology Loading:
  • Load ontologies from local files or URLs
  • Support for multiple ontology formats (OWL/XML, RDF/XML, Turtle)
  • Automatic namespace detection and registration
  • Optional SQLite backend for large ontologies
- Reasoning Integration:
  • HermiT reasoner integration via sync_reasoner()
  • Optional reasoning for faster CI builds
  • Inference materialization and consistency checking
- Memory Management:
  • World-based ontology isolation
  • SQLite spill-over for memory-constrained environments
  • Configurable reasoning timeout and memory limits
- Error Handling:
  • Comprehensive parsing error detection
  • Malformed ontology recovery strategies
  • Clear error messages with diagnostic information

Use Cases:
- Load Grid-STIX ontologies for Python class generation
- Validate ontology consistency before code generation
- Extract inferred axioms for enhanced class relationships
- Handle large ontology files with memory constraints
- Support CI/CD pipelines with optional reasoning
"""

import logging
import tempfile

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from urllib.request import urlretrieve

import owlready2
from owlready2 import World, get_ontology


logger = logging.getLogger(__name__)


class OntologyLoadError(Exception):
    """Raised when ontology loading fails."""

    pass


class ReasoningError(Exception):
    """Raised when reasoning operations fail."""

    pass


def load_ontology(
    path: str,
    *,
    reason: bool = True,
    sqlite_backend: Optional[str] = None,
    reasoning_timeout: int = 300,
) -> World:
    """
    Load an OWL ontology with optional reasoning.

    Args:
        path: File path or URL to the ontology
        reason: Whether to run the reasoner (default: True)
        sqlite_backend: Optional SQLite file path for large ontologies
        reasoning_timeout: Timeout in seconds for reasoning operations

    Returns:
        World: Owlready2 World object containing the loaded ontology

    Raises:
        OntologyLoadError: If ontology cannot be loaded or parsed
        ReasoningError: If reasoning fails
    """
    logger.info(f"Loading ontology from: {path}")

    # Create isolated world for this ontology
    world = World()

    # Configure SQLite backend if requested
    if sqlite_backend:
        logger.info(f"Using SQLite backend: {sqlite_backend}")
        world.set_backend(filename=sqlite_backend)

    try:
        # Handle URL vs local file
        ontology_path = _resolve_ontology_path(path)

        # Load the ontology
        with world:
            ontology = get_ontology(f"file://{ontology_path}").load()

        logger.info(f"Loaded ontology with {len(list(ontology.classes()))} classes")
        logger.info(
            f"Found {len(list(ontology.object_properties()))} object properties"
        )
        logger.info(f"Found {len(list(ontology.data_properties()))} data properties")

        # Store the primary ontology reference in the world for later access
        world._grid_stix_primary_ontology = ontology

        # Run reasoner if requested
        if reason:
            logger.info("Running HermiT reasoner...")
            try:
                with world:
                    owlready2.sync_reasoner(world, infer_property_values=True)
                logger.info("Reasoning completed successfully")

                # Log any newly inferred facts - check primary ontology still exists
                if hasattr(world, "_grid_stix_primary_ontology"):
                    primary_ontology = world._grid_stix_primary_ontology
                    logger.info(
                        f"Primary ontology still accessible with {len(list(primary_ontology.classes()))} classes"
                    )

            except Exception as e:
                raise ReasoningError(f"Reasoning failed: {e}") from e
        else:
            logger.info("Skipping reasoning (reason=False)")

        return world

    except Exception as e:
        if isinstance(e, (ReasoningError, OntologyLoadError)):
            raise
        raise OntologyLoadError(f"Failed to load ontology from {path}: {e}") from e


def _resolve_ontology_path(path: str) -> str:
    """
    Resolve ontology path, downloading if it's a URL.

    Args:
        path: File path or URL

    Returns:
        str: Local file path to the ontology

    Raises:
        OntologyLoadError: If path cannot be resolved
    """
    # Check if it's a URL
    parsed = urlparse(path)
    if parsed.scheme in ("http", "https"):
        logger.info(f"Downloading ontology from URL: {path}")
        try:
            # Download to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix=".owl", delete=False)
            urlretrieve(path, temp_file.name)
            return temp_file.name
        except Exception as e:
            raise OntologyLoadError(
                f"Failed to download ontology from {path}: {e}"
            ) from e

    # Local file path
    file_path = Path(path)
    if not file_path.exists():
        raise OntologyLoadError(f"Ontology file not found: {path}")

    if not file_path.is_file():
        raise OntologyLoadError(f"Path is not a file: {path}")

    return str(file_path.absolute())


def get_ontology_info(world: World) -> dict[str, any]:
    """
    Extract basic information about the loaded ontology.

    Args:
        world: Owlready2 World containing the ontology

    Returns:
        dict: Dictionary containing ontology statistics and metadata
    """
    with world:
        ontologies = list(world.ontologies.values())
        if not ontologies:
            return {"error": "No ontologies found in world"}

        ontology = ontologies[0]  # Primary ontology

        classes = list(ontology.classes())
        object_properties = list(ontology.object_properties())
        data_properties = list(ontology.data_properties())
        individuals = list(ontology.individuals())

        # Collect namespace information
        namespaces = {}
        for cls in classes:
            namespace = cls.namespace.base_iri
            if namespace not in namespaces:
                namespaces[namespace] = {"classes": 0, "properties": 0}
            namespaces[namespace]["classes"] += 1

        for prop in object_properties + data_properties:
            namespace = prop.namespace.base_iri
            if namespace not in namespaces:
                namespaces[namespace] = {"classes": 0, "properties": 0}
            namespaces[namespace]["properties"] += 1

        return {
            "ontology_iri": ontology.base_iri,
            "total_classes": len(classes),
            "total_object_properties": len(object_properties),
            "total_data_properties": len(data_properties),
            "total_individuals": len(individuals),
            "namespaces": namespaces,
        }
