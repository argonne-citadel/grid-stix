#!/usr/bin/env python3
"""
Comprehensive script to fix all remaining property domain/range reference issues.
"""

import re
import os
from pathlib import Path


def get_comprehensive_mappings():
    """Get comprehensive mapping of problematic references to correct kebab-case names."""
    return {
        # DER entities
        "DER_Device": "der-device",
        "DER_Operator": "der-operator", 
        "DER_Owner": "der-owner",
        "DER_User": "der-user",
        "DER_Controller": "der-controller",
        "DER_System": "der-system",
        "DER_SCADA": "der-scada",
        "DER_Firmware": "der-firmware",
        "DER_Communication_Interface": "der-communication-interface",
        "DER_Network_Interface": "der-network-interface",
        "DER_Aggregator": "der-aggregator",
        
        # EVSE entities
        "EVSE_Controller": "evse-controller",
        "Electric_Vehicle_Supply_Equipment": "electric-vehicle-supply-equipment",
        "Electric_Vehicle": "electric-vehicle",
        
        # Management systems
        "DERMS": "derms",
        "Distribution_Management_System": "distribution-management-system",
        
        # Grid components
        "Point_of_Common_Coupling": "point-of-common-coupling", 
        "grid-component": "grid-component",  # This one is already correct
        
        # Generation assets
        "Generation_Asset": "generation-asset",
        "GenerationAsset": "generation-asset",
        
        # Other entities
        "Local_Electric_Power_System": "local-electric-power-system",
        "Facility_Energy_Management_System": "facility-energy-management-system",
        "Smart_Inverter": "smart-inverter",
        "Battery_Energy_Storage_System": "battery-energy-storage-system",
        "Photovoltaic_System": "photovoltaic-system",
        "Sensor_Inputs": "sensor-inputs",
        "Human_Machine_Interface": "human-machine-interface",
        "Maintenance_Port": "maintenance-port",
        "Edge_Intelligent_Device": "edge-intelligent-device",
        
        # Relationship classes
        "feeds-relationship": "feeds-relationship",
    }


def fix_all_domain_range_references():
    """Fix all domain and range references across OWL files."""
    mappings = get_comprehensive_mappings()
    
    # Find all OWL files (excluding auto-generated full.owl file)
    owl_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.owl') and not file.endswith('-full.owl'):
                # Focus on the Grid-STIX files, skip tac-ontology
                if not root.startswith('./tac-ontology'):
                    owl_files.append(os.path.join(root, file))
    
    total_fixes = 0
    
    for owl_file in owl_files:
        print(f"\nProcessing: {owl_file}")
        
        try:
            with open(owl_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            changes_made = []
            
            # Fix domain and range references (both full URIs and fragment references)
            # Pattern for internal fragment references: rdf:resource="#ClassName"
            fragment_pattern = r'(rdf:resource="[^"]*#)([^"]+)(")'
            
            def replace_fragment_reference(match):
                prefix = match.group(1)
                class_ref = match.group(2)
                suffix = match.group(3)
                
                if class_ref in mappings:
                    new_ref = mappings[class_ref]
                    changes_made.append(f"  {class_ref} -> {new_ref}")
                    return prefix + new_ref + suffix
                
                return match.group(0)  # No change if not in mappings
            
            content = re.sub(fragment_pattern, replace_fragment_reference, content)
            
            if changes_made:
                with open(owl_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"  Fixed {len(changes_made)} references:")
                for change in changes_made:
                    print(change)
                total_fixes += len(changes_made)
            else:
                print("  No reference fixes needed")
        
        except Exception as e:
            print(f"  ERROR: {e}")
    
    print(f"\nCompleted! Fixed {total_fixes} total references across all files.")


if __name__ == "__main__":
    fix_all_domain_range_references()