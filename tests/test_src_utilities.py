"""
Unit tests for the Grid-STIX utility modules in src/.

This module tests ontology validation, Python validation, and OWL to HTML conversion utilities.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch


# Test the validate_python.py utility
class TestPythonValidator:
    """Test cases for Python code validation utility."""

    def test_find_python_files(self):
        """Test finding Python files in directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)

            # Create test Python files
            (test_dir / "test1.py").touch()
            (test_dir / "test2.py").touch()
            (test_dir / "__init__.py").touch()  # Should be excluded
            (test_dir / "subdir").mkdir()
            (test_dir / "subdir" / "test3.py").touch()
            (test_dir / "not_python.txt").touch()

            # Import and test the function
            import sys

            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

            try:
                from validate_python import find_python_files

                result = find_python_files(test_dir)

                # Should find test1.py, test2.py, and subdir/test3.py (but not __init__.py)
                assert len(result) == 3
                file_names = [f.name for f in result]
                assert "test1.py" in file_names
                assert "test2.py" in file_names
                assert "test3.py" in file_names
                assert "__init__.py" not in file_names

            finally:
                sys.path.remove(str(Path(__file__).parent.parent / "src"))

    def test_test_syntax_valid_file(self):
        """Test syntax validation with valid Python file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "valid.py"

            with open(test_file, "w") as f:
                f.write(
                    """
def hello_world():
    print("Hello, World!")
    return True

class TestClass:
    def __init__(self):
        self.value = 42
"""
                )

            import sys

            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

            try:
                from validate_python import test_syntax

                result = test_syntax(test_file)
                assert result is True

            finally:
                sys.path.remove(str(Path(__file__).parent.parent / "src"))

    def test_test_syntax_invalid_file(self):
        """Test syntax validation with invalid Python file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "invalid.py"

            with open(test_file, "w") as f:
                f.write(
                    """
def broken_function(
    # Missing closing parenthesis and colon
    print("This is broken")
"""
                )

            import sys

            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

            try:
                from validate_python import test_syntax

                with patch("builtins.print"):  # Suppress error output
                    result = test_syntax(test_file)
                    assert result is False

            finally:
                sys.path.remove(str(Path(__file__).parent.parent / "src"))

    def test_validate_class_structure_valid(self):
        """Test class structure validation with valid Grid-STIX class."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "valid_class.py"

            with open(test_file, "w") as f:
                f.write(
                    """
from pydantic import BaseModel
from typing import Optional, Any

class TestGridSTIXClass(BaseModel):
    name: Optional[str] = None
    value: Optional[int] = None
"""
                )

            import sys

            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

            try:
                from validate_python import validate_class_structure

                result = validate_class_structure(test_file)
                assert result is True

            finally:
                sys.path.remove(str(Path(__file__).parent.parent / "src"))

    def test_validate_class_structure_no_class(self):
        """Test class structure validation with file containing no classes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "no_class.py"

            with open(test_file, "w") as f:
                f.write(
                    """
def some_function():
    return "No classes here"

SOME_CONSTANT = 42
"""
                )

            import sys

            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

            try:
                from validate_python import validate_class_structure

                with patch("builtins.print"):  # Suppress error output
                    result = validate_class_structure(test_file)
                    assert result is False

            finally:
                sys.path.remove(str(Path(__file__).parent.parent / "src"))

    def test_main_function_no_python_dir(self):
        """Test main function when python directory doesn't exist."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        try:
            from validate_python import main

            # Create a mock that doesn't exist
            mock_python_dir = Mock()
            mock_python_dir.exists.return_value = False

            # Mock the entire path construction by patching the specific line
            with patch("validate_python.Path") as mock_path_class:
                # Create a mock script directory that supports the / operator
                class MockScriptDir:
                    def __init__(self):
                        # Create a parent that supports the / operator
                        class MockParent:
                            def __truediv__(self, other):
                                if other == "python":
                                    # Return another MockPath that when divided by "grid_stix" returns mock_python_dir
                                    class MockPythonPath:
                                        def __truediv__(self, other):
                                            if other == "grid_stix":
                                                return mock_python_dir
                                            return Mock()

                                    return MockPythonPath()
                                return Mock()

                        self.parent = MockParent()

                mock_script_dir = MockScriptDir()

                # Mock Path(__file__).parent to return our mock script directory
                mock_path_class.return_value.parent = mock_script_dir

                with patch("builtins.print"):  # Suppress output
                    result = main()
                    assert result == 1

        finally:
            sys.path.remove(str(Path(__file__).parent.parent / "src"))

    def test_main_function_no_files(self):
        """Test main function when no Python files are found."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        try:
            from validate_python import main

            with (
                patch("validate_python.Path") as mock_path,
                patch("validate_python.find_python_files") as mock_find,
            ):

                mock_python_dir = Mock()
                mock_python_dir.exists.return_value = True
                mock_path.return_value.parent.__truediv__.return_value = mock_python_dir

                mock_find.return_value = []  # No files found

                with patch("builtins.print"):  # Suppress output
                    result = main()
                    assert result == 1

        finally:
            sys.path.remove(str(Path(__file__).parent.parent / "src"))


