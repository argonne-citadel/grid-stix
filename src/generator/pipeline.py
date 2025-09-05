"""
Grid-STIX Code Generation Pipeline

This module orchestrates the four-stage generation pipeline for converting
OWL ontologies to Python classes.

Features:
- Pipeline Orchestration:
  • Stage 1: Ontology loading with Owlready2
  • Stage 2: Intermediate representation building
  • Stage 3: Dependency optimization and circular import resolution
  • Stage 4: Python code generation with quality checks
- Error Handling:
  • Comprehensive error reporting at each stage
  • Clean rollback on failures
  • Detailed logging for debugging
- Configuration:
  • Flexible configuration via YAML files
  • Template customization support
  • Output directory management

Use Cases:
- Generate Python libraries from Grid-STIX ontologies
- Automated code generation in CI/CD pipelines
- Custom ontology-to-code transformations
- Batch processing of multiple ontologies
- Development workflow integration
"""

import logging

from pathlib import Path
from typing import Optional

from .build_ir import IRBuilder
from .gen_code import generate_python_code
from .loader import load_ontology
from .optimise_ir import IROptimizer


logger = logging.getLogger(__name__)


class GenerationPipelineError(Exception):
    """Raised when the generation pipeline fails."""

    pass


def generate_python_classes(
    ontology_path: str,
    output_dir: str,
    *,
    config_path: Optional[str] = None,
    templates_dir: Optional[str] = None,
    reason: bool = True,
    sqlite_backend: Optional[str] = None,
) -> None:
    """
    Generate Python classes from OWL ontology using the four-stage pipeline.

    Args:
        ontology_path: Path or URL to the OWL ontology file
        output_dir: Directory where generated Python code will be written
        config_path: Path to YAML configuration file (defaults to bundled config)
        templates_dir: Directory containing Jinja2 templates (defaults to bundled)
        reason: Whether to run the reasoner (default: True)
        sqlite_backend: Optional SQLite file for large ontologies

    Raises:
        GenerationPipelineError: If any stage of the pipeline fails
    """
    logger.info("Starting Grid-STIX Python class generation pipeline...")

    try:
        # Set default paths if not provided
        if config_path is None:
            config_path = str(Path(__file__).parent / "config.yml")
        if templates_dir is None:
            templates_dir = str(Path(__file__).parent / "templates")

        # Stage 1: Load ontology
        logger.info("Stage 1: Loading ontology...")
        world = load_ontology(
            ontology_path, reason=reason, sqlite_backend=sqlite_backend
        )

        # Stage 2: Build intermediate representation
        logger.info("Stage 2: Building intermediate representation...")
        ir_builder = IRBuilder(config_path)
        ir = ir_builder.build_ir(world)

        # Stage 3: Optimize IR and resolve dependencies
        logger.info("Stage 3: Optimizing intermediate representation...")
        optimizer = IROptimizer()
        optimized_ir = optimizer.optimize_ir(ir)

        # Stage 4: Generate Python code
        logger.info("Stage 4: Generating Python code...")
        generate_python_code(optimized_ir, templates_dir, output_dir)

        logger.info("Pipeline completed successfully!")

    except Exception as e:
        raise GenerationPipelineError(f"Generation pipeline failed: {e}") from e
