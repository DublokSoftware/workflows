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
        return False
        
    if not os.path.exists(old_sbom_path):
        print("Old SBOM file doesn't exist. This is the first SBOM.")
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            print(f"new_sbom=true", file=fh)
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
            with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
                print(f"new_sbom=true", file=fh)
            sys.exit(0)
        else:
            print("SBOM files are identical")
            print("Notice: No changes detected in SBOM files. Stopping workflow.")
            with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
                print(f"new_sbom=false", file=fh)
            sys.exit(78)  # Custom exit code for no changes

    except Exception as e:
        print(f"Error comparing SBOM files: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("Comparing SBOMs")
    compare_sbom_files()