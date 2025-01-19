#!/usr/bin/env python3
import os
import sys
import base64
import logging
import requests
from pathlib import Path
from typing import Dict, List

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_github_file(headers: Dict, github_repo: str, file_path: Path, github_path: str, commit_message: str) -> bool:
    """Update or create a file in GitHub repository using the API."""
    try:
        url = f'https://api.github.com/repos/{github_repo}/contents/{github_path}'
        
        # Read file content
        with open(file_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode()

        # Check if file exists
        response = requests.get(url, headers=headers)
        
        data = {
            'message': commit_message,
            'content': content,
        }
        
        if response.status_code == 200:
            # File exists, include its SHA
            data['sha'] = response.json()['sha']

        # Create or update file
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        logger.info(f"Successfully updated {github_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to update {github_path}: {e}")
        return False

def commit_files(version: str, branch: str) -> bool:
    """Commit all generated files to the repository."""
    try:
        github_token = os.environ['GITHUB_TOKEN']
        github_repo = os.environ['GITHUB_REPOSITORY']
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        commit_message = f"Update version files for {version}"
        
        # Define files to commit
        files_to_commit = [
            # (local_path, github_path)
            (Path('sbom_output/sbom.json'), '.sbom/sbom.json'),
            (Path('sbom_output/sbom.txt'), '.sbom/sbom.txt'),
            (Path('.vulnerability_report.txt'), '.vulnerability_report.txt'),
            (Path(f'.version_{branch}.json'), f'.version_{branch}.json'),
        ]

        success = True
        for local_path, github_path in files_to_commit:
            if local_path.exists():
                if not update_github_file(headers, github_repo, local_path, github_path, commit_message):
                    success = False
            else:
                logger.warning(f"File not found: {local_path}")

        return success

    except Exception as e:
        logger.error(f"Failed to commit files: {e}")
        return False

def main():
    """Main function to orchestrate file commits."""
    try:
        version = os.environ.get('VERSION')
        branch = os.environ.get('GITHUB_REF', '').replace('refs/heads/', '')

        if not version or not branch:
            logger.error("Missing required environment variables")
            sys.exit(1)

        if not commit_files(version, branch):
            logger.error("Failed to commit some files")
            sys.exit(1)

        logger.info("Successfully committed all files")

    except Exception as e:
        logger.error(f"File commit process failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()