#!/usr/bin/env python3
import os
import sys
import base64
import logging
import subprocess
from pathlib import Path
import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_output_directory():
    """Create output directory for SBOM if it doesn't exist."""
    output_dir = Path('.sbom')
    output_dir.mkdir(exist_ok=True)
    return output_dir

def docker_login():
    """Login to GitHub Container Registry."""
    try:
        github_token = os.environ['GITHUB_TOKEN']
        github_actor = os.environ['GITHUB_ACTOR']
        
        login_cmd = [
            'docker', 'login', 'ghcr.io',
            '-u', github_actor,
            '--password-stdin'
        ]
        
        subprocess.run(
            login_cmd,
            input=github_token.encode(),
            check=True,
            capture_output=True
        )
        logger.info("Successfully logged in to GitHub Container Registry")
    except Exception as e:
        logger.error(f"Failed to login to GitHub Container Registry: {e}")
        raise

def generate_sbom():
    """Generate SBOM using sbominify Docker container."""
    try:
        repo_owner = os.environ['GITHUB_REPOSITORY_OWNER'].lower()
        image_name = os.environ['IMAGE_NAME']
        full_version = os.environ['FULL_VERSION']
        
        image_tag = f"ghcr.io/{repo_owner}/{image_name}:{full_version}"
        
        sbom_cmd = [
            'docker', 'run', '--rm',
            '-e', f'IMAGES={image_tag}',
            '-e', 'FILE_PREFIX=',
            '-e', 'FILE_SUFFIX=',
            '-e', 'FILE_NAME=sbom',
            '-v', '/var/run/docker.sock:/var/run/docker.sock',
            '-v', f'{os.getcwd()}/.sbom:/output',
            '-v', f'{os.environ["HOME"]}/.docker/config.json:/root/.docker/config.json:ro',
            'ghcr.io/dockforge/sbominify:latest'
        ]
        
        subprocess.run(sbom_cmd, check=True)
        logger.info("Successfully generated SBOM")
        
        output_dir = Path('.sbom')
        logger.info("Generated SBOM files:")
        for file in output_dir.iterdir():
            logger.info(f"- {file.name}")
            
    except Exception as e:
        logger.error(f"Failed to generate SBOM: {e}")
        raise

def update_github_file(file_path: Path, github_path: str):
    """Update or create a file in GitHub repository."""
    try:
        github_token = os.environ['GITHUB_TOKEN']
        github_repo = os.environ['GITHUB_REPOSITORY']
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        url = f'https://api.github.com/repos/{github_repo}/contents/{github_path}'

        # Read file content
        with open(file_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode()

        # Check if file exists
        response = requests.get(url, headers=headers)
        
        data = {
            'message': f'Update {github_path}',
            'content': content,
        }

        if response.status_code == 200:
            # File exists, include its SHA
            data['sha'] = response.json()['sha']

        # Create or update file
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        logger.info(f"Successfully updated {github_path}")

    except Exception as e:
        logger.error(f"Failed to update {github_path}: {e}")
        raise

def main():
    """Main function to orchestrate SBOM generation and upload."""
    try:
        setup_output_directory()
        docker_login()
        generate_sbom()

        output_dir = Path('.sbom')
        
        # Update sbom.json in root
        json_file = output_dir / 'sbom.json'
        if json_file.exists():
            update_github_file(json_file, '.sbom/sbom.json')

        # Update sbom.txt in sbom directory
        txt_file = output_dir / 'sbom.txt'
        if txt_file.exists():
            update_github_file(txt_file, '.sbom/sbom.txt')

    except Exception as e:
        logger.error(f"SBOM generation and upload failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()