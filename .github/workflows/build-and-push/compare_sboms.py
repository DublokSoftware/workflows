#!/usr/bin/env python3
import os
import sys

def compare_sbom_files():
    # Define paths for old and new SBOM files
    old_sbom_path = '.sbom_/sbom.txt'
    new_sbom_path = '.sbom/sbom.txt'
    
    # Check if both files exist
    if not os.path.exists(new_sbom_path):
        print("New SBOM file doesn't exist")
        print("::error::New SBOM file not found")
        sys.exit(1)
        
    if not os.path.exists(old_sbom_path):
        print("Old SBOM file doesn't exist. This is the first SBOM.")
        print("::set-output name=new_sbom::true")
        return True

    try:
        # Read contents of both files
        with open(old_sbom_path, 'r') as old_file:
            old_content = old_file.read()
        
        with open(new_sbom_path, 'r') as new_file:
            new_content = new_file.read()

        # Compare contents
        if old_content != new_content:
            print("SBOM files are different")
            print("::set-output name=new_sbom::true")
            return True
        else:
            print("SBOM files are identical")
            print("::notice::No changes detected in SBOM files. Stopping workflow.")
            print("::set-output name=new_sbom::false")
            sys.exit(78)

    except Exception as e:
        print(f"Error comparing SBOM files: {str(e)}")
        print(f"::error::Failed to compare SBOM files: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    compare_sbom_files()