
import time
import os

from google import genai
from google.genai.types import CreateBatchJobConfig, JobState, HttpOptions,BatchJob
from google import genai
from google.genai import types
# Initialize the client

# Create and monitor batch job
# Initialize credentials from service account file
from google.oauth2 import service_account

project_id=os.getenv("PROJECT_ID")

credentials_path=os.getenv("SERVICE_ACCOUNT_CREDENTIALS")


def fetch_job(client, job_name: str) -> JobState:
    """
    Fetches the current state of a batch prediction job.
    
    Args:
        client: Initialized Gemini client
        job_name: Name or ID of the batch job to check
        
    Returns:
        JobState: Current state of the job
        
    Example:
        state = fetch_job_state(client, "projects/123/locations/us-central1/batchPredictionJobs/456")
        print(f"Current job state: {state}")
    """
    try:
        job = client.batches.get(name=job_name)
        return job
    except Exception as e:
        print(f"Error fetching job state: {e}")
        return None


def get_output_uri_from_job(job: BatchJob) -> str:
    """
    Extracts the output URI from a BatchJob object.

    Args:
        job: The BatchJob object.

    Returns:
        The output URI as a string, or None if not found.
    """
    if job and job.dest and job.dest.gcs_uri:
        return job.dest.gcs_uri
    return None


def read_output_file(output_uri: str,credentials=None) -> dict:
        """
        Reads the output file from GCS and creates a mapping of queries to responses.
        
        Args:
            output_uri: GCS URI where the output files are stored
            
        Returns:
            dict: Mapping of input queries to their corresponding responses
        """
        from google.cloud import storage
        import json
        
        results = []
        client = storage.Client(credentials=credentials)
        
        # Parse bucket and prefix from output URI
        bucket_name = output_uri.split("/")[2]
        prefix = "/".join(output_uri.split("/")[3:])
        
        print("bucket_name",bucket_name,prefix)

        bucket = client.get_bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        for blob in blobs:
            print("blobs",blob)
            if not blob.name.endswith('.jsonl'):
                continue
                
            content = blob.download_as_string()
            for line in content.decode('utf-8').splitlines():
                response = json.loads(line)
                query = response['request']['contents'][0]['parts'][0]['text']
                answer = response['response']['candidates'][0]['content']['parts'][0]['text']
                results.append({"query":query , "answer":answer })
                
        return results

def wait_for_job_completion(client, job_name: str, interval: int = 5) -> JobState:
    """
    Waits for a batch job to complete and returns final state.
    
    Args:
        client: Initialized Gemini client
        job_name: Name or ID of the batch job
        interval: Sleep interval between checks in seconds
        
    Returns:
        JobState: Final state of the completed job
    """
    completed_states = {
        JobState.JOB_STATE_SUCCEEDED,
        JobState.JOB_STATE_FAILED, 
        JobState.JOB_STATE_CANCELLED,
        JobState.JOB_STATE_PAUSED
    }
    
    job = fetch_job(client, job_name)
    current_state = job.state 
    while current_state not in completed_states:
        time.sleep(interval)
        current_job = fetch_job(client, job_name)
        current_state=current_job.state
        print(f"Job state: {current_state}")
        
    print(job,job.dest.gcs_uri)


    #print("output uri is ",uri)
    return current_state,job


def list_jobs(client):

    for job in client.batches.list(config=types.ListBatchJobsConfig(page_size=10)):
        print(job)


credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )

# Create and monitor batch job
client = genai.Client(
        project=project_id,
        location="us-central1",
        credentials=credentials,
        vertexai=True, 
        http_options=types.HttpOptions(api_version='v1'))



job_name="1234489749108686848"
final_state,job = wait_for_job_completion(client, job_name)
output_uri=get_output_uri_from_job(job)

result=read_output_file(output_uri,credentials)

print("result , ",result)
print(f"Job completed with final state: {final_state}")