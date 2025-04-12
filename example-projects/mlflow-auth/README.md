 # Securing MLflow: Implementing User Authentication and Experiment Access Control

## Introduction

This guide demonstrates how to set up a self-hosted MLflow server with basic authentication and implement user-specific experiment access control. For a comprehensive overview of MLflow hosting with authentication, you can also refer to this excellent article: [Hosting MLflow with Authentication: A Step-by-Step Guide](https://medium.com/neural-engineer/hosting-mlflow-with-authentication-a-step-by-step-guide-5db351ddede0).

## Project Structure

The project consists of the following key components:

```
mlflow-auth/
├── docker-compose.yaml
├── mlflow-auth/
│   └── basic-auth.ini
├── user_auth.py
└── README.md
```

## Setting up MLflow Server with Authentication

### 1. Docker Compose Configuration

We use Docker Compose to set up our MLflow server. Here's our configuration:

```yaml
version: '3.7'

services:
    mlflow:
        image: ghcr.io/mlflow/mlflow:v2.15.1
        container_name: mlflow
        expose:
            - "17001"
        ports:
            - "17001:17001"
        environment:
            MLFLOW_BACKEND_STORE_URI: "./mlflow-db/mlflow.db"
            MLFLOW_AUTH_CONFIG_PATH: "/var/lib/mlflow/mlflow-auth/basic-auth.ini"
            MLFLOW_ARTIFACT_ROOT: "/var/lib/mlflow/mlflow-artifacts"
        volumes:
            - ./mlflow-auth:/var/lib/mlflow/mlflow-auth
            - ./mlflow-db:/var/lib/mlflow/mlflow-db
            - ./mlflow-artifacts:/var/lib/mlflow/mlflow-artifacts
        command: mlflow server --host 0.0.0.0 --port 17001 --app-name=basic-auth
```

### 2. Basic Authentication Configuration

The `basic-auth.ini` file configures the authentication settings:

```ini
[mlflow]
admin_username = admin
admin_password = admin
default_permission = NO_PERMISSIONS
database_uri = sqlite:///basic_auth.db
```

This configuration block defines authentication and permission settings for MLflow server:

default_permission = NO_PERMISSIONS is particularly important for access control:
- Sets the baseline permission level for all new users/requests .It implements a "deny by default" security model and Prevents unauthorized access
- NO_PERMISSIONS means users have no access by default  
- Users need to be explicitly granted permissions to access MLflow resources

admin_username and admin_password - Credentials for the admin user
database_uri - Location of the authentication database

### 3. User Management and Experiment Access Control

Below is a Python script that demonstrates:
- Creating users with authentication
- Managing user-specific experiment access
- Demonstrating how different users can only see their own experiments
- Showing admin access to all experiments

```python
# Import required libraries
from mlflow.server import get_app_client
import os 
from mlflow import MlflowClient
import mlflow 
from mlflow.entities import ViewType

class User:
    MLFLOW_TRACKING_USERNAME = "MLFLOW_TRACKING_USERNAME"
    MLFLOW_TRACKING_PASSWORD = "MLFLOW_TRACKING_PASSWORD"

    def __init__(self, username, password) -> None:
        self.username = username
        self.password = password
        self.env = {}

    # ... (context manager methods)

# Initialize MLflow setup
admin = User("admin", "admin")
tracking_uri = "http://localhost:7001/"

mlflow.set_tracking_uri(uri=tracking_uri)

# Create users and experiments
with admin:
    auth_client = get_app_client(
        "basic-auth", 
        tracking_uri="http://localhost:7001/"
    )
    
    # Create test users
    for username, password in [("user1", "test123"), ("user2", "test123")]:
        try:
            auth_client.create_user(username=username, password=password)
            print(f"Created user: {username}")
        except Exception as e:
            print(f"User {username} already exists or error: {str(e)}")
```

## Running the Example

Here's how to create and search for experiments with different users:

```python
# Create experiments with different users
user1 = User("user1", "test123")
user2 = User("user2", "test123")

# User 1 creates and runs experiments
with user1:
    mlflow.set_experiment("/user1/experiment1")
    with mlflow.start_run():
        mlflow.log_metric("metric1", 1.0)
    
    mlflow.set_experiment("/user1/experiment2")
    with mlflow.start_run():
        mlflow.log_metric("metric2", 2.0)

# User 2 creates and runs experiments
with user2:
    mlflow.set_experiment("/user2/experiment1")
    with mlflow.start_run():
        mlflow.log_metric("metric3", 3.0)

# Search experiments with different users
def list_experiments(user):
    with user:
        experiments = mlflow.search_experiments()
        print(f"\n{user.username}'s visible experiments:")
        for exp in experiments:
            print(f"- {exp.name}")

# Show experiments visible to each user
list_experiments(user1)  # Should see only user1's experiments
list_experiments(user2)  # Should see only user2's experiments
list_experiments(admin)  # Should see all experiments
```

Expected output:

```
user1's visible experiments:
- /user1/experiment1
- /user1/experiment2

user2's visible experiments:
- /user2/experiment1

admin's visible experiments:
- /user1/experiment1
- /user1/experiment2
- /user2/experiment1
```


1. Start the MLflow server:
```bash
1. Start the MLflow server:
```bash
docker-compose -f docker-compose.yaml up -d
```

2. Stop the MLflow server:
```bash
docker-compose -f docker-compose.yaml down
```

3. To stop and remove all containers, networks, and volumes:
```bash
docker-compose -f docker-compose.yaml down -v
```

2. Run the user authentication script:
```bash
python user_auth.py
```

## Expected Behavior

1. **Admin User**:
   - Can create new users
   - Has access to view all experiments

2. **Regular Users**:
   - Can only view and modify their own experiments
   - Cannot access experiments created by other users

## Security Considerations

- Always change default admin credentials in production
- Use strong passwords for all users
- Consider implementing additional security measures like SSL/TLS for production deployments
- Regularly backup the authentication database

## Source Code

The complete source code for this example project is available on GitHub:
[mlflow-auth example project](https://github.com/neural-engineer/example-projects/tree/main/mlflow-auth)

## Conclusion


This setup provides a secure way to host MLflow with user authentication and experiment isolation. It's suitable for teams that need to maintain separate experiment tracking while having centralized administration.

For production deployments, consider:
- Using a more robust database backend
- Implementing proper backup strategies
- Setting up SSL/TLS encryption
- Implementing more sophisticated user management

## References

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Hosting MLflow with Authentication: A Step-by-Step Guide](https://medium.com/neural-engineer/hosting-mlflow-with-authentication-a-step-by-step-guide-5db351ddede0)