class TestOntologyChecker:
    """Test cases for ontology validation functionality."""

    def test_ontology_checker_imports(self):
        """Test that ontology checker can be imported and has expected functions."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        try:
            import ontology_checker

            # Check that key functions exist
            assert hasattr(ontology_checker, "check_stix_inheritance_compliance")
            assert hasattr(ontology_checker, "check_stix_namespace_consistency")
            assert hasattr(ontology_checker, "check_stix_property_patterns")
            assert hasattr(ontology_checker, "check_unreachable_classes")
            assert hasattr(ontology_checker, "find_properties_missing_domain_range")

        finally:
            sys.path.remove(str(Path(__file__).parent.parent / "src"))

    def test_naming_pattern_constants(self):
        """Test that naming pattern constants are defined correctly."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        try:
            import ontology_checker

            # Check that naming patterns exist
            assert hasattr(ontology_checker, "CLASS_URI_PATTERN")
            assert hasattr(ontology_checker, "PROPERTY_URI_PATTERN")
            assert hasattr(ontology_checker, "LABEL_PATTERN")
            assert hasattr(ontology_checker, "TECHNICAL_NAMING_PATTERN")

            # Test pattern matching
            import re

            # Test class URI pattern (kebab-case)
            assert re.match(ontology_checker.CLASS_URI_PATTERN, "test-class")
            assert re.match(ontology_checker.CLASS_URI_PATTERN, "generation-asset")
            assert not re.match(ontology_checker.CLASS_URI_PATTERN, "TestClass")
            assert not re.match(ontology_checker.CLASS_URI_PATTERN, "test_class")

            # Test property URI pattern (kebab-case)
            assert re.match(ontology_checker.PROPERTY_URI_PATTERN, "has-component")
            assert re.match(ontology_checker.PROPERTY_URI_PATTERN, "source-ref")
            assert not re.match(ontology_checker.PROPERTY_URI_PATTERN, "hasComponent")
            assert not re.match(ontology_checker.PROPERTY_URI_PATTERN, "has_component")

            # Test label pattern (snake_case)
            assert re.match(ontology_checker.LABEL_PATTERN, "test_class")
            assert re.match(ontology_checker.LABEL_PATTERN, "generation_asset")
            assert not re.match(ontology_checker.LABEL_PATTERN, "TestClass")
            assert not re.match(ontology_checker.LABEL_PATTERN, "test-class")

        finally:
            sys.path.remove(str(Path(__file__).parent.parent / "src"))

    def test_case_conversion_functions(self):
        """Test case conversion utility functions."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        try:
            import ontology_checker

            # Test to_kebab_case function
            assert ontology_checker.to_kebab_case("TestClass") == "test-class"
            assert ontology_checker.to_kebab_case("test_class") == "test-class"
            assert ontology_checker.to_kebab_case("already-kebab") == "already-kebab"
            assert (
                ontology_checker.to_kebab_case("ComplexClassName")
                == "complex-class-name"
            )

            # Test to_snake_case function
            assert ontology_checker.to_snake_case("TestClass") == "test_class"
            assert ontology_checker.to_snake_case("test-class") == "test_class"
            assert ontology_checker.to_snake_case("already_snake") == "already_snake"
            assert (
                ontology_checker.to_snake_case("ComplexClassName")
                == "complex_class_name"
            )

        finally:
            sys.path.remove(str(Path(__file__).parent.parent / "src"))

    def test_stix_namespace_constants(self):
        """Test STIX namespace and class constants."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        try:
            import ontology_checker

            # Check STIX namespaces
            assert hasattr(ontology_checker, "STIX_NAMESPACES")
            stix_namespaces = ontology_checker.STIX_NAMESPACES
            assert isinstance(stix_namespaces, list)
            assert len(stix_namespaces) > 0

            # Check that expected STIX namespaces are present
            expected_stix_ns = "http://docs.oasis-open.org/ns/cti/stix"
            assert any(expected_stix_ns in ns for ns in stix_namespaces)

            # Check STIX core classes
            assert hasattr(ontology_checker, "STIX_CORE_CLASSES")
            stix_classes = ontology_checker.STIX_CORE_CLASSES
            assert isinstance(stix_classes, list)
            assert "Infrastructure" in stix_classes
            assert "DomainObject" in stix_classes
            assert "Relationship" in stix_classes

        finally:
            sys.path.remove(str(Path(__file__).parent.parent / "src"))


