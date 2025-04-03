#  CrewAI Patterns: Conditional Tasks and Structured Outputs for Email Analysis

In this technical deep dive, we'll explore advanced patterns in CrewAI development using a real-world expense tracking system. We'll focus on three powerful features of crewAI : YAML-based configuration, conditional task execution, and structured outputs. Our example will demonstrate how to process ride-sharing expense emails using these patterns.

## Introduction

CrewAI is a powerful framework for orchestrating multiple AI agents to work together on complex tasks. While you can configure agents and tasks programmatically, using YAML files provides a more maintainable and scalable approach, especially for larger projects.

## Project Setup

To get started with a CrewAI project, use the CLI tool to create a boilerplate:

```bash
crewai create crew email-analyzer
```

It will create the project directory and the files 

```
API keys and model saved to .env file
Selected model: gpt-4o-mini
  - Created email_analyzer/.gitignore
  - Created email_analyzer/pyproject.toml
  - Created email_analyzer/README.md
  - Created email_analyzer/knowledge/user_preference.txt
  - Created email_analyzer/src/email_analyzer/__init__.py
  - Created email_analyzer/src/email_analyzer/main.py
  - Created email_analyzer/src/email_analyzer/crew.py
  - Created email_analyzer/src/email_analyzer/tools/email_tool.py
  - Created email_analyzer/src/email_analyzer/tools/__init__.py
  - Created email_analyzer/src/email_analyzer/config/agents.yaml
  - Created email_analyzer/src/email_analyzer/config/tasks.yaml
Crew email-analyzer created successfully!.
```

You can now start developing your crew by editing the files in the src/email-analyzer folder.

To customize your project, you can:
Modify src/email-analyzer/config/agents.yaml to define your agents.
Modify src/email-analyzer/config/tasks.yaml to define your tasks.
Modify src/email-analyzer/crew.py to add your own logic, tools, and specific arguments.
Modify src/email-analyzer/main.py to add custom inputs for your agents and tasks.
Add your environment variables into the .env file.

In this article we will create a email expense analysis system that will

1. Connect to Gmail using service account credentials
2. Fetch emails from the specified sender
3. Queue them for processing
4. Analyze each email for expense information
5. Store results in processed_emails.json

## Installation

The complete source for the files used in the project can be found at 

Ensure you have Python >=3.10 <3.13 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management and package handling, offering a seamless setup and execution experience.

First, if you haven't already, install uv . uv (short for "universal virtualenv") is a modern Python packaging tool designed to be a faster, more reliable alternative to pip

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# export the path 
source $HOME/.local/bin/env
# Create and activate virtual environment
uv venv v3
source v3/bin/activate

# Or if using pyproject.toml directly:
uv pip install .

```

## Environment Setup

Obtain the `OPENAI_API_KEY` key from openai website

```bash
OPENAI_API_KEY=your-openai-key
```

### Setting Up Google Credentials
To enable the email access your Gmail account, you need to set up a `credentials.json` file. Follow these steps:
outlined in the blog article https://medium.com/@pi_45757/gmail-api-integration-guide-a-comprehensive-guide-for-email-automation-8cc04b3ffc25 to setup and create a service account credentials files with domain wide delegation access 


### ENV File 

Create a `.env` file with required credentials:
```bash
OPENAI_API_KEY=your-openai-key
GMAIL_CREDENTIALS_FILE=path-to-service-account.json
USER_EMAIL=your-email@domain.com
```

Note: Keep your API key secure and never commit ENV file to version control.

## Running the Project

To kickstart your crew of AI agents and begin task execution, run this from the root folder of your project:

```bash
cd src
python -c "from email_analyzer.main import run; run()"
```

This command initializes the email-analyzer Crew, assembling the agents and assigning them tasks as defined in your configuration.


## Data-Driven Agent Configuration


The real power of CrewAI's data-driven approach comes from the YAML configuration files.  The project uses a YAML-based configuration approach for defining:
- Agent roles, goals, and backstories (`config/agents.yaml`)
- Task descriptions and execution parameters (`config/tasks.yaml`)


### Agent Configuration 

```yaml
# config/agents.yaml
expense_manager:
  role: "Expense Manager Agent"
  goal: >
    Review the subject of each email if it belongs to ola or uber, review the subject 
    and contents of the email to determine if it corresponds trip details including 
    date, payment mode, expense ammount
  backstory: >
    As an experienced expense management specialist, I have extensive expertise in 
    analyzing ride-sharing receipts and travel expenses. I'm trained to quickly 
    identify and extract key information from Uber and Ola emails, including trip 
    dates, payment details, and expense amounts. My background includes years of 
    working with corporate expense management systems and automated receipt 
    processing, making me highly efficient at categorizing and organizing 
    transportation-related expenses.

