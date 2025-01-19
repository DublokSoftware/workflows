#!/usr/bin/env python3
import os
import sys
import json
from typing import List, Dict
import re

def get_version_parts(branch: str) -> tuple[str, str, str]:
    """Extract version parts from branch name."""
    pattern = r'^(v[0-9]+(\.[0-9]+)*)([-][a-zA-Z0-9._-]+)?$'
    match = re.match(pattern, branch)
    if match:
        version_part = match.group(1)
        suffix = match.group(3) or ''
        return version_part, version_part.lstrip('v'), suffix
    return 'v0.0', '0.0', ''

def generate_tags(version_nums: str, suffix: str, build_number: int) -> List[str]:
    """Generate Docker tags."""
    tags = []
    parts = version_nums.split('.')
    current = 'v'
    # Add incremental version tags
    for part in parts:
        current += part
        tags.append(f"{current}{suffix}")
        current += '.'
    # Add full version tag
    full_version = f"v{version_nums}.{build_number}{suffix}"
    tags.append(full_version)
    # Add latest or suffix tag
    tags.append(suffix.lstrip('-') if suffix else 'latest')
    return tags

def main():
    # Get environment variables
    branch = os.environ['GITHUB_REF'].replace('refs/heads/', '')
    
    # Get version information
    version_part, version_nums, suffix = get_version_parts(branch)
    print(f"Branch: {branch}")
    print(f"Version part: {version_part}")
    print(f"Suffix: {suffix}")

    # Set build number to 1 for new versions
    build_number = 1
    
    # Generate version information
    full_version = f"{version_part}.{build_number}{suffix}"
    tags = generate_tags(version_nums, suffix, build_number)
    
    # Create version file content
    version_data = {
        'branch': branch,
        'build_number': build_number,
        'version': full_version,
        'tags': tags
    }

    # Write version file
    filename = f".version_{branch}.json"
    with open(filename, 'w') as f:
        json.dump(version_data, indent=2, fp=f)

    # Set GitHub Actions outputs
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write(f"full_version={full_version}\n")
        f.write("tags<<EOF\n")
        f.write(json.dumps(tags))
        f.write("\nEOF\n")

if __name__ == '__main__':
    main()