class TestOwlToHtml:
    """Test cases for OWL to HTML conversion utility."""

    def test_owl_to_html_imports(self):
        """Test that OWL to HTML converter can be imported."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        try:
            import owl_to_html

            # The module should import without errors
            # Specific functionality would depend on implementation details
            assert owl_to_html is not None

        except ImportError:
            # If the module has dependencies that aren't available in test environment,
            # we can skip this test
            pytest.skip("owl_to_html module dependencies not available")

        finally:
            if str(Path(__file__).parent.parent / "src") in sys.path:
                sys.path.remove(str(Path(__file__).parent.parent / "src"))


class TestUtilityIntegration:
    """Integration tests for utility modules working together."""

    def test_validation_workflow(self):
        """Test a complete validation workflow using multiple utilities."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test Python file structure
            python_dir = Path(temp_dir) / "python" / "grid_stix"
            python_dir.mkdir(parents=True)

            # Create a valid Grid-STIX class file
            test_file = python_dir / "TestClass.py"
            with open(test_file, "w") as f:
                f.write(
                    """
from pydantic import BaseModel
from typing import Optional, Any

class TestClass(BaseModel):
    '''A test Grid-STIX class.'''
    name: Optional[str] = None
    value: Optional[int] = None
    
    def validate_properties(self) -> bool:
        return True
"""
                )

            import sys

            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

            try:
                from validate_python import (
                    find_python_files,
                    test_syntax,
                    validate_class_structure,
                )

                # Test the complete workflow
                files = find_python_files(python_dir)
                assert len(files) == 1
                assert files[0].name == "TestClass.py"

                # Test syntax validation
                syntax_valid = test_syntax(files[0])
                assert syntax_valid is True

                # Test structure validation
                structure_valid = validate_class_structure(files[0])
                assert structure_valid is True

            finally:
                sys.path.remove(str(Path(__file__).parent.parent / "src"))

    def test_error_handling_across_utilities(self):
        """Test error handling consistency across utility modules."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create an invalid Python file
            invalid_file = Path(temp_dir) / "invalid.py"
            with open(invalid_file, "w") as f:
                f.write("This is not valid Python syntax !!!")

            import sys

            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

            try:
                from validate_python import test_syntax, validate_class_structure

                # Both functions should handle errors gracefully
                with patch("builtins.print"):  # Suppress error output
                    syntax_result = test_syntax(invalid_file)
                    structure_result = validate_class_structure(invalid_file)

                    # Both should return False for invalid files
                    assert syntax_result is False
                    assert structure_result is False

            finally:
                sys.path.remove(str(Path(__file__).parent.parent / "src"))

    def test_utility_module_isolation(self):
        """Test that utility modules can be used independently."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        try:
            # Each utility should be importable independently
            import validate_python
            import ontology_checker

            # They should not interfere with each other
            assert validate_python is not None
            assert ontology_checker is not None

            # They should have different purposes
            assert hasattr(validate_python, "main")
            assert hasattr(ontology_checker, "STIX_NAMESPACES")

        finally:
            sys.path.remove(str(Path(__file__).parent.parent / "src"))
