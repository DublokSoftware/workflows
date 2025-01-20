#!/usr/bin/env python3
import json
import os
import sys

def generate_docker_tags(tags_json: str, docker_username: str, image_name: str, repo_owner: str) -> tuple[str, str, str]:
    """Generate Docker Hub and GitHub Container Registry tags."""
    try:
        # Print inputs
        print("=== Input Parameters ===")
        print(f"TAGS_JSON: {tags_json}")
        print(f"DOCKER_USERNAME: {docker_username}")
        print(f"IMAGE_NAME: {image_name}")
        print(f"REPO_OWNER: {repo_owner}")
        print("=====================")

        # Convert repository owner to lowercase
        repo_owner = repo_owner.lower()
        
        # Parse tags JSON
        tags = json.loads(tags_json)
        
        # Generate Docker Hub tags
        dockerhub_tags = [f"{docker_username}/{image_name}:{tag}" for tag in tags]
        dockerhub_tags_str = ','.join(dockerhub_tags)
        print("\n=== Docker Hub Tags ===")
        for tag in dockerhub_tags:
            print(tag)
        
        # Generate GitHub Container Registry tags
        ghcr_tags = [f"ghcr.io/{repo_owner}/{image_name}:{tag}" for tag in tags]
        ghcr_tags_str = ','.join(ghcr_tags)
        print("\n=== GitHub Container Registry Tags ===")
        for tag in ghcr_tags:
            print(tag)
        
        # Combine all tags into a comma-separated list
        all_tags = ','.join(dockerhub_tags + ghcr_tags)
        
        # Print final outputs
        print("\n=== Final Outputs ===")
        print(f"dockerhub_tags={dockerhub_tags_str}")
        print(f"ghcr_tags={ghcr_tags_str}")
        print(f"tags={all_tags}")
        print("=====================")
        
        # Set outputs
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"dockerhub_tags={dockerhub_tags_str}\n")
            f.write(f"ghcr_tags={ghcr_tags_str}\n")
            f.write(f"tags={all_tags}\n")
            
        return dockerhub_tags_str, ghcr_tags_str, all_tags
        
    except Exception as e:
        print(f"Error generating Docker tags: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    tags_json = os.environ['TAGS_JSON']
    docker_username = os.environ['DOCKER_USERNAME']
    image_name = os.environ['IMAGE_NAME']
    repo_owner = os.environ['REPO_OWNER']
    
    generate_docker_tags(tags_json, docker_username, image_name, repo_owner)