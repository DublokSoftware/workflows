#!/usr/bin/env python3
import base64
import os
import sys
import json
from typing import List, Dict
import re
import requests

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
    """Main function to orchestrate version updates."""
    try:
        # Get environment variables
        github_token = os.environ['GH_TOKEN']
        github_repo = os.environ['GITHUB_REPOSITORY']
        branch = os.environ['GITHUB_REF'].replace('refs/heads/', '')
        # Get optional project name
        project_name = os.environ.get('PROJECT_NAME', '')
        # Get version information
        version_part, version_nums, suffix = get_version_parts(branch)
        print(f"Branch: {branch}")
        print(f"Version part: {version_part}")
        print(f"Suffix: {suffix}")
        # Setup API
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        filename = f".version_{project_name}_{branch}.json" if project_name else f".version_{branch}.json"
        local_path = os.path.abspath(filename)
        url = f"https://api.github.com/repos/{github_repo}/contents/{filename}"
        print(f"Local file path: {local_path}")
        # Add ref parameter to specify branch
        params = {'ref': branch}
        # Get existing file if it exists
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            # File exists, increment build number
            existing_data = json.loads(base64.b64decode(response.json()['content']))
            build_number = existing_data['build_number'] + 1
            sha = response.json()['sha']
            print(f"Old file content: {existing_data}")
        else:
            # Create new file with initial values
            build_number = 0
            sha = None
            print("Old file content: None (file does not exist)")
        # Generate tags using existing function
        tags = generate_tags(version_nums, suffix, build_number)
        # Create version file content
        version_data = {
            'branch': branch,
            'build_number': build_number,
            'version': tags[-2],  # The full version is second to last in tags
            'tags': tags
        }
        # Save locally
        with open(filename, 'w') as f:
            json.dump(version_data, f, indent=2)
        print(f"File saved locally at: {local_path}")
        print(f"New file content: {version_data}")

        # Set GitHub Actions outputs
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"full_version={version_data['version']}\n")
            f.write("tags<<EOF\n")
            f.write(json.dumps(tags))
            f.write("\nEOF\n")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    import time

    def retry_main(max_retries=3, delay=2):
        for attempt in range(max_retries):
            try:
                main()
                break
            except Exception as e:
                # Only retry for JSON parse or missing file errors
                if 'Expecting value' in str(e) or 'FileNotFoundError' in str(e):
                    print(f"Retrying due to error: {e} (attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                else:
                    print(f"Non-retriable error: {e}")
                    sys.exit(1)
        else:
            print(f"Failed after {max_retries} attempts.")
            sys.exit(1)

    retry_main(max_retries=3, delay=2)