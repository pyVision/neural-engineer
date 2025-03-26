---
noteId: "24dd3650093111f087e069cc366e9361"
tags: ["crewai", "ai", "agents", "llm"]
title: "Understanding CrewAI: Building Multi-Agent AI Systems"
---

# Understanding CrewAI: Building Multi-Agent AI Systems

In the rapidly evolving landscape of AI development, CrewAI has emerged as a powerful framework for orchestrating multiple AI agents to work together on complex tasks. This framework enables developers to create collaborative AI systems that can tackle sophisticated problems through division of labor and specialized expertise. In this article, we'll explore the core concepts of CrewAI and how they fit together to create intelligent, collaborative systems.

## What is CrewAI?

CrewAI is an open-source framework designed to facilitate the creation of multi-agent AI systems. It allows developers to define specialized AI agents, assign them specific tasks, and orchestrate their collaboration to achieve complex goals. The framework is built on top of large language models (LLMs) and provides a structured approach to creating AI systems that can work together effectively.

## Core Components of CrewAI

The core components of CrewAI Are 
- Agents
- Tasks
- Tools
- Crew


### Agents

Agents are the fundamental building blocks of a CrewAI system. Each agent represents a specialized AI entity with:

- **Role**: Defines the agent's professional identity (e.g., "Data Analyst," "Marketing Specialist")
- **Goal**: Specifies what the agent aims to accomplish
- **Backstory**: Provides context and personality to guide the agent's behavior
- **Tools**: Equips the agent with specific capabilities to interact with external systems or data 

In this article we define an agent that is tasked with extraction storage and analysis of medium blog artlces . The agent is typically defined in the `agents.py` file . 

```python
# agents.py - Defines the Medium Blog Agent
import os
from textwrap import dedent
from crewai import Agent
from langchain_community.chat_models import ChatOpenAI
from tools import MediumTool

class MediumBlogAgent:
    def __init__(self):
        # Initialize the language model for the agent
        self.llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"),
                    model_name="gpt-4o-mini"
                    )

    def create_agent1(self):
        # Create a specialized agent for fetching and storing Medium blog content
        agent = Agent(
            role="Medium Blog Fetcher",
            goal="Extract the latest blog content from medium blogs and store contents in local database for processing",
            backstory="You are a specialized web scraper expert who efficiently extracts and organizes content from Medium blogs. You understand the structure of Medium's platform and can reliably collect and store article data for further analysis.",
            tools=[MediumTool.get_data, MediumTool.store_articles_in_db],
            llm=self.llm,
            verbose=True,
        )
        return agent
```

The LLM gives the agent its ability to understand tasks, make decisions, and generate responses. Different agents can use different models based on their needs - more complex roles might require more powerful models like GPT-4, while simpler tasks could use smaller, faster models.


## Tools 

Tools extend an agent's capabilities by allowing it to interact with external systems, APIs, databases, or perform specialized functions. 

In CrewAI, tools are Python functions decorated with the `@tool` decorator from LangChain. Each tool has a name, description, and implementation that defines what it does when invoked.

For our Medium Blog Agent, we've defined two essential tools defined in `neural-engineer/example-projects/crewai-medium/tools.py` file in the github repository `https://github.com/pyVision/neural-engineer.git` 
- Fetches articles and information from a Medium publication and saves it to temporary local file defined by the function `get_data`
- Load the medium article from the temporary local file and store  article information and content to SQLlite database defined by the function `store_articles_in_db`

## Tasks

Tasks are the actionable units of work in a CrewAI system. Tasks are specific assignments or instructions given to agents with defined success criteria. They define what an agent needs to accomplish and provide the necessary context

Each task includes:

- **Description**: A clear explanation of what needs to be accomplished
- **Expected Output**: The format or type of result the task should produce
- **Agent Assignment**: Which agent is responsible for completing the task
- **Context**: Additional information the agent needs to understand the task

Tasks can be sequential or parallel, depending on the workflow design.

For our Medium Blog system, we define 2 Tasks
1. **Fetch Medium Blog Content**: This task instructs the agent to retrieve content from a specified Medium publication. It provides the publication name as context and expects the agent to use its `get_data` tool to fetch the latest articles.

