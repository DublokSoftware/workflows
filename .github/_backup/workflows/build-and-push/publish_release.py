#!/usr/bin/env python3
import os
import sys
import json
import base64
import requests
from typing import Dict, Optional

def get_version_file_content(github_token: str, github_repo: str, branch: str) -> Optional[Dict]:
    """Get content of version file from repository."""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    # Look for version file in root directory
    version_file = f".version_{branch}.json"
    url = f"https://api.github.com/repos/{github_repo}/contents/{version_file}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return json.loads(base64.b64decode(response.json()['content']))
    return None

def create_tag(github_token: str, github_repo: str, tag_name: str, sha: str) -> bool:
    """Create a new tag in the repository."""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    url = f"https://api.github.com/repos/{github_repo}/git/refs"
    data = {
        'ref': f'refs/tags/{tag_name}',
        'sha': sha
    }
    response = requests.post(url, headers=headers, json=data)
    return response.status_code == 201

def create_release(github_token: str, github_repo: str, version_data: Dict, sha: str) -> Optional[str]:
    """Create a new release in the repository."""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    url = f"https://api.github.com/repos/{github_repo}/releases"

    # Extract suffix if exists
    version = version_data['version']
    suffix = version.split('-')[1] if '-' in version else ''

    # Determine if it should be a pre-release
    is_prerelease = suffix.lower() in ['alpha', 'beta']

    # Create release notes with version and tags information
    release_notes = f"""Version {version}
Build Number: {version_data['build_number']}
Branch: {version_data['branch']}
Release Type: {'Pre-release' if is_prerelease else 'Regular Release'}
Docker Tags:
{chr(10).join(['- ' + tag for tag in version_data['tags']])}
"""
    data = {
        'tag_name': version,
        'target_commitish': sha,
        'name': f"Release {version}",
        'body': release_notes,
        'draft': False,
        'prerelease': is_prerelease
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            print(f"Successfully created release: {version}")
            return response.json()['upload_url']
        else:
            print(f"Failed to create release. Status code: {response.status_code}")
            print(f"Error message: {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred while creating release: {str(e)}")
        return None

def main():
    # Get environment variables
    github_token = os.environ.get('GITHUB_TOKEN')
    github_repo = os.environ.get('GITHUB_REPOSITORY')
    branch = os.environ.get('GITHUB_REF').replace('refs/heads/', '')
    sha = os.environ.get('GITHUB_SHA')
    if not all([github_token, github_repo, branch, sha]):
        print("Missing required environment variables")
        sys.exit(1)
    # Get version information
    version_data = get_version_file_content(github_token, github_repo, branch)
    if not version_data:
        print("Failed to get version information")
        sys.exit(1)
    # Create tag
    if not create_tag(github_token, github_repo, version_data['version'], sha):
        print("Failed to create tag")
        sys.exit(1)
    print(f"Successfully created tag: {version_data['version']}")
    # Create release
    upload_url = create_release(github_token, github_repo, version_data, sha)
    if not upload_url:
        print("Failed to create release")
        sys.exit(1)
    print(f"Successfully created release: {version_data['version']}")
    # Set output for GitHub Actions
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write(f"version={version_data['version']}\n")
        f.write(f"release_created=true\n")
        f.write(f"upload_url={upload_url}\n")

if __name__ == '__main__':
    main()