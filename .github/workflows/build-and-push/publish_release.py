#!/usr/bin/env python3
import os
import sys
import json
import base64
import time
import requests
import logging
from typing import Dict, Optional, Tuple
from requests.exceptions import RequestException

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors"""
    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)

class GitHubReleaseManager:
    def __init__(self, token: str, repo: str, branch: str, sha: str):
        self.token = token
        self.repo = repo
        self.branch = branch
        self.sha = sha
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = f"https://api.github.com/repos/{repo}"
        self.project_name = os.environ.get('PROJECT_NAME', '')

    def _make_request(self, method: str, endpoint: str, data: Dict = None, 
                     max_retries: int = 3, retry_delay: int = 2) -> requests.Response:
        """Make HTTP request to GitHub API with retry mechanism"""
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data
                )
                
                if response.status_code in [200, 201, 204]:
                    return response
                
                if response.status_code == 404:
                    return response
                
                if response.status_code == 429:  # Rate limit exceeded
                    reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                    sleep_time = max(reset_time - time.time(), 0) + 1
                    logger.warning(f"Rate limit exceeded. Waiting {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    continue
                
                logger.error(f"Request failed: {response.status_code} - {response.text}")
                
            except RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {str(e)}")
                
            if attempt < max_retries - 1:
                sleep_time = retry_delay * (attempt + 1)
                logger.warning(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            
        raise GitHubAPIError(
            f"Failed after {max_retries} attempts",
            response.status_code if 'response' in locals() else None,
            response.text if 'response' in locals() else None
        )

    def get_version_file_name(self) -> str:
        """Get version file name based on project name if available"""
        return f".version_{self.project_name}_{self.branch}.json" if self.project_name else f".version_{self.branch}.json"

    def get_tag_name(self, version: str) -> str:
        """Get tag name based on project name if available"""
        return f"{self.project_name}-{version}" if self.project_name else version

    def get_release_name(self, version: str) -> str:
        """Get release name based on project name if available"""
        return f"Release {self.project_name} {version}" if self.project_name else f"Release {version}"

    def get_version_file_content(self) -> Dict:
        """Get and parse version file content"""
        version_file = self.get_version_file_name()
        endpoint = f"contents/{version_file}?ref={self.branch}"
        response = self._make_request('GET', endpoint)
        
        if response.status_code == 404:
            raise GitHubAPIError(f"Version file {version_file} not found")
        
        try:
            content = base64.b64decode(response.json()['content']).decode('utf-8')
            return json.loads(content)
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
            raise GitHubAPIError(f"Failed to parse version file: {str(e)}")

    def check_tag_exists(self, tag_name: str) -> Tuple[bool, Optional[str]]:
        """Check if tag exists and return its SHA if it does"""
        response = self._make_request('GET', f"git/refs/tags/{tag_name}")
        if response.status_code == 200:
            return True, response.json()['object']['sha']
        return False, None

    def delete_tag(self, tag_name: str) -> bool:
        """Delete an existing tag"""
        logger.info(f"Attempting to delete tag: {tag_name}")
        response = self._make_request('DELETE', f"git/refs/tags/{tag_name}")
        return response.status_code in [200, 204]

    def delete_release(self, tag_name: str) -> bool:
        """Delete an existing release"""
        logger.info(f"Attempting to delete release for tag: {tag_name}")
        response = self._make_request('GET', f"releases/tags/{tag_name}")
        
        if response.status_code == 200:
            release_id = response.json()['id']
            delete_response = self._make_request('DELETE', f"releases/{release_id}")
            return delete_response.status_code in [200, 204]
        return True

    def create_tag(self, tag_name: str) -> bool:
        """Create a new tag, handling existing tags"""
        logger.info(f"Creating tag: {tag_name}")
        
        # Check and handle existing tag
        tag_exists, existing_sha = self.check_tag_exists(tag_name)
        if tag_exists:
            logger.info(f"Tag {tag_name} already exists with SHA: {existing_sha}")
            if not self.delete_release(tag_name) or not self.delete_tag(tag_name):
                raise GitHubAPIError(f"Failed to delete existing tag/release: {tag_name}")
        
        response = self._make_request(
            'POST',
            "git/refs",
            data={
                'ref': f'refs/tags/{tag_name}',
                'sha': self.sha
            }
        )
        return True

    def create_release(self, version_data: Dict) -> str:
        """Create a new release with detailed release notes"""
        logger.info(f"Creating release for version: {version_data['version']}")
        
        version = version_data['version']
        suffix = version.split('-')[1] if '-' in version else ''
        is_prerelease = suffix.lower() in ['alpha', 'beta', 'rc']
        
        tag_name = self.get_tag_name(version)
        release_name = self.get_release_name(version)
        
        release_notes = self._generate_release_notes(version_data, is_prerelease)
        
        response = self._make_request(
            'POST',
            "releases",
            data={
                'tag_name': tag_name,
                'target_commitish': self.sha,
                'name': release_name,
                'body': release_notes,
                'draft': False,
                'prerelease': is_prerelease
            }
        )
        
        return response.json()['upload_url']

    def _generate_release_notes(self, version_data: Dict, is_prerelease: bool) -> str:
        """Generate formatted release notes"""
        project_info = f"Project: {self.project_name}\n" if self.project_name else ""
        
        return f"""# {self.get_release_name(version_data['version'])}

## Release Information
{project_info}- Version: {version_data['version']}
- Build Number: {version_data['build_number']}
- Branch: {version_data['branch']}
- Release Type: {'Pre-release' if is_prerelease else 'Stable Release'}
- Commit SHA: {self.sha}

## Docker Tags
{chr(10).join(['- ' + tag for tag in version_data['tags']])}

## Additional Information
- Release Date: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}
- Created by: GitHub Actions
"""

def main():
    # Validate environment variables
    required_env_vars = {
        'GITHUB_TOKEN': os.environ.get('GITHUB_TOKEN'),
        'GITHUB_REPOSITORY': os.environ.get('GITHUB_REPOSITORY'),
        'GITHUB_REF': os.environ.get('GITHUB_REF'),
        'GITHUB_SHA': os.environ.get('GITHUB_SHA')
    }

    missing_vars = [k for k, v in required_env_vars.items() if not v]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    branch = required_env_vars['GITHUB_REF'].replace('refs/heads/', '')
    
    try:
        manager = GitHubReleaseManager(
            token=required_env_vars['GITHUB_TOKEN'],
            repo=required_env_vars['GITHUB_REPOSITORY'],
            branch=branch,
            sha=required_env_vars['GITHUB_SHA']
        )

        # Get version information
        version_data = manager.get_version_file_content()
        logger.info(f"Version data: {json.dumps(version_data, indent=2)}")

        # Create tag with project name if available
        tag_name = manager.get_tag_name(version_data['version'])
        manager.create_tag(tag_name)
        logger.info(f"Successfully created tag: {tag_name}")

        # Create release
        upload_url = manager.create_release(version_data)
        logger.info(f"Successfully created release: {tag_name}")

        # Set output for GitHub Actions
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"version={tag_name}\n")
            f.write(f"release_created=true\n")
            f.write(f"upload_url={upload_url}\n")

    except GitHubAPIError as e:
        logger.error(f"GitHub API Error: {e.message}")
        if e.status_code:
            logger.error(f"Status Code: {e.status_code}")
        if e.response_text:
            logger.error(f"Response: {e.response_text}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()