2. **Store Articles in Database**: This task directs the agent to process the fetched content and store it in a local SQLite database for further analysis. The agent uses its `store_articles_in_db` tool to accomplish this.

```python
class MediumBlogTasks:

    def task1(self,agent,publication_name):
        task1 = Task(
            description=dedent(f"""
                ONLY fetch the latest medium publication blog for publication name {publication_name} and save output to temporary file.
                DO NOT process or store this data in any database - that will be handled by a separate task.
                Your ONLY responsibility is to fetch the data and save it to a file, then return the file name.
            """),
            agent=agent,
            async_execution=False
        )
        return task1
    
    def task2(self,agent,publication_name):
        task2 = Task(
            description=dedent(f"""
                Using ONLY the file created in the previous task, load the contents of this temporary file 
                which contains content of rss feed for medium publication blog {publication_name}.
                Then store the articles metadata and content in sqlite database.
                Do not fetch any new data from Medium.
            """),
            agent=agent,
            #context=[tasks1],  # This explicitly provides the context from task1
            async_execution=False
        )
        return task2
```

When an agent is assigned a task, agent will use the LLM to reason and decide which of the tools listed in the `tools` argument to use based on the task requirements. The LLM understands the purpose of each tool through its description and can invoke the appropriate tool at the right time. 


### 4. Crew

A Crew is the orchestration layer that brings agents and tasks together. It manages the workflow, facilitates communication between agents, and ensures tasks are completed in the right order. The Crew:

- Assigns tasks to appropriate agents
- Manages the execution flow
- Handles delegation between agents
- Collects and processes the final outputs

Here's how we set up our Crew for the Medium Blog processing:

```python
from agents import MediumBlogAgent

agent = MediumBlogAgent().create_agent1()
t=MediumBlogTasks()
input={}
input['publication_name']="neural-engineer"
tasks1 = t.task1(agent,input['publication_name'])
tasks2 = t.task2(agent,input['publication_name'])

# Create the Crew
crew = Crew(
    agents=[agent],
    tasks=[tasks1,tasks2],
    verbose=2,
    process=Process.sequential  # Tasks will run in the defined order
)

print("🤖 Starting Medium Blog AI Assistant...")
result = crew.kickoff()
    
print("\n✅ Email Assistant Results:")
print(result)
```

When the crew is kicked off:
   - The system determines the execution order based on the process type
   - Each agent receives its assigned tasks
   - Agents use their LLM capabilities to understand tasks and plan approaches
   - Agents utilize their tools to gather information or perform actions
   - Results from completed tasks can be passed to subsequent tasks
   - The crew returns the final output after all tasks are completed

## Process Types in CrewAI

CrewAI supports different process types for task execution:

- **Sequential**: Tasks are executed in a predefined order, with outputs from earlier tasks feeding into later ones
- **Hierarchical**: A manager agent delegates tasks and coordinates the work of other agents
- **Parallel**: Multiple tasks can be executed simultaneously by different agents

In our example, we use the Sequential process since we need to first fetch the data before storing it.

Our Medium Blog example demonstrates a practical application for content aggregation and analysis, which could be extended to:
- Automatically summarize new articles
- Track trends in specific publications
- Generate reports on content performance
- Create personalized content recommendations

The full source file can be found in the subdirectory `neural-engineer/example-projects/crewai-medium/` in the github repository `https://github.com/pyVision/neural-engineer.git` 

## Conclusion

CrewAI represents a significant advancement in AI system design by enabling the creation of collaborative, multi-agent systems. By breaking down complex problems into specialized roles and tasks, CrewAI allows developers to build AI solutions that can tackle sophisticated challenges through coordinated effort.

The framework's modular design—with agents, tools, tasks, and crews—provides a flexible yet structured approach to creating AI systems that can reason, act, and collaborate effectively. As AI continues to evolve, frameworks like CrewAI will play an increasingly important role in developing intelligent systems that can work together to solve complex real-world problems.

Whether you're building a sophisticated research assistant, an automated analysis pipeline, or a creative content generation system, CrewAI offers a powerful paradigm for orchestrating AI agents to achieve results beyond what a single model could accomplish alone.


## REFERENCES
- https://docs.crewai.com/
- https://github.com/joaomdmoura/crewAI
- https://github.com/muhammad-usman-108/medium-article-py/blob/main/src/medium_article_py/medium.py