"""
Unit tests for the Grid-STIX code generation pipeline components in src/.

This module tests the core pipeline orchestration and error handling.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from owlready2 import World

from generator.pipeline import (
    generate_python_classes,
    GenerationPipelineError,
)


class TestGenerationPipeline:
    """Test cases for the main generation pipeline."""

    def test_generate_python_classes_success(self):
        """Test successful pipeline execution with all stages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = str(Path(temp_dir) / "test.owl")
            output_dir = str(Path(temp_dir) / "output")

            # Create a minimal test ontology file
            with open(ontology_path, "w") as f:
                f.write(
                    """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:owl="http://www.w3.org/2002/07/owl#">
    <owl:Ontology rdf:about="http://test.example.com/ontology"/>
    <owl:Class rdf:about="http://test.example.com/TestClass"/>
</rdf:RDF>"""
                )

            with patch("generator.pipeline.load_ontology") as mock_load, patch(
                "generator.pipeline.IRBuilder"
            ) as mock_ir_builder, patch(
                "generator.pipeline.IROptimizer"
            ) as mock_optimizer, patch(
                "generator.pipeline.generate_python_code"
            ) as mock_gen_code:

                # Setup mocks
                mock_world = Mock(spec=World)
                mock_load.return_value = mock_world

                mock_ir_instance = Mock()
                mock_ir = Mock()
                mock_ir_instance.build_ir.return_value = mock_ir
                mock_ir_builder.return_value = mock_ir_instance

                mock_opt_instance = Mock()
                mock_optimized_ir = Mock()
                mock_opt_instance.optimize_ir.return_value = mock_optimized_ir
                mock_optimizer.return_value = mock_opt_instance

                # Execute pipeline
                generate_python_classes(ontology_path, output_dir)

                # Verify all stages were called
                mock_load.assert_called_once()
                mock_ir_builder.assert_called_once()
                mock_ir_instance.build_ir.assert_called_once_with(mock_world)
                mock_optimizer.assert_called_once()
                mock_opt_instance.optimize_ir.assert_called_once_with(mock_ir)
                mock_gen_code.assert_called_once()

    def test_generate_python_classes_with_custom_config(self):
        """Test pipeline with custom configuration paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = str(Path(temp_dir) / "test.owl")
            output_dir = str(Path(temp_dir) / "output")
            config_path = str(Path(temp_dir) / "config.yml")
            templates_dir = str(Path(temp_dir) / "templates")

            # Create test files
            with open(ontology_path, "w") as f:
                f.write('<?xml version="1.0"?><rdf:RDF></rdf:RDF>')

            with open(config_path, "w") as f:
                f.write("namespaces: {}")

            Path(templates_dir).mkdir()

            with patch("generator.pipeline.load_ontology") as mock_load, patch(
                "generator.pipeline.IRBuilder"
            ) as mock_ir_builder, patch(
                "generator.pipeline.IROptimizer"
            ) as mock_optimizer, patch(
                "generator.pipeline.generate_python_code"
            ) as mock_gen_code:

                mock_load.return_value = Mock(spec=World)
                mock_ir_builder.return_value.build_ir.return_value = Mock()
                mock_optimizer.return_value.optimize_ir.return_value = Mock()

                generate_python_classes(
                    ontology_path,
                    output_dir,
                    config_path=config_path,
                    templates_dir=templates_dir,
                    reason=False,
                    sqlite_backend="test.db",
                )

                # Verify custom parameters were passed
                mock_load.assert_called_once_with(
                    ontology_path, reason=False, sqlite_backend="test.db"
                )
                mock_ir_builder.assert_called_once_with(config_path)

    def test_generate_python_classes_stage1_failure(self):
        """Test pipeline failure in Stage 1 (ontology loading)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = str(Path(temp_dir) / "test.owl")
            output_dir = str(Path(temp_dir) / "output")

            with patch("generator.pipeline.load_ontology") as mock_load:
                mock_load.side_effect = Exception("Failed to load ontology")

                with pytest.raises(GenerationPipelineError) as exc_info:
                    generate_python_classes(ontology_path, output_dir)

                assert "Generation pipeline failed" in str(exc_info.value)
                assert "Failed to load ontology" in str(exc_info.value)

    def test_generate_python_classes_stage2_failure(self):
        """Test pipeline failure in Stage 2 (IR building)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = str(Path(temp_dir) / "test.owl")
            output_dir = str(Path(temp_dir) / "output")

            with patch("generator.pipeline.load_ontology") as mock_load, patch(
                "generator.pipeline.IRBuilder"
            ) as mock_ir_builder:

                mock_load.return_value = Mock(spec=World)
                mock_ir_instance = Mock()
                mock_ir_instance.build_ir.side_effect = Exception("IR building failed")
                mock_ir_builder.return_value = mock_ir_instance

                with pytest.raises(GenerationPipelineError) as exc_info:
                    generate_python_classes(ontology_path, output_dir)

                assert "Generation pipeline failed" in str(exc_info.value)
                assert "IR building failed" in str(exc_info.value)

    def test_generate_python_classes_stage3_failure(self):
        """Test pipeline failure in Stage 3 (IR optimization)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = str(Path(temp_dir) / "test.owl")
            output_dir = str(Path(temp_dir) / "output")

            with patch("generator.pipeline.load_ontology") as mock_load, patch(
                "generator.pipeline.IRBuilder"
            ) as mock_ir_builder, patch(
                "generator.pipeline.IROptimizer"
            ) as mock_optimizer:

                mock_load.return_value = Mock(spec=World)
                mock_ir_builder.return_value.build_ir.return_value = Mock()

                mock_opt_instance = Mock()
                mock_opt_instance.optimize_ir.side_effect = Exception(
                    "Optimization failed"
                )
                mock_optimizer.return_value = mock_opt_instance

                with pytest.raises(GenerationPipelineError) as exc_info:
                    generate_python_classes(ontology_path, output_dir)

                assert "Generation pipeline failed" in str(exc_info.value)
                assert "Optimization failed" in str(exc_info.value)

    def test_generate_python_classes_stage4_failure(self):
        """Test pipeline failure in Stage 4 (code generation)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = str(Path(temp_dir) / "test.owl")
            output_dir = str(Path(temp_dir) / "output")

            with patch("generator.pipeline.load_ontology") as mock_load, patch(
                "generator.pipeline.IRBuilder"
            ) as mock_ir_builder, patch(
                "generator.pipeline.IROptimizer"
            ) as mock_optimizer, patch(
                "generator.pipeline.generate_python_code"
            ) as mock_gen_code:

                mock_load.return_value = Mock(spec=World)
                mock_ir_builder.return_value.build_ir.return_value = Mock()
                mock_optimizer.return_value.optimize_ir.return_value = Mock()
                mock_gen_code.side_effect = Exception("Code generation failed")

                with pytest.raises(GenerationPipelineError) as exc_info:
                    generate_python_classes(ontology_path, output_dir)

                assert "Generation pipeline failed" in str(exc_info.value)
                assert "Code generation failed" in str(exc_info.value)

    def test_default_paths_resolution(self):
        """Test that default config and template paths are resolved correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = str(Path(temp_dir) / "test.owl")
            output_dir = str(Path(temp_dir) / "output")

            with patch("generator.pipeline.load_ontology") as mock_load, patch(
                "generator.pipeline.IRBuilder"
            ) as mock_ir_builder, patch(
                "generator.pipeline.IROptimizer"
            ) as mock_optimizer, patch(
                "generator.pipeline.generate_python_code"
            ) as mock_gen_code:

                mock_load.return_value = Mock(spec=World)
                mock_ir_builder.return_value.build_ir.return_value = Mock()
                mock_optimizer.return_value.optimize_ir.return_value = Mock()

                generate_python_classes(ontology_path, output_dir)

                # Check that IRBuilder was called with default config path
                args, kwargs = mock_ir_builder.call_args
                config_path = args[0]
                assert config_path.endswith("config.yml")

                # Check that generate_python_code was called with default templates path
                args, kwargs = mock_gen_code.call_args
                templates_dir = args[1]
                assert templates_dir.endswith("templates")


