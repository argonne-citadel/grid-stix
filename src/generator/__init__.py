"""
Grid-STIX Python Code Generator

This package provides a complete pipeline for generating Python classes from OWL/RDF ontologies.
The generation process follows a clean four-stage architecture for maintainability and reliability.

Features:
- Pipeline Architecture:
  • Stage 1: Ontology loading with Owlready2
  • Stage 2: Intermediate representation building
  • Stage 3: Dependency optimization and forward reference resolution
  • Stage 4: Clean Python code generation with Jinja2 templates
- Ontology Processing:
  • Support for OWL/XML, RDF/XML, and Turtle formats
  • HermiT reasoner integration for inference
  • Large ontology support with SQLite backend
  • Comprehensive error handling and validation
- Code Quality:
  • Type-safe Pydantic v2 model generation
  • Automatic black formatting and ruff linting
  • MyPy strict type checking
  • Forward reference resolution for circular imports
- Modularity:
  • Configurable namespace to package mapping
  • Template-based code generation for customization
  • Consolidation rules for related classes
  • Incremental generation support

Use Cases:
- Generate Python libraries from Grid-STIX ontologies
- Create type-safe data models for semantic applications
- Build validation schemas from OWL constraints
- Support automated code generation in CI/CD pipelines
- Enable rapid prototyping from ontology specifications
"""

# Import main components
from .build_ir import IRBuilder
from .gen_code import CodeGenerator
from .optimise_ir import IROptimizer
from .pipeline import generate_python_classes, GenerationPipelineError


# Public API
__all__ = [
    "generate_python_classes",
    "GenerationPipelineError",
    "IRBuilder",
    "IROptimizer",
    "CodeGenerator",
]
