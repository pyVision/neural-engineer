from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from langchain_community.chat_models import ChatOpenAI
import os 
from email_analyzer.tools.email_tools import EmailTools, TOutput

import os
from dotenv import load_dotenv
from crewai import Task,Process
from pydantic import BaseModel
from crewai.tasks.task_output import TaskOutput
from crewai.tasks.conditional_task import ConditionalTask
# Load environment variables
load_dotenv()
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"),
					model_name="gpt-4o-mini"
		)



@CrewBase
class EmailAnalyzer():
    """EmailAnalyzer crew"""

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools

    @agent
    def email_fetcher(self) -> Agent:
        return Agent(
            config=self.agents_config['email_fetcher'],
            tools=[EmailTools.fetch_and_queue_emails,
                   EmailTools.fetch_and_process_email,
                   ],
			llm=llm,
			allow_delegation=False,
			verbose=True,
			return_direct=False
        )


    def check_data(self,output: TaskOutput) -> bool:
        print("task output is ",output.agent,output.summary,output.json_dict,output.output_format,output.description)
        try:
            c=output.json_dict
            return c["count"] > 0  # this will skip this task
        except Exception as e:
            return False  # Return True if we can't parse the output


    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def fetch_analysis_task(self) -> Task:
        """Task to fetch and analyze emails
        
        This task is configured in tasks.yaml and typically includes:
        - Initial email fetching setup
        - Setting search criteria
        - Determining which emails to process
        """
        return Task(
            config=self.tasks_config['fetch_analysis_task'],
            output_json=TOutput
        )

    @task
    def fetch_and_process_email_task(self) -> Task:
        """Task to process individual emails
        
        This task is configured in tasks.yaml and typically includes:
        - Processing each email's content
        - Extracting relevant information
        - Performing analysis on email content
        - Generating reports or summaries
        
        Depends on fetch_analysis_task to be completed first to know
        which emails to process.
        """
        return ConditionalTask(
            config=self.tasks_config['fetch_and_process_email_task'],
            condition=self.check_data,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the EmailAnalyzer crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