class TestPipelineIntegration:
    """Integration tests for pipeline components working together."""

    def test_pipeline_logging_messages(self):
        """Test that pipeline produces expected logging messages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ontology_path = str(Path(temp_dir) / "test.owl")
            output_dir = str(Path(temp_dir) / "output")

            with patch("generator.pipeline.load_ontology") as mock_load, patch(
                "generator.pipeline.IRBuilder"
            ) as mock_ir_builder, patch(
                "generator.pipeline.IROptimizer"
            ) as mock_optimizer, patch(
                "generator.pipeline.generate_python_code"
            ) as mock_gen_code, patch(
                "generator.pipeline.logger"
            ) as mock_logger:

                mock_load.return_value = Mock(spec=World)
                mock_ir_builder.return_value.build_ir.return_value = Mock()
                mock_optimizer.return_value.optimize_ir.return_value = Mock()

                generate_python_classes(ontology_path, output_dir)

                # Verify expected log messages
                expected_messages = [
                    "Starting Grid-STIX Python class generation pipeline...",
                    "Stage 1: Loading ontology...",
                    "Stage 2: Building intermediate representation...",
                    "Stage 3: Optimizing intermediate representation...",
                    "Stage 4: Generating Python code...",
                    "Pipeline completed successfully!",
                ]

                for message in expected_messages:
                    mock_logger.info.assert_any_call(message)

    def test_pipeline_parameter_validation(self):
        """Test pipeline parameter validation and edge cases."""
        # Test with None parameters
        with pytest.raises(Exception):
            generate_python_classes(None, "output")

        with pytest.raises(Exception):
            generate_python_classes("ontology.owl", None)

        # Test with empty strings
        with pytest.raises(Exception):
            generate_python_classes("", "output")

        with pytest.raises(Exception):
            generate_python_classes("ontology.owl", "")
