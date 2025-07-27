#!/usr/bin/env python3
"""
Script to fix property domain/range references in Grid-STIX OWL files.
Updates domain/range references to use kebab-case class URIs to match the actual class definitions.
"""

import re
import os
from pathlib import Path


def convert_to_kebab_case(name):
    """Convert PascalCase/camelCase/snake_case to kebab-case."""
    # Handle common patterns first
    name = name.replace('_', '-')
    
    # Convert PascalCase/camelCase to kebab-case
    # Insert hyphens before capital letters (except the first one)
    name = re.sub('([a-z0-9])([A-Z])', r'\1-\2', name)
    
    # Convert to lowercase
    name = name.lower()
    
    # Clean up multiple hyphens
    name = re.sub('-+', '-', name)
    
    return name


def collect_class_mappings(owl_content):
    """Collect mappings from old references to correct kebab-case class URIs."""
    mappings = {}
    
    # Find all class definitions with rdf:about
    class_pattern = r'<owl:Class\s+rdf:about="[^"]*#([^"]+)"[^>]*>'
    class_matches = re.findall(class_pattern, owl_content)
    
    for class_name in class_matches:
        # Skip union classes
        if class_name.startswith('union-'):
            continue
            
        # The class_name should already be in kebab-case after our previous fixes
        kebab_name = class_name
        
        # Generate possible old reference formats that might appear in domain/range
        # Convert kebab-case to PascalCase variations
        words = kebab_name.split('-')
        
        # PascalCase without separators: ElectricVehicleSupplyEquipment
        pascal_case = ''.join(word.capitalize() for word in words)
        
        # PascalCase with underscores: Electric_Vehicle_Supply_Equipment (most common issue)
        pascal_with_underscores = '_'.join(word.capitalize() for word in words)
        
        # snake_case version: electric_vehicle_supply_equipment
        snake_case = kebab_name.replace('-', '_')
        
        # CamelCase version (first letter lowercase): electricVehicleSupplyEquipment
        camel_case = pascal_case[0].lower() + pascal_case[1:] if pascal_case else kebab_name
        
        possible_old_formats = [
            pascal_with_underscores,  # Most common: Electric_Vehicle_Supply_Equipment
            pascal_case,              # Less common: ElectricVehicleSupplyEquipment
            snake_case,               # snake_case: electric_vehicle_supply_equipment
            camel_case,               # camelCase: electricVehicleSupplyEquipment
        ]
        
        for old_format in possible_old_formats:
            if old_format != kebab_name:  # Only map if different
                mappings[old_format] = kebab_name
    
    return mappings


def fix_domain_range_references(owl_content, mappings):
    """Fix domain and range references to use correct kebab-case class URIs."""
    changes_made = []
    
    # Pattern to match domain and range references (including internal # references)
    domain_range_pattern = r'(rdfs:(?:domain|range)\s+rdf:resource="[^"]*#)([^"]+)(")'
    
    def replace_reference(match):
        prefix = match.group(1)
        class_ref = match.group(2)
        suffix = match.group(3)
        
        if class_ref in mappings:
            new_ref = mappings[class_ref]
            changes_made.append(f"  {class_ref} -> {new_ref}")
            return prefix + new_ref + suffix
        
        return match.group(0)  # No change if not in mappings
    
    updated_content = re.sub(domain_range_pattern, replace_reference, owl_content)
    
    return updated_content, changes_made


def fix_owl_file(file_path):
    """Fix property domain/range references in a single OWL file."""
    print(f"\nProcessing: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Collect class mappings from this file
        mappings = collect_class_mappings(content)
        
        if not mappings:
            print("  No class mappings found")
            return
        
        print(f"  Found {len(mappings)} potential class reference mappings")
        
        # Fix domain/range references
        updated_content, changes_made = fix_domain_range_references(content, mappings)
        
        if changes_made:
            # Write back the updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print(f"  Fixed {len(changes_made)} domain/range references:")
            for change in changes_made:
                print(change)
        else:
            print("  No domain/range reference fixes needed")
    
    except Exception as e:
        print(f"  ERROR: {e}")


def main():
    """Main function to fix all OWL files."""
    print("Fixing property domain/range references in Grid-STIX OWL files...")
    
    # Find all OWL files (excluding auto-generated full.owl file)
    owl_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.owl') and not file.endswith('-full.owl'):
                owl_files.append(os.path.join(root, file))
    
    if not owl_files:
        print("No OWL files found!")
        return
    
    print(f"Found {len(owl_files)} OWL files:")
    for owl_file in owl_files:
        print(f"  {owl_file}")
    
    # Process each OWL file
    total_fixes = 0
    for owl_file in owl_files:
        fix_owl_file(owl_file)
    
    print(f"\nCompleted fixing property domain/range references in {len(owl_files)} OWL files")


if __name__ == "__main__":
    main()