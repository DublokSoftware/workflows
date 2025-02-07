#!/usr/bin/env python3
import os
import shutil
import sys
import base64
import logging
import requests
import time
import json
from pathlib import Path
from typing import Dict, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_directory_names():
    """Generate directory names based on project name if available."""
    project_name = os.environ.get('PROJECT_NAME', '')
    if project_name:
        return {
            'sbom_old': f'.sbom_{project_name}_',
            'sbom_new': f'.sbom_{project_name}',
            'vuln_report': f'.vulnerability_report_{project_name}.txt',
            'vuln_report_no_dot': f'vulnerability_report_{project_name}.txt'
        }
    return {
        'sbom_old': '.sbom_',
        'sbom_new': '.sbom',
        'vuln_report': '.vulnerability_report.txt',
        'vuln_report_no_dot': 'vulnerability_report.txt'
    }

def setup_directories():
    """Create necessary directories."""
    dirs = get_directory_names()
    Path(dirs['sbom_old']).mkdir(exist_ok=True)

def organize_files():
    """Organize files into their correct locations."""
    try:
        dirs = get_directory_names()
        # Create copy of vulnerability report without dot
        if Path(dirs['vuln_report']).exists():
            shutil.copy2(dirs['vuln_report'], dirs['vuln_report_no_dot'])
        logger.info("Successfully organized files")
    except Exception as e:
        logger.error(f"Failed to organize files: {e}")
        raise

def get_version_data(branch: str) -> Optional[Dict]:
    """Read the current version file."""
    try:
        project_name = os.environ.get('PROJECT_NAME', '')
        version_file = Path(f'.version_{project_name}_{branch}.json' if project_name else f'.version_{branch}.json')
        if version_file.exists():
            with open(version_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read version file: {e}")
    return None

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
        project_name = os.environ.get('PROJECT_NAME', '')
        dirs = get_directory_names()

        # First get the current version data
        version_data = get_version_data(branch)
        if not version_data:
            logger.error("Could not read version data")
            return False

        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        commit_message = f"Update version files for {version_data['version']}"
        logger.info(f"Committing files with version: {version_data['version']}")

        # First organize files
        setup_directories()
        organize_files()

        # Define files to commit
        files_to_commit = [
            # (local_path, github_path)
            (Path(f"{dirs['sbom_old']}/sbom.json"), f"{dirs['sbom_new']}/sbom.json"),
            (Path(f"{dirs['sbom_old']}/sbom.txt"), f"{dirs['sbom_new']}/sbom.txt"),
            (Path(dirs['vuln_report']), dirs['vuln_report']),
            (Path(f'.version_{project_name}_{branch}.json' if project_name else f'.version_{branch}.json'),
             f'.version_{project_name}_{branch}.json' if project_name else f'.version_{branch}.json'),
        ]

        success = True
        for local_path, github_path in files_to_commit:
            if local_path.exists():
                logger.info(f"Committing file: {local_path} to {github_path}")
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

        # Wait a moment for version file to be updated
        time.sleep(2)

        # Log current version file content
        version_data = get_version_data(branch)
        if version_data:
            logger.info(f"Current version file content: {json.dumps(version_data, indent=2)}")
        else:
            logger.error("Could not read version file")
            sys.exit(1)

        if not commit_files(version, branch):
            logger.error("Failed to commit some files")
            sys.exit(1)
        logger.info("Successfully committed all files")
    except Exception as e:
        logger.error(f"File processing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()