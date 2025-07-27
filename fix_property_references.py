#!/usr/bin/env python3
"""
Script to fix property reference naming violations in Grid-STIX attack patterns file.
Updates ns4: property references to use kebab-case to match declared property names.
"""

import re

def fix_property_references():
    """Fix property references in attack patterns file."""
    
    file_path = "threat/grid-stix-2.1-attack-patterns.owl"
    
    # Mapping of underscore references to hyphen references
    property_fixes = {
        "ns4:affects_ot_device": "ns4:affects-ot-device",
        "ns4:affects_protocol": "ns4:affects-protocol", 
        "ns4:attack_id": "ns4:attack-id",
        "ns4:capec_id": "ns4:capec-id",
        "ns4:has_impact_type": "ns4:has-impact-type",
        "ns4:likelihood_of_success": "ns4:likelihood-of-success",
        "ns4:skill_level_required": "ns4:skill-level-required"
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Apply fixes
        for old_ref, new_ref in property_fixes.items():
            if old_ref in content:
                content = content.replace(old_ref, new_ref)
                changes_made.append(f"  {old_ref} -> {new_ref}")
        
        # Write back if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"Fixed {len(changes_made)} property references in {file_path}:")
            for change in changes_made:
                print(change)
        else:
            print("No property reference violations found.")
    
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    fix_property_references()