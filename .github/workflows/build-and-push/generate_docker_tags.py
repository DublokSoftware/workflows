#!/usr/bin/env python3
import json
import os
import sys

def generate_docker_tags(tags_json: str, docker_username: str, image_name: str, repo_owner: str, push_to_dockerhub: bool, push_to_ghcr: bool) -> tuple[str, str, str, str, str]:
    """Generate Docker Hub and GitHub Container Registry tags."""
    try:
        # Print inputs
        print("=== Input Parameters ===")
        print(f"PUSH_TO_DOCKERHUB: {push_to_dockerhub}")
        print(f"PUSH_TO_GHCR: {push_to_ghcr}")
        print(f"TAGS_JSON: {tags_json}")
        print(f"DOCKER_USERNAME: {docker_username}")
        print(f"IMAGE_NAME: {image_name}")
        print(f"REPO_OWNER: {repo_owner}")
        print(f"GITHUB_SHA: {os.environ.get('GITHUB_SHA', '')}")        
        print("=====================")

        # Get full SHA from environment
        full_sha = os.environ.get('GITHUB_SHA', '')

        # Truncate SHA to the first 7 characters
        short_sha = full_sha[:7]

        # Convert repository owner to lowercase
        repo_owner = repo_owner.lower()

        # Parse tags JSON
        tags = json.loads(tags_json)

        # Generate Docker Hub tags
        dockerhub_tags = [f"{docker_username}/{image_name}:{tag}" for tag in tags]
        dockerhub_tags_str = ','.join(dockerhub_tags)

        # Generate GitHub Container Registry tags
        ghcr_tags = [f"ghcr.io/{repo_owner}/{image_name}:{tag}" for tag in tags]
        ghcr_tags_str = ','.join(ghcr_tags)

        # Generate GitHub Container Registry SHA tag
        ghcr_sha_tag = f"ghcr.io/{repo_owner}/{image_name}:{short_sha}"
        dockerhub_sha_tag = f"{docker_username}/{image_name}:{short_sha}"

        # Combine all tags into a comma-separated list
        all_tags = ""
        if push_to_dockerhub:
            all_tags = ','.join(dockerhub_tags) + f",{dockerhub_sha_tag}"
        if push_to_ghcr:
            all_tags = ','.join(ghcr_tags) + f",{ghcr_sha_tag}"

        sha_tag = ""
        if push_to_ghcr:
            sha_tag = ghcr_sha_tag
        elif push_to_dockerhub:
            sha_tag = dockerhub_sha_tag

        # Print all tags
        print("\n=== Docker Hub Tags ===")
        for tag in dockerhub_tags:
            print(tag)

        print("\n=== GitHub Container Registry Tags ===")
        for tag in ghcr_tags:
            print(tag)

        print("\n=== GitHub Container Registry SHA Tag ===")
        print(ghcr_sha_tag)

        print("\n=== Docker Hub SHA Tag ===")
        print(dockerhub_sha_tag)

        print("\n+== SHA Tag ===")
        print(sha_tag)

        # Print final outputs
        print("\n=== Final Outputs ===")
        print(f"dockerhub_tags={dockerhub_tags_str}")
        print(f"ghcr_tags={ghcr_tags_str}")
        print(f"ghcr_sha_tag={ghcr_sha_tag}")
        print(f"dockerhub_sha_tag={dockerhub_sha_tag}")
        print(f"sha_tag={sha_tag}")
        print(f"tags={all_tags}")
        print("=====================")

        # Set outputs
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"dockerhub_tags={dockerhub_tags_str}\n")
            f.write(f"ghcr_tags={ghcr_tags_str}\n")
            f.write(f"ghcr_sha_tag={ghcr_sha_tag}\n")
            f.write(f"dockerhub_sha_tag={dockerhub_sha_tag}\n")
            f.write(f"sha_tag={sha_tag}\n")
            f.write(f"tags={all_tags}\n")

        return dockerhub_tags_str, ghcr_tags_str, ghcr_sha_tag, dockerhub_sha_tag, sha_tag, all_tags

    except Exception as e:
        print(f"Error generating Docker tags: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    tags_json = os.environ['TAGS_JSON']
    docker_username = os.environ['DOCKER_USERNAME']
    image_name = os.environ['IMAGE_NAME']
    repo_owner = os.environ['REPO_OWNER']
    push_to_dockerhub = os.environ['PUSH_TO_DOCKERHUB'] == 'true'
    push_to_ghcr = os.environ['PUSH_TO_GHCR'] == 'true'

    generate_docker_tags(tags_json, docker_username, image_name, repo_owner, push_to_dockerhub, push_to_ghcr)