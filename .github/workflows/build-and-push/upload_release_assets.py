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

def copy_files():
    """Copy files without dots to match release naming."""
    try:
        if Path('.vulnerability_report.txt').exists():
            shutil.copy2('.vulnerability_report.txt', 'vulnerability_report.txt')
        logger.info("Successfully copied files")
    except Exception as e:
        logger.error(f"Failed to copy files: {e}")
        raise

def upload_release_assets(version: str, image_name: str):
    """Upload release assets using GitHub CLI."""
    try:
        # Copy files without dots to match release naming
        copy_files()

        # Prepare the upload command
        upload_cmd = [
            'gh', 'release', 'upload', version,
            f"../{image_name}.tar",
            ".sbom_/sbom.json",
            ".sbom_/sbom.txt",
            "vulnerability_report.txt"
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