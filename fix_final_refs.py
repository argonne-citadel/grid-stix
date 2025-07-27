#!/usr/bin/env python3
"""
Fix final namespace mismatches for cross-file class references.
"""

import re
import os


def fix_cross_namespace_references():
    """Fix references that point to classes in different OWL files."""
    
    # Define namespace corrections for cross-file references
    namespace_fixes = {
        # grid-component is defined in assets.owl, not components.owl
        'rdf:resource="http://www.anl.gov/sss/grid-stix-2.1-components.owl#grid-component"': 
        'rdf:resource="http://www.anl.gov/sss/grid-stix-2.1-assets.owl#grid-component"',
        
        'rdf:resource="#grid-component"':
        'rdf:resource="http://www.anl.gov/sss/grid-stix-2.1-assets.owl#grid-component"',
    }
    
    # Find OWL files to process
    owl_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.owl') and not file.endswith('-full.owl'):
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
            
            # Apply namespace fixes
            for old_ref, new_ref in namespace_fixes.items():
                if old_ref in content:
                    content = content.replace(old_ref, new_ref)
                    changes_made.append(f"  {old_ref} -> {new_ref}")
            
            if changes_made:
                with open(owl_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"  Fixed {len(changes_made)} cross-namespace references:")
                for change in changes_made:
                    print(change)
                total_fixes += len(changes_made)
            else:
                print("  No cross-namespace reference fixes needed")
        
        except Exception as e:
            print(f"  ERROR: {e}")
    
    print(f"\nCompleted! Fixed {total_fixes} total cross-namespace references.")


def add_missing_class_definitions():
    """Add missing class definitions that are referenced but not defined."""
    
    # Add point-of-common-coupling to components.owl
    components_file = "core/grid-stix-2.1-components.owl"
    
    point_of_common_coupling_class = '''
  <owl:Class rdf:about="http://www.anl.gov/sss/grid-stix-2.1-components.owl#point-of-common-coupling">
    <rdfs:subClassOf rdf:resource="http://www.anl.gov/sss/grid-stix-2.1-assets.owl#grid-component"/>
    <rdfs:comment>Point where a distributed resource is electrically connected to the utility system.</rdfs:comment>
    <rdfs:label>point_of_common_coupling</rdfs:label>
  </owl:Class>'''
    
    # Add feeds-relationship to relationships.owl  
    relationships_file = "core/grid-stix-2.1-relationships.owl"
    
    feeds_relationship_class = '''
  <owl:Class rdf:about="http://www.anl.gov/sss/grid-stix-2.1-relationships.owl#feeds-relationship">
    <rdfs:subClassOf rdf:resource="http://www.anl.gov/sss/grid-stix-2.1-relationships.owl#grid-relationship"/>
    <rdfs:comment>Relationship indicating that one component feeds or supplies another.</rdfs:comment>
    <rdfs:label>feeds_relationship</rdfs:label>
  </owl:Class>'''
    
    files_to_fix = [
        (components_file, point_of_common_coupling_class, "point-of-common-coupling"),
        (relationships_file, feeds_relationship_class, "feeds-relationship")
    ]
    
    for file_path, class_definition, class_name in files_to_fix:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if class already exists
                if f'rdf:about="http://www.anl.gov/sss/grid-stix-2.1-{file_path.split("/")[1]}.owl#{class_name}"' in content:
                    print(f"Class {class_name} already exists in {file_path}")
                    continue
                
                # Insert class definition before the closing </rdf:RDF> tag
                if '</rdf:RDF>' in content:
                    content = content.replace('</rdf:RDF>', class_definition + '\n</rdf:RDF>')
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"Added missing class {class_name} to {file_path}")
                else:
                    print(f"Could not find closing tag in {file_path}")
            
            except Exception as e:
                print(f"Error adding class to {file_path}: {e}")
        else:
            print(f"File not found: {file_path}")


if __name__ == "__main__":
    print("Fixing cross-namespace references...")
    fix_cross_namespace_references()
    
    print("\nAdding missing class definitions...")
    add_missing_class_definitions()
    
    print("\nCompleted all fixes!")