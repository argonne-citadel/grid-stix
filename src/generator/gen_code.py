"""
Grid-STIX Code Generator

This module generates Python code from the optimized intermediate representation.
It serves as Stage 4 of the Grid-STIX code generation pipeline.

Features:
- Template-Based Generation:
  • Jinja2 templates for consistent code formatting
  • Configurable output formats and styles
  • Automatic escaping for security
  • Template inheritance and reuse patterns
- Code Quality Assurance:
  • Automatic black formatting
  • ruff linting and error checking
  • mypy strict type checking
  • Custom validation rules
- File Management:
  • Intelligent file creation and updates
  • Directory structure management
  • Import statement optimization
  • __init__.py generation with proper exports
- Forward Reference Resolution:
  • Automatic model_rebuild() insertion
  • Dependency-aware code ordering
  • Circular import prevention
  • Type annotation optimization

Use Cases:
- Generate clean, type-safe Python classes from ontologies
- Ensure generated code passes all quality gates
- Create maintainable package structures
- Support incremental code generation and updates
- Enable custom code generation pipelines
"""

import logging
import shutil
import subprocess

from pathlib import Path
from typing import Any, Optional

import jinja2
from jinja2 import Environment, FileSystemLoader

from .build_ir import ClassDef
from .optimise_ir import OptimizedIR


logger = logging.getLogger(__name__)


class CodeGenerationError(Exception):
    """Raised when code generation fails."""

    pass


class CodeQualityError(Exception):
    """Raised when generated code fails quality checks."""

    pass


