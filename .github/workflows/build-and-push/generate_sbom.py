#!/usr/bin/env python3
import os
import sys
import logging
import subprocess
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_output_directory_name():
    """Generate output directory name based on project name if available."""
    project_name = os.environ.get('PROJECT_NAME', '')
    return f'.sbom_{project_name}_' if project_name else '.sbom_'

def setup_output_directory():
    """Create output directory for SBOM if it doesn't exist."""
    output_dir = Path(get_output_directory_name())
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
        image_tag = os.environ['IMAGE_TAG']
        output_dir = get_output_directory_name()
        
        sbom_cmd = [
            'docker', 'run', '--rm',
            '-e', f'IMAGES={image_tag}',
            '-e', 'FILE_PREFIX=',
            '-e', 'FILE_SUFFIX=',
            '-e', 'FILE_NAME=sbom',
            '-v', '/var/run/docker.sock:/var/run/docker.sock',
            '-v', f'{os.getcwd()}/{output_dir}:/output',
            '-v', f'{os.environ["HOME"]}/.docker/config.json:/root/.docker/config.json:ro',
            'ghcr.io/dockforge/sbominify:latest'
        ]
        
        # Log the environment variables and command
        logger.info(f"IMAGE_TAG: {image_tag}")
        logger.info(f"sbom_cmd: {sbom_cmd}")
        subprocess.run(sbom_cmd, check=True)
        logger.info("Successfully generated SBOM")
        
        # Log the location of the generated SBOMs
        sbom_output_dir = Path(os.getcwd()) / output_dir
        sbom_files = list(sbom_output_dir.glob('*'))
        for sbom_file in sbom_files:
            logger.info(f"Generated SBOM location: {sbom_file}")
    except Exception as e:
        logger.error(f"Failed to generate SBOM: {e}")
        raise

def main():
    """Main function to orchestrate SBOM generation."""
    try:
        setup_output_directory()
        # docker_login()
        generate_sbom()
    except Exception as e:
        logger.error(f"SBOM generation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()