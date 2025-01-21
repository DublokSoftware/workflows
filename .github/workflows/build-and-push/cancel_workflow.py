#!/usr/bin/env python3
import os
import requests
import time

def get_workflow_status(github_token, github_repository, github_run_id):
    url = f"https://api.github.com/repos/{github_repository}/actions/runs/{github_run_id}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get('status'), data.get('conclusion')
        else:
            print(f"Failed to get workflow status. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None, None
    except Exception as e:
        print(f"Error occurred while getting workflow status: {str(e)}")
        return None, None

def wait_for_workflow_stop(github_token, github_repository, github_run_id, timeout=300, check_interval=5):
    print("Waiting for workflow to stop...")
    start_time = time.time()
    
    while True:
        status, conclusion = get_workflow_status(github_token, github_repository, github_run_id)
        
        if status is None:
            return False
            
        print(f"Current workflow status: {status}, conclusion: {conclusion}")
        
        if status == "completed":
            print("Workflow has stopped successfully")
            return True
            
        if time.time() - start_time > timeout:
            print(f"Timeout reached ({timeout}s) while waiting for workflow to stop")
            return False
            
        time.sleep(check_interval)

def cancel_workflow(max_retries=3, retry_delay=2):
    # Get environment variables
    github_token = os.environ.get('GITHUB_TOKEN')
    github_repository = os.environ.get('GITHUB_REPOSITORY')
    github_run_id = os.environ.get('GITHUB_RUN_ID')

    # Check if required environment variables are present
    if not all([github_token, github_repository, github_run_id]):
        print("Error: Required environment variables are not set")
        return False

    # API endpoint
    url = f"https://api.github.com/repos/{github_repository}/actions/runs/{github_run_id}/cancel"
    
    # Headers for the request
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    for attempt in range(max_retries):
        try:
            print(f"Cancelling workflow... (Attempt {attempt + 1}/{max_retries})")
            response = requests.post(url, headers=headers)
            
            if response.status_code == 202:
                print("Workflow cancellation request successful")
                # Wait for the workflow to actually stop
                if wait_for_workflow_stop(github_token, github_repository, github_run_id):
                    return True
                else:
                    print("Failed to confirm workflow stoppage")
            else:
                print(f"Failed to cancel workflow. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                
            if attempt < max_retries - 1:  # Don't sleep after the last attempt
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                
        except Exception as e:
            print(f"Error occurred while cancelling workflow: {str(e)}")
            
            if attempt < max_retries - 1:  # Don't sleep after the last attempt
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
    
    return False

def main():
    if cancel_workflow():
        print("Workflow cancellation completed")
        # Keep the script running
        while True:
            time.sleep(1)
    else:
        print("Failed to cancel workflow after all retry attempts")
        exit(1)

if __name__ == "__main__":
    main()