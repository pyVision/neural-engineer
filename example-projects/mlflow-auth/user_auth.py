# Import required libraries
from mlflow.server import get_app_client
import os 
from mlflow import MlflowClient
import uuid
import mlflow 
from mlflow.entities import ViewType

class User:
    # Constants for MLflow authentication environment variables
    MLFLOW_TRACKING_USERNAME = "MLFLOW_TRACKING_USERNAME"
    MLFLOW_TRACKING_PASSWORD = "MLFLOW_TRACKING_PASSWORD"

    def __init__(self, username, password) -> None:
        # Initialize user with credentials
        self.username = username
        self.password = password
        self.env = {}

    def _record_env_var(self, key):
        # Store existing environment variables
        if key := os.getenv(key):
            self.env[key] = key

    def _restore_env_var(self, key):
        # Restore previous environment variables
        if value := self.env.get(key):
            os.environ[key] = value
        else:
            del os.environ[key]

    def __enter__(self):
        # Context manager entry: Set MLflow authentication credentials
        print("entering user context")
        self._record_env_var(User.MLFLOW_TRACKING_USERNAME)
        self._record_env_var(User.MLFLOW_TRACKING_PASSWORD)
        os.environ[User.MLFLOW_TRACKING_USERNAME] = self.username
        os.environ[User.MLFLOW_TRACKING_PASSWORD] = self.password
        return self

    def __exit__(self, *_exc):
        # Context manager exit: Clean up environment variables
        self._restore_env_var(User.MLFLOW_TRACKING_USERNAME)
        self._restore_env_var(User.MLFLOW_TRACKING_PASSWORD)
        self.env.clear()


# Search experiments with different users
def list_experiments(user):
    with user:
        experiments = mlflow.search_experiments()
        print(f"\n{user.username}'s visible experiments:")
        for exp in experiments:
            print(f"- {exp.name}")


# Create admin user and set tracking URI
admin = User("admin", "admin")
tracking_uri = "http://localhost:7001/"

# Initialize MLflow client
client = MlflowClient(tracking_uri=tracking_uri)
mlflow.set_tracking_uri(uri=tracking_uri)

# Using admin context to create users
with admin:
    auth_client = get_app_client(
        "basic-auth", tracking_uri="http://localhost:7001/",
    )

    r = mlflow.search_experiments(ViewType.ALL)
    
    # Create test users with error handling
    for user_info in [("user1", "test123"), ("user2", "test123")]:
        username, password = user_info
        try:
            auth_client.create_user(username=username, password=password)
            print(f"Created user: {username}")
        except Exception as e:
            if "already exists" in str(e):
                print(f"User {username} already exists, skipping creation")
            else:
                print(f"Error creating user {username}: {str(e)}")

# Create user instances
user1 = User("user1", "test123")
user2 = User("user2", "test123")

# User1 context: Create and view experiments
with user1:

    exp_a = mlflow.set_experiment(experiment_name="user1_exp")


# User2 context: Create and view experiments
with user2:
    exp_b = mlflow.set_experiment(experiment_name="user2_exp")


# Show experiments visible to each user
list_experiments(user1)  # Should see only user1's experiments
list_experiments(user2)  # Should see only user2's experiments
list_experiments(admin)  # Should see all experiments

