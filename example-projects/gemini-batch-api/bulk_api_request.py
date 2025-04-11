
import time
import os

from google import genai
from google.genai.types import CreateBatchJobConfig, JobState, HttpOptions,BatchJob
from google import genai
from google.genai import types
from google.genai.types import CreateBatchJobConfig, JobState, HttpOptions, BatchJob, Content
from google.oauth2 import service_account

project_id=os.getenv("PROJECT_ID")

credentials_path=os.getenv("SERVICE_ACCOUNT_CREDENTIALS")


def setup_gemini_client():
    # Method 1: Using service account credentials file
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )

    # Initialize the client
    client = genai.Client(
        project=project_id,
        location="us-central1",
        credentials=credentials,
        vertexai=True,
        http_options=types.HttpOptions(api_version='v1')
    )

    return client 

def create_batch_job(
    client,
    model: str = "gemini-1.5-flash-002",
    input_uri: str = "gs://your-bucket/input.jsonl",
    output_uri: str = "gs://your-bucket/output/a1"
) -> BatchJob:
    """
    Creates a batch prediction job using Google Gemini API.
    
    Args:
        client: Initialized Gemini client
        model: Model name to use for predictions
        input_uri: BigQuery source URI containing requests
        output_uri: BigQuery destination URI for results
    
    Returns:
        BatchJob: Job object containing name and state
    """
    if not output_uri:
        raise ValueError("output_uri must be specified")

    job = client.batches.create(
        model=model,
        src=input_uri, 
        config=CreateBatchJobConfig(
            dest=output_uri
            
            )
       
    )
    
    return job


    def read_output_file(output_uri: str) -> dict:
        """
        Reads the output file from GCS and creates a mapping of queries to responses.
        
        Args:
            output_uri: GCS URI where the output files are stored
            
        Returns:
            dict: Mapping of input queries to their corresponding responses
        """
        from google.cloud import storage
        import json
        
        results = {}
        client = storage.Client()
        
        # Parse bucket and prefix from output URI
        bucket_name = output_uri.split("/")[2]
        prefix = "/".join(output_uri.split("/")[3:])
        
        bucket = client.get_bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        for blob in blobs:
            if not blob.name.endswith('.jsonl'):
                continue
                
            content = blob.download_as_string()
            for line in content.decode('utf-8').splitlines():
                response = json.loads(line)
                query = response['request']['contents'][0]['parts'][0]['text']
                answer = response['response']['candidates'][0]['content']['parts'][0]['text']
                results[query] = answer
                
        return results



def main():
    # Set up input and output URIs
    bucket_name = "gemini-input-1"
    input_uri = f"gs://{bucket_name}/input.jsonl"
    output_uri = f"gs://{bucket_name}/output/a1"
    


    # Create and monitor batch job
    client = setup_gemini_client()

    job = create_batch_job(
        client=client,
        input_uri=input_uri,
        output_uri=output_uri
    )
    
    print(f"Created batch job: {job.name}")

if __name__ == "__main__":
    main()