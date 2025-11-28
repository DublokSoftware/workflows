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
    output_dir = Path(f'{os.getcwd()}/{get_output_directory_name()}')
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

def is_docker_in_docker():
    """
    Detect if we're running inside a Docker container (Docker-in-Docker).
    In DinD environments, volume mounts from the runner don't work as expected
    because they mount from the Docker daemon's host, not from the runner container.
    """
    # Check for /.dockerenv file (present inside Docker containers)
    if Path('/.dockerenv').exists():
        return True
    # Check cgroup for docker/container indicators
    try:
        with open('/proc/1/cgroup', 'r') as f:
            return 'docker' in f.read() or 'containerd' in f.read()
    except (FileNotFoundError, PermissionError):
        pass
    return False


def generate_sbom():
    """Generate SBOM using sbominify Docker container."""
    try:
        image_tag = os.environ['IMAGE_TAG']
        output_dir = Path(f'{os.getcwd()}/{get_output_directory_name()}')
        output_dir_str = str(output_dir.resolve())
        
        logger.info(f"IMAGE_TAG: {image_tag}")
        
        # Check if we're in a Docker-in-Docker environment
        use_docker_cp = is_docker_in_docker()
        if use_docker_cp:
            logger.info("Detected Docker-in-Docker environment, using docker cp method")
        
        sbom_json = output_dir / 'sbom.json'
        sbom_txt = output_dir / 'sbom.txt'
        
        if not use_docker_cp:
            # Try volume mount approach first (works in standard environments)
            sbom_cmd = [
                'docker', 'run', '--rm',
                '-e', f'IMAGES={image_tag}',
                '-e', 'FILE_PREFIX=',
                '-e', 'FILE_SUFFIX=',
                '-e', 'FILE_NAME=sbom',
                '-v', '/var/run/docker.sock:/var/run/docker.sock',
                '-v', f'{output_dir_str}:/output',
                '-v', f'{os.environ["HOME"]}/.docker/config.json:/root/.docker/config.json:ro',
                'ghcr.io/dockforge/sbominify:latest'
            ]
            logger.info(f"sbom_cmd: {sbom_cmd}")
            subprocess.run(sbom_cmd, check=True)
            
            # Check if files were created
            if sbom_json.exists() and sbom_txt.exists():
                logger.info("Successfully generated SBOM using volume mount")
            else:
                logger.warning("SBOM files not found after Docker run, falling back to docker cp method")
                use_docker_cp = True
        
        if use_docker_cp:
            # Use docker cp approach (works in Docker-in-Docker environments)
            container_name = f"sbom-gen-{os.getpid()}"
            alt_cmd = [
                'docker', 'run', '--name', container_name,
                '-e', f'IMAGES={image_tag}',
                '-e', 'FILE_PREFIX=',
                '-e', 'FILE_SUFFIX=',
                '-e', 'FILE_NAME=sbom',
                '-v', '/var/run/docker.sock:/var/run/docker.sock',
                '-v', f'{os.environ["HOME"]}/.docker/config.json:/root/.docker/config.json:ro',
                'ghcr.io/dockforge/sbominify:latest'
            ]
            logger.info(f"Running SBOM generation with docker cp: {alt_cmd}")
            subprocess.run(alt_cmd, check=True)
            
            # Copy files from container
            try:
                subprocess.run(['docker', 'cp', f'{container_name}:/output/sbom.json', str(sbom_json)], check=True)
                subprocess.run(['docker', 'cp', f'{container_name}:/output/sbom.txt', str(sbom_txt)], check=True)
                logger.info("Successfully copied SBOM files from container")
            finally:
                # Clean up container
                subprocess.run(['docker', 'rm', '-f', container_name], capture_output=True)
        
        logger.info("Successfully generated SBOM")

        # Log the location of the generated SBOMs
        sbom_files = list(output_dir.glob('*'))
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