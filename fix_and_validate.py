#!/usr/bin/env python3
"""
Combined script to fix property domain/range references and validate them.
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n=== {description} ===")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ {description} completed successfully")
            if result.stdout.strip():
                print(result.stdout)
        else:
            print(f"✗ {description} failed with exit code {result.returncode}")
            if result.stderr.strip():
                print("STDERR:", result.stderr)
            if result.stdout.strip():
                print("STDOUT:", result.stdout)
        return result.returncode == 0
    except Exception as e:
        print(f"✗ Error running {description}: {e}")
        return False

def main():
    """Main function to fix and validate OWL files."""
    print("Starting Grid-STIX domain/range reference fixes and validation...")
    
    # Step 1: Fix property domain/range references
    success = run_command("python3 fix_property_domains.py", "Fixing property domain/range references")
    if not success:
        print("Failed to fix property references, stopping.")
        sys.exit(1)
    
    # Step 2: Run validation to check for unresolved types
    run_command("make check", "Running ontology validation")
    
    print("\nCompleted fixing and validation process.")

if __name__ == "__main__":
    main()