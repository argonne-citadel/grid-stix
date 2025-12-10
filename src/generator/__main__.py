"""
Grid-STIX Code Generator Command Line Interface

This module provides the command-line interface for the Grid-STIX code generator.
Run with: python -m src.generator <ontology_path> <output_dir>
"""

import argparse
import logging
import sys

from .pipeline import generate_python_classes, GenerationPipelineError


def main() -> None:
    """Command-line interface for the Grid-STIX code generator."""
    parser = argparse.ArgumentParser(
        description="Generate Python classes from Grid-STIX OWL ontologies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.generator ontology.owl python/grid_stix
  python -m src.generator --no-reason ontology.owl output/
  python -m src.generator --config custom.yml ontology.owl output/
        """,
    )

    parser.add_argument("ontology_path", help="Path or URL to the OWL ontology file")

    parser.add_argument(
        "output_dir", help="Directory where generated Python code will be written"
    )

    parser.add_argument("--config", help="Path to YAML configuration file")

    parser.add_argument("--templates", help="Directory containing Jinja2 templates")

    parser.add_argument(
        "--no-reason",
        action="store_false",
        dest="reason",
        help="Skip reasoning for faster generation",
    )

    parser.add_argument(
        "--sqlite-backend", help="SQLite file for large ontology processing"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="WARNING",
        help="Set logging level",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        generate_python_classes(
            ontology_path=args.ontology_path,
            output_dir=args.output_dir,
            config_path=args.config,
            templates_dir=args.templates,
            reason=args.reason,
            sqlite_backend=args.sqlite_backend,
        )

        print(f"Successfully generated Python classes in: {args.output_dir}")

    except GenerationPipelineError as e:
        logging.error(f"Generation failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