email_fetcher:
  role: "Email Retrieval Specialist"
  goal: >
    Efficiently retrieve and organize emails from Gmail inbox, ensuring all relevant 
    messages are properly queued for downstream processing.
  backstory: >
    I'm a specialized agent that securely connects to Gmail API, retrieves messages 
    and then adds to agent queue for async processing
```

The YAML configuration clearly defines each agent's role, goal, and backstory. This separation of concerns makes it easy to modify agent behaviors without changing the underlying implementation code.

### Task Configuration 

Here's our task configuration:

```yaml
# config/tasks.yaml
fetch_analysis_task:
  description: >
    Fetch emails from the user's Gmail account with email id {email},
    from email {fromemail} and add to email_queue table managed in
    the sqlite database. mark the task as success even if no emails are fetched 
  expected_output: >
    number of emails fetched . 
  agent: email_fetcher
  async_execution: true

fetch_and_process_email_task:
  description: >
    fetch the most recent emails from email_queue table
    managed in the sqlite database as defined by the queue name
    email_processor_expenseagent_queue and process the email 
  expected_output: >
    Processed email data from the database queue
  agent: email_fetcher
  async_execution: true
```

# Implementing Advanced CrewAI Features

The crewAI core implementation is done using the `@CrewBase` decorator:

```python
@CrewBase
class EmailAnalyzer():
    """EmailAnalyzer crew"""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
```


## 1. Structured Tasks Outputs Pydantic models

One of the key features in CrewAI is the ability to [enforce structured task outputs using Pydantic models ](https://docs.crewai.com/concepts/tasks#getting-structured-consistent-outputs-from-tasks). This ensures type safety and data validation throughout the Task's workflow:

Key advantages of structured outputs:
- Automatic validation of Task responses
- Clear documentation through type hints
- Easier integration with downstream systems
- Reduced error handling code

```python
from pydantic import BaseModel
from crewai.tasks.task_output import TaskOutput

# We use TOutput (defined in tools) to specify the structure
@task
def fetch_analysis_task(self) -> Task:
    return Task(
        config=self.tasks_config['fetch_analysis_task'],
        output_json=TOutput
    )
```



## 2. Conditional Task Execution

A powerful feature we're using is [conditional task execution](https://docs.crewai.com/how-to/conditional-tasks) to control the flow of our email analysis pipeline. This allows tasks to be executed only when certain conditions are met, improving efficiency and resource usage.


Here's how we implement conditional task execution:

1. Define a condition checker function:
```python
def check_data(self, output: TaskOutput) -> bool:
  try:
    c = output.json_dict
    return c["count"] > 0  # Only proceed if emails found
  except Exception as e:
    return False
```

2. Create a conditional task using the `ConditionalTask` class:
```python 
@task
def fetch_and_process_email_task(self) -> Task:
  return ConditionalTask(
    config=self.tasks_config['fetch_and_process_email_task'],
    condition=self.check_data,
  )
```

The task will only execute if check_data() returns True, preventing unnecessary processing when no new emails are found.


## 3. Agent Tools Integration and Structured Task Outputs

One of the powerful features of CrewAI is the ability to create custom tools. Our implementation includes specialized tools for email processing `email_tools.py`

```python
class EmailTools:
    @tool("Process emails from the expense agent queue")
    def fetch_and_process_email(queue: str) -> bool:
        """Processes all emails from the specified queue until queue is empty"""
        // ...implementation details...

    @tool("Fetch and queue unique emails from Gmail inbox")
    def fetch_and_queue_emails(email: str, from_email: str) -> TOutput:
        """Fetches emails from Gmail inbox and queues them for processing"""
        // ...implementation details...
```

These tools are integrated with our agents through the `@tool` decorator and provide structured input/output handling using Pydantic models:

```python
class TOutput(BaseModel):
    count: int
```


### Gmail Utils (`gmail_utils.py`) is used by Email Tools

We will be using the gmail api python library `https://github.com/pyVision/simplegmail.git`

To build and install the project run the below commands 

```bash
git clone https://github.com/pyVision/simplegmail.git
cd simplegmail
# Build the package
python setup.py build

# Install in development mode
uv pip install -e .

```

```python
@agent
def email_fetcher(self) -> Agent:
    return Agent(
        config=self.agents_config['email_fetcher'],
        tools=[
            EmailTools.fetch_and_queue_emails,
            EmailTools.fetch_and_process_email,
        ],
        llm=llm,
        allow_delegation=False,
        verbose=True,
        return_direct=False
    )
```


### fetch_and_queue_emails function
The `fetch_and_queue_emails` function manages the process of retrieving emails from Gmail and queueing them for processing. Here's how it works:

1. **Gmail Connection and Authentication**:
   - Uses service account credentials from the GMAIL_CREDENTIALS_FILE
   - Establishes connection with Gmail API using domain-wide delegation

2. **Query Construction and Filtering**:
   - Constructs a Gmail API query to filter emails by:
     - Specific sender(s) (e.g., noreply@uber.com)
     - Date range using checkpoints
   - Supports multiple sender filtering using OR conditions

3. **Email Processing Pipeline**:
   - Fetches emails matching the query criteria
   - Extracts key email components:
     - Subject, sender, receiver
     - HTML and plain text content
     - Thread ID and message ID
   - Cleans and normalizes content using BeautifulSoup
   - Implements deduplication using message IDs

4. **Caching and Queue Management**:
   - Maintains an SQLite cache of processed emails
   - Uses FIFO queuing system with counter-based ordering
   - Updates checkpoints for incremental processing
   - Returns structured output with count of new emails processed

### fetch_process_emails function:

The `fetch_process_emails` function handles the continuous processing of queued emails from the database. Here's a detailed breakdown:

1. **Queue Management**:
   - Retrieves emails from a specified queue (e.g., "email_processor_expenseagent_queue")
   - Implements FIFO (First-In-First-Out) processing order
   - Uses counter-based tracking for queue position

2. **Processing Pipeline**:
   - Extracts email data from the queue in JSON format
   - Processes one email at a time to ensure reliable handling
   - Removes processed emails from the queue automatically
   - Updates queue counters to maintain ordering

3. **Error Handling**:
   - Implements robust error handling for database operations
   - Manages queue state consistently even during failures
   - Returns None for both email_data and msg_id if queue is empty

4. **Database Operations**:
   - Uses SQLite for persistent queue storage
   - Maintains atomic operations for queue updates
   - Handles concurrent access safely



### 4. Sequential Process Flow

We set up our crew to process tasks sequentially, ensuring proper order of operations:

```python
@crew
def crew(self) -> Crew:
    return Crew(
        agents=self.agents,
        tasks=self.tasks,
        process=Process.sequential,
        verbose=True
    )
```

## Main Function

The main entry point of our application is configured in `main.py`. This file demonstrates how to set up and run the CrewAI workflow with specific inputs:

```python
def run():
    """
    Run the crew.
    """
    # Replace with your Google Workspace email ID in .env file
    email=os.getenv("USER_EMAIL")

    fromemail = "noreply@uber.com"
    inputs = {
        'email': email,
        'fromemail': fromemail
    }
    try:
        EmailAnalyzer().crew().kickoff(inputs=inputs)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"An error occurred while running the crew: {e}")
```

### Database Schema

The SQLite database uses three main tables:

1. **email_queue**: Stores emails in agent-specific queues
```sql
CREATE TABLE IF NOT EXISTS email_queue (
    queue_name TEXT,
    msg_id TEXT,
    counter INTEGER,
    email_data TEXT,
    PRIMARY KEY (queue_name, msg_id)
)
```

2. **emails**: Stores unique emails
```sql
CREATE TABLE IF NOT EXISTS emails (
    msg_id TEXT PRIMARY KEY,
    email_data TEXT
)
```

3. **counters**: Manages FIFO ordering
```sql
CREATE TABLE IF NOT EXISTS counters (
    counter_key TEXT PRIMARY KEY,
    counter_value INTEGER
)
```

4. **checkpoint** : the date from which mails should be fetched 
The implementation includes a checkpoint system to track email processing progress:
```sql
CREATE TABLE IF NOT EXISTS checkpoints (
    key TEXT PRIMARY KEY,
    value TEXT
)
```


## Performance Considerations

The implementation includes several performance optimizations:

1. **Caching**: Emails are cached in SQLite to prevent repeated API calls
2. **Batched Processing**: Emails are processed in configurable batch sizes
3. **Checkpoint System**: Prevents reprocessing of already handled emails
4. **FIFO Queue**: Ensures orderly processing of emails

## Running the System

To run the email analyzer system:

1. Set up environment variables:
```bash
export OPENAI_API_KEY="your-key"
export GMAIL_CREDENTIALS_FILE="path-to-credentials.json"
```

2. Run the main script:
```bash
python -m email_analyzer.main
```

## Summary and Key Takeaways

This implementation demonstrates several advanced CrewAI development patterns and architectural decisions . 
The patterns demonstrated here can be adapted for various other CrewAI applications requiring structured data processing and multi-agent coordination.

Future Enhancement Opportunities:
- Integration with additional expense email categories 
- Implementation of LLM based email filtering and processing capabilities
- Enhanced reporting with data visualization
- Machine learning-based expense categorization
- Automated accounting system integration

## Project Repository

The complete source code for this project is available at:
[GitHub - Email Expense Analyzer](https://github.com/yourusername/email-expense-analyzer)

## References

1. [CrewAI Documentation](https://docs.crewai.com/)
2. [Gmail API Python Reference](https://developers.google.com/gmail/api/quickstart/python)
3. [Pydantic Documentation](https://docs.pydantic.dev/)
4. [SQLite Best Practices](https://sqlite.org/bestpractices.html)
5. [Python AsyncIO Guide](https://docs.python.org/3/library/asyncio.html)
6. [OAuth 2 for Google APIs](https://developers.google.com/identity/protocols/oauth2)

