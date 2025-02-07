#!/usr/bin/env python3
import os
import sys
import shutil
import logging
from pathlib import Path
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_file_paths():
    """Generate file paths based on project name if available."""
    project_name = os.environ.get('PROJECT_NAME', '')
    if project_name:
        return {
            'vuln_report_dot': f'.vulnerability_report_{project_name}.txt',
            'vuln_report_no_dot': f'vulnerability_report_{project_name}.txt',
            'sbom_dir': f'.sbom_{project_name}_',
            'sbom_json': f'.sbom_{project_name}_/sbom.json',
            'sbom_txt': f'.sbom_{project_name}_/sbom.txt'
        }
    return {
        'vuln_report_dot': '.vulnerability_report.txt',
        'vuln_report_no_dot': 'vulnerability_report.txt',
        'sbom_dir': '.sbom_',
        'sbom_json': '.sbom_/sbom.json',
        'sbom_txt': '.sbom_/sbom.txt'
    }

def copy_files():
    """Copy files without dots to match release naming."""
    try:
        paths = get_file_paths()
        if Path(paths['vuln_report_dot']).exists():
            shutil.copy2(paths['vuln_report_dot'], paths['vuln_report_no_dot'])
        logger.info("Successfully copied files")
    except Exception as e:
        logger.error(f"Failed to copy files: {e}")
        raise

def upload_release_assets(version: str, image_name: str):
    """Upload release assets using GitHub CLI."""
    try:
        # Copy files without dots to match release naming
        copy_files()

        paths = get_file_paths()

        # Prepare the upload command
        upload_cmd = [
            'gh', 'release', 'upload', version,
            f"../{image_name}.tar",
            paths['sbom_json'],
            paths['sbom_txt'],
            paths['vuln_report_no_dot']
        ]

        # Log the upload command
        logger.info(f"Uploading release assets for version {version} with command: {upload_cmd}")

        # Run the upload command
        subprocess.run(upload_cmd, check=True)
        logger.info(f"Successfully uploaded release assets for version {version}")
    except Exception as e:
        logger.error(f"Failed to upload release assets: {e}")
        raise

def main():
    try:
        # Get environment variables
        version = os.environ.get('VERSION')
        image_name = os.environ.get('IMAGE_NAME')
        if not version or not image_name:
            logger.error("Missing required environment variables")
            sys.exit(1)

        # Log environment variables
        logger.info(f"VERSION: {version}")
        logger.info(f"IMAGE_NAME: {image_name}")

        # Upload release assets
        upload_release_assets(version, image_name)
    except Exception as e:
        logger.error(f"Release asset upload failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()