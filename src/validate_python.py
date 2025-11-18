#!/usr/bin/env python3
"""
Validation script for generated Grid-STIX Python files.
Checks syntax, imports, and basic type consistency.
"""

import os
import sys
import py_compile
import importlib.util
from pathlib import Path
from typing import List, Dict, Any
import tempfile
import subprocess  # nosec B404 - needed for validation, uses safe subprocess.run() patterns


def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in the given directory recursively."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                python_files.append(Path(root) / file)
    return python_files


def test_syntax(file_path: Path) -> bool:
    """Test if a Python file has valid syntax."""
    try:
        py_compile.compile(str(file_path), doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f"❌ Syntax error in {file_path}: {e}")
        return False


def test_imports(file_path: Path) -> bool:
    """Test if all imports in a Python file can be resolved."""
    try:
        # Read the file and extract import statements
        with open(file_path, "r") as f:
            content = f.read()

        # Create a temporary module to test imports
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        if spec is None or spec.loader is None:
            print(f"❌ Could not create module spec for {file_path}")
            return False

        module = importlib.util.module_from_spec(spec)

        # Add python directory to path so grid_stix imports work
        python_dir = file_path.parent
        while python_dir.name != "python" and python_dir.parent != python_dir:
            python_dir = python_dir.parent

        if python_dir.name == "python":
            sys.path.insert(0, str(python_dir))

        # Try to execute the module (this will test imports)
        spec.loader.exec_module(module)
        return True

    except ImportError as e:
        print(f"❌ Import error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return False
    finally:
        # Clean up sys.path
        if python_dir.name == "python" and str(python_dir) in sys.path:
            sys.path.remove(str(python_dir))


def validate_class_structure(file_path: Path) -> bool:
    """Validate that the class structure matches expected patterns."""
    try:
        with open(file_path, "r") as f:
            content = f.read()

        # Check for basic class definition
        if "class " not in content:
            print(f"❌ No class definition found in {file_path}")
            return False

        # Check for proper import structure
        if "from pydantic import BaseModel" not in content:
            print(f"⚠️  No pydantic BaseModel import in {file_path}")

        if "from typing import Optional, Any" not in content:
            print(f"⚠️  No typing imports in {file_path}")

        return True

    except Exception as e:
        print(f"❌ Error validating class structure in {file_path}: {e}")
        return False


def main():
    """Main validation function."""
    print("🔍 Grid-STIX Python Code Validation")
    print("=" * 50)

    # Find the python directory
    script_dir = Path(__file__).parent
    python_dir = script_dir.parent / "python" / "grid_stix"

    if not python_dir.exists():
        print(f"❌ Python directory not found: {python_dir}")
        return 1

    print(f"📁 Scanning directory: {python_dir}")

    # Find all Python files
    python_files = find_python_files(python_dir)
    print(f"📄 Found {len(python_files)} Python files")

    if not python_files:
        print("❌ No Python files found!")
        return 1

    # Validation counters
    syntax_pass = 0
    import_pass = 0
    structure_pass = 0
    total_files = len(python_files)

    print("\n🧪 Running validation tests...")

    for file_path in python_files:
        relative_path = file_path.relative_to(python_dir.parent)
        print(f"\n📝 Testing {relative_path}")

        # Test syntax
        if test_syntax(file_path):
            print(f"  ✅ Syntax: PASS")
            syntax_pass += 1
        else:
            print(f"  ❌ Syntax: FAIL")

        # Test imports (only if syntax passes)
        if syntax_pass > 0:
            if test_imports(file_path):
                print(f"  ✅ Imports: PASS")
                import_pass += 1
            else:
                print(f"  ❌ Imports: FAIL")

        # Test class structure
        if validate_class_structure(file_path):
            print(f"  ✅ Structure: PASS")
            structure_pass += 1
        else:
            print(f"  ❌ Structure: FAIL")

    # Print summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    print(f"Total files: {total_files}")
    print(
        f"Syntax valid: {syntax_pass}/{total_files} ({syntax_pass/total_files*100:.1f}%)"
    )
    print(
        f"Imports valid: {import_pass}/{total_files} ({import_pass/total_files*100:.1f}%)"
    )
    print(
        f"Structure valid: {structure_pass}/{total_files} ({structure_pass/total_files*100:.1f}%)"
    )

    if syntax_pass == total_files and import_pass == total_files:
        print("\n🎉 ALL TESTS PASSED! Generated Python code is valid.")
        return 0
    else:
        print(f"\n⚠️  Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