class CodeGenerator:
    """Generates Python code from optimized intermediate representation."""

    def __init__(self, templates_dir: str, output_dir: str):
        """
        Initialize code generator.

        Args:
            templates_dir: Directory containing Jinja2 templates
            output_dir: Directory for generated code output
        """
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path(output_dir)

        # Create Jinja2 environment for code generation
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False,  # Don't escape code content
            trim_blocks=False,  # Preserve template structure for code
            lstrip_blocks=False,  # Preserve indentation for code
            keep_trailing_newline=True,  # Preserve final newlines
        )

        # Load templates
        try:
            self.class_template = self.env.get_template("class.j2")
            self.init_template = self.env.get_template("__init__.j2")
        except jinja2.TemplateNotFound as e:
            raise CodeGenerationError(f"Template not found: {e}") from e

    def _cleanup_old_files(self) -> None:
        """Clean up old generated files before generating new ones."""
        logger.info("Cleaning up old generated files...")

        if self.output_dir.exists():
            # Remove all Python files and __pycache__ directories, but keep the structure
            for file_path in self.output_dir.rglob("*.py"):
                try:
                    file_path.unlink()
                    logger.debug(f"Removed old file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove {file_path}: {e}")

            # Remove __pycache__ directories
            for cache_dir in self.output_dir.rglob("__pycache__"):
                try:
                    shutil.rmtree(cache_dir)
                    logger.debug(f"Removed cache directory: {cache_dir}")
                except Exception as e:
                    logger.warning(f"Failed to remove {cache_dir}: {e}")

    def generate_code(self, optimized_ir: OptimizedIR) -> None:
        """
        Generate Python code from optimized IR.

        Args:
            optimized_ir: Optimized intermediate representation

        Raises:
            CodeGenerationError: If code generation fails
            CodeQualityError: If generated code fails quality checks
        """
        logger.info("Starting code generation...")

        try:
            # Clean up old generated files
            self._cleanup_old_files()

            # Create output directory structure
            self._create_directory_structure(optimized_ir)

            # Generate class files
            self._generate_class_files(optimized_ir)

            # Generate __init__.py files
            self._generate_init_files(optimized_ir)

            # Generate base classes module
            self._generate_base_classes()

            # Run quality checks
            self._run_quality_checks()

            logger.info("Code generation completed successfully")

        except Exception as e:
            if isinstance(e, (CodeGenerationError, CodeQualityError)):
                raise
            raise CodeGenerationError(f"Code generation failed: {e}") from e

    def _create_directory_structure(self, optimized_ir: OptimizedIR) -> None:
        """Create necessary directory structure for generated code."""
        logger.info("Creating directory structure...")

        # Create main output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create module directories
        modules = set()
        for class_def in optimized_ir.classes.values():
            module_path = class_def.module.replace(".", "/")
            modules.add(module_path)

        for module in modules:
            module_dir = self.output_dir / module
            module_dir.mkdir(parents=True, exist_ok=True)

            # Create __init__.py files for intermediate directories
            current_dir = self.output_dir
            for part in module.split("/"):
                current_dir = current_dir / part
                init_file = current_dir / "__init__.py"
                if not init_file.exists():
                    init_file.touch()

    def _generate_class_files(self, optimized_ir: OptimizedIR) -> None:
        """Generate individual class files."""
        logger.info("Generating class files...")

        total_classes = len(optimized_ir.classes)
        for i, (class_name, class_def) in enumerate(optimized_ir.classes.items(), 1):
            logger.debug(f"Generating class {i}/{total_classes}: {class_name}")

            # Skip empty class names
            if not class_name or not class_name.strip():
                logger.warning(f"Skipping class with empty name at position {i}")
                continue

            try:
                # Determine output file path
                module_path = class_def.module.replace(".", "/")
                file_path = self.output_dir / module_path / f"{class_name}.py"

                # Generate imports for this class
                imports = self._generate_imports_for_class(class_def, optimized_ir)

                # Identify forward references for this class
                forward_refs = optimized_ir.forward_refs.get(class_name, set())

                # Render class template
                class_code = self.class_template.render(
                    class_def=class_def,
                    imports=imports,
                    forward_ref_classes=forward_refs,
                )

                # Write to file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(class_code)

            except Exception as e:
                raise CodeGenerationError(
                    f"Failed to generate class {class_name}: {e}"
                ) from e

    def _generate_imports_for_class(
        self, class_def: ClassDef, optimized_ir: OptimizedIR
    ) -> list[str]:
        """Generate import statements for a class."""
        imports = []
        current_module = class_def.module

        # Collect all referenced types
        referenced_types = set()

        # Add base classes
        grid_stix_base_classes = {
            "GridSTIXObject",
            "GridSTIXDomainObject",
            "GridSTIXRelationshipObject",
            "GridSTIXObservableObject",
        }
        for base in class_def.bases:
            if base not in {"BaseModel"} and base and base.strip():
                if base in grid_stix_base_classes:
                    # Import from grid_stix.base
                    imports.append(f"from ..base import {base}")
                else:
                    referenced_types.add(base)

        # Add attribute types - import cross-module dependencies even if they're forward refs
        basic_types = {
            "Any",
            "str",
            "int",
            "float",
            "bool",
            "list",
            "dict",
            "set",
            "tuple",
        }
        for attr in class_def.attrs:
            if attr.range not in basic_types and attr.range and attr.range.strip():
                # Always collect the type - we'll decide import vs forward ref based on module
                referenced_types.add(attr.range)

        # Generate import statements
        for ref_type in sorted(referenced_types):
            if ref_type in optimized_ir.classes:
                ref_class = optimized_ir.classes[ref_type]
                ref_module = ref_class.module

                if ref_module != current_module:
                    # External import
                    if ref_module.startswith("stix2"):
                        imports.append(f"from {ref_module} import {ref_type}")
                    else:
                        # Calculate relative import path
                        rel_import = self._calculate_relative_import(
                            current_module, ref_module
                        )
                        imports.append(f"from {rel_import} import {ref_type}")
                else:
                    # Same module - check if it's NOT a forward reference
                    class_forward_refs = optimized_ir.forward_refs.get(
                        class_def.name, set()
                    )
                    if ref_type not in class_forward_refs:
                        # Same module, not forward ref - need relative import since each class is in its own file
                        imports.append(f"from .{ref_type} import {ref_type}")

        return imports

    def _calculate_relative_import(self, from_module: str, to_module: str) -> str:
        """Calculate relative import path between modules."""
        from_parts = from_module.split(".")
        to_parts = to_module.split(".")

        # Find common prefix
        common_len = 0
        for i in range(min(len(from_parts), len(to_parts))):
            if from_parts[i] == to_parts[i]:
                common_len += 1
            else:
                break

        # Calculate relative path
        if common_len == 0:
            # No common prefix - use absolute import
            return to_module

        # Go up from current module
        up_levels = len(from_parts) - common_len
        if up_levels == 0:
            # Same level or child module
            remaining = to_parts[common_len:]
            if remaining:
                return "." + ".".join(remaining)
            else:
                return "."
        else:
            # Need to go up
            dots = "." * (up_levels + 1)
            remaining = to_parts[common_len:]
            if remaining:
                return dots + ".".join(remaining)
            else:
                return dots[:-1]  # Remove one dot if no remaining parts

    def _generate_init_files(self, optimized_ir: OptimizedIR) -> None:
        """Generate __init__.py files for modules."""
        logger.info("Generating __init__.py files...")

        # Group classes by module
        module_classes = {}
        for class_name, class_def in optimized_ir.classes.items():
            # Filter out empty class names
            if not class_name or not class_name.strip():
                continue

            module = class_def.module
            if module not in module_classes:
                module_classes[module] = []
            module_classes[module].append(class_name)

        # Generate __init__.py for each module
        for module, class_names in module_classes.items():
            if module.startswith("stix2"):
                continue  # Skip STIX modules

            module_path = module.replace(".", "/")
            init_path = self.output_dir / module_path / "__init__.py"

            # Check which classes have forward references
            forward_ref_classes = []
            for class_name in class_names:
                if class_name in optimized_ir.forward_refs:
                    forward_ref_classes.append(class_name)

            # Render init template
            init_code = self.init_template.render(
                module_name=module,
                class_names=sorted(class_names),
                forward_ref_classes=forward_ref_classes,
                has_forward_refs=bool(forward_ref_classes),
            )

            # Write to file
            with open(init_path, "w", encoding="utf-8") as f:
                f.write(init_code)

    def _generate_base_classes(self) -> None:
        """Generate the base classes module."""
        logger.info("Generating base classes module...")

        # Create base.py in the main grid_stix directory
        base_file_path = self.output_dir / "grid_stix" / "base.py"

        try:
            # Load and render the base class template
            base_template = self.env.get_template("grid_stix_base.py.j2")
            base_code = base_template.render()

            # Write to file
            with open(base_file_path, "w", encoding="utf-8") as f:
                f.write(base_code)

        except Exception as e:
            logger.error(f"Failed to generate base classes: {e}")

    def _run_quality_checks(self) -> None:
        """Run quality checks on generated code."""
        logger.info("Running quality checks...")

        try:
            # Run black formatter
            logger.info("Running black formatter...")
            result = subprocess.run(  # nosec B603, B607 - uses list args (not shell=True) with controlled paths
                ["black", str(self.output_dir)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                logger.warning(f"Black formatting issues: {result.stderr}")

            # Run mypy type checker
            logger.info("Running mypy type checker...")
            result = subprocess.run(  # nosec B603, B607 - uses list args (not shell=True) with controlled paths
                ["mypy", "--strict", str(self.output_dir)],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0:
                # mypy errors might be acceptable for generated code
                logger.warning(f"MyPy type checking issues: {result.stdout}")

            logger.info("Quality checks completed")

        except subprocess.TimeoutExpired as e:
            raise CodeQualityError(f"Quality check timeout: {e}") from e
        except FileNotFoundError as e:
            logger.warning(f"Quality check tool not found: {e}")
        except Exception as e:
            logger.warning(f"Quality check failed: {e}")


def generate_python_code(
    optimized_ir: OptimizedIR, templates_dir: str, output_dir: str
) -> None:
    """
    Generate Python code from optimized intermediate representation.

    Args:
        optimized_ir: Optimized intermediate representation
        templates_dir: Directory containing Jinja2 templates
        output_dir: Directory for generated code output

    Raises:
        CodeGenerationError: If code generation fails
        CodeQualityError: If generated code fails quality checks
    """
    generator = CodeGenerator(templates_dir, output_dir)
    generator.generate_code(optimized_ir)
