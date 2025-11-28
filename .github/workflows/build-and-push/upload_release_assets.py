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
            'sbom_txt': f'.sbom_{project_name}_/sbom.txt',
            'version_prefix': f'{project_name}-'
        }
    return {
        'vuln_report_dot': '.vulnerability_report.txt',
        'vuln_report_no_dot': 'vulnerability_report.txt',
        'sbom_dir': '.sbom_',
        'sbom_json': '.sbom_/sbom.json',
        'sbom_txt': '.sbom_/sbom.txt',
        'version_prefix': ''
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
        
        # Construct version with optional prefix
        versioned_tag = f"{paths['version_prefix']}{version}"

        # Define all potential assets
        all_assets = [
            (f"../{image_name}.tar", True),  # (path, required)
            (paths['sbom_json'], False),
            (paths['sbom_txt'], False),
            (paths['vuln_report_no_dot'], False)
        ]
        
        # Filter to only existing files
        existing_assets = []
        for asset_path, required in all_assets:
            if Path(asset_path).exists():
                existing_assets.append(asset_path)
                logger.info(f"Found asset: {asset_path}")
            else:
                if required:
                    logger.error(f"Required asset not found: {asset_path}")
                    raise FileNotFoundError(f"Required asset not found: {asset_path}")
                else:
                    logger.warning(f"Optional asset not found: {asset_path}")

        if not existing_assets:
            logger.error("No assets found to upload")
            raise FileNotFoundError("No assets found to upload")

        # Prepare the upload command
        upload_cmd = ['gh', 'release', 'upload', versioned_tag] + existing_assets

        # Log the upload command
        logger.info(f"Uploading release assets for version {versioned_tag} with command: {upload_cmd}")

        # Run the upload command
        subprocess.run(upload_cmd, check=True)
        logger.info(f"Successfully uploaded release assets for version {versioned_tag}")
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
    import time

    def retry_main(max_retries=3, delay=2):
        for attempt in range(max_retries):
            try:
                main()
                break
            except Exception as e:
                # Retry on any Exception, especially for transient CLI errors
                logger.warning(f"Retrying due to error: {e} (attempt {attempt+1}/{max_retries})")
                time.sleep(delay)
        else:
            logger.error(f"Failed after {max_retries} attempts.")
            sys.exit(1)

    retry_main(max_retries=3, delay=2)