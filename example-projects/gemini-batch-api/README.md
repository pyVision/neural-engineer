# Maximizing Efficiency with Google Gemini's Bulk Completion API

## Introduction

Google Gemini's Batch Prediction API represents a significant advancement in handling large-scale language model inference tasks efficiently and cost-effectively. Unlike traditional single-request APIs, the batch prediction feature allows developers to process multiple prompts in a single API call, offering substantial improvements in throughput while reducing per-request costs. By batching requests together, organizations can benefit from optimized pricing structures and lower operational costs compared to individual API calls. 

This article explores the capabilities, advantages, and practical implementation of Gemini's batch prediction API.


## Setting up Google Gemini's Batch Prediction API

The following Gemini models support batch predictions:

Gemini 2.0 Flash
Gemini 2.0 Flash-Lite

Batch requests for Gemini models accept BigQuery storage sources and Cloud Storage sources.  In this article we will use Google Cloud Storage as a source . 

### Service Account Setup and Storage Configuration

First, create a service account and grant necessary permissions:

```bash
export SERVICE_ACCOUNT_ID="genai-neuralengineer"
# Get project ID
export PROJECT_ID="my-gemini-project-123"
export PROJECT_LOCATION="us-central1"

# Get project location
gcloud config get-value compute/region

# Create service account
gcloud iam service-accounts create ${SERVICE_ACCOUNT_ID} \
    --display-name="Gemini API Service Account"

# Download service account key
gcloud iam service-accounts keys create credentials.json \
    --iam-account=${SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com

# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable generativelanguage.googleapis.com

# Grant Vertex AI User role
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Grant Storage Object Viewer role for model access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"

# Grant Storage Object User role for writing outputs
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectUser"

# Grant Storage Object User role for writing outputs and full bucket access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.buckets.get"

# Grant Storage Admin role for full bucket access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
```

### Create a GCS bucket and set permissions:

```bash
export BUCKET_NAME="gemini-input-1"
# Create a GCS bucket
gsutil mb -p ${PROJECT_ID} gs://${BUCKET_NAME}

# Apply bucket permissions
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com:objectViewer,objectCreator gs://${BUCKET_NAME}
```

### Input File Preparation

To use the bulk completion API, you'll need to prepare your input in a specific format. The recommended approach is to create a JSONL (JSON Lines) file where each line represents a separate prompt:

Create a JSONL file (input.jsonl) with your prompts:

```json
{
    "request": {
        "contents": [
            {
                "role": "user", 
                "parts": [{"text": "What is machine learning?"}]
            }
        ],
        "system_instruction": {
            "parts": ["text": "I am an AI assistant"]
        },
        "generation_config": {
            "temperature": 0.7,
            "maxOutputTokens": 50, 
            "topP": 0.8,
            "topK": 40
        }
    }
}
```

The input JSONL file should contain one request per line. Each request can include:

- `contents`: The prompt text and role (required)
- `system_instruction`: Optional system prompt to guide model behavior
- `generation_config`: Optional parameters to control generation including:
  - `temperature`: Controls randomness (0.0-1.0)
  - `maxOutputTokens`: Maximum length of response
  - `topP`: Nucleus sampling parameter  
  - `topK`: Number of highest probability tokens to consider

Example JSONL with multiple requests:

```json
{"request": {"contents": [{"role": "user", "parts": [{"text": "What is machine learning?"}]}],"system_instruction":{"parts":["text":"I am an AI assistant"]},"generation_config": {"temperature": 0.7, "maxOutputTokens": 50, "topP": 0.8, "topK": 40}}}
{"request": {"contents": [{"role": "user", "parts": [{"text": "Explain neural networks"}]}]}}
```


Copy the file to your GCS bucket:

```bash
# Copy input file to GCS
gsutil cp input.jsonl gs://${BUCKET_NAME}/input.jsonl
```

Remember to replace:
- PROJECT_ID with your Google Cloud project ID
- SERVICE_ACCOUNT_ID with your chosen service account name
- BUCKET_NAME with your desired bucket name

## Implementation Guide


### Pre Requisite Installation and Setup

```bash
pip install --upgrade google-genai

#export the environment variables 
export PROJECT_ID=""
export SERVICE_ACCOUNT_CREDENTIALS=""


```

### 1. Authentication Setup

Authentication with Google Gemini's API requires proper credentials setup. There are two main approaches:

```python
from google.oauth2 import service_account
from google import genai
from google.genai import types

project_id=os.getenv("PROJECT_ID")
credentials_path=os.getenv("SERVICE_ACCOUNT_CREDENTIALS")


def setup_gemini_client()
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
```

### 2. Creating and Submitting Bulk Requests

The bulk API accepts input through various sources including Google Cloud Storage (GCS) or BigQuery. Here's how to create a batch job:

```python
def create_batch_job(
    client,
    model: str = "gemini-1.5-flash-002",
    input_uri: str = "gs://your-bucket/input.jsonl",
    output_uri: str = "gs://your-bucket/output/"
) -> BatchJob:
    """
    Creates a batch prediction job using Google Gemini API.
    
    Args:
        client: Initialized Gemini client
        model: Model name to use for predictions
        input_uri: GCS source URI containing requests
        output_uri: GCS destination URI for results
    
    Returns:
        BatchJob: Job object containing name and state
    """


    # Create the batch job with configuration
    job = client.batches.create(
        model=model,
        src=input_uri,
        config=types.CreateBatchJobConfig(
            dest=output_uri
        )
    )
    return job
```

### 3. Monitoring Job Status

Batch jobs are asynchronous, so it's important to monitor their status:

```python
def wait_for_job_completion(client, job_name: str, interval: int = 30) -> JobState:
    """
    Waits for a batch job to complete and returns final state.
    
    Args:
        client: Initialized Gemini client
        job_name: Name or ID of the batch job
        interval: Sleep interval between checks in seconds
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
        current_state = current_job.state
        print(f"Job state: {current_state}")
    
    return current_state, job
```

### 4. Processing Output Results

Once the job is complete, you can process the results from the output location:

```python
def read_output_file(output_uri: str, credentials=None) -> dict:
    """
    Reads the output file from GCS and creates a mapping of queries to responses.
    
    Args:
        output_uri: GCS URI where the output files are stored
        credentials: Service account credentials
    
    Returns:
        list: List of dictionaries containing query-answer pairs
    """
    from google.cloud import storage
    import json
    
    results = []
    client = storage.Client(credentials=credentials)
    
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
            results.append({"query": query, "answer": answer})
    
    return results
```

## Job Management and Monitoring


### Monitoring via Google Cloud Console

The Google Cloud Console provides a comprehensive visual interface for monitoring and managing your batch prediction jobs. Navigate to the Vertex AI Batch Predictions page at https://console.cloud.google.com/vertex-ai/batch-predictions to access:



The console interface allows you to:
- Track multiple batch jobs simultaneously and Analyze historical job patterns
- View detailed performance metrics and Monitor resource allocation
- Access error logs for troubleshooting

This visual monitoring capability complements the programmatic monitoring methods and provides a user-friendly way to oversee your batch prediction operations.

### 1. Listing Active Jobs

You can monitor all your batch jobs using the list operation:

```python
def list_jobs(client):
    for job in client.batches.list(config=types.ListBatchJobsConfig(page_size=10)):
        print(job)
```

### 2. Individual Job Status Checking

To check the status of a specific job:

```python
def fetch_job(client, job_name: str) -> JobState:
    """
    Retrieves the current state of a batch prediction job.
    
    Args:
        client: Initialized Gemini API client
        job_name: The unique identifier/name of the batch job
    
    Returns:
        JobState: Object containing job details and current state
        None: If there's an error fetching the job
    
    Raises:
        Exception: When API call fails or job cannot be found
    """
    try:
        job = client.batches.get(name=job_name)
        return job
    except Exception as e:
        print(f"Error fetching job state: {e}")
        return None
```


## End-to-End Implementation Example

Here's how to put it all together:

```python
# Initialize client
client = setup_gemini_client()

# Create and submit batch job
job = create_batch_job(
    client=client,
    input_uri="gs://your-bucket/t1/input.jsonl",
    output_uri="gs://your-bucket/t1/output/"
)

# Wait for job completion
final_state, job = wait_for_job_completion(client, job.name)

# Get output URI and process results
output_uri = get_output_uri_from_job(job)
results = read_output_file(output_uri, credentials)

print(f"Job completed with state: {final_state}")
for result in results:
    print(f"Query: {result['query']}")
    print(f"Answer: {result['answer']}\n")
```



## Summary

Google Gemini's bulk completion API offers a powerful solution for organizations needing to process large volumes of text generation requests efficiently. The key benefits include:

- Significantly improved throughput and performance
- Cost-effective processing of large-scale requests
- Simplified implementation and maintenance

## REFERENCES
- https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/batch-prediction-gemini