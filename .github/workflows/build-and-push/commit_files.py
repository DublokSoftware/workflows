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

def commit_multiple_files_github_api(headers: Dict, github_repo: str, files_to_commit, commit_message: str, branch: str) -> bool:
    """
    Commit multiple files in a single commit using the GitHub Git Data API.
    """
    try:
        # 1. Get the latest commit SHA of the branch
        ref_url = f'https://api.github.com/repos/{github_repo}/git/refs/heads/{branch}'
        ref_resp = requests.get(ref_url, headers=headers)
        if ref_resp.status_code != 200:
            logger.error(f"Failed to get ref for branch {branch}: {ref_resp.text}")
            return False
        latest_commit_sha = ref_resp.json()["object"]["sha"]

        # 2. Get the tree SHA from the latest commit
        commit_url = f'https://api.github.com/repos/{github_repo}/git/commits/{latest_commit_sha}'
        commit_resp = requests.get(commit_url, headers=headers)
        if commit_resp.status_code != 200:
            logger.error(f"Failed to get latest commit info: {commit_resp.text}")
            return False
        base_tree_sha = commit_resp.json()["tree"]["sha"]

        # 3. Create blobs for each file
        blob_sha_paths = []
        for local_path, github_path in files_to_commit:
            with open(local_path, 'rb') as f:
                content_bytes = f.read()
            is_binary = b'\0' in content_bytes
            if is_binary:
                # For binaries (such as .tar), must base64 encode and set encoding
                content = base64.b64encode(content_bytes).decode()
                blob_req = {
                    "content": content,
                    "encoding": "base64"
                }
            else:
                try:
                    content = content_bytes.decode('utf-8')
                    blob_req = {
                        "content": content,
                        "encoding": "utf-8"
                    }
                except UnicodeDecodeError:
                    content = base64.b64encode(content_bytes).decode()
                    blob_req = {
                        "content": content,
                        "encoding": "base64"
                    }
            url = f"https://api.github.com/repos/{github_repo}/git/blobs"
            blob_resp = requests.post(url, headers=headers, json=blob_req)
            if blob_resp.status_code not in (201, 200):
                logger.error(f"Failed to create blob for {github_path}: {blob_resp.text}")
                return False
            blob_sha = blob_resp.json()["sha"]
            blob_sha_paths.append({
                "path": github_path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha
            })

        # 4. Create a new tree
        tree_url = f"https://api.github.com/repos/{github_repo}/git/trees"
        tree_req = {
            "base_tree": base_tree_sha,
            "tree": blob_sha_paths
        }
        tree_resp = requests.post(tree_url, headers=headers, json=tree_req)
        if tree_resp.status_code not in (201, 200):
            logger.error(f"Failed to create tree: {tree_resp.text}")
            return False
        new_tree_sha = tree_resp.json()["sha"]

        # 5. Create a new commit object
        commit_req = {
            "message": commit_message,
            "tree": new_tree_sha,
            "parents": [latest_commit_sha]
        }
        new_commit_url = f"https://api.github.com/repos/{github_repo}/git/commits"
        new_commit_resp = requests.post(new_commit_url, headers=headers, json=commit_req)
        if new_commit_resp.status_code not in (201, 200):
            logger.error(f"Failed to create commit: {new_commit_resp.text}")
            return False
        new_commit_sha = new_commit_resp.json()["sha"]

        # 6. Update branch reference to point to new commit
        update_ref_url = f"https://api.github.com/repos/{github_repo}/git/refs/heads/{branch}"
        update_req = {
            "sha": new_commit_sha,
            "force": False
        }
        update_ref_resp = requests.patch(update_ref_url, headers=headers, json=update_req)
        if update_ref_resp.status_code not in (201, 200):
            logger.error(f"Failed to update ref: {update_ref_resp.text}")
            return False

        logger.info(f"Successfully committed all files in a single commit to branch {branch}")
        return True
    except Exception as e:
        logger.error(f"Failed to commit multiple files: {e}")
        return False

def commit_files(version: str, branch: str) -> bool:
    """Commit all generated files to the repository in a single commit, targeting a specific branch."""
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
        logger.info(f"Committing files with version: {version_data['version']} to branch {branch}")

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

        # Only commit files that exist
        files_to_really_commit = [(lp, gp) for lp, gp in files_to_commit if lp.exists()]
        for lp, gp in files_to_commit:
            if not lp.exists():
                logger.warning(f"File not found: {lp}")

        if not files_to_really_commit:
            logger.warning("No files to commit.")
            return False

        success = commit_multiple_files_github_api(headers, github_repo, files_to_really_commit, commit_message, branch